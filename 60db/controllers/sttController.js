const db = require("../config/database");
const { v4: uuidv4 } = require("uuid");
const fs = require("fs");
const fsPromises = require("fs").promises;
const FormData = require("form-data");
const axios = require("axios");
const creditDeduction = require("../utils/creditDeduction");
const SERVICE_PRICES = require("../constants/servicePrices");

// Allowed MIME types for audio files
const ALLOWED_MIMES = [
  "audio/mpeg",
  "audio/mp3",
  "audio/wav",
  "audio/wave",
  "audio/x-wav",
  "audio/ogg",
  "audio/webm",
  "audio/flac",
  "audio/m4a",
  "audio/mp4",
  "video/mp4",
];

// Per-file limit for STT. Upstream now accepts 100 MB (was effectively 1 MB at
// upstream nginx). Our nginx already permits 100M; raise the controller cap
// so we stop being the bottleneck. Env-tunable for ops.
const STT_MAX_FILE_SIZE =
  parseInt(process.env.STT_MAX_FILE_SIZE_BYTES, 10) || 10 * 1024 * 1024; // 10MB

class STTController {
  // POST /stt
  async transcribeAudio(req, res) {
    const userId = req.user.id;
    if (!req.files || !req.files.file) {
      return res
        .status(400)
        .json({ success: false, message: "Audio file is required" });
    }

    const client = await db.pool.connect();
    let uploadedFilePath = null;

    try {
      await client.query("BEGIN");

      // =====================================
      // 1️⃣ Validate input file
      // =====================================
      if (!req.files || !req.files.file) {
        return res
          .status(400)
          .json({ success: false, message: "Audio file is required" });
      }

      const file = req.files.file;

      if (!ALLOWED_MIMES.includes(file.mimetype)) {
        return res
          .status(400)
          .json({ success: false, message: "Invalid file type" });
      }

      if (file.size > STT_MAX_FILE_SIZE) {
        const maxMB = Math.round(STT_MAX_FILE_SIZE / 1024 / 1024);
        return res
          .status(413)
          .json({ success: false, message: `File too large. Maximum allowed size is ${maxMB}MB` });
      }

      uploadedFilePath = file.tempFilePath;

      const executorUserId = req.user.id;
      const workspaceId = req.cerbosPrincipal?.attr?.workspace_id || req.user?.workspace_id || req.user?.current_workspace?.workspace_id || req.body?.workspace_id;

      if (!workspaceId) {
        return res
          .status(400)
          .json({ success: false, message: "Workspace required" });
      }

      // =====================================
      // 2️⃣ Resolve billing owner
      // =====================================
      const workspaceRes = await client.query(
        `
      SELECT billing_owner_id
      FROM workspace
      WHERE id = $1 AND deleted_at IS NULL
      `,
        [workspaceId],
      );

      if (workspaceRes.rows.length === 0) {
        throw new Error("Workspace not found");
      }

      const billingOwnerId = workspaceRes.rows[0].billing_owner_id;
      // =====================================
      // 3️⃣ Fetch active plan (USER LEVEL) — used only for the LLM-refinement
      // feature gate. Pay-as-you-go: no monthly minute cap.
      // =====================================
      const planRes = await client.query(
        `
      SELECT
        mp.name AS plan_name,
        mp.features
      FROM user_plans up
      JOIN master_plans mp ON mp.id = up.plan_id
      WHERE up.user_id = $1
        AND up.is_active = true
      LIMIT 1
      `,
        [billingOwnerId],
      );

      if (planRes.rows.length === 0) {
        throw new Error("No active plan for workspace billing owner");
      }

      const { plan_name, features: planFeatures } = planRes.rows[0];

      // =====================================
      // 4️⃣ Call external STT (to get duration)
      // =====================================
      const sttForm = new FormData();

      if (file.tempFilePath) {
        sttForm.append("file", fs.createReadStream(file.tempFilePath), {
          filename: file.name,
          contentType: file.mimetype,
        });
      } else {
        sttForm.append("file", file.data, {
          filename: file.name,
          contentType: file.mimetype,
        });
      }

      // STT Labs v1: omit `language` entirely to auto-detect across the full supported set
      const requestedLanguage = req.body.language;
      if (requestedLanguage && requestedLanguage !== "auto") {
        sttForm.append("language", requestedLanguage);
      }

      // Forward the rest of the upstream's documented form fields when the
      // caller supplies them. Without this allow-list, customers cannot
      // reach features like `keywords` (vocab boost), multi-language
      // candidate sets via `languages`, or word-level timestamps —
      // we'd silently drop them. Boolean fields use the upstream's
      // string-encoded convention.
      const PASSTHROUGH_STR = [
        "languages",          // CSV / repeated form value, narrows LID candidates
        "return_timestamps",  // "none" | "word"
        "keywords",           // Deepgram-compatible CSV with optional :weight
        "min_split_sec",      // LID flapping detector tuning
      ];
      for (const k of PASSTHROUGH_STR) {
        if (req.body[k] !== undefined && req.body[k] !== null && req.body[k] !== "") {
          sttForm.append(k, String(req.body[k]));
        }
      }
      const PASSTHROUGH_INT = ["min_speakers", "max_speakers"];
      for (const k of PASSTHROUGH_INT) {
        if (req.body[k] !== undefined && req.body[k] !== null && req.body[k] !== "") {
          const n = parseInt(req.body[k], 10);
          if (Number.isFinite(n)) sttForm.append(k, String(n));
        }
      }
      const PASSTHROUGH_BOOL = ["diarize", "include_confidence", "script_correction"];
      for (const k of PASSTHROUGH_BOOL) {
        const v = req.body[k];
        if (v === true || v === "true") sttForm.append(k, "true");
        else if (v === false || v === "false") sttForm.append(k, "false");
      }

      // Forward the optional `context` field to the upstream
      // /v1/transcribe endpoint. Free-form paragraph (or JSON object with
      // `terms`) describing the session / domain / speakers / jargon —
      // opens the LLM refinement gate (Gemma 4, real per-token cost
      // upstream) AND now drives the fuzzy/phonetic keyword boost.
      // Plan-tier gate: free plans cannot trigger LLM refinement.
      const llmRefinementAllowed =
        plan_name !== "Free" &&
        (planFeatures?.llm_refinement !== false);
      const refinementWarnings = [];
      if (
        req.body.context !== undefined &&
        req.body.context !== null &&
        req.body.context !== ""
      ) {
        if (!llmRefinementAllowed) {
          refinementWarnings.push({
            code: "llm_refinement_not_in_plan",
            message: "LLM refinement (context) is not available on the Free plan; field ignored.",
          });
        } else {
          const ctxStr =
            typeof req.body.context === "string"
              ? req.body.context
              : JSON.stringify(req.body.context);
          sttForm.append("context", ctxStr);
        }
      }

      const sttHeaders = sttForm.getHeaders();
      if (process.env.STT_API_KEY) {
        sttHeaders["Authorization"] = `Bearer ${process.env.STT_API_KEY}`;
      }
      // Tenant label for upstream metrics (asr_tenant_audio_seconds_total).
      sttHeaders["X-Tenant-Id"] = String(workspaceId);

      // Cancellation propagation: if the client aborts, cancel the upstream
      // call so we don't pay for compute we'll never bill the user for.
      const abortController = new AbortController();
      const onClientAbort = () => abortController.abort();
      req.once("close", onClientAbort);
      req.once("aborted", onClientAbort);

      // Long-file safe: upstream now auto-chunks at silence boundaries with
      // parallel cross-worker dispatch (RTF ~0.006), so a 27-min file
      // returns in ~10s. The legacy 120s ceiling was the bottleneck for
      // anything over ~20 min of audio. 600s covers the 100 MB upload
      // window plus chunked processing for any practical input.
      const sttTimeoutMs = parseInt(process.env.STT_AXIOS_TIMEOUT_MS, 10) || 600000;
      let sttResp;
      try {
        sttResp = await axios.post(`${process.env.STT_API_URL}/v1/transcribe`, sttForm, {
          headers: sttHeaders,
          timeout: sttTimeoutMs,
          signal: abortController.signal,
          // Large files: don't crash on big response bodies (chunked
          // transcripts on long audio can be hundreds of KB).
          maxContentLength: Infinity,
          maxBodyLength: Infinity,
        });
      } catch (err) {
        // Pass through upstream rate-limit + server errors with the right
        // status so SDKs can back off correctly. Generic 500 hides the
        // signal from clients.
        if (err.response?.status === 429) {
          const retryAfter = err.response.headers?.["retry-after"];
          const passErr = new Error("Upstream STT rate-limited");
          passErr.statusCode = 429;
          passErr.code = "STT_UPSTREAM_RATE_LIMIT";
          passErr.details = { retry_after: retryAfter };
          throw passErr;
        }
        if (err.response?.status >= 500 && err.response?.status < 600) {
          const passErr = new Error("Upstream STT service unavailable");
          passErr.statusCode = 503;
          passErr.code = "STT_UPSTREAM_UNAVAILABLE";
          throw passErr;
        }
        if (err.name === "AbortError" || err.code === "ERR_CANCELED") {
          const passErr = new Error("Request cancelled by client");
          passErr.statusCode = 499;
          passErr.code = "STT_CLIENT_CANCELLED";
          throw passErr;
        }
        throw new Error("External STT provider error");
      } finally {
        req.removeListener("close", onClientAbort);
        req.removeListener("aborted", onClientAbort);
      }

      const sttData = sttResp.data || {};
      // STT Labs v1 returns `duration_sec`; older shapes used `duration` or
      // `file_info.duration_seconds` — accept all three for compat.
      const actualDuration =
        sttData.duration_sec ||
        sttData.duration ||
        sttData.file_info?.duration_seconds ||
        0;

      const durationMinutes = actualDuration / 60;

      // Quality / routing / billing-classification signals from upstream.
      // `warning_codes: ["low_snr_dropped"]` means upstream dropped the
      // audio before LID/ASR (text=""), so we MUST NOT charge for it.
      // Once upstream ships the `billing.billable` object (see
      // design/stt-cost-model-rewrite.md), prefer that signal.
      const warningCodes = Array.isArray(sttData.warning_codes)
        ? sttData.warning_codes
        : [];
      const snrDb = typeof sttData.snr_db === "number" ? sttData.snr_db : null;
      const languageSource =
        typeof sttData.language_source === "string"
          ? sttData.language_source
          : null;
      const billable = !warningCodes.includes("low_snr_dropped");
      const billableReason = billable ? "ok" : "low_snr_dropped";
      const billableMinutes = billable ? durationMinutes : 0;

      // =====================================
      // CREDIT CHECK (New System)
      // Uses the SAME rate as the actual deduction ($0.006/min base
      // + 30% diarization surcharge when requested) so the pre-flight
      // check and the post-hoc deduction agree.
      // =====================================
      const baseCostEstimate = durationMinutes * SERVICE_PRICES.STT.RATE_PER_MINUTE;
      const diarizeRequested = req.body.diarize === "true" || req.body.diarize === true;
      const sttCost = billable ? baseCostEstimate * (diarizeRequested ? 1.30 : 1) : 0;

      // Check if workspace has sufficient credits
      const creditCheck = await creditDeduction.checkCredits(workspaceId, sttCost);

      if (!creditCheck.sufficient) {
        await client.query("ROLLBACK");
        return creditDeduction.insufficientCreditsResponse(
          res,
          sttCost,
          creditCheck.currentBalance,
          creditCheck.shortfall
        );
      }

      // =====================================
      // 5️⃣ Save STT item (AUDIT = executor)
      // =====================================
      const transcript = sttData.text || "";
      const detectedLanguage = sttData.detected_language || sttData.language;
      const upstreamRequestId = sttData.request_id || null;

      // Cost: base + diarize surcharge. Diarize is a real GPU surcharge
      // upstream (pyannote). Detect from request flag OR from response
      // (speakers populated => diarization actually ran). Both costs are
      // zeroed when the result was non-billable (low_snr_dropped etc.).
      // diarizeRequested is declared above (credit check block).
      const diarizeRan =
        diarizeRequested ||
        (Array.isArray(sttData.speakers) && sttData.speakers.length > 0);
      const DIARIZE_SURCHARGE_RATE = SERVICE_PRICES.STT.DIARIZE_SURCHARGE;
      const baseCostUsd = billable ? durationMinutes * SERVICE_PRICES.STT.RATE_PER_MINUTE : 0;
      const diarizeCostUsd =
        billable && diarizeRan ? baseCostUsd * DIARIZE_SURCHARGE_RATE : 0;
      const costUsd = baseCostUsd + diarizeCostUsd;

      const sttItemRes = await client.query(
        `
      INSERT INTO stt_item (
        workspace_id,
        user_id,
        input_audio_url,
        transcript,
        language,
        duration_seconds,
        model_name,
        cost_usd,
        status,
        response_json,
        source_type,
        upstream_request_id,
        snr_db,
        language_source,
        billable_reason
      )
      VALUES ($1, $2, $3, $4, $5, $6, $7, $8, 'completed', $9, 'upload', $10, $11, $12, $13)
      RETURNING id, hash_id
      `,
        [
          workspaceId,
          executorUserId, // executor, not billing owner
          file.name,
          transcript,
          detectedLanguage,
          actualDuration,
          "external-stt-qcall",
          costUsd,
          JSON.stringify(sttData),
          upstreamRequestId,
          snrDb,
          languageSource,
          billableReason,
        ],
      );

      const sttItem = sttItemRes.rows[0];

      // =====================================
      // 7️⃣ STT logs (AUDIT)
      // =====================================
      await client.query(
        `
      INSERT INTO stt_logs (
        stt_item_id,
        user_id,
        workspace_id,
        words_count,
        duration_seconds,
        cost_usd,
        api_key_id,
        upstream_request_id
      )
      VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
      `,
        [
          sttItem.id,
          executorUserId,
          workspaceId,
          sttData.word_count || 0,
          actualDuration,
          costUsd,
          req.apiKey ? req.apiKey.id : null,
          upstreamRequestId,
        ],
      );

      // =====================================
      // 8️⃣ Update DAILY usage_summary + deduct credits — BILLABLE PATH ONLY
      // =====================================
      // Non-billable results (low_snr_dropped, etc.) write stt_item and
      // stt_logs above for audit, but skip both the usage_summary upsert
      // AND the wallet deduction. The user got nothing usable; we
      // shouldn't charge or burn cycle minutes.
      if (billable) {
        const today = new Date().toISOString().split("T")[0];

        try {
          await client.query(
            `
          INSERT INTO usage_summary (
            user_id,
            workspace_id,
            usage_date,
            stt_minutes,
            cost_usd,
            updated_at
          )
          VALUES ($1, $2, $3, $4, $5, NOW())
          ON CONFLICT (user_id, workspace_id, usage_date)
          DO UPDATE SET
            stt_minutes = usage_summary.stt_minutes + EXCLUDED.stt_minutes,
            cost_usd = usage_summary.cost_usd + EXCLUDED.cost_usd,
            updated_at = NOW()
          `,
            [billingOwnerId, workspaceId, today, durationMinutes, costUsd],
          );
        } catch (upsertErr) {
          // Fallback: Handle rare race condition
          if (upsertErr.code === '23505') {
            console.warn('Upsert race condition, retrying...');
            await client.query(
              `UPDATE usage_summary
               SET stt_minutes = stt_minutes + $1,
                   cost_usd = cost_usd + $2,
                   updated_at = NOW()
               WHERE user_id = $3 AND workspace_id = $4 AND usage_date = $5`,
              [durationMinutes, costUsd, billingOwnerId, workspaceId, today]
            );
          } else {
            throw upsertErr;
          }
        }


        // =====================================
        // CREDIT DEDUCTION (Workspace Wallet)
        // =====================================
        // Run on the same `client` as the rest of this handler's writes so the
        // wallet UPDATE is atomic with stt_item / stt_logs / usage_summary.
        // Any throw past this point — including the COMMIT below — rolls back
        // the deduction along with the inserts; no orphan charges possible.
        const deductResult = await creditDeduction.deductCredits({
          userId: userId,
          serviceType: "STT",
          amountDeducted: costUsd,
          unitsUsed: durationMinutes,
          workspaceId: workspaceId,
          billingOwnerId: billingOwnerId,
          client,
        });
        console.log(`Deducted $${costUsd.toFixed(6)} for STT (${durationMinutes.toFixed(2)} min) from workspace ${workspaceId}, tx=${deductResult.transactionHashId}`);
      } else {
        console.log(`[STT] Non-billable result (reason=${billableReason}, duration=${actualDuration}s); skipped deduction + usage_summary for workspace ${workspaceId}`);
      }

      await client.query("COMMIT");

      if (uploadedFilePath) {
        await fsPromises.unlink(uploadedFilePath).catch(() => {});
      }

      // Merge any plan-tier warnings into the response so clients can see
      // why their `context` was ignored without breaking the upstream shape.
      const responseBody = { ...sttData };
      if (refinementWarnings.length > 0) {
        responseBody.warnings = [
          ...(Array.isArray(responseBody.warnings) ? responseBody.warnings : []),
          ...refinementWarnings,
        ];
        responseBody.warning_codes = [
          ...(Array.isArray(responseBody.warning_codes) ? responseBody.warning_codes : []),
          ...refinementWarnings.map((w) => w.code),
        ];
      }
      res.status(sttResp.status).json(responseBody);
      // res.status(201).json({
      //   success: true,
      //   message: "Transcription completed successfully",
      //   data: {
      //     id: sttItem.id,
      //     hash_id: sttItem.hash_id,
      //     text: transcript,
      //     language: detectedLanguage,
      //     duration_seconds: actualDuration,
      //     cost_usd: costUsd,
      //     stt_response: sttData,
      //   },
      // });
    } catch (error) {
      await client.query("ROLLBACK");

      if (uploadedFilePath) {
        await fsPromises.unlink(uploadedFilePath).catch(() => {});
      }

      console.error("STT error:", error);

      const status = error.statusCode || 500;
      const body = {
        success: false,
        message: error.message || "Transcription failed",
      };
      if (error.code) body.error_code = error.code;
      if (error.details) body.details = error.details;
      // Surface upstream Retry-After as an HTTP header so SDK backoff logic
      // can honour it without parsing the JSON body.
      if (status === 429 && error.details?.retry_after) {
        res.setHeader("Retry-After", String(error.details.retry_after));
      }
      res.status(status).json(body);
    } finally {
      client.release();
    }
  }

