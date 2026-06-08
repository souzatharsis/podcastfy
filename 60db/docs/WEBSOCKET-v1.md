# STT Labs v1 — WebSocket API Reference

Reference for integrating STT Labs streaming STT into voicebots, Twilio call flows, and browser capture apps. Mirrors the shape of the legacy `websocket-stt.md` so existing client code needs only mechanical updates, but the semantics (backends, languages, normalization) are different — read the **What changed from the legacy doc** section at the bottom before porting.

---

## Connection

| Property | Value |
|----------|-------|
| URL | `ws://HOST:8000/v1/stream` or `wss://HOST:8000/v1/stream` |
| Protocol | WebSocket (RFC 6455) — mounted inside FastAPI, shares the REST port |
| Frame types | Binary (telephony / μ-law) or Text/JSON (browser / linear PCM) |
| Auth | None by default; put a reverse proxy in front for prod |
| Ping/keepalive | Starlette WebSocket default — client may send WS pings every 20–30 s |
| Max session duration | Unlimited (continuous mode); single utterance capped internally at 30 s |

The same host also serves `GET /healthz` (liveness), `GET /readyz` (model readiness), and `GET /v1/languages` (full language catalog) for load-balancer and UI integration.

---

## Session lifecycle

```
Client                          Server
  │                               │
  │──── TCP/TLS connect ─────────►│
  │◄─── {"type":"connected"} ─────│  immediate on connect
  │                               │
  │──── {"type":"start", ...} ───►│
  │◄─── {"type":"session_started"}│
  │                               │
  │──── audio frames / messages ─►│
  │◄─── {"type":"speech_started"} │  VAD detected voice
  │◄─── {"type":"transcription"}  │  is_final=true, speech_final=true
  │◄─── {"type":"refined"}        │  optional — LLM correction, ~400ms later
  │                               │
  │──── {"type":"stop"} ─────────►│
  │◄─── {"type":"session_stopped"}│
```

Continuous mode (`continuous_mode: true`, the default) keeps the session alive across multiple utterances in one connection — send a single `start`, stream audio as long as you want, finalize each utterance automatically, then `stop` at call end.

**Two-phase finals (context-gated LLM refinement).** When the caller supplies a `context` object on `start`, every utterance produces **two** `transcription` events with the same `sentence_id`:

1. **First emit** — `is_final: true, speech_final: false` — fast path, dict-corrected text. Use this for low-latency UI updates and barge-in.
2. **Second emit** — `is_final: true, speech_final: true` — canonical answer. Either the LLM-refined text (when correction succeeded) or the original text re-emitted (when LLM failed/timed-out/was skipped). The `llm_applied` boolean tells you which.

When `context` is **not** supplied, every utterance produces **one** `transcription` event with `is_final: true, speech_final: true` (current/legacy behavior). Consumers that don't care about the fast-first-emit optimization can simply gate on `speech_final: true` and ignore the rest — that gives them exactly one canonical event per utterance regardless of whether refinement is on.

---

## Client → Server messages

### `start` — begin session

Sent once after `connected` is received. Must be sent before any audio.

```json
{
  "type": "start",
  "languages": ["en", "hi"],
  "context": {
    "general": [
      {"key": "domain",  "value": "Healthcare"},
      {"key": "doctor",  "value": "Dr. Martha Smith"},
      {"key": "patient", "value": "Mr. David Miller"}
    ],
    "text":  "Routine diabetes follow-up consultation.",
    "terms": ["Celebrex", "Zyrtec", "Metformin", "HbA1c"]
  },
  "config": {
    "encoding": "mulaw",
    "sample_rate": 8000,
    "utterance_end_ms": 500,
    "continuous_mode": true,
    "interim_results_frequency": 300,
    "no_speech_threshold": 0.60,
    "diarize": false,
    "min_speakers": null,
    "max_speakers": null
  }
}
```

**`languages` rules** — ISO-639-1 codes drawn from the `/v1/languages` catalog:

- Single-element array `["en"]` → fast path, skips language ID entirely, lowest latency.
- Multi-element array `["en","hi"]` → if both languages share one backend (Vaani handles Indic+English natively), the session collapses to that backend's fast path. Otherwise runs per-utterance language ID.
- Omit or send `null` → auto-detect across the 39-language v1 set.
- `"EN"`, `"en-US"`, `"en_GB"` are accepted; the server lowercases and strips region suffixes.
- **Arabic dialect tags** (`ar-eg`, `ar-lv`, `ar-gu`, `ar-ma`, etc.) are explicitly rejected with an `error` message — FC-Arabic is MSA only. Pass `language=ar` to opt in to best-effort MSA transcription of dialectal audio. See `KNOWN_LIMITATIONS.md` for the full policy.
- **Urdu (`ur`)** and other unsupported v1 languages (see `EXPLICITLY_UNSUPPORTED_V1` in the server) return an `unsupported_language` error.

