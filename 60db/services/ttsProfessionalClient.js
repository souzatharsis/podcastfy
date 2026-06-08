// Thin HTTP client for tts.qcall.ai's professional cloning endpoints.
//
// ⚠️ Contract assumptions — confirm with TTS team before production:
//   POST /v1/voices/professional     body: { name, audio_urls[], metadata? }
//                                    response: { voice_id, status }
//   GET  /v1/voices/professional/:id response: { voice_id, status, provider_updated_at, failure_reason? }
//
// Provider status values we map:
//   'transcribing' | 'embedding' | 'training' | 'complete' | 'failed'
//
// When the real API differs, adjust `buildSubmitBody`, `mapProviderStatus`,
// and the status endpoint URL. No other code in worker/poller needs to change.

const axios = require("axios");
const fs = require("fs");
const path = require("path");
const FormData = require("form-data");

const TTS_BASE_URL = (
  process.env.TTS_PROFESSIONAL_BASE_URL || "https://tts.qcall.ai"
).replace(/\/+$/, "");
const TTS_API_KEY = process.env.TTS_PROFESSIONAL_API_KEY || "";

function buildHeaders(extra = {}) {
  const headers = { ...extra };
  if (TTS_API_KEY) headers["Authorization"] = `Bearer ${TTS_API_KEY}`;
  return headers;
}

function buildJsonHeaders() {
  return buildHeaders({ "Content-Type": "application/json" });
}

// Map provider status string → our app state. Unknown values stay as "training".
// tts.qcall.ai's /v1/voices/{id}/train/status returns `state` values like
// "queued", "running", "completed", "failed". The `phase` field gives a more
// granular description (loading_model, embedding, training, etc.) which we
// pass through as provider_status for observability.
function mapProviderStatus(raw) {
  const s = (raw || "").toString().toLowerCase();
  if (["transcribing", "embedding"].includes(s)) return s;
  if (["running", "training", "in_progress", "processing"].includes(s))
    return "training";
  if (["complete", "completed", "succeeded", "ready", "done"].includes(s))
    return "complete";
  if (["failed", "error", "rejected", "cancelled", "canceled"].includes(s))
    return "failed";
  // "queued" or any unknown → assume still in flight
  return "training";
}

/**
 * Submit a voice for training. tts.qcall.ai's
 * `POST /v1/voices/professional` expects **multipart/form-data** with the
 * actual audio bytes under the `audio_files` field, plus `name`, `language`,
 * and optional gender/accent/languages.
 *
 * @param {object} payload
 * @param {string} payload.name
 * @param {string[]} payload.audio_file_paths  - Absolute paths on disk
 * @param {string} [payload.language]          - Primary language code (required; default 'en')
 * @param {string[]} [payload.languages]       - Additional codes for code-mixed speech
 * @param {string} [payload.gender]            - male | female | nonbinary | unspecified
 * @param {string} [payload.accent]            - free-form accent descriptor
 * @param {string} [payload.description]
 * @returns {Promise<{voice_id: string, status: string, raw: any}>}
 */
async function submitVoice(payload) {
  const form = new FormData();
  form.append("name", payload.name);
  // `language` is the primary language — send as a plain string (earlier we
  // JSON-stringified the array which produced labels like "[\"en\"" on the
  // voice — visible in the voice's metadata until we re-trained).
  if (payload.language) form.append("language", String(payload.language));
  // `languages` accepts anyOf(string | array). Repeated-append is the
  // canonical multipart pattern for array values and is accepted by FastAPI.
  if (Array.isArray(payload.languages)) {
    for (const code of payload.languages) {
      if (code) form.append("languages", String(code));
    }
  }
  if (payload.gender) form.append("gender", String(payload.gender));
  if (payload.accent) form.append("accent", String(payload.accent));
  if (payload.description) form.append("description", payload.description);

  for (const filePath of payload.audio_file_paths || []) {
    const stat = await fs.promises.stat(filePath).catch(() => null);
    if (!stat || !stat.isFile()) {
      throw new Error(`Audio file missing or unreadable: ${filePath}`);
    }
    form.append("audio_files", fs.createReadStream(filePath), {
      filename: path.basename(filePath),
      contentType: "audio/wav",
      knownLength: stat.size,
    });
  }

  const res = await axios.post(`${TTS_BASE_URL}/v1/voices/professional`, form, {
    headers: buildHeaders(form.getHeaders()),
    timeout: 300_000,
    maxContentLength: Infinity,
    maxBodyLength: Infinity,
    validateStatus: () => true,
  });

  if (res.status >= 400) {
    const bodyText =
      typeof res.data === "string"
        ? res.data
        : JSON.stringify(res.data).slice(0, 500);
    const err = new Error(`TTS submit ${res.status}: ${bodyText}`);
    err.statusCode = res.status;
    err.responseBody = res.data;
    throw err;
  }

  const body = res.data || {};
  return {
    voice_id: body.voice_id || body.id,
    status: mapProviderStatus(body.status),
    raw: body,
  };
}

