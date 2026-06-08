/**
 * Concurrency Limiter
 *
 * In-memory per-user concurrency cap for STT and TTS, counting REST and
 * WebSocket sessions together. Caps in-flight requests, not throughput
 * (RPS rate limit is a separate concern — see design/rps-rate-limit.md).
 *
 * Storage: Map<userId, count> per kind. Single-process today; the
 * `acquire`/`release` interface lets a Redis backend slot in later
 * without changes to controllers or WS handlers.
 */

// Upstream STT now caps total concurrent backend dispatches at 24
// (4 workers × 6 GPU sem). With a per-user limit of 8, three saturated
// users hit exactly that ceiling; pushing higher just gets us 429s and
// upstream queue contention. Bump via env once upstream adds workers.
const STT_CONCURRENCY_LIMIT = parseInt(process.env.STT_CONCURRENCY_LIMIT, 10) || 8;
const TTS_CONCURRENCY_LIMIT = parseInt(process.env.TTS_CONCURRENCY_LIMIT, 10) || 5;

const limits = {
  stt: STT_CONCURRENCY_LIMIT,
  tts: TTS_CONCURRENCY_LIMIT,
};

const counts = {
  stt: new Map(),
  tts: new Map(),
};

function getCount(kind, userId) {
  return counts[kind].get(userId) || 0;
}

function setCount(kind, userId, n) {
  if (n <= 0) counts[kind].delete(userId);
  else counts[kind].set(userId, n);
}

/**
 * Try to acquire a slot. Returns a single-shot release function on success,
 * or `null` if the user is at the cap. The release fn is idempotent.
 */
function tryAcquire(kind, userId) {
  if (!counts[kind]) {
    throw new Error(`concurrencyLimiter: unknown kind "${kind}"`);
  }
  if (!userId) {
    throw new Error("concurrencyLimiter: userId is required");
  }
  const limit = limits[kind];
  const current = getCount(kind, userId);
  if (current >= limit) return null;
  setCount(kind, userId, current + 1);

  let released = false;
  return function release() {
    if (released) return;
    released = true;
    setCount(kind, userId, getCount(kind, userId) - 1);
  };
}

/**
 * Express middleware factory. Acquires a slot before forwarding to the
 * controller, releases on `finish` or `close` (covers normal completion
 * and client aborts). Must be mounted AFTER `authenticateToken` so
 * `req.user.id` is populated.
 */
function concurrencyLimit(kind) {
  return function concurrencyLimitMiddleware(req, res, next) {
    const userId = req.user && req.user.id;
    if (!userId) {
      return res.status(401).json({
        success: false,
        message: "Authentication required",
        error_code: "UNAUTHENTICATED",
      });
    }

    const release = tryAcquire(kind, userId);
    if (!release) {
      return res.status(429).json({
        success: false,
        message: `Too many concurrent ${kind.toUpperCase()} requests for this user`,
        error_code: `${kind.toUpperCase()}_CONCURRENCY_LIMIT`,
        details: {
          limit: limits[kind],
          retry_hint: "Wait for an in-flight request to complete",
        },
      });
    }

    let releasedFlag = false;
    function safeRelease() {
      if (releasedFlag) return;
      releasedFlag = true;
      release();
    }

    res.once("finish", safeRelease);
    res.once("close", safeRelease);
    next();
  };
}

module.exports = {
  concurrencyLimit,
  tryAcquire,
  limits,
  _getCount: getCount,
};
