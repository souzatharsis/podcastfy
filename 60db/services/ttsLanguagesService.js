// Lightweight wrapper around tts.qcall.ai/v1/languages with in-memory caching.
// The TTS provider's supported-language list is the source of truth — keep it
// out of hard-coded enums in app code so a TTS rollout is one less thing to
// chase across repos.

const axios = require("axios");

const TTS_BASE_URL = (
  process.env.TTS_PROFESSIONAL_BASE_URL || "https://tts.qcall.ai"
).replace(/\/+$/, "");

// Cache: { fetchedAt: number, payload: Array<{code,label}> }
let cache = null;
const TTL_MS = 60 * 60 * 1000; // 1h

// Common fallback when the upstream call fails (rare, but keeps the wizard
// usable in dev / offline). Trimmed to the most-used languages.
const FALLBACK = [
  { code: "en", label: "English" },
  { code: "hi", label: "Hindi" },
  { code: "es", label: "Spanish" },
  { code: "fr", label: "French" },
  { code: "de", label: "German" },
  { code: "ja", label: "Japanese" },
  { code: "zh", label: "Chinese" },
];

// Small built-in display labels for known codes. Anything not in this map
// falls back to whatever the upstream returned for `name`/`label`, then to
// the raw code itself.
const KNOWN_LABELS = {
  en: "English", hi: "Hindi", es: "Spanish", fr: "French", de: "German",
  it: "Italian", pt: "Portuguese", nl: "Dutch", ja: "Japanese", zh: "Chinese",
  ko: "Korean", ar: "Arabic", ru: "Russian", tr: "Turkish", id: "Indonesian",
  vi: "Vietnamese", th: "Thai", pl: "Polish", sv: "Swedish", da: "Danish",
  fi: "Finnish", no: "Norwegian", el: "Greek", he: "Hebrew", cs: "Czech",
  ro: "Romanian", uk: "Ukrainian", bn: "Bengali", ta: "Tamil", te: "Telugu",
  ml: "Malayalam", kn: "Kannada", gu: "Gujarati", mr: "Marathi", pa: "Punjabi",
  ur: "Urdu", fa: "Persian", ms: "Malay", tl: "Filipino",
};

function normalize(item) {
  if (!item) return null;
  // Accept several shapes the upstream might return:
  //   { code, name } | { code, label } | { language_code, language_name } | "en"
  if (typeof item === "string") {
    const code = item.toLowerCase();
    return { code, label: KNOWN_LABELS[code] || code.toUpperCase() };
  }
  const code = (
    item.code ||
    item.language_code ||
    item.language_id ||  // tts.qcall.ai uses this key
    item.id ||
    ""
  )
    .toString()
    .toLowerCase();
  if (!code) return null;
  const upstreamLabel =
    item.label || item.name || item.language_name || item.display_name || null;
  return { code, label: KNOWN_LABELS[code] || upstreamLabel || code.toUpperCase() };
}

async function fetchFromUpstream() {
  const url = `${TTS_BASE_URL}/v1/languages`;
  const headers = { Accept: "application/json" };
  if (process.env.TTS_PROFESSIONAL_API_KEY) {
    headers.Authorization = `Bearer ${process.env.TTS_PROFESSIONAL_API_KEY}`;
  }
  const res = await axios.get(url, { headers, timeout: 10_000 });
  // Accept several body shapes: array, { languages: [] }, { data: [] }
  const raw = Array.isArray(res.data)
    ? res.data
    : Array.isArray(res.data?.languages)
    ? res.data.languages
    : Array.isArray(res.data?.data)
    ? res.data.data
    : [];
  const normalized = raw.map(normalize).filter(Boolean);
  // Surface a warning only when something looks wrong (upstream returned data
  // but we couldn't normalize any of it — usually means a key-name change).
  if (raw.length > 0 && normalized.length === 0) {
    console.warn(
      "[ttsLanguages] upstream returned data but none could be normalized — check parser key names. First item:",
      JSON.stringify(raw[0]).slice(0, 200)
    );
  }
  // De-dup by code (defensive)
  const seen = new Set();
  return normalized.filter((l) => {
    if (seen.has(l.code)) return false;
    seen.add(l.code);
    return true;
  });
}

async function getLanguages({ force = false } = {}) {
  if (!force && cache && Date.now() - cache.fetchedAt < TTL_MS) {
    return cache.payload;
  }
  try {
    const payload = await fetchFromUpstream();
    if (payload.length > 0) {
      cache = { fetchedAt: Date.now(), payload };
      return payload;
    }
    // Empty response — keep stale cache if we have one, else fallback
    if (cache?.payload?.length) return cache.payload;
    return FALLBACK;
  } catch (err) {
    console.error("ttsLanguages.getLanguages upstream failed:", {
      message: err.message,
      url: `${TTS_BASE_URL}/v1/languages`,
      status: err.response?.status,
      response_data: err.response?.data
        ? JSON.stringify(err.response.data).slice(0, 300)
        : undefined,
      code: err.code,
      stack: err.stack?.split("\n").slice(0, 3).join(" | "),
    });
    if (cache?.payload?.length) return cache.payload; // serve stale
    return FALLBACK;
  }
}

function isSupported(code) {
  if (!cache?.payload) return true; // permissive until we've fetched once
  return cache.payload.some((l) => l.code === code);
}

module.exports = { getLanguages, isSupported };
