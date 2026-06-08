// TTS status poller — drives jobs through provider states without webhooks.
//
// Cadence per D28: 7s (first 2m) → 15s (2–10m) → 30s (10–60m) → 60s (1h+).
// One entry per voice. Multiple API instances are safe because the poll
// handler CAS-updates state with unique constraint on voice_job_events.

const db = require("../config/database");
const ttsClient = require("./ttsProfessionalClient");
const { notifyStatusChange } = require("./cloneJobNotifications");

const STATE = new Map(); // voice_id -> { timer, startedAt }
const JITTER_MS = 1500;

function intervalForAge(ageMs) {
  if (ageMs < 2 * 60_000) return 7_000;
  if (ageMs < 10 * 60_000) return 15_000;
  if (ageMs < 60 * 60_000) return 30_000;
  return 60_000;
}

function withJitter(baseMs) {
  return baseMs + Math.floor((Math.random() * 2 - 1) * JITTER_MS);
}

async function advanceStatus(voiceId, client, newStatus, providerStatus, providerUpdatedAt, extra = {}) {
  // Idempotent — only transition if the target status differs
  const fromRes = await client.query(
    `SELECT status, version FROM voice_clone_jobs WHERE id = $1 FOR UPDATE`,
    [voiceId]
  );
  if (fromRes.rows.length === 0) return false;
  const from = fromRes.rows[0].status;
  const ver = fromRes.rows[0].version;

  if (from !== newStatus) {
    await client.query(
      `UPDATE voice_clone_jobs SET
         status = $2,
         tts_provider_status = $3,
         version = version + 1,
         updated_at = NOW()
       WHERE id = $1 AND status = $4 AND version = $5`,
      [voiceId, newStatus, providerStatus, from, ver]
    );
  } else if (providerStatus && providerStatus !== fromRes.rows[0].tts_provider_status) {
    await client.query(
      `UPDATE voice_clone_jobs SET tts_provider_status = $2, updated_at = NOW()
       WHERE id = $1`,
      [voiceId, providerStatus]
    );
  }

  // Always record an event if provider_updated_at changes or state transitions
  try {
    await client.query(
      `INSERT INTO voice_job_events
         (clone_job_id, event_type, from_status, to_status, provider_status, provider_updated_at, payload)
       VALUES ($1, 'poll', $2, $3, $4, $5, $6)
       ON CONFLICT (clone_job_id, provider_status, provider_updated_at)
       WHERE provider_status IS NOT NULL AND provider_updated_at IS NOT NULL
       DO NOTHING`,
      [voiceId, from, newStatus, providerStatus, providerUpdatedAt, extra]
    );
  } catch {
    // Unique violation fallback — already recorded, safe to ignore
  }
  return from !== newStatus;
}

// On training completion, create a `voices` row linked back to the clone job
// so the creator can synthesize with their voice immediately (privately).
// If a row already exists (e.g., the poller retried after a partial commit),
// this is a no-op via the (clone_job_id) idempotency check.
async function publishPrivateVoice(client, cloneJobId) {
  // Idempotency: skip if already published
  const existing = await client.query(
    `SELECT id FROM voices WHERE clone_job_id = $1 LIMIT 1`,
    [cloneJobId]
  );
  if (existing.rows.length > 0) return existing.rows[0].id;

  const jobRes = await client.query(
    `SELECT id, creator_user_id, workspace_id, name, description, method,
            languages, tts_voice_id
     FROM voice_clone_jobs WHERE id = $1`,
    [cloneJobId]
  );
  if (jobRes.rows.length === 0) return null;
  const job = jobRes.rows[0];
  const jobLanguages =
    Array.isArray(job.languages) && job.languages.length > 0
      ? job.languages
      : ["en"];

  const inserted = await client.query(
    `INSERT INTO voices (
       workspace_id, user_id, name, description,
       language, provider, voice_id,
       is_public, quality_checked, clone_job_id, metadata
     ) VALUES ($1, $2, $3, $4, $5, 'qcall_professional', $6, FALSE, FALSE, $7, $8)
     RETURNING id`,
    [
      job.workspace_id,
      job.creator_user_id,
      job.name,
      job.description,
      jobLanguages[0],
      job.tts_voice_id,
      job.id,
      {
        // tts.voice_id is read by voiceController.getMyVoices to match this
        // local row against the TTS provider's /v1/voices listing. Without
        // this nesting the voice appears in the marketplace (Default Voices)
        // instead of the creator's My Voices tab.
        tts: { voice_id: job.tts_voice_id },
        clone_job_id: job.id,
        method: job.method,
        languages: jobLanguages,
        private_until_sa_approval: true,
      },
    ]
  );
  const publishedVoiceId = inserted.rows[0].id;
  await client.query(
    `UPDATE voice_clone_jobs SET published_voice_id = $2 WHERE id = $1`,
    [cloneJobId, publishedVoiceId]
  );
  return publishedVoiceId;
}

async function releaseSingletonIfHeld(client, voiceId) {
  await client.query(
    `UPDATE voice_training_slot SET
       clone_job_id = NULL, held_by = NULL, held_until = NULL, heartbeat_at = NULL,
       updated_at = NOW()
     WHERE id = 1 AND clone_job_id = $1`,
    [voiceId]
  );
}