  // GET /stt/logs
  async getSTTLogs(req, res) {
    try {
      const userId = req.user.id;
      const {
        workspace_id,
        page = 1,
        limit = 20,
        language,
        date_from,
        date_to,
      } = req.query;

      const offset = (page - 1) * limit;

      let query = `
        SELECT si.id, si.hash_id, si.input_audio_url, si.transcript,
               si.language, si.duration_seconds, si.cost_usd,
               si.status, si.created_at, si.source_type,
               sl.words_count,
               w.name as workspace_name,
               SUBSTRING(si.transcript, 1, 100) as text_preview
        FROM stt_item si
        JOIN stt_logs sl ON si.id = sl.stt_item_id
        JOIN workspace w ON si.workspace_id = w.id
        WHERE si.user_id = $1 AND si.deleted_at IS NULL
      `;

      const params = [userId];
      let paramIndex = 2;

      if (workspace_id) {
        query += ` AND si.workspace_id = $${paramIndex}`;
        params.push(workspace_id);
        paramIndex++;
      }

      if (language) {
        query += ` AND si.language = $${paramIndex}`;
        params.push(language);
        paramIndex++;
      }

      if (date_from) {
        query += ` AND si.created_at >= $${paramIndex}`;
        params.push(date_from);
        paramIndex++;
      }

      if (date_to) {
        query += ` AND si.created_at <= $${paramIndex}`;
        params.push(date_to);
        paramIndex++;
      }

      query += ` ORDER BY si.created_at DESC LIMIT $${paramIndex} OFFSET $${
        paramIndex + 1
      }`;
      params.push(limit, offset);

      const result = await db.query(query, params);

      // Get total count for pagination
      let countQuery = `
        SELECT COUNT(*) as total
        FROM stt_item si
        WHERE si.user_id = $1 AND si.deleted_at IS NULL
      `;

      const countParams = [userId];
      let countParamIndex = 2;

      if (workspace_id) {
        countQuery += ` AND si.workspace_id = $${countParamIndex}`;
        countParams.push(workspace_id);
        countParamIndex++;
      }

      if (language) {
        countQuery += ` AND si.language = $${countParamIndex}`;
        countParams.push(language);
        countParamIndex++;
      }

      if (date_from) {
        countQuery += ` AND si.created_at >= $${countParamIndex}`;
        countParams.push(date_from);
        countParamIndex++;
      }

      if (date_to) {
        countQuery += ` AND si.created_at <= $${countParamIndex}`;
        countParams.push(date_to);
        countParamIndex++;
      }

      const countResult = await db.query(countQuery, countParams);
      const total = parseInt(countResult.rows[0].total);

      res.status(200).json({
        success: true,
        message: "STT logs retrieved successfully",
        logs: result.rows,
        pagination: {
          page: parseInt(page),
          limit: parseInt(limit),
          total,
          pages: Math.ceil(total / limit),
        },
      });
    } catch (error) {
      console.error("Get STT logs error:", error);
      res
        .status(500)
        .json({ success: false, message: "Internal server error" });
    }
  }