**`context` rules (optional)** — structured hint object that opens the server-side LLM refinement gate. Shape matches Soniox's WebSocket context schema:

| Field | Type | Required | Purpose |
|---|---|---|---|
| `general` | `[{key: string, value: string}]` | no | Free-form key/value metadata (`domain`, `topic`, speaker names). Surfaced to the LLM verbatim as hint lines. |
| `text` | `string` | no | Free-form background paragraph describing the session. Useful for narrative context ("The doctor is reviewing a recent lab report…"). |
| `terms` | `string[]` | no | Domain-specific proper nouns / acronyms / drug names. These are injected into the LLM prompt and future revisions may also merge them into the session's script-correction dictionary for zero-latency preservation. |

Rules:

- **Omit `context` entirely** to disable LLM refinement for the session. Finals arrive once as plain `transcription` events (legacy behavior).
- **Include any non-empty combination** of `general`, `text`, `terms` to enable refinement. All three are optional but at least one should be populated — an empty object is accepted but provides no hinting value.
- The server emits `session_started.llm_refinement: true` to confirm the LLM path is active (see `session_started`).
- Malformed context (non-object, wrong types) is silently dropped — the session still starts, but refinement stays off.
- **Context never leaks into the `transcription.text`.** It is only used as an LLM hint; callers do not need to strip it from the transcript.
- Server-side config `STT_LLM_ENABLED=false` is a kill switch that disables refinement globally regardless of per-session context.

### `audio` — JSON audio chunk (browser mode)

```json
{
  "type": "audio",
  "audio": "<base64-encoded Int16 PCM or μ-law bytes>",
  "encoding": "linear",
  "sample_rate": 48000,
  "timestamp": 1700000000000
}
```

- `encoding`: `"linear"` for Int16 little-endian PCM (browser capture), `"mulaw"` for μ-law.
- `sample_rate`: actual rate of the encoded bytes. The server resamples to 16 kHz internally using `audioop.ratecv`, which is stateful per-session — do not stop and restart mid-utterance or you will get a discontinuity at the boundary.
- `timestamp`: optional unix-ms tick, echoed for round-trip measurement.

**Chunking guidance**:
- Browser PCM at 48 kHz: any size works; 20–100 ms frames are typical.
- The server coalesces small frames into ≥160 ms blocks before VAD, adding 160 ms fixed latency in exchange for stable VAD decisions.

### Binary frame — raw μ-law audio (telephony mode)

Send a raw WebSocket binary frame with μ-law bytes, no JSON wrapper. The server auto-detects this as telephony mode on the first binary frame and flips `session.mode = "telephony"`.

```
Recommended chunk size: 480 bytes  = 60 ms at 8 kHz
Twilio default:         160 bytes  = 20 ms — the server buffers 8 frames (1280 bytes / 160 ms) before decoding
```

The μ-law resampler state is persistent per session. Twilio's 20 ms frames coalesce into 160 ms blocks inside the server; you do not need to batch them on the client.

### `config` — change session mid-flight

```json
{
  "type": "config",
  "languages": ["hi"],
  "continuous_mode": true
}
```

Both `languages` and `continuous_mode` are optional — include only fields you want to change. Send `"languages": null` to revert to auto-detect. Server emits `language_changed` and/or `mode_changed` events in response.

### `stop` — end session

```json
{ "type": "stop" }
```

The server drains any remaining audio buffer as a final utterance, emits `session_stopped`, then closes the WebSocket.

### `test` — ping / latency check

```json
{
  "type": "test",
  "message": "ping",
  "timestamp": 1700000000000
}
```

Server echoes `test_response` with the same `timestamp` for round-trip measurement.

---

## Server → Client messages

### `connected` — sent immediately on TCP connect

```json
{
  "type": "connected",
  "server_info": {
    "server_type": "STT Labs Streaming STT",
    "ready": true,
    "total_languages": 40,
    "features": {
      "vad_segmentation": true,
      "multi_language_per_session": true,
      "max_languages_per_session": 5,
      "telephony_mulaw": true,
      "browser_pcm": true,
      "continuous_mode": true,
      "interim_results": true,
      "speaker_diarization": true,
      "code_switching_indic_english": true,
      "non_hallucinating": true
    },
    "timing": {
      "min_utterance_end_ms": 300,
      "default_utterance_end_ms": 500,
      "max_utterance_seconds": 30
    }
  }
}
```

Backend identity (`parakeet`, `vaani`, `arabic_fc`) is **never exposed** in `connected`, `session_started`, or any per-utterance event. Clients should read `GET /v1/languages` at startup to build language pickers rather than depending on a hard-coded list.

### `session_started` — after `start` is processed

```json
{
  "type": "session_started",
  "session_id": "sess_8c3d1a9f4b7e2c51",
  "language": "Multi-language: EN, HI",
  "languages": ["hi"],
  "device": "cuda:0",
  "model": "real",
  "processing_mode": "sentence_based_continuous",
  "continuous_mode": true,
  "interim_frequency": 300,
  "diarize": false,
  "llm_refinement": true
}
```

