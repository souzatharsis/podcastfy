const WebSocket = require('ws');
const { v4: uuidv4 } = require('uuid');
const { deductCredits, calculateTTSCost, calculateSTTCost } = require('../utils/creditDeduction');
const SERVICE_PRICES = require('../constants/servicePrices');

// 60db WebSocket URLs
// STT WS derived from STT_API_URL (STT Labs v1: mounted at /v1/stream, shares REST port)
const STT_WS_URL = process.env.OWN_STT_WS_URL ||
  ((process.env.STT_API_URL || 'https://stt.60db.ai').replace(/^https/, 'wss') + '/v1/stream');
const TTS_WS_URL = process.env.OWN_TTS_URL || 'ws://154.210.190.179:9090';

// Pricing — sourced from centralized SERVICE_PRICES
const TTS_RATE_PER_CHAR = SERVICE_PRICES.TTS.RATE_PER_CHAR;
const STT_RATE_PER_SECOND = SERVICE_PRICES.STT.RATE_PER_SECOND;
const MIN_CREDIT_RESERVE = 0.01; // Minimum reserve to start session

// Allowed values for the audio_enhancement config key sent in {type:'start'}.
const AUDIO_ENHANCEMENT_MODES = new Set(['off', 'light', 'adaptive']);

/**
 * Normalize a `{type:'start'|'config', languages: ...}` message so the
 * `languages` field never contains the literal string "auto" — the upstream
 * STT server only accepts real ISO codes and uses `null` as the auto-detect
 * signal. Mutates the message in place.
 *
 * Handled inputs:
 *   - languages: "auto"                → languages: null
 *   - languages: ["auto"]              → languages: null
 *   - languages: ["en","auto","hi"]    → languages: ["en","hi"]
 *   - languages: []                    → languages: null
 *   - other values untouched
 */
function normalizeAutoLanguages(message) {
  if (!message || typeof message !== 'object') return;
  const raw = message.languages;
  if (raw === 'auto') {
    message.languages = null;
    return;
  }
  if (Array.isArray(raw)) {
    const filtered = raw.filter((code) => typeof code === 'string' && code && code !== 'auto');
    message.languages = filtered.length > 0 ? filtered : null;
  }
}

/**
 * STT WebSocket Proxy Session
 * Handles bidirectional streaming between client and 60db STT service
 */
class STTProxySession {
  constructor(clientWs, userId, workspaceId) {
    this.clientWs = clientWs;
    this.sixtyDbWs = null;
    this.userId = userId;
    this.workspaceId = workspaceId;
    this.sessionId = uuidv4();
    this.sessionStarted = false;
    this.audioDuration = 0; // Sum of upstream-confirmed billable utterance durations
    this.billedDuration = 0; // Sum of audio time we've actually deducted credits for
    this.clientByteEstimate = 0; // Inbound byte-derived estimate (diagnostic only, NEVER billed)
    this.lastAudioTime = null;
    this.sessionStartTime = null;
    this.initialCreditCheck = false;
    this.charAccumulator = 0; // Track characters for transcription
    this.finalized = false; // Idempotent guard for handleStop/cleanup billing finalization

    // --- Word-preservation guardrail state ---
    // Under the two-phase final flow (see WEBSOCKET.md "Canonical-answer
    // semantics: speech_final"), every utterance with LLM refinement
    // enabled emits TWO `transcription` events sharing a `sentence_id`:
    //   1. `is_final: true,  speech_final: false` — fast dict-corrected
    //      text (the "original" for guardrail purposes).
    //   2. `is_final: true,  speech_final: true`  — canonical answer
    //      (LLM-refined when `llm_applied: true`, else the same text
    //      promoted unchanged).
    // We cache the first emit's text so that when the canonical arrives
    // we can compare word-counts and roll back destructive refinements
    // in place. Map is insertion-ordered → oldest-eviction when capped.
    this.firstEmitByStmtId = new Map();
    // The most recent interim transcript text — used as the fallback
    // payload for utterances the server rejects as hallucinations
    // (`processing_mode: "hallucination_rejected"`), so downstream
    // consumers (voicebot, UI) never see words silently disappear.
    this.lastInterim = '';
  }