  // GET /stt/:id
  async getSTTDetail(req, res) {
    try {
      const { id } = req.params;
      const userId = req.user.id;

      const isNumeric = /^\d+$/.test(id);
      const result = await db.query(
        `
        SELECT si.*, sl.words_count, w.name as workspace_name
        FROM stt_item si
        JOIN stt_logs sl ON si.id = sl.stt_item_id
        JOIN workspace w ON si.workspace_id = w.id
        WHERE (${isNumeric ? 'si.id = $1' : 'si.hash_id = $1::uuid'})
              AND si.user_id = $2 AND si.deleted_at IS NULL
      `,
        [id, userId],
      );

      if (result.rows.length === 0) {
        return res
          .status(404)
          .json({ success: false, message: "STT record not found" });
      }

      res.status(200).json({
        success: true,
        message: "STT record retrieved successfully",
        data: result.rows[0],
      });
    } catch (error) {
      console.error("Get STT detail error:", error);
      res
        .status(500)
        .json({ success: false, message: "Internal server error" });
    }
  }

  // DELETE /stt/:id
  async deleteSTT(req, res) {
    const client = await db.pool.connect();

    try {
      await client.query("BEGIN");

      const { id } = req.params;
      const userId = req.user.id;

      // Find and delete STT item
      const isNumeric = /^\d+$/.test(id);
      const result = await client.query(
        `
        UPDATE stt_item
        SET deleted_at = NOW()
        WHERE (${isNumeric ? 'id = $1' : 'hash_id = $1::uuid'}) AND user_id = $2 AND deleted_at IS NULL
        RETURNING id
      `,
        [id, userId],
      );

      if (result.rows.length === 0) {
        return res
          .status(404)
          .json({ success: false, message: "STT record not found" });
      }

      // Also delete related STT logs
      await client.query(
        `
        UPDATE stt_logs 
        SET deleted_at = NOW() 
        WHERE stt_item_id = $1 AND deleted_at IS NULL
      `,
        [result.rows[0].id],
      );

      await client.query("COMMIT");

      res
        .status(200)
        .json({ success: true, message: "STT record deleted successfully" });
    } catch (error) {
      await client.query("ROLLBACK");
      console.error("Delete STT error:", error);
      res
        .status(500)
        .json({ success: false, message: "Internal server error" });
    } finally {
      client.release();
    }
  }

