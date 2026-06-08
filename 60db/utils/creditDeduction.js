/**
 * Credit Deduction Utility
 *
 * Wallet operations against `users.amount`, with an audit trail in
 * `transaction_log`. Every mutation goes through a single atomic statement
 * so concurrent requests can never produce a lost-update race.
 *
 * Supports: TTS, STT, LLM (existing), and MEMORY_INGEST, MEMORY_EXTRACT,
 * MEMORY_RECALL, MEMORY_CONTEXT (new). Also supports refunds via
 * `refundCredits()`, which inserts a compensating row that references the
 * original transaction by hash_id.
 */

const db = require("../config/database");
const SERVICE_PRICES = require("../constants/servicePrices");

// Backward-compatible aliases (existing code still works)
const TTS_RATE_PER_CHAR = SERVICE_PRICES.TTS.RATE_PER_CHAR;
const STT_RATE_PER_SECOND = SERVICE_PRICES.STT.RATE_PER_SECOND;
const SIGNUP_BONUS_CREDITS = SERVICE_PRICES.SIGNUP_BONUS_CREDITS;
const MEMORY_RATES = SERVICE_PRICES.MEMORY;

// ─ Balance check ───────────────────────────────────────────
/**
 * Check whether a workspace has sufficient wallet balance. Read-only; never
 * mutates. Safe to use before a deduction to give an early 402 response.
 */
async function checkCredits(workspaceId, requiredAmount) {
  const result = await db.query(
    "SELECT amount FROM workspace WHERE id = $1 AND deleted_at IS NULL",
    [workspaceId]
  );
  if (result.rows.length === 0) {
    throw new Error("Workspace not found");
  }
  const currentBalance = parseFloat(result.rows[0].amount) || 0;
  return {
    sufficient: currentBalance >= requiredAmount,
    currentBalance,
    shortfall: Math.max(0, requiredAmount - currentBalance),
  };
}

// ─ Workspace billing owner lookup ──────────────────────────
/**
 * Return the user_id of the workspace owner who pays for operations in
 * this workspace. Matches the pattern in billingController.js — the
 * `workspace.billing_owner_id` column is authoritative.
 *
 * Cerbos enforces `billing:manage` as owner-only, so by charging this
 * user we guarantee the wallet belongs to someone who has billing
 * authority over the workspace.
 */
async function getBillingOwnerId(workspaceId) {
  const { rows } = await db.query(
    `SELECT billing_owner_id FROM workspace
     WHERE id = $1 AND deleted_at IS NULL`,
    [workspaceId]
  );
  if (rows.length === 0) {
    const err = new Error("Workspace not found");
    err.statusCode = 404;
    err.code = "WORKSPACE_NOT_FOUND";
    throw err;
  }
  const ownerId = rows[0].billing_owner_id;
  if (!ownerId) {
    const err = new Error("Workspace has no billing owner configured");
    err.statusCode = 500;
    err.code = "NO_BILLING_OWNER";
    throw err;
  }
  return ownerId;
}

// ─ Atomic deduct ───────────────────────────────────────────
/**
 * Deduct `amountDeducted` from the workspace wallet and log the transaction.
 *
 * Race-free: the balance check and the write happen in a single SQL
 * statement. Two concurrent requests cannot double-spend because Postgres
 * applies the `amount >= $1` predicate and the `SET amount = amount - $1`
 * update as an atomic row-level operation.
 *
 * Workspace-level billing: deducts from `workspace.amount` (not users.amount).
 * The `billingOwnerId` is still resolved and stored in the audit log for
 * accountability, but the wallet lives on the workspace now.
 *
 * @returns {Promise<{previousBalance, newBalance, transactionHashId, transactionId}>}
 * @throws {Error} with code "INSUFFICIENT_CREDITS" and statusCode 402 if
 *                 the workspace wallet can't cover the charge.
 */
async function deductCredits({
  userId,                   // the authenticated user making the request
  serviceType,              // 'TTS' | 'STT' | 'LLM' | 'MEMORY_INGEST' | ...
  amountDeducted,           // USD, must be > 0
  unitsUsed = 0,            // chars / seconds / tokens / bytes
  workspaceId = null,       // workspace to charge (required)
  billingOwnerId = null,    // workspace owner (for audit trail)
  metadata = {},            // per-operation details (chunk counts, memory IDs…)
  client = null,            // existing pg client to run inside caller's tx;
                            // when null, opens a private connection + tx
}) {
  if (!(amountDeducted >= 0)) {
    throw new Error(`deductCredits: amountDeducted must be >= 0, got ${amountDeducted}`);
  }

  if (!workspaceId) {
    throw new Error("deductCredits: workspaceId is required for workspace-level billing");
  }

  if (!billingOwnerId) {
    billingOwnerId = await getBillingOwnerId(workspaceId);
  }

  const args = {
    userId, serviceType, amountDeducted, unitsUsed,
    workspaceId, billingOwnerId, metadata,
  };

  // Caller-managed transaction: don't BEGIN/COMMIT/ROLLBACK here. Any throw
  // bubbles up so the caller's catch can ROLLBACK, which atomically unwinds
  // the wallet UPDATE alongside the caller's other writes.
  if (client) {
    return _runDeduct(client, args);
  }

  const ownClient = await db.pool.connect();
  try {
    await ownClient.query("BEGIN");
    const result = await _runDeduct(ownClient, args);
    await ownClient.query("COMMIT");
    return result;
  } catch (err) {
    try { await ownClient.query("ROLLBACK"); } catch (_) {}
    throw err;
  } finally {
    ownClient.release();
  }
}