  // Memory cap on the sentence_id → first-emit text map. The canonical
  // follow-up typically arrives within ~700 ms, so anything older than
  // a few seconds of backlog is already dead; the cap is purely a
  // safety against long-running sessions and out-of-order canonicals.
  static FIRST_EMIT_MAX = 256;
  // Retention threshold on refined text. Below this the refinement is
  // considered *catastrophically* truncated and rolled back to the
  // first-emit text.
  //
  // Previous value (0.7) was too aggressive: the upstream LLM
  // legitimately strips fillers, collapses mid-utterance repetitions,
  // and rephrases Hinglish code-switching patterns — honest polish on
  // cricket-style commentary routinely lands at 50–70 % retention and
  // was being silently reverted, producing the "ajun mata" raw-text
  // effect reported from the realtime UI. We now only roll back when
  // the LLM lost more than ~60 % of the original tokens — at that
  // point the output is almost always a truncated sentence fragment,
  // not a useful refinement.
  static REFINED_WORD_RETENTION_MIN = 0.4;

  static wordCount(s) {
    return (s || '').split(/\s+/).filter(Boolean).length;
  }

  // Processing modes that mean "transcription was dropped/rejected upstream"
  // and therefore must NOT be billed. The first three come from the spec's
  // utterance-billing rules; `speech_end_no_result` is genuine silence.
  static NON_BILLABLE_MODES = new Set([
    'hallucination_rejected',
    'low_snr_dropped',
    'speech_end_too_short',
    'speech_end_no_result',
  ]);

  /**
   * Decide whether a transcription event should result in a credit deduction.
   * Bill only on the CANONICAL emit of a two-phase pair (`is_final=true,
   * speech_final=true`) — the first emit (`speech_final=false`) is a
   * preview that gets superseded by the canonical, so billing it would
   * double-charge. Also skip events the server marked as dropped.
   */
  static isBillable(message) {
    if (!message || message.type !== 'transcription') return false;
    if (message.is_final !== true) return false;
    if (message.speech_final !== true) return false;
    if (STTProxySession.NON_BILLABLE_MODES.has(message.processing_mode)) return false;
    return true;
  }

  /**
   * Start the STT session
   */
  async start() {
    return new Promise((resolve, reject) => {
      try {
        console.log(`[STT Session ${this.sessionId}] Starting session, client WS state: ${this.clientWs.readyState}`);

        // Connect to 60db STT service. X-Tenant-Id labels the upstream
        // tenant metric (asr_tenant_audio_seconds_total). Falls back to
        // userId so we still get a usable label when workspaceId is null.
        const sttUpstreamHeaders = {
          "X-Tenant-Id": String(this.workspaceId || this.userId || "unknown"),
        };
        if (process.env.STT_API_KEY) {
          sttUpstreamHeaders["Authorization"] = `Bearer ${process.env.STT_API_KEY}`;
        }
        this.sixtyDbWs = new WebSocket(STT_WS_URL, {
          handshakeTimeout: 10000,
          headers: sttUpstreamHeaders,
        });

        // Handle 60db connection open
        this.sixtyDbWs.on('open', () => {
          console.log(`[STT Session ${this.sessionId}] Connected to 60db STT service, client WS state: ${this.clientWs.readyState}`);

          // Send connected message to client
          this.sendToClient({
            type: 'connected',
            session_id: this.sessionId,
            server_info: {
              server_type: 'qlabs-stt-proxy',
              backend_url: STT_WS_URL
            }
          });

          resolve();
        });

        // Handle messages from 60db (forward to client)
        this.sixtyDbWs.on('message', (data) => {
          this.handleSixtyDbMessage(data);
        });

        // Handle 60db errors
        this.sixtyDbWs.on('error', (error) => {
          console.error(`[STT Session ${this.sessionId}] 60db WebSocket error:`, error.message);
          this.sendToClient({
            type: 'error',
            error: `STT service error: ${error.message}`,
            timestamp: Date.now()
          });
        });

        // Handle 60db close
        this.sixtyDbWs.on('close', (code, reason) => {
          console.log(`[STT Session ${this.sessionId}] 60db connection closed - code: ${code}, reason: ${reason?.toString() || 'none'}`);
          this.sendToClient({
            type: 'connection_closed',
            reason: '60db service disconnected',
            code: code
          });
          this.finalize('upstream_close').catch((e) =>
            console.error(`[STT Session ${this.sessionId}] finalize error:`, e)
          );
          this.cleanup();
        });

        // Handle client messages
        this.clientWs.on('message', (data) => {
          this.handleClientMessage(data);
        });

        // Handle client close
        this.clientWs.on('close', (code, reason) => {
          console.log(`[STT Session ${this.sessionId}] Client disconnected - code: ${code}, reason: ${reason?.toString() || 'none'}`);
          this.finalize('client_close').catch((e) =>
            console.error(`[STT Session ${this.sessionId}] finalize error:`, e)
          );
          this.cleanup();
        });

        // Handle client errors
        this.clientWs.on('error', (error) => {
          console.error(`[STT Session ${this.sessionId}] Client WebSocket error:`, error.message);
          this.finalize('client_error').catch((e) =>
            console.error(`[STT Session ${this.sessionId}] finalize error:`, e)
          );
          this.cleanup();
        });

        // Handle client ping/pong for keepalive
        this.clientWs.on('ping', () => {
          if (this.clientWs.readyState === WebSocket.OPEN) {
            this.clientWs.pong();
          }
        });

      } catch (error) {
        reject(error);
      }
    });
  }