/**
 * Fetch current provider status.
 *
 * Hits `GET /v1/voices/{id}/train/status`, which returns:
 *   { state, phase, progress, step, total_steps, message? }
 *
 * `state` is the canonical pipeline state we map to our statuses. `phase`
 * is a human-readable sub-state (e.g., "loading_model", "embedding") that
 * we expose as `provider_status` for observability.
 *
 * @returns {Promise<{voice_id: string, status: string, provider_status: string, provider_updated_at: string|null, failure_reason: string|null, progress: number|null, raw: any}>}
 */
async function getVoiceStatus(ttsVoiceId) {
  const res = await axios.get(
    `${TTS_BASE_URL}/v1/voices/${encodeURIComponent(ttsVoiceId)}/train/status`,
    { headers: buildJsonHeaders(), timeout: 15_000, validateStatus: () => true }
  );
  if (res.status === 404) {
    const err = new Error("voice_not_found_on_provider");
    err.statusCode = 404;
    throw err;
  }
  if (res.status >= 500) {
    const err = new Error(`provider_5xx: ${res.status}`);
    err.statusCode = res.status;
    err.retryable = true;
    throw err;
  }
  const body = res.data || {};
  const phaseOrState = body.phase || body.state || "";
  return {
    voice_id: ttsVoiceId,
    status: mapProviderStatus(body.state),
    provider_status: phaseOrState,
    provider_updated_at: body.updated_at || null,
    failure_reason: body.state === "failed" ? body.message || null : null,
    progress: Number.isFinite(body.progress) ? body.progress : null,
    raw: body,
  };
}

/**
 * Synthesize a short audio preview for SA review. Uses the Inworld-compatible
 * `/tts/v1/voice` sync endpoint. Returns `{ audio: Buffer, content_type }`.
 *
 * Note: the exact request/response shape of tts.qcall.ai's sync TTS may
 * evolve — adjust the payload keys here if the provider changes them.
 */
async function synthesizePreview({ tts_voice_id, text, sample_rate = 24000 }) {
  const url = `${TTS_BASE_URL}/tts/v1/voice`;
  const body = {
    text,
    voice_id: tts_voice_id,
    voiceId: tts_voice_id, // some Inworld-compat servers accept camelCase
    audio_config: {
      audio_encoding: "LINEAR16",
      sample_rate_hertz: sample_rate,
    },
  };
  const res = await axios.post(url, body, {
    headers: buildHeaders(),
    timeout: 60_000,
    validateStatus: () => true,
  });
  if (res.status >= 400) {
    throw new Error(
      `TTS synth ${res.status}: ${
        typeof res.data === "string"
          ? res.data.slice(0, 200)
          : JSON.stringify(res.data).slice(0, 200)
      }`
    );
  }
  // Inworld format: { result: { audioContent: "<base64>" } }
  const body64 =
    res.data?.result?.audioContent ||
    res.data?.audioContent ||
    res.data?.audio ||
    null;
  if (!body64) {
    throw new Error(
      `TTS synth returned no audio payload: ${JSON.stringify(res.data).slice(0, 200)}`
    );
  }
  return {
    audio: Buffer.from(body64, "base64"),
    content_type: "audio/wav",
  };
}

/**
 * Edit an existing voice's metadata on tts.qcall.ai. Used when a creator
 * updates name/description/language/gender/accent/categories on their
 * professional voice so the provider's labels stay in sync with our
 * local row. Best-effort — caller should not fail the overall update if
 * this call errors.
 *
 * POST /v1/voices/{voice_id}/edit
 *
 * Accepts multipart/form-data. All fields optional — send what changed.
 */
async function editVoice(ttsVoiceId, changes = {}) {
  if (!ttsVoiceId) throw new Error("ttsVoiceId is required");
  const form = new FormData();
  const maybeAppend = (key, value) => {
    if (value === undefined || value === null) return;
    if (Array.isArray(value)) {
      for (const v of value) if (v) form.append(key, String(v));
    } else if (String(value).length > 0) {
      form.append(key, String(value));
    }
  };
  maybeAppend("name", changes.name);
  maybeAppend("description", changes.description);
  maybeAppend("language", changes.language);
  maybeAppend("languages", changes.languages);
  maybeAppend("gender", changes.gender);
  maybeAppend("accent", changes.accent);
  maybeAppend("categories", changes.categories);

  const res = await axios.post(
    `${TTS_BASE_URL}/v1/voices/${encodeURIComponent(ttsVoiceId)}/edit`,
    form,
    {
      headers: buildHeaders(form.getHeaders()),
      timeout: 30_000,
      validateStatus: () => true,
    }
  );
  if (res.status >= 400) {
    const bodyText =
      typeof res.data === "string"
        ? res.data
        : JSON.stringify(res.data).slice(0, 300);
    const err = new Error(`TTS edit ${res.status}: ${bodyText}`);
    err.statusCode = res.status;
    err.responseBody = res.data;
    throw err;
  }
  return res.data;
}

module.exports = {
  submitVoice,
  getVoiceStatus,
  mapProviderStatus,
  synthesizePreview,
  editVoice,
};