  // POST /stt/realtime-save
  async saveRealtimeSession(req, res) {
    const client = await db.pool.connect();

    try {
      await client.query("BEGIN");

      const userId = req.user.id;
      const workspaceId = req.cerbosPrincipal?.attr?.workspace_id || req.user?.workspace_id || req.user?.current_workspace?.workspace_id || req.body?.workspace_id;
      const {
        transcript,
        segments,
        duration_seconds,
        languages,
        cost_usd,
      } = req.body;

      if (!transcript && (!segments || segments.length === 0)) {
        return res
          .status(400)
          .json({ success: false, message: "No transcript data to save" });
      }

      // Build the full transcript from segments if not provided
      const fullTranscript =
        transcript ||
        (segments || []).map((s) => s.text).join(" ");

      const detectedLanguage = Array.isArray(languages)
        ? languages.join(",")
        : languages || null;

      const duration = parseFloat(duration_seconds) || 0;
      const cost = parseFloat(cost_usd) || 0;

      // Build the response_json with segments for VAD display
      const responseJson = {
        type: "realtime",
        segments: segments || [],
        text: fullTranscript,
        duration_sec: duration,
        languages: languages || [],
      };

      const sttItemRes = await client.query(
        `
        INSERT INTO stt_item (
          workspace_id, user_id, input_audio_url, transcript,
          language, duration_seconds, model_name, cost_usd,
          status, response_json, source_type
        )
        VALUES ($1, $2, 'realtime-recording', $3, $4, $5, '60db-stt-v01', $6, 'completed', $7, 'realtime')
        RETURNING id, hash_id
        `,
        [
          workspaceId,
          userId,
          fullTranscript,
          detectedLanguage,
          duration,
          cost,
          JSON.stringify(responseJson),
        ],
      );

      const sttItem = sttItemRes.rows[0];

      // Insert stt_logs for audit
      const wordCount = fullTranscript
        ? fullTranscript.split(/\s+/).filter(Boolean).length
        : 0;

      await client.query(
        `
        INSERT INTO stt_logs (
          stt_item_id, user_id, workspace_id,
          words_count, duration_seconds, cost_usd
        )
        VALUES ($1, $2, $3, $4, $5, $6)
        `,
        [sttItem.id, userId, workspaceId, wordCount, duration, cost],
      );

      await client.query("COMMIT");

      res.status(201).json({
        success: true,
        message: "Realtime session saved",
        data: {
          id: sttItem.id,
          hash_id: sttItem.hash_id,
        },
      });
    } catch (error) {
      await client.query("ROLLBACK");
      console.error("Save realtime STT error:", error);
      res
        .status(500)
        .json({ success: false, message: "Internal server error" });
    } finally {
      client.release();
    }
  }