  /**
   * Handle messages from 60db STT service
   */
  async handleSixtyDbMessage(data) {
    try {
      // Parse the message (60db sends JSON)
      const message = JSON.parse(data);
      console.log(`[STT Session ${this.sessionId}] ← From 60db: ${message.type}`);

      // Track transcription results for billing.
      //
      // Bill only on canonical finals (is_final=true && speech_final=true)
      // and only when the server didn't drop the utterance. This is the
      // sole place credits get deducted — handleStop / cleanup do NOT
      // re-deduct (avoids the prior double-bill bug where per-final
      // deductions were charged again as a sum at session end).
      if (STTProxySession.isBillable(message)) {
        this.charAccumulator += (message.text || '').length;

        if (message.duration && message.duration > 0) {
          this.audioDuration += message.duration;
          this.billedDuration += message.duration;
          await this.deductForAudioDuration(message.duration);
        }
      }

      // Word-preservation guardrail — see class-level doc on
      // firstEmitByStmtId / lastInterim / REFINED_WORD_RETENTION_MIN.
      // Runs BEFORE rebrand / forward so downstream (voicebot, web UI,
      // any other consumer) never sees words disappear due to either
      // (a) the server's hallucination-rate guard emitting empty finals
      // or (b) the upstream LLM refinement pass over-trimming content.
      //
      // Two-phase final flow (WEBSOCKET.md → "Canonical-answer semantics"):
      //   interim          — is_final=false
      //   first emit       — is_final=true,  speech_final=false  (dict-corrected)
      //   canonical emit   — is_final=true,  speech_final=true   (LLM-refined, or
      //                                                           original re-emit
      //                                                           when llm_applied=false)
      // When no `context` was supplied on `start`, the first-emit phase
      // is skipped and every utterance arrives as a single canonical
      // event — the cache simply stays empty on those sessions.
      if (message.type === 'transcription') {
        const text = (message.text || '').trim();
        const sid = typeof message.sentence_id === 'number' ? message.sentence_id : null;

        if (message.is_final === true && message.speech_final === false) {
          // FIRST EMIT of a two-phase pair. Remember the text so the
          // canonical event (next to arrive for this sentence_id) can
          // be sanity-checked against it.
          if (text && sid !== null) {
            this.firstEmitByStmtId.set(sid, text);
            if (this.firstEmitByStmtId.size > STTProxySession.FIRST_EMIT_MAX) {
              const oldest = this.firstEmitByStmtId.keys().next().value;
              this.firstEmitByStmtId.delete(oldest);
            }
          }
          this.lastInterim = '';
        } else if (message.is_final === true && message.speech_final === true) {
          // CANONICAL EMIT — either the LLM polished version, or (when
          // LLM was skipped/failed) the first-emit text promoted as-is.
          const firstEmit = sid !== null ? this.firstEmitByStmtId.get(sid) : undefined;

          if (text) {
            // If the canonical came out of an LLM pass, sanity-check it
            // against the first emit. An honest polish rarely drops
            // more than ~10–15 % of tokens; past 30 % we treat the
            // refinement as destructive and roll back to the first
            // emit's text (which is what the server would have sent
            // anyway with `llm_applied: false`).
            if (message.llm_applied === true && firstEmit) {
              const origWords = STTProxySession.wordCount(firstEmit);
              const refinedWords = STTProxySession.wordCount(text);
              if (
                origWords > 0 &&
                refinedWords < origWords * STTProxySession.REFINED_WORD_RETENTION_MIN
              ) {
                console.warn(
                  `[STT Session ${this.sessionId}] Rolling back refined sentence_id=${sid}: ${origWords}→${refinedWords} words (${Math.round((refinedWords / origWords) * 100)}% retained) — preserving first-emit text`
                );
                message.text = firstEmit;
                message.llm_applied = false;
                message.llm_reason = 'dropped_too_many_words';
                // `llm_latency_ms` stays — the call still happened, it
                // just wasn't usable. Downstream SLA dashboards want it.
              }
            }
            this.lastInterim = '';
          } else if (message.processing_mode === 'hallucination_rejected') {
            // The server rejected the utterance as a suspected
            // hallucination (word-rate > STT_WS_HALLUCINATION_WPS,
            // default 8 wps). This legitimately fires on fast-paced
            // mixed Hindi/English audio where Devanagari tokens are
            // short. Rather than silently dropping the final, upgrade
            // it to a tentative canonical carrying the last interim
            // text and a marker downstream clients can inspect.
            // Voicebots typically treat `tentative: true` as "route on
            // this text but flag it in logs for manual review".
            const fallback = firstEmit || this.lastInterim;
            if (fallback) {
              message.text = fallback;
              message.tentative = true;
              message.tentative_reason = 'hallucination_rejected';
              this.charAccumulator += fallback.length;
            }
            this.lastInterim = '';
          }
          // `speech_end_no_result` is genuine silence / noise — nothing
          // to preserve. Fall through and forward as-is.

          // Retain the canonical text in firstEmitByStmtId so that a
          // possible old-protocol `refined` follow-up (upstream workers
          // not yet on the two-phase build) can still be guardrailed
          // against the user's originally-spoken content. The entry
          // naturally evicts via FIRST_EMIT_MAX; we don't delete it
          // eagerly because we don't know yet whether refined is
          // coming.
          if (sid !== null) {
            const retained = (message.text || text || '').trim();
            if (retained) {
              this.firstEmitByStmtId.set(sid, retained);
              if (this.firstEmitByStmtId.size > STTProxySession.FIRST_EMIT_MAX) {
                const oldest = this.firstEmitByStmtId.keys().next().value;
                this.firstEmitByStmtId.delete(oldest);
              }
            }
          }
        } else if (message.is_final === false) {
          this.lastInterim = text;
        }
      }

      // OLD-PROTOCOL SHIM — `refined` event.
      //
      // Pre-two-phase upstream builds emit LLM refinement as a separate
      // `refined` event keyed by sentence_id, arriving ~400 ms after
      // the raw `transcription` final. Post-migration upstream folds
      // refinement into the second `transcription` (speech_final=true)
      // and never emits `refined` at all — this branch just never
      // fires in that case, so it's free defense-in-depth.
      //
      // When refined DOES come through, apply the same word-retention
      // guardrail as the two-phase canonical: if the LLM lost more than
      // ~60 % of the tokens, drop the event so downstream consumers
      // keep the original transcription they already rendered.
      if (message.type === 'refined' && typeof message.sentence_id === 'number') {
        const refinedText = (message.text || '').trim();
        const originalText = this.firstEmitByStmtId.get(message.sentence_id);
        if (originalText && refinedText) {
          const origWords = STTProxySession.wordCount(originalText);
          const refinedWords = STTProxySession.wordCount(refinedText);
          if (
            origWords > 0 &&
            refinedWords < origWords * STTProxySession.REFINED_WORD_RETENTION_MIN
          ) {
            console.warn(
              `[STT Session ${this.sessionId}] Dropping old-protocol refined sentence_id=${message.sentence_id}: ${origWords}→${refinedWords} words (${Math.round((refinedWords / origWords) * 100)}% retained)`
            );
            return; // don't forward — client keeps the raw transcription
          }
        }
        // Forwarding an accepted refined. Clean the cache entry so the
        // same sid can't be double-applied if upstream misbehaves.
        this.firstEmitByStmtId.delete(message.sentence_id);
      }

      // Rebrand upstream backend identity — clients see `60db-stt-v01` rather
      // than the raw STT Labs internal label (`real`, `mock`, backend name).
      if (message.type === 'session_started') {
        message.model = '60db-stt-v01';
        if (message.device) message.device = undefined;
      }
      if (message.type === 'connected' && message.server_info) {
        message.server_info.server_type = '60db STT';
      }

      // Forward message to client
      this.sendToClient(message);

    } catch (error) {
      console.log(`[STT Session ${this.sessionId}] ← From 60db: binary data (${data.length} bytes)`);
      // If not JSON, forward as binary
      this.clientWs.send(data);
    }
  }