async function _runDeduct(client, {
  userId, serviceType, amountDeducted, unitsUsed,
  workspaceId, billingOwnerId, metadata,
}) {
  const updateResult = await client.query(
    `UPDATE workspace
     SET    amount = amount - $1
     WHERE  id = $2
       AND  amount >= $1
       AND  deleted_at IS NULL
     RETURNING amount AS new_balance,
               amount + $1 AS previous_balance`,
    [amountDeducted, workspaceId]
  );

  if (updateResult.rowCount === 0) {
    const check = await client.query(
      "SELECT amount FROM workspace WHERE id = $1 AND deleted_at IS NULL",
      [workspaceId]
    );
    if (check.rows.length === 0) {
      const err = new Error("Workspace not found");
      err.statusCode = 404;
      err.code = "WORKSPACE_NOT_FOUND";
      throw err;
    }
    const current = parseFloat(check.rows[0].amount) || 0;
    const err = new Error("Insufficient credits");
    err.statusCode = 402;
    err.code = "INSUFFICIENT_CREDITS";
    err.details = {
      required: parseFloat(amountDeducted.toFixed(6)),
      available: parseFloat(current.toFixed(6)),
      shortfall: parseFloat((amountDeducted - current).toFixed(6)),
    };
    throw err;
  }

  const previousBalance = parseFloat(updateResult.rows[0].previous_balance);
  const newBalance = parseFloat(updateResult.rows[0].new_balance);

  const txResult = await client.query(
    `INSERT INTO transaction_log
       (user_id, workspace_billing_owner_id, workspace_id, service_type,
        amount_deducted, units_used, previous_balance, new_balance, metadata)
     VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
     RETURNING id, hash_id`,
    [
      userId,
      billingOwnerId,
      workspaceId,
      serviceType,
      amountDeducted,
      unitsUsed,
      previousBalance,
      newBalance,
      JSON.stringify(metadata || {}),
    ]
  );

  return {
    previousBalance,
    newBalance,
    transactionId: txResult.rows[0].id,
    transactionHashId: txResult.rows[0].hash_id,
  };
}

// ─ Atomic refund ───────────────────────────────────────────
/**
 * Refund a previously-deducted charge. Idempotent: if a refund already
 * exists for the given `originalTxHashId`, this is a no-op.
 *
 * Inserts a compensating row (`amount_deducted` = negative of the
 * original) linked via `reference_hash_id`, and atomically adds the
 * amount back to the wallet of whoever was originally charged.
 */