async function pollOnce(voiceId) {
  const client = await db.pool.connect();
  try {
    const jobRes = await client.query(
      `SELECT id, tts_voice_id, status FROM voice_clone_jobs WHERE id = $1`,
      [voiceId]
    );
    if (jobRes.rows.length === 0) {
      deregister(voiceId);
      return;
    }
    const job = jobRes.rows[0];
    if (!job.tts_voice_id) {
      // Not submitted yet — stop polling; worker will register once submitted
      deregister(voiceId);
      return;
    }
    if (!["transcribing", "embedding", "training"].includes(job.status)) {
      deregister(voiceId);
      return;
    }

    // Per-voice advisory lock so only one instance polls this voice at a time
    const lockKeyA = Math.floor(Math.abs(hashString(voiceId)) / 2);
    const lockKeyB = Math.floor(Math.abs(hashString("tts_poll:" + voiceId)) / 2);
    const lockRes = await client.query(
      `SELECT pg_try_advisory_xact_lock($1, $2) AS ok`,
      [lockKeyA, lockKeyB]
    );
    if (!lockRes.rows[0].ok) return; // another instance has it this tick

    let providerData;
    try {
      providerData = await ttsClient.getVoiceStatus(job.tts_voice_id);
    } catch (e) {
      await client.query(
        `UPDATE voice_clone_jobs SET
           last_polled_at = NOW(),
           poll_attempt_count = poll_attempt_count + 1
         WHERE id = $1`,
        [voiceId]
      );
      if (e.statusCode === 404) {
        await client.query("BEGIN");
        await advanceStatus(voiceId, client, "failed", null, null, {
          reason: "provider_voice_missing",
        });
        await releaseSingletonIfHeld(client, voiceId);
        await client.query("COMMIT");
        deregister(voiceId);
        return;
      }
      // 5xx and other retryable — just wait for next tick
      return;
    }

    await client.query("BEGIN");
    await client.query(
      `UPDATE voice_clone_jobs SET
         last_polled_at = NOW(),
         poll_attempt_count = poll_attempt_count + 1
       WHERE id = $1`,
      [voiceId]
    );

    if (providerData.status === "complete") {
      await advanceStatus(voiceId, client, "awaiting_approval", providerData.status, providerData.provider_updated_at);
      // Publish a private voices row so the creator can synthesize with
      // their newly-trained voice immediately (is_public=false), and so SA
      // has a real voice row to test against when reviewing. Marketplace
      // visibility (is_public=true, quality_checked=true) is flipped on
      // by saVoiceApprovalController.approve.
      await publishPrivateVoice(client, voiceId);
      await releaseSingletonIfHeld(client, voiceId);
      await client.query("COMMIT");
      notifyStatusChange({ cloneJobId: voiceId, toStatus: "awaiting_approval" });
      deregister(voiceId);
    } else if (providerData.status === "failed") {
      await advanceStatus(voiceId, client, "failed", providerData.status, providerData.provider_updated_at, {
        reason: providerData.failure_reason,
      });
      await releaseSingletonIfHeld(client, voiceId);
      await client.query("COMMIT");
      notifyStatusChange({
        cloneJobId: voiceId,
        toStatus: "failed",
        context: { failureReason: providerData.failure_reason },
      });
      deregister(voiceId);
    } else {
      // Still in-flight — just record provider status if changed
      await advanceStatus(voiceId, client, providerData.status, providerData.status, providerData.provider_updated_at);
      await client.query("COMMIT");
    }
  } catch (err) {
    try {
      await client.query("ROLLBACK");
    } catch {
      /* noop */
    }
    console.error("ttsPoller.pollOnce error for", voiceId, err);
  } finally {
    client.release();
  }
}

function hashString(s) {
  let h = 0;
  for (let i = 0; i < s.length; i++) h = (h * 31 + s.charCodeAt(i)) | 0;
  return h;
}

function schedule(voiceId, startedAt) {
  const ageMs = Date.now() - startedAt.getTime();
  const delay = withJitter(intervalForAge(ageMs));
  const timer = setTimeout(async () => {
    await pollOnce(voiceId);
    if (STATE.has(voiceId)) schedule(voiceId, startedAt);
  }, delay);
  STATE.set(voiceId, { timer, startedAt });
}

function register(voiceId, startedAt) {
  if (STATE.has(voiceId)) return;
  schedule(voiceId, startedAt);
}

function deregister(voiceId) {
  const entry = STATE.get(voiceId);
  if (entry?.timer) clearTimeout(entry.timer);
  STATE.delete(voiceId);
}

/**
 * On boot, restart polling for any in-flight voices.
 * Called from server.js after DB connection is ready.
 */
async function rehydrate() {
  try {
    const res = await db.pool.query(
      `SELECT id, updated_at FROM voice_clone_jobs
       WHERE status IN ('transcribing', 'embedding', 'training')
         AND tts_voice_id IS NOT NULL
         AND deleted_at IS NULL`
    );
    for (const row of res.rows) {
      register(row.id, new Date(row.updated_at));
    }
    if (res.rows.length > 0) {
      console.log(`🔁 TTS poller rehydrated ${res.rows.length} in-flight voice(s)`);
    }
  } catch (err) {
    console.error("ttsPoller.rehydrate failed:", err);
  }
}

module.exports = { register, deregister, rehydrate, pollOnce };