  /**
   * Handle messages from client
   */
  async handleClientMessage(data) {
    try {
      let message;

      // Try to parse as JSON
      try {
        message = JSON.parse(data);
      } catch {
        // Binary audio data - forward to 60db
        if (this.sixtyDbWs && this.sixtyDbWs.readyState === WebSocket.OPEN) {
          this.sixtyDbWs.send(data);

          // Diagnostic only: rough estimate from inbound bytes (60ms per
          // 480 bytes at 8kHz mulaw). NEVER bill this — billing happens
          // off the upstream's confirmed canonical finals so we don't
          // charge for audio that failed to transcribe / got rejected.
          const estimatedDuration = (data.length / 480) * 0.06;
          this.clientByteEstimate += estimatedDuration;
        }
        return;
      }

      // Handle JSON messages
      switch (message.type) {
        case 'start':
          // The upstream STT server rejects the literal string "auto" with
          // `language 'auto' is not in the v1 supported`. Callers that mean
          // "auto-detect" should send `languages: null`. We sanitize here as
          // defense in depth so older clients don't blow up mid-session.
          normalizeAutoLanguages(message);
          // Diagnostic: confirm the context payload actually reaches the
          // upstream verbatim. If `has_context` is false here but the UI
          // thinks it set one, the breakage is client-side; if it's true
          // but session_started reports `llm_refinement: false`, upstream
          // has disabled refinement (STT_LLM_ENABLED=false or similar).
          console.log(
            `[STT Session ${this.sessionId}] → start payload:`,
            JSON.stringify({
              languages: message.languages,
              "config": {
                  audio_enhancement: message.audio_enhancement || null
              },
              has_context: !!message.context,
              context_shape: message.context
                ? {
                    general: Array.isArray(message.context.general)
                      ? message.context.general.length
                      : 0,
                    text_len:
                      typeof message.context.text === 'string'
                        ? message.context.text.length
                        : 0,
                    terms: Array.isArray(message.context.terms)
                      ? message.context.terms.length
                      : 0,
                  }
                : null,
            })
          );
          // Validate audio_enhancement — only allow off / light / adaptive.
          // Default to 'off' when omitted; reject invalid values early.
          if (message.audio_enhancement !== undefined && message.audio_enhancement !== null) {
            const mode = String(message.audio_enhancement).toLowerCase();
            if (!AUDIO_ENHANCEMENT_MODES.has(mode)) {
              this.sendToClient({
                type: 'error',
                error: `Invalid audio_enhancement value "${message.audio_enhancement}". Allowed: off, light, adaptive`,
                error_code: 'INVALID_AUDIO_ENHANCEMENT',
                timestamp: Date.now(),
              });
              return;
            }
            message.audio_enhancement = mode;
          }
          await this.handleStart(message);
          break;

        case 'audio':
          // Forward audio to 60db
          if (this.sixtyDbWs && this.sixtyDbWs.readyState === WebSocket.OPEN) {
            this.sixtyDbWs.send(JSON.stringify(message));

            // Diagnostic only: timestamp-derived duration estimate.
            // NEVER billed — see binary-audio branch above for why.
            if (message.timestamp) {
              if (this.lastAudioTime) {
                const duration = (message.timestamp - this.lastAudioTime) / 1000;
                this.clientByteEstimate += duration;
              }
              this.lastAudioTime = message.timestamp;
            }
          }
          break;

        case 'config':
          // Strip any `"auto"` entries from mid-session language updates too.
          normalizeAutoLanguages(message);
          if (this.sixtyDbWs && this.sixtyDbWs.readyState === WebSocket.OPEN) {
            this.sixtyDbWs.send(JSON.stringify(message));
          }
          break;

        case 'stop':
          // Final billing deduction and stop session
          await this.handleStop();
          break;

        case 'test':
          // Echo test back
          this.sendToClient({
            type: 'test_response',
            message: 'pong - qlabs-stt-proxy ready',
            timestamp: message.timestamp || Date.now(),
            processing_mode: 'proxy'
          });
          break;

        default:
          // Forward unknown messages to 60db
          if (this.sixtyDbWs && this.sixtyDbWs.readyState === WebSocket.OPEN) {
            this.sixtyDbWs.send(JSON.stringify(message));
          }
      }
    } catch (error) {
      console.error(`[STT Session ${this.sessionId}] Error handling client message:`, error);
      this.sendToClient({
        type: 'error',
        error: `Error processing message: ${error.message}`,
        timestamp: Date.now()
      });
    }
  }