async function refundCredits({
  originalTxHashId,
  reason = "unknown",
  metadata = {},
}) {
  if (!originalTxHashId) {
    throw new Error("refundCredits: originalTxHashId is required");
  }

  const client = await db.pool.connect();
  try {
    await client.query("BEGIN");

    // Look up the original row and lock it so concurrent refunds can't
    // double-refund. Also check if it already has a refund.
    const { rows: origRows } = await client.query(
      `SELECT id, workspace_billing_owner_id, user_id, workspace_id,
              service_type, amount_deducted, units_used, metadata
       FROM   transaction_log
       WHERE  hash_id = $1 AND deleted_at IS NULL
       FOR UPDATE`,
      [originalTxHashId]
    );
    if (origRows.length === 0) {
      await client.query("ROLLBACK");
      return { refunded: false, reason: "original_not_found" };
    }
    const orig = origRows[0];

    // Idempotent: already refunded?
    const { rows: existing } = await client.query(
      `SELECT hash_id FROM transaction_log
       WHERE  reference_hash_id = $1 AND amount_deducted < 0 AND deleted_at IS NULL
       LIMIT  1`,
      [originalTxHashId]
    );
    if (existing.length > 0) {
      await client.query("ROLLBACK");
      return {
        refunded: false,
        reason: "already_refunded",
        refundHashId: existing[0].hash_id,
      };
    }

    const amount = parseFloat(orig.amount_deducted);
    if (amount <= 0) {
      // Nothing to refund (was free) or the original was itself a refund.
      await client.query("ROLLBACK");
      return { refunded: false, reason: "nothing_to_refund" };
    }

    // Refund to the workspace wallet that was originally charged.
    const refundWorkspaceId = orig.workspace_id;
    const walletUserId = orig.workspace_billing_owner_id || orig.user_id;
    const updateResult = await client.query(
      `UPDATE workspace
       SET    amount = amount + $1
       WHERE  id = $2 AND deleted_at IS NULL
       RETURNING amount AS new_balance,
                 amount - $1 AS previous_balance`,
      [amount, refundWorkspaceId]
    );
    if (updateResult.rowCount === 0) {
      // Workspace was deleted between deduction and refund. Log the refund
      // against null wallet state — the finance team can reconcile later.
      await client.query(
        `INSERT INTO transaction_log
           (user_id, workspace_billing_owner_id, workspace_id, service_type,
            amount_deducted, units_used, previous_balance, new_balance,
            reference_hash_id, metadata)
         VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)`,
        [
          orig.user_id, walletUserId, refundWorkspaceId,
          `${orig.service_type}_REFUND`,
          -amount, orig.units_used, 0, 0,
          originalTxHashId,
          JSON.stringify({ ...metadata, reason, ghost: true }),
        ]
      );
      await client.query("COMMIT");
      return { refunded: true, ghost: true, reason };
    }

    const previousBalance = parseFloat(updateResult.rows[0].previous_balance);
    const newBalance = parseFloat(updateResult.rows[0].new_balance);

    const refundInsert = await client.query(
      `INSERT INTO transaction_log
         (user_id, workspace_billing_owner_id, workspace_id, service_type,
          amount_deducted, units_used, previous_balance, new_balance,
          reference_hash_id, metadata)
       VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
       RETURNING hash_id`,
      [
        orig.user_id, walletUserId, refundWorkspaceId,
        `${orig.service_type}_REFUND`,
        -amount, orig.units_used, previousBalance, newBalance,
        originalTxHashId,
        JSON.stringify({ ...metadata, reason }),
      ]
    );

    await client.query("COMMIT");
    return {
      refunded: true,
      amount,
      previousBalance,
      newBalance,
      refundHashId: refundInsert.rows[0].hash_id,
    };
  } catch (err) {
    try { await client.query("ROLLBACK"); } catch (_) {}
    throw err;
  } finally {
    client.release();
  }
}

// ─ Cost calculators ────────────────────────────────────────
function calculateTTSCost(characterCount) {
  return characterCount * TTS_RATE_PER_CHAR;
}

function calculateSTTCost(durationSeconds) {
  return durationSeconds * STT_RATE_PER_SECOND;
}

/**
 * Calculate the pre-charge cost for a memory operation.
 *
 * @param {object} op
 * @param {"ingest"|"extract"|"recall"|"context"} op.operation
 * @param {number} [op.chars]   - total characters (ingest / extract)
 * @param {number} [op.bytes]   - file size in bytes (extract)
 * @param {number} [op.queries] - number of queries (recall / context)
 * @returns {number} USD
 */
function calculateMemoryCost({ operation, chars = 0, bytes = 0, queries = 1 }) {
  switch (operation) {
    case "ingest": {
      // Per-1k-char rate
      return (chars / 1000) * MEMORY_RATES.INGEST_PER_1K_CHARS;
    }
    case "extract": {
      // Per-MB for extraction + per-1k-char for the downstream ingest.
      // Note: at pre-charge time we often don't know the post-extraction
      // char count, so we bill only the extract fee here and charge the
      // ingest portion after extraction via a second deduction OR rely
      // on the middleware to estimate chars = bytes/2 as a worst case.
      const mb = bytes / (1024 * 1024);
      return mb * MEMORY_RATES.EXTRACT_PER_MB;
    }
    case "recall": {
      return queries * MEMORY_RATES.RECALL_PER_QUERY;
    }
    case "context": {
      return queries * MEMORY_RATES.CONTEXT_PER_QUERY;
    }
    default:
      throw new Error(`calculateMemoryCost: unknown operation "${operation}"`);
  }
}

// ─ Error response helper ───────────────────────────────────
function insufficientCreditsResponse(res, required, available, shortfall) {
  return res.status(402).json({
    success: false,
    message: "Your credit balance is low. Please top up to continue using services.",
    error_code: "INSUFFICIENT_CREDITS",
    details: {
      required: parseFloat(required.toFixed(6)),
      available: parseFloat(available.toFixed(6)),
      shortfall: parseFloat(shortfall.toFixed(6)),
    },
  });
}

module.exports = {
  // Centralized pricing
  SERVICE_PRICES,

  // Backward-compatible aliases
  TTS_RATE_PER_CHAR,
  STT_RATE_PER_SECOND,
  SIGNUP_BONUS_CREDITS,
  MEMORY_RATES,

  // Balance ops
  checkCredits,
  deductCredits,
  refundCredits,
  getBillingOwnerId,

  // Cost calculators
  calculateTTSCost,
  calculateSTTCost,
  calculateMemoryCost,

  // Error helper
  insufficientCreditsResponse,
};