- `language` is a human-readable label for logging; `languages` is the authoritative resolved candidate list after normalization and shared-backend collapse.
- `model` is `"real"` or `"mock"` depending on whether the GPU backends loaded successfully. Mock mode is only used in tests and is explicitly gated by `STT_INFERENCE_MODE=mock`.
- `llm_refinement` — `true` when the caller supplied a valid `context` AND the server has `STT_LLM_ENABLED=true`. When `true`, clients should be ready to receive follow-up `refined` events keyed by `sentence_id`. When `false` (or absent), finals arrive exactly once as `transcription` events.
- It is safe to start sending audio immediately after this event.

### `speech_started` — VAD detected voice activity

```json
{
  "type": "speech_started",
  "timestamp": 1700000000.123
}
```

Use this for **barge-in**: stop any TTS playback the moment this event arrives. Fired when Silero VAD crosses the speech threshold (default 0.5, configurable via `STT_VAD_THRESHOLD` env var).

### `transcription` — result event (interim and final share one type)

All results use `type: "transcription"`. Differentiate with the `is_final` / `speech_final` / `is_partial` flags.

**Final result** (`is_final=true`, `speech_final=true`):

```json
{
  "type": "transcription",
  "text": "Hello, how are you? मैं 2025 में Bangalore जा रहा हूं।",
  "confidence": 0.87,
  "language": "hi",
  "language_name": "HI",
  "is_final": true,
  "speech_final": true,
  "is_partial": false,
  "sentence_id": 3,
  "duration": 1.82,
  "latency": 0.43,
  "timestamp": 1700000000.456,
  "words": [
    { "word": "Hello", "start": 0.0,  "end": 0.32, "confidence": 0.94 },
    { "word": "how",   "start": 0.35, "end": 0.52, "confidence": 0.92 }
  ],
  "speakers": null
}
```

The `text` field is always passed through the shared hygiene pipeline before being sent:
1. **NFC Unicode normalization** (Indic conjuncts, Latin accented chars).
2. **Whitespace strip** (leading/trailing spaces from the backend tokenizer).
3. **Arabic tashkeel strip** when `language="ar"` (MSA outputs are deterministic — diacritics are non-deterministic artifacts of training data mixture).
4. **Digit normalization** — Devanagari / Bengali / Gurmukhi / Gujarati / Odia / Tamil / Telugu / Kannada / Malayalam / Arabic-Indic / Extended-Arabic-Indic → ASCII 0-9.
5. **Entity normalization** — percents (`"20 percent"` → `"20%"`), currency (`"500 rupees"` → `"₹500"`), phone with country code (`"plus 91 98765 43210"` → `"+91 9876543210"`), URL (`"www dot example dot com"` → `"www.example.com"`), email (`"john dot doe at example dot com"` → `"john.doe@example.com"`), hashtag (`"hashtag foo bar"` → `"#FooBar"`), ordinal (`"twenty first"` → `"21st"`), range (`"5 to 10"` → `"5-10"`).
6. **Bidi marks** (U+202A / U+202B / U+202C) wrapping mixed Arabic↔Latin strings so RTL clients render direction correctly.

See `KNOWN_LIMITATIONS.md` section 2 for the cases where script preservation is still pending (A-class Hinglish cricket scenarios).

**Empty speech-final signal** (`text=""`, `is_final=true`, `speech_final=true`):

```json
{
  "type": "transcription",
  "text": "",
  "confidence": 0.0,
  "is_final": true,
  "speech_final": true,
  "processing_mode": "speech_end_no_result",
  "timestamp": 1700000000.789
}
```

Sent when audio was detected but produced no transcript (silence buffer, sub-threshold speech, noise-only segment). Your client should reset its interim state on this event and **not** treat it as an error or retry. This is the WS equivalent of the REST `no_speech_detected` warning.

**Interim result** (`is_final=false`, `speech_final=false`, `is_partial=true`) — only sent when `interim_results_frequency` is set:

```json
{
  "type": "transcription",
  "text": "Hello how",
  "confidence": 0.72,
  "language": "en",
  "language_name": "EN",
  "is_final": false,
  "speech_final": false,
  "is_partial": true
}
```

Use interims **only** for barge-in word-count checks and UI feedback. **Never send interim text to an LLM** — a final with `is_final=true, speech_final=true` will always follow.

### Canonical-answer semantics: `speech_final`

`is_final` and `speech_final` are NOT identical when LLM refinement is active. They split into two distinct meanings:

| `is_final` | `speech_final` | Meaning |
|---|---|---|
| `false` | `false` | Interim partial — text may still change as more audio arrives. |
| `true` | `false` | End-of-speech reached, dict-corrected text. **The LLM is still processing.** A follow-up event with `speech_final: true` will arrive shortly with the canonical text. Only emitted when refinement is active for this utterance. |
| `true` | `true` | **Canonical answer.** Definitive, will not be revised. Either the LLM-refined version (when `llm_applied: true`) or the original text promoted unchanged (when `llm_applied: false`). |