  /**
   * Handle start message from client
   */
  async handleStart(message) {
    this.sessionStartTime = Date.now();
    this.sessionStarted = true;

    // Check if user has minimum credits
    try {
      const { checkCredits } = require('../utils/creditDeduction');
      const creditCheck = await checkCredits(this.workspaceId, MIN_CREDIT_RESERVE);

      if (!creditCheck.sufficient) {
        this.sendToClient({
          type: 'error',
          error: 'Insufficient credits to start STT session',
          error_code: 'INSUFFICIENT_CREDITS',
          details: {
            required: MIN_CREDIT_RESERVE,
            available: creditCheck.currentBalance
          }
        });
        this.clientWs.close(1008, 'Insufficient credits');
        return;
      }

      this.initialCreditCheck = true;
    } catch (error) {
      console.error(`[STT Session ${this.sessionId}] Credit check failed:`, error);
      this.sendToClient({
        type: 'error',
        error: 'Failed to verify credits',
        timestamp: Date.now()
      });
      this.clientWs.close(1011, 'Credit check failed');
      return;
    }

    // Forward start to 60db
    if (this.sixtyDbWs && this.sixtyDbWs.readyState === WebSocket.OPEN) {
      this.sixtyDbWs.send(JSON.stringify(message));
    }
  }

