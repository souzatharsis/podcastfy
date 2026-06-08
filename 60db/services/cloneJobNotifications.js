/**
 * Sends status-change emails for Professional Voice Cloning jobs.
 *
 * Called from every code path that transitions a clone job's status
 * (finalize → queued, worker → transcribing/embedding/training, poller →
 * awaiting_approval/failed, SA → approved/rejected). Best-effort: email
 * failures must NEVER break the DB transaction or the status transition.
 *
 * De-dup: the same (clone_job_id, to_status) is only emailed once by
 * recording a row in `voice_clone_job_emails`. If the table doesn't exist
 * yet (first deploy) we just try-catch and continue.
 */

const db = require("../config/database");
const { sendMail } = require("../utils/sendEmail");
const {
  cloneJobStatusEmail,
  subjectFor,
} = require("../templates/clone-job-status-temp");

const APP_URL = (
  process.env.APP_URL || process.env.PUBLIC_APP_URL || "https://app.60db.ai"
).replace(/\/+$/, "");

// Statuses that warrant an email to the creator. `draft` and `pending_verify`
// are purely internal; `unpublished` is covered by the takedown path.
const NOTIFY_STATUSES = new Set([
  "queued",
  "transcribing",
  "embedding",
  "training",
  "awaiting_approval",
  "approved",
  "rejected",
  "failed",
]);

async function notifyStatusChange({
  cloneJobId,
  toStatus,
  context = {},
}) {
  if (!NOTIFY_STATUSES.has(toStatus)) return;

  try {
    // Load job + creator email in one query.
    const r = await db.pool.query(
      `SELECT j.name, j.description, j.rejection_reason_text,
              u.email, u.full_name
       FROM voice_clone_jobs j
       JOIN users u ON u.id = j.creator_user_id
       WHERE j.id = $1`,
      [cloneJobId]
    );
    if (r.rows.length === 0) return;
    const row = r.rows[0];
    if (!row.email) return;

    // De-dup: if we've already emailed this status for this job, skip.
    // Safe to ignore errors — worst case we send a duplicate, which is
    // noisy but not wrong.
    try {
      const dup = await db.pool.query(
        `SELECT 1 FROM voice_clone_job_emails
         WHERE clone_job_id = $1 AND to_status = $2 LIMIT 1`,
        [cloneJobId, toStatus]
      );
      if (dup.rows.length > 0) return;
    } catch (_noTable) {
      /* table may not exist on first deploy — fall through */
    }

    const html = cloneJobStatusEmail({
      userName: row.full_name || (row.email.split("@")[0] || ""),
      voiceName: row.name,
      status: toStatus,
      appUrl: APP_URL,
      rejectionReason: context.rejectionReason || row.rejection_reason_text,
      failureReason: context.failureReason,
    });
    const subject = subjectFor(toStatus, row.name);

    await sendMail(row.email, html, subject);

    // Record the send so we don't send duplicates on retries.
    try {
      await db.pool.query(
        `INSERT INTO voice_clone_job_emails
           (clone_job_id, to_status, recipient_email, sent_at)
         VALUES ($1, $2, $3, NOW())
         ON CONFLICT (clone_job_id, to_status) DO NOTHING`,
        [cloneJobId, toStatus, row.email]
      );
    } catch (_noTable) {
      /* table missing — non-fatal */
    }
  } catch (err) {
    // Swallow ALL errors. The worker/poller/SA flow must not fail because
    // email delivery hiccupped.
    console.error("cloneJobNotifications.notifyStatusChange failed:", {
      cloneJobId,
      toStatus,
      message: err?.message,
    });
  }
}

module.exports = { notifyStatusChange };