The same `sentence_id` is echoed across both phases so consumers can reconcile.

**Canonical (speech_final=true) example after LLM refinement:**

```json
{
  "type": "transcription",
  "sentence_id": 3,
  "text": "डॉक्टर साहब, मेरा sugar level बहुत high है। Metformin की dose बढ़ाओ।",
  "confidence": 0.87,
  "language": "hi",
  "language_name": "HI",
  "is_final": true,
  "speech_final": true,
  "is_partial": false,
  "duration": 1.82,
  "words": [
    { "word": "डॉक्टर", "start": 0.0, "end": 0.32, "confidence": 0.94 }
  ],
  "speakers": null,
  "llm_applied": true,
  "llm_latency_ms": 431,
  "timestamp": 1700000000.789
}
```

**Canonical event extra fields (when refinement was attempted):**

| Field | Type | Description |
|---|---|---|
| `llm_applied` | bool | `true` if the LLM ran and produced refined text. `false` if the LLM was skipped (gate closed, text too short) or failed (timeout, network error) — in which case `text` is the same as the first-emit and `llm_reason` explains why. |
| `llm_latency_ms` | number | Round-trip time in milliseconds to the LLM endpoint. Only present when `llm_applied: true`. |
| `llm_reason` | string | Diagnostic reason when `llm_applied: false`. Values include `gate_closed`, `error:TimeoutException`, `error:HTTPStatusError`, etc. Useful for SLA monitoring; safe to ignore in display logic. |

**Guarantees:**

- **Exactly one canonical event per utterance.** When refinement is on, you get exactly two `transcription` events per utterance (one `speech_final: false` + one `speech_final: true`). When refinement is off, you get exactly one (`speech_final: true`). Never zero, never three.
- **Same `sentence_id`** across both phases. Use it as the reconciliation key.
- **The `speech_final: true` event always arrives.** If the LLM fails or times out, the original text is re-emitted with `llm_applied: false` so consumers waiting on canonical text never hang.
- **Words / timestamps** are carried on both phases unchanged. The LLM doesn't realign tokens — `words[]` always corresponds to the original ASR output, not the refined text. Use `words[]` for word-level timing, `text` for display.
- `sentence_id` ordering is preserved per session, but **canonical events are NOT guaranteed to arrive in `sentence_id` order** when LLM is on — two utterances close in time may complete refinement out of order due to variable LLM latency. Always key on `sentence_id`, not arrival order.

**Recommended client patterns:**