  /**
   * Handle stop message from client
   */
  async handleStop() {
    // No additional deduction here. Billing happens per-canonical-final in
    // handleSixtyDbMessage; re-deducting `audioDuration` would double-charge.
    // We only forward the stop, emit a summary, and tear down.
    await this.finalize('client_stop');

    // Forward stop to 60db
    if (this.sixtyDbWs && this.sixtyDbWs.readyState === WebSocket.OPEN) {
      this.sixtyDbWs.send(JSON.stringify({ type: 'stop' }));
    }

    // Send session_stopped to client (summary reflects what was actually billed).
    this.sendToClient({
      type: 'session_stopped',
      billing_summary: {
        total_duration_seconds: parseFloat(this.billedDuration.toFixed(2)),
        total_cost: parseFloat(calculateSTTCost(this.billedDuration).toFixed(6)),
        characters_transcribed: this.charAccumulator,
        client_estimated_seconds: parseFloat(this.clientByteEstimate.toFixed(2)),
      }
    });

    // Close connections
    this.cleanup();
  }

  /**
   * Idempotent session-finalization hook. Called from handleStop and from
   * every cleanup path (60db close, client close, error). Today there's
   * nothing to deduct here because billing is per-canonical-final, but
   * the hook exists as a single seam:
   *   - to log the final billed amount once per session,
   *   - to land any future "settle pending charges" logic safely,
   *   - to guarantee handleStop's summary doesn't fire twice if the
   *     client both sends `stop` AND drops the connection.
   */
  async finalize(reason = 'unknown') {
    if (this.finalized) return;
    this.finalized = true;
    console.log(
      `[STT Session ${this.sessionId}] Finalized (${reason}): ` +
      `billed=${this.billedDuration.toFixed(2)}s, ` +
      `client_estimated=${this.clientByteEstimate.toFixed(2)}s, ` +
      `chars=${this.charAccumulator}`
    );
  }

  /**
   * Deduct credits for audio duration
   */
  async deductForAudioDuration(duration) {
    try {
      const cost = calculateSTTCost(duration);

      if (cost > 0) {
        await deductCredits({
          userId: this.userId,
          serviceType: 'STT',
          amountDeducted: cost,
          unitsUsed: duration,
          workspaceId: this.workspaceId
        });

        console.log(`[STT Session ${this.sessionId}] Deducted $${cost.toFixed(6)} for ${duration.toFixed(2)}s of audio`);
      }
    } catch (error) {
      console.error(`[STT Session ${this.sessionId}] Failed to deduct credits:`, error);
      this.sendToClient({
        type: 'error',
        error: { code: 'INSUFFICIENT_CREDITS', message: 'Insufficient credits. Please top up to continue.' }
      });
      this.clientWs.close(1008, 'Insufficient credits');
    }
  }

  /**
   * Send message to client
   */
  sendToClient(message) {
    if (this.clientWs && this.clientWs.readyState === WebSocket.OPEN) {
      try {
        this.clientWs.send(JSON.stringify(message));
        const msgType = message.type || Object.keys(message)[0];
        const sessionType = this.sessionId ? 'STT' : 'TTS';
        console.log(`[${sessionType} Session] → Sent to client: ${msgType}`);
      } catch (error) {
        console.error(`[${this.sessionId || 'TTS'}] Failed to send to client:`, error.message);
      }
    } else {
      console.warn(`[${this.sessionId || 'TTS'}] Cannot send - client not ready (state: ${this.clientWs?.readyState})`);
    }
  }

  /**
   * Cleanup resources
   */
  cleanup() {
    if (this.sixtyDbWs) {
      this.sixtyDbWs.close();
      this.sixtyDbWs = null;
    }
    if (this.clientWs) {
      this.clientWs.close();
      this.clientWs = null;
    }
  }
}

/**
 * TTS WebSocket Proxy Session
 * Handles bidirectional streaming between client and 60db TTS service
 */