  // POST /stt/batch
  async batchTranscribe(req, res) {
    try {
      const { files } = req.body; // Array of file URLs
      const userId = req.user.id;

      if (!Array.isArray(files) || files.length === 0) {
        return res.status(400).json({ error: "Files array is required" });
      }

      if (files.length > 10) {
        return res
          .status(400)
          .json({ error: "Maximum 10 files allowed per batch" });
      }

      // TODO: Implement batch processing logic
      // For now, return batch job ID
      const batchId = uuidv4();

      res.status(202).json({
        batch_id: batchId,
        status: "queued",
        files_count: files.length,
        message: "Batch transcription job created",
      });
    } catch (error) {
      console.error("Batch STT error:", error);
      res.status(500).json({ error: "Internal server error" });
    }
  }

  // GET /stt/batch/:batchId
  async getBatchStatus(req, res) {
    try {
      const { batchId } = req.params;

      // TODO: Implement actual batch status checking from database/Redis
      res.status(200).json({
        success: true,
        message: "Batch status retrieved successfully",
        batch_id: batchId,
        status: "processing",
        completed: 3,
        total: 5,
        results: [],
      });
    } catch (error) {
      console.error("Get batch status error:", error);
      res
        .status(500)
        .json({ success: false, message: "Internal server error" });
    }
  }