*Simplest (don't care about the fast-first-emit optimization):*

```js
function onMessage(msg) {
  if (msg.type === 'transcription' && msg.speech_final) {
    // Canonical — render and forget
    render(msg);
  }
  // Ignore is_final && !speech_final (it's an intermediate)
  // Ignore is_partial (handle separately if you need live partials)
}
```

*With fast first-emit (UX-aware):*

```js
const livePainted = new Map();   // sentence_id → DOM ref / state slot

function onMessage(msg) {
  if (msg.type !== 'transcription') return;
  const sid = msg.sentence_id;

  if (msg.is_partial) { renderPartial(msg); return; }

  let entry = livePainted.get(sid);
  if (!entry) {
    entry = createLine();
    livePainted.set(sid, entry);
  }
  entry.text = msg.text;
  entry.pending = msg.is_final && !msg.speech_final;  // border style
  render(entry);

  if (msg.speech_final) {
    finalize(entry, msg.llm_applied, msg.llm_latency_ms);
    livePainted.delete(sid);
  }
}
```

**For middle-layer / proxy implementations:** forward both phases unchanged to downstream consumers, preserving `sentence_id`. Downstream clients that only want the canonical answer can filter on `speech_final: true`. Do not collapse the two events into one in the proxy — the fast first-emit is the whole point of the design.

### `language_changed` — after `config` message changes language

```json
{
  "type": "language_changed",
  "language": "Multi-language: HI",
  "language_code": ["hi"]
}
```

### `mode_changed` — after `config` changes `continuous_mode`

```json
{
  "type": "mode_changed",
  "continuous_mode": true,
  "mode_name": "continuous"
}
```

### `session_stopped` — after `stop` is processed

```json
{ "type": "session_stopped" }
```

### `error` — processing error

```json
{
  "type": "error",
  "error": "language 'ur' is not supported in v1 (see /v1/languages for the supported set)",
  "timestamp": 1700000000.0
}
```

Non-fatal — session continues unless the error occurred on `start` (in which case no `session_started` is sent and the client should retry with corrected parameters).

### `test_response` — reply to `test` ping

```json
{
  "type": "test_response",
  "message": "pong - STT Labs v2 ready",
  "timestamp": 1700000000000,
  "processing_mode": "sentence_based"
}
```

---

## Parameters reference

### `start.config` fields

| Parameter | Type | Default | Range | Description | Notes |
|---|---|---|---|---|---|
| `encoding` | string | `"linear"` | `"linear"`, `"mulaw"` | Audio encoding. `linear` = Int16 LE PCM; `mulaw` = G.711 μ-law. | Mismatch produces garbled audio silently. First binary frame also auto-selects `mulaw`. |
| `sample_rate` | int | `16000` | `8000`, `16000`, `24000`, `44100`, `48000` | Actual capture rate of the audio. Server resamples to 16 kHz with stateful `audioop.ratecv`. | Must match the real capture rate — do not hardcode 16000 on 48 kHz browser input. |
| `utterance_end_ms` | int | `500` | `≥ 300` | Silence (ms) after last speech before finalizing the utterance. | **Values below 300 ms are clamped to 300 ms with no error.** Recommended 500–1000 ms for voicebots; 300 ms for barge-in heavy flows. |
| `continuous_mode` | bool | `true` | `true`, `false` | Keep session alive between utterances. | Required for voicebot / phone call use cases. `false` = single-shot STT. |
| `interim_results_frequency` | int\|null | `null` (disabled) | `≥ 300` ms | How often to emit interim partial results during speech. | **Values below 300 ms are clamped to 300 ms.** Enabling adds CPU overhead. Use 300 ms for barge-in, 500 ms otherwise, omit entirely if not needed. |
| `no_speech_threshold` | float | `0.60` | `0.0–1.0` | Reserved for cross-compatibility with legacy clients. No effect on STT Labs backends — we use non-hallucinating architectures (Parakeet RNN-T, Vaani FastConformer, FC-Arabic) that don't report a `no_speech_prob`. | Pass-through for client code migration; safe to omit. |
| `diarize` | bool | `false` | `true`, `false` | Run pyannote speaker diarization on each finalized utterance and attach a `speakers` array. | Requires `HF_TOKEN` on server. Adds ~50–150 ms latency per final. |
| `min_speakers` | int\|null | `null` | `≥ 1` or `null` | Lower bound on diarization speaker count. `0` and negative values are silently clamped to `null`. | Only read when `diarize=true`. |
| `max_speakers` | int\|null | `null` | `≥ 1` or `null` | Upper bound on diarization speaker count. | Only read when `diarize=true`. |

### Top-level `start` fields

| Field | Type | Default | Description |
|---|---|---|---|
| `languages` | `string[]` \| `null` | `null` (auto) | Array of ISO-639-1 language codes, e.g. `["en","hi"]`. Max 5 per session. Accepts uppercase and BCP-47 region tags (`"EN"`, `"en-US"`); lowercases and strips region. Arabic dialect tags (`ar-eg`) return an error. |
| `context` | object \| `null` | `null` (refinement off) | Soniox-compatible structured context `{general, text, terms}`. Opens the server-side LLM refinement gate — when set (and valid), each final is followed by a `refined` event. See the `context` rules section. |

### `audio` message fields (browser mode)

| Field | Type | Required | Description |
|---|---|---|---|
| `type` | string | yes | `"audio"` |
| `audio` | string | yes | Base64-encoded audio bytes (Int16 PCM or μ-law) |
| `encoding` | string | yes | `"linear"` or `"mulaw"` |
| `sample_rate` | int | yes | Actual sample rate of the bytes |
| `timestamp` | int | no | Client unix-ms timestamp for latency measurement |

---

## Transcription result fields

| Field | Type | Description |
|---|---|---|
| `text` | string | Normalized transcript (NFC + digits + entities + bidi — see the pipeline block above). Empty string = speech-end-no-result signal. |
| `confidence` | float | Backend confidence, 0.0–1.0. Parakeet typically emits 0.7–0.95 on wideband audio; Vaani 0.5–0.85; FC-Arabic 0.5–0.9. Telephony is typically 0.1–0.15 lower than browser audio due to the 8→16 kHz resample. |
| `language` | string | ISO-639-1 code, e.g. `"en"`, `"hi"`, `"ar"`. |
| `language_name` | string | Uppercase language code, e.g. `"EN"`. (Note: differs from the REST `/v1/transcribe` response where `language_name` is the full English name — this WS field is a legacy shape we preserve for client compatibility.) |
| `is_final` | bool | `true` = end of speech reached for this utterance. May still be followed by an upgrade if LLM refinement is active. |
| `speech_final` | bool | `true` = canonical answer, will not be revised further. When LLM refinement is on, the server emits one `is_final: true, speech_final: false` event followed by one `is_final: true, speech_final: true` event. When LLM refinement is off, every final is `speech_final: true`. See "Canonical-answer semantics" section. |
| `is_partial` | bool | `true` for interim results only. |
| `llm_applied` | bool \| absent | Present on `speech_final: true` events when refinement was attempted. `true` = LLM upgraded the text; `false` = LLM was skipped or failed and `text` is the unchanged first-emit. Absent when no `context` was provided on `start`. |
| `llm_latency_ms` | number \| absent | LLM round-trip in ms; present only when `llm_applied: true`. |
| `llm_reason` | string \| absent | Diagnostic reason when `llm_applied: false` (`gate_closed`, `error:TimeoutException`, etc.). |
| `sentence_id` | int | Monotonically increasing counter per session, starts at 1. |
| `duration` | float | Duration (seconds) of the audio segment transcribed. |
| `latency` | float | Seconds from finalization start to result ready (excludes queue time and audio duration). |
| `timestamp` | float | Server unix timestamp (fractional seconds) when the event was emitted. |
| `words` | array \| null | Word-level timestamps `[{word, start, end, confidence}]`. Note: the field is `confidence`, not `probability` — differs from the legacy doc. Present on finals; empty on interims. |
| `speakers` | array \| null | List of `{speaker, start, end}` diarization turns when `diarize=true`, otherwise `null`. |
| `processing_mode` | string | One of `"speech_end_no_result"` (silence/noise produced no transcript), `"speech_end_too_short"` (utterance < 300 ms, skipped), `"hallucination_rejected"` (word-rate exceeded `STT_WS_HALLUCINATION_WPS`, see Limitations). Omitted on ordinary finals. Clients should treat any non-empty `processing_mode` as a diagnostic, not an error. |

---

## Voicebot integration checklist

A condensed recipe for the common call-flow integration. Copy-paste into your voicebot module as a starting point and adapt.

1. **Connect once per call** to `wss://HOST/v1/stream`. Do not reconnect between utterances — use `continuous_mode: true`.
2. **Wait for `connected`** before sending `start`. `ready: true` in `server_info` means all backends are loaded; `ready: false` means you should retry the connection in 1–3 s.
3. **Send `start`** with:
   - `languages: ["en","hi"]` (or whatever your call targets — multi-language with shared backend is free, cross-backend lists add LID latency).
   - `config.encoding: "mulaw"` and `config.sample_rate: 8000` for Twilio; `"linear"` and `16000` for browser.
   - `config.continuous_mode: true`.
   - `config.utterance_end_ms: 500` for normal flows, `300` if you need the fastest possible barge-in.
   - `config.interim_results_frequency: 300` **only** if you need word-count-based barge-in; omit otherwise.
4. **Start streaming audio** after `session_started`.
5. **On `speech_started`**, stop your TTS immediately. Do not wait for a transcript.
6. **On `transcription` with `is_final=true`**:
   - Empty `text`? → ignore (it's the no-speech signal). Do not clear intent state; do not play an error sound.
   - Non-empty? → feed to your NLU / LLM. Use `words[]` for precise timing if you need it. Use `confidence` for guardrail thresholds (reject below 0.4 for telephony, 0.55 for browser).
7. **On language mismatch**: clients that support language switching should send a `config` message with the new `languages` list. The next utterance will use the new setting.
8. **On `error`**: log the message; non-`start` errors do not close the session.
9. **At call end**, send `{"type": "stop"}` and wait for `session_stopped` before closing the socket.
10. **If you sent `context` on `start`**:
    - **Simple consumers**: gate everything on `speech_final: true` and ignore intermediate finals. You'll get exactly one canonical event per utterance, identical in shape to the no-context path. Zero extra logic.
    - **Latency-sensitive consumers** (live captions, barge-in): also handle `is_final: true, speech_final: false` as a fast preview. Render it dimmed or with a "pending" indicator. When the matching `speech_final: true` arrives (same `sentence_id`), upgrade the line in place.
    - **Voicebot NLU routing**: feed the `speech_final: false` text to NLU immediately for fast intent dispatch — do NOT wait for `speech_final: true`. If your NLU benefits from proper-noun accuracy (name-spelling slots, drug-name lookup), run a second-pass NLU call on the `speech_final: true` text and reconcile on `sentence_id`. Most call flows don't need this — first emit is good enough for intent.
    - The server guarantees `speech_final: true` always arrives, even on LLM failure (with `llm_applied: false`). You never need to time out / give up waiting.

**Thresholds worth tuning per deployment**:
- `STT_VAD_THRESHOLD` env var (0.0–1.0, default 0.5) — lower for quiet callers, raise for noisy environments. Applies server-wide.
- `utterance_end_ms` — lower (300) for impatient users, higher (800) for thoughtful long-form.
- `interim_results_frequency` — 300 for fast barge-in, 500 for text-streaming UIs, omit for everything else.

---

## Limitations and warnings

**`utterance_end_ms` clamp**
Values below 300 ms are silently clamped to 300 ms. Sub-300 ms would fragment utterances and cause the non-hallucinating backends to drop short segments.

**Language count**
Max 5 languages per session (`STT_MAX_LANGUAGES` env var). Cross-backend multi-language (e.g. `["en","ar"]`) runs per-utterance LID which adds ~20–50 ms per utterance. Same-backend multi-language (e.g. `["en","hi"]`) collapses to a single backend's fast path with zero LID overhead — use this whenever possible.

**Telephony confidence**
8 kHz μ-law → 16 kHz resampling reduces backend confidence by ~0.10–0.15 compared to native wideband input. Use a client-side threshold of 0.35 for telephony vs 0.55 for browser.

**Buffer limits**
- Pre-speech ring buffer: 1.0 s (captures first word before VAD fires).
- Minimum coalesce before VAD: 160 ms (μ-law 1280 bytes, linear `sample_rate × 2 × 160 / 1000` bytes).
- Maximum utterance duration: 30 s (anything longer force-finalizes).

**VAD thresholds**
- Speech start: Silero probability > `STT_VAD_THRESHOLD` (default 0.5, configurable).
- Silence → utterance end: `utterance_end_ms` of consecutive sub-threshold audio.
- No separate continuation threshold — the single VAD threshold controls both edges.

**Non-hallucinating architecture**
Parakeet (RNN-T), Vaani (FastConformer), and FC-Arabic (Hybrid Conformer) do not output `no_speech_prob` because they physically cannot produce text from silence — the CTC/RNN-T topology emits blank tokens on non-speech. A secondary word-rate sanity check rejects finals whose `word_count / duration` exceeds `STT_WS_HALLUCINATION_WPS` (default **8.0 words/sec**). Dropped finals are emitted with `text: ""` and `processing_mode: "hallucination_rejected"`. Tune via env var — lower (5.0) for English-heavy workloads where even fast speech rarely exceeds 5 wps; keep at 8.0 or raise for Indic/Arabic where Devanagari/Arabic tokens are short and natural fast speech can legitimately hit 6–8 wps.

**Diarization**
`diarize=true` requires `HF_TOKEN` configured on the server and a gated model approval for `pyannote/speaker-diarization-3.1`. Without both, diarization silently falls back to a deterministic mock. Check `session_started.diarize` to confirm the request was accepted.

**Model loading**
- Parakeet-TDT-0.6B-v3 (FP16, 25 European languages)
- Vaani-FastConformer-Multilingual (FP32, 14 Indic languages + Hinglish code-switching)
- FC-Arabic-Hybrid (FP32, MSA)
- VoxLingua107-ECAPA (FP32, language identification across 107 languages → masked to 39 supported)
- Silero VAD (FP32, `torch.hub`)
- Pyannote speaker-diarization-3.1 (FP32, gated behind HF_TOKEN)

Warmup takes ~45–60 s on a cold GPU; `readyz` returns 503 until all models are loaded.

**Concurrent sessions**
One GPU handles ~8 concurrent WebSocket sessions at default concurrency (`STT_GPU_SEM=4`). Beyond that, utterance latency increases proportionally — scale horizontally with a load balancer hashing on `session_id` for sticky routing.

**Language aliasing policy (new in v1)**
No silent aliasing. Urdu (`ur`), Japanese (`ja`), Korean (`ko`), Chinese (`zh`), Thai (`th`), Vietnamese (`vi`), Indonesian (`id`), Tagalog (`tl`), Swahili (`sw`), Turkish (`tr`), Persian (`fa`), Hebrew (`he`) all return `unsupported_language` errors. Arabic dialect tags return `dialect_not_supported`. See `KNOWN_LIMITATIONS.md` for the full policy.

**LLM refinement — server-side controls**
All fields are server-side only — callers never see an `llm_*` field in request payloads. The only caller-facing switch is the presence/absence of `context`.

| Env var | Default | Purpose |
|---|---|---|
| `STT_LLM_ENABLED` | `true` | Master kill-switch. `false` = refinement off globally regardless of per-session context. `llm_refinement` in `session_started` reports `false` when this is `false`. |
| `STT_LLM_BASE_URL` | `https://llm.qcall.ai/v1` | OpenAI-compatible chat completions endpoint (vLLM, TGI, llama.cpp server, etc.). |
| `STT_LLM_MODEL` | `qcall/slm-3b-int4` | Model identifier sent in the `model` field of the chat completions request. |
| `STT_LLM_TIMEOUT_SEC` | `10.0` | Per-call timeout. On timeout no `refined` event is emitted; the session continues. |
| `STT_LLM_MAX_TOKENS` | `512` | Max tokens the LLM may emit per correction. Should comfortably exceed the longest expected utterance. |
| `STT_LLM_MIN_WORDS` | `4` | Skip LLM refinement for finals shorter than this. Tiny utterances (`"Yeah"`, `"Okay"`) aren't worth the round-trip and are often misleading to correct. |

**LLM refinement — operational notes**

- Refinement runs as an `asyncio.create_task` background job keyed off each final. It does not block the next utterance's processing. A slow LLM affects `refined` arrival time, never subsequent `transcription` emission.
- The refinement endpoint must be OpenAI-compatible: `POST /chat/completions` with `{model, messages, max_tokens, temperature, stream: false}`. vLLM, sglang, and OpenAI itself all qualify. Set up `STT_LLM_BASE_URL` so the `/chat/completions` suffix is appended cleanly.
- For middle-layer implementations proxying STT Labs to an upstream consumer: treat `refined` as a distinct event type in your forwarder. Do not try to splice `refined.text` back into the original `transcription` event — preserve the two-phase shape so downstream clients can opt in.
- The LLM preserves script per-language (Hindi→Devanagari, Arabic→Arabic) and does not translate. English loanwords written in non-Latin scripts are cast to Latin. See `api/src/stt_api/utils/llm_postprocess.py` for the exact system prompt and few-shot examples used to enforce this.

---

## What changed from the legacy `websocket-stt.md`

If you are porting a client that was written against the old Whisper-based doc, these are the differences that matter. Everything else is the same shape.

| Area | Legacy doc | STT Labs v1 |
|---|---|---|
| URL | `ws://HOST:8765` (dedicated port) | `ws://HOST:8000/v1/stream` (mounted in main FastAPI app) |
| Model | Whisper large-v3 (int8_float16 CT2) | Parakeet-TDT + Vaani + FC-Arabic, non-hallucinating |
| Language count | 99+ (all Whisper langs) | 39 v1-supported + 1 explicit MSA Arabic |
| `languages` = `null` | Auto-detect across 99+ langs | Auto-detect across 39-lang v1 mask |
| Urdu `ur` | Silently aliased to `hi` | Returns `unsupported_language` error |
| Malay `ms` | Silently aliased to `id` | Returns `unsupported_language` error |
| Arabic dialects | N/A (Whisper covers them) | `ar-eg` / `ar-lv` / `ar-gu` / `ar-ma` return `dialect_not_supported` error |
| `language_name` | Uppercase code | Uppercase code (WS) / full English name (REST) — WS preserves legacy shape |
| Word field | `probability` | **`confidence`** (NeMo convention, not Whisper) |
| `no_speech_threshold` | Controls Whisper's `no_speech_prob` filter | **Ignored** — non-hallucinating backends don't emit it. Safe to pass for compat. |
| Diarization | Not available | Available via `config.diarize: true` + pyannote-3.1 |
| Entity normalization | Not applied | Percent / currency / phone / URL / email / hashtag / ordinal / range rewriting applied to every transcript |
| Digit normalization | Not applied | Devanagari, Bengali, Arabic-Indic, and 8 more Indic scripts normalized to ASCII 0-9 |
| Bidi marks | Not applied | Arabic↔Latin mixed output wrapped in U+202A / U+202B / U+202C |
| Code-switching | Hinglish / Banglish "accepted without script rejection" | Natively supported via Vaani; `languages=[en,hi]` collapses to Vaani fast path with zero LID overhead |
| Backend identity in responses | `"model": "large-v3"` | **Never exposed** — all backend names stripped from `connected`, `session_started`, and `transcription` events |
| Max languages per session | "Max 2 recommended" | Hard max 5 (`STT_MAX_LANGUAGES`) |
| Max utterance duration | 5.0 s | 30 s |
| Context-aware correction | Not available | `start.context` object (Soniox-compatible) triggers a two-phase final per utterance: fast `speech_final: false` emit (dict-corrected) followed by canonical `speech_final: true` emit (LLM-refined). Same event type, same `sentence_id`, no second event type to handle. |
| `is_final` vs `speech_final` | Identical on finals | Distinct when LLM is active. `is_final: true, speech_final: false` = end-of-speech, intermediate. `is_final: true, speech_final: true` = canonical. |
| `sentence_id` | Not emitted | Monotonic per-session counter; primary reconciliation key for the two-phase final flow. |

---

## Related documentation

- **`SCENARIOS.md`** — internal engineering catalog of 152 edge cases, with per-scenario severity, root cause, and status.
- **`KNOWN_LIMITATIONS.md`** — customer-facing limitation reference with workarounds. Read before filing a bug.
- **`README.md`** — service overview, setup, deployment.
- **REST transcription** — `POST /v1/transcribe` documented in the OpenAPI spec at `GET /docs`. Same text normalization pipeline; different shape for sync/async batch use cases.

---

_Last updated: 2026-04-14 — context-gated LLM refinement now uses two-phase `transcription` events keyed on `speech_final` (no separate `refined` event type). Single `transcription` event type for all final flows; consumers can opt into the fast first-emit or simply gate on `speech_final: true` for the canonical answer. Maintained alongside `KNOWN_LIMITATIONS.md` and `SCENARIOS.md`. For changes to the WebSocket wire format, the contract is: backwards-compatible field additions are allowed, field renames and removals require a v2 endpoint._