class TTSProxySession {
  constructor(clientWs, userId, workspaceId) {
    this.clientWs = clientWs;
    this.sixtyDbWs = null;
    this.userId = userId;
    this.workspaceId = workspaceId;
    this.sessionId = uuidv4();
    this.contextId = null;
    this.contextCreated = false;
    this.textBuffer = '';
    this.totalCharacters = 0;
    this.initialCreditCheck = false;
  }

  /**
   * Start the TTS session
   */
  async start() {
    return new Promise((resolve, reject) => {
      try {
        // Connect to 60db TTS service with tenant header for upstream metrics.
        const ttsUpstreamHeaders = {
          "X-Tenant-Id": String(this.workspaceId || this.userId || "unknown"),
        };
        if (process.env.QCALL_TTS_API_KEY) {
          ttsUpstreamHeaders["Authorization"] = `Bearer ${process.env.QCALL_TTS_API_KEY}`;
        }
        this.sixtyDbWs = new WebSocket(`${TTS_WS_URL}/tts/v1/voice:streamBidirectional`, {
          handshakeTimeout: 10000,
          headers: ttsUpstreamHeaders,
        });

        // Handle 60db connection open
        this.sixtyDbWs.on('open', () => {
          console.log(`[TTS Session ${this.sessionId}] Connected to 60db TTS service`);
          resolve();
        });

        // Handle messages from 60db (forward to client)
        this.sixtyDbWs.on('message', (data) => {
          this.handleSixtyDbMessage(data);
        });

        // Handle 60db errors
        this.sixtyDbWs.on('error', (error) => {
          console.error(`[TTS Session ${this.sessionId}] 60db WebSocket error:`, error.message);
          this.sendToClient({
            error: {
              context_id: this.contextId,
              message: `TTS service error: ${error.message}`
            }
          });
        });

        // Handle 60db close
        this.sixtyDbWs.on('close', (code, reason) => {
          console.log(`[TTS Session ${this.sessionId}] 60db connection closed - code: ${code}, reason: ${reason?.toString() || 'none'}`);
          this.sendToClient({
            error: {
              context_id: this.contextId,
              message: '60db service disconnected',
              code: code
            }
          });
          this.cleanup();
        });

        // Handle client messages
        this.clientWs.on('message', (data) => {
          this.handleClientMessage(data);
        });

        // Handle client close
        this.clientWs.on('close', (code, reason) => {
          console.log(`[TTS Session ${this.sessionId}] Client disconnected - code: ${code}, reason: ${reason?.toString() || 'none'}`);
          this.cleanup();
        });

        // Handle client errors
        this.clientWs.on('error', (error) => {
          console.error(`[TTS Session ${this.sessionId}] Client WebSocket error:`, error.message);
          this.cleanup();
        });

        // Handle client ping/pong for keepalive
        this.clientWs.on('ping', () => {
          if (this.clientWs.readyState === WebSocket.OPEN) {
            this.clientWs.pong();
          }
        });

      } catch (error) {
        reject(error);
      }
    });
  }

  /**
   * Handle messages from 60db TTS service
   */
  handleSixtyDbMessage(data) {
    try {
      const message = JSON.parse(data);

      // Forward all messages to client
      this.sendToClient(message);

      // Track context creation
      if (message.context_created) {
        this.contextId = message.context_created.context_id;
        this.contextCreated = true;
      }

    } catch (error) {
      console.error(`[TTS Session ${this.sessionId}] Error parsing 60db message:`, error);
    }
  }

  /**
   * Handle messages from client
   */
  async handleClientMessage(data) {
    try {
      const message = JSON.parse(data);

      if (message.create_context) {
        await this.handleCreateContext(message);
      } else if (message.send_text) {
        await this.handleSendText(message);
      } else if (message.flush_context) {
        await this.handleFlushContext(message);
      } else if (message.close_context) {
        await this.handleCloseContext(message);
      } else {
        // Forward other messages to 60db
        if (this.sixtyDbWs && this.sixtyDbWs.readyState === WebSocket.OPEN) {
          this.sixtyDbWs.send(JSON.stringify(message));
        }
      }
    } catch (error) {
      console.error(`[TTS Session ${this.sessionId}] Error handling client message:`, error);
      this.sendToClient({
        error: {
          context_id: this.contextId,
          message: `Error processing message: ${error.message}`
        }
      });
    }
  }