  // GET /stt/models
  //
  // Static catalog of the STT transcription models exposed to clients. The
  // current backend runs a single non-hallucinating multi-backend stack
  // surfaced as one model ID. Adding more entries later is a matter of
  // extending this array — no schema changes required.
  async getSTTModels(req, res) {
    try {
      const models = [
        {
          id: "60db-stt-v01",
          model_name: "60db STT v01",
          description:
            "Non-hallucinating speech recognition supporting 39 languages with auto-detection, speaker diarization, and real-time streaming",
          category: "speech-to-text",
          type: "stt",
          languages: 39,
          features: [
            "auto_language_detection",
            "speaker_diarization",
            "word_timestamps",
            "code_switching_indic_english",
            "continuous_mode",
            "telephony_mulaw",
            "websocket_streaming",
          ],
        },
      ];

      res.status(200).json({
        success: true,
        message: "STT models fetched successfully",
        data: models,
      });
    } catch (error) {
      console.error("Get STT models error:", error);
      res
        .status(500)
        .json({ success: false, message: "Internal server error" });
    }
  }

  // GET /stt/languages
  async getSupportedLanguages(req, res) {
    try {
      const response = await axios.get(`${process.env.STT_API_URL}/v1/languages`);

      // STT Labs v1 returns { v1_languages: { en: { name, ... } }, total_languages, features, ... }
      // Transform to a flat [{ code, name, native, code_switching }] list with `auto` prepended.
      const v1 = response.data?.v1_languages || {};
      const languages = [
        { code: "auto", name: "Auto-detect", native: "Auto", code_switching: false },
        ...Object.entries(v1).map(([code, meta]) => ({
          code,
          name: meta?.name || code,
          native: meta?.name || code,
          code_switching: meta?.code_switching || false,
          wer_target: meta?.wer_target,
        })),
      ];

      res.status(200).json({
        success: true,
        message: "Languages retrieved successfully",
        data: {
          languages,
          total: languages.length,
          features: response.data?.features || {},
        },
      });
    } catch (error) {
      console.error("Get languages error:", error.message);
      res.status(502).json({
        success: false,
        message: "Failed to fetch languages from external provider",
        error: error.message,
      });
    }
  }

  // POST /stt/bulk-delete
  async bulkDeleteSTT(req, res) {
    const client = await db.pool.connect();

    try {
      await client.query("BEGIN");

      const { ids } = req.body;
      const userId = req.user.id;

      if (!Array.isArray(ids) || ids.length === 0) {
        return res
          .status(400)
          .json({ success: false, message: "ids array is required" });
      }

      if (ids.length > 100) {
        return res
          .status(400)
          .json({ success: false, message: "Maximum 100 records per bulk delete" });
      }

      // Soft delete stt_items owned by the user
      const result = await client.query(
        `
        UPDATE stt_item
        SET deleted_at = NOW()
        WHERE hash_id = ANY($1::uuid[])
          AND user_id = $2
          AND deleted_at IS NULL
        RETURNING id
      `,
        [ids, userId],
      );

      if (result.rows.length === 0) {
        await client.query("ROLLBACK");
        return res
          .status(404)
          .json({ success: false, message: "No matching STT records found" });
      }

      // Also soft delete related stt_logs
      const deletedItemIds = result.rows.map((r) => r.id);
      await client.query(
        `
        UPDATE stt_logs
        SET deleted_at = NOW()
        WHERE stt_item_id = ANY($1::int[])
          AND deleted_at IS NULL
      `,
        [deletedItemIds],
      );

      await client.query("COMMIT");

      res.status(200).json({
        success: true,
        message: `${result.rows.length} STT record(s) deleted successfully`,
        deleted_count: result.rows.length,
      });
    } catch (error) {
      await client.query("ROLLBACK");
      console.error("Bulk delete STT error:", error);
      res
        .status(500)
        .json({ success: false, message: "Internal server error" });
    } finally {
      client.release();
    }
  }
}

module.exports = new STTController();