  /**
   * Handle create_context message
   */
  async handleCreateContext(message) {
    // Check if user has minimum credits
    try {
      const { checkCredits } = require('../utils/creditDeduction');
      const creditCheck = await checkCredits(this.workspaceId, MIN_CREDIT_RESERVE);

      if (!creditCheck.sufficient) {
        this.sendToClient({
          error: {
            context_id: message.create_context.context_id,
            message: 'Insufficient credits to start TTS session',
            error_code: 'INSUFFICIENT_CREDITS',
            details: {
              required: MIN_CREDIT_RESERVE,
              available: creditCheck.currentBalance
            }
          }
        });
        this.clientWs.close(1008, 'Insufficient credits');
        return;
      }

      this.initialCreditCheck = true;
    } catch (error) {
      console.error(`[TTS Session ${this.sessionId}] Credit check failed:`, error);
      this.sendToClient({
        error: {
          message: 'Failed to verify credits'
        }
      });
      this.clientWs.close(1011, 'Credit check failed');
      return;
    }

    // Forward to 60db
    if (this.sixtyDbWs && this.sixtyDbWs.readyState === WebSocket.OPEN) {
      this.sixtyDbWs.send(JSON.stringify(message));
    }
  }

  /**
   * Handle send_text message
   */
  async handleSendText(message) {
    const text = message.send_text.text;
    this.textBuffer += text;
    this.totalCharacters += text.length;

    // Forward to 60db
    if (this.sixtyDbWs && this.sixtyDbWs.readyState === WebSocket.OPEN) {
      this.sixtyDbWs.send(JSON.stringify(message));
    }
  }

  /**
   * Handle flush_context message
   */
  async handleFlushContext(message) {
    // Deduct credits for text length
    if (this.textBuffer.length > 0) {
      try {
        const cost = calculateTTSCost(this.textBuffer.length);

        await deductCredits({
          userId: this.userId,
          serviceType: 'TTS',
          amountDeducted: cost,
          unitsUsed: this.textBuffer.length,
          workspaceId: this.workspaceId
        });

        console.log(`[TTS Session ${this.sessionId}] Deducted $${cost.toFixed(6)} for ${this.textBuffer.length} characters`);

        // Clear buffer after successful flush
        this.textBuffer = '';
      } catch (error) {
        console.error(`[TTS Session ${this.sessionId}] Failed to deduct credits:`, error);
        this.sendToClient({
          error: {
            context_id: this.contextId,
            message: 'Failed to process TTS request: credit deduction failed'
          }
        });
        return;
      }
    }

    // Forward to 60db
    if (this.sixtyDbWs && this.sixtyDbWs.readyState === WebSocket.OPEN) {
      this.sixtyDbWs.send(JSON.stringify(message));
    }
  }

  /**
   * Handle close_context message
   */
  async handleCloseContext(message) {
    // Final billing if any text remaining
    if (this.textBuffer.length > 0) {
      try {
        const cost = calculateTTSCost(this.textBuffer.length);

        await deductCredits({
          userId: this.userId,
          serviceType: 'TTS',
          amountDeducted: cost,
          unitsUsed: this.textBuffer.length,
          workspaceId: this.workspaceId
        });

        console.log(`[TTS Session ${this.sessionId}] Final deduction: $${cost.toFixed(6)} for ${this.textBuffer.length} characters`);
      } catch (error) {
        console.error(`[TTS Session ${this.sessionId}] Failed to deduct final credits:`, error);
      }
    }

    // Forward to 60db
    if (this.sixtyDbWs && this.sixtyDbWs.readyState === WebSocket.OPEN) {
      this.sixtyDbWs.send(JSON.stringify(message));
    }

    // Cleanup after short delay to receive context_closed
    setTimeout(() => this.cleanup(), 1000);
  }

  /**
   * Send message to client
   */
  sendToClient(message) {
    if (this.clientWs && this.clientWs.readyState === WebSocket.OPEN) {
      try {
        this.clientWs.send(JSON.stringify(message));
        const msgType = message.type || Object.keys(message)[0];
        const sessionType = this.sessionId ? 'STT' : 'TTS';
        console.log(`[${sessionType} Session] → Sent to client: ${msgType}`);
      } catch (error) {
        console.error(`[${this.sessionId || 'TTS'}] Failed to send to client:`, error.message);
      }
    } else {
      console.warn(`[${this.sessionId || 'TTS'}] Cannot send - client not ready (state: ${this.clientWs?.readyState})`);
    }
  }

  /**
   * Cleanup resources
   */
  cleanup() {
    if (this.sixtyDbWs) {
      this.sixtyDbWs.close();
      this.sixtyDbWs = null;
    }
    if (this.clientWs) {
      this.clientWs.close();
      this.clientWs = null;
    }
  }
}

module.exports = {
  STTProxySession,
  TTSProxySession,
  STT_WS_URL,
  TTS_WS_URL,
};
