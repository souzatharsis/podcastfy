const db = require("../config/database");
const path = require("path");
const axios = require("axios");
// Stripe Connect removed per D9 — replaced by synth_events + settler
const fs = require("fs");
const fetch = require("node-fetch");
const creditDeduction = require("../utils/creditDeduction");
const SERVICE_PRICES = require("../constants/servicePrices");
const s3Service = require("../services/s3Service");

class TTSController {
  // POST /tts
  // need to add usage and cost related logic in this if we are going to use this api. we are not using this api. We are using streamTTS
  async generateSpeech(req, res) {
    try {
      // Validate minimal input
      const {
        text,
        voice,
        stream = true,
        response_format = "mp3",
        sample_rate = 24000,
        normalization = true,
        speed = 1,
        enhance = false,
      } = req.body;

      if (!text || !voice) {
        return res.status(400).json({
          success: false,
          message: "`text` and `voice` are required in request body",
        });
      }

      // Build payload exactly as specified
      const qcallPayload = {
        text,
        voice,
        stream: !!stream,
        response_format,
        sample_rate,
        normalization: !!normalization,
        speed,
      };
      if (enhance) qcallPayload.enhance = true;

      const qcallUrl = `${process.env.TTS_API_URL}/v1/text-to-speech`;

      // Tenant label for upstream metrics. Resolve from cerbos principal /
      // workspace context with safe fallbacks.
      const ttsTenantId =
        req.cerbosPrincipal?.attr?.workspace_id ||
        req.user?.workspace_id ||
        req.user?.current_workspace?.workspace_id ||
        req.body?.workspace_id ||
        req.user?.id;
      const headers = {
        "Content-Type": "application/json",
      };
      if (process.env.QCALL_TTS_API_KEY) {
        headers["Authorization"] = `Bearer ${process.env.QCALL_TTS_API_KEY}`;
        // Or use x-api-key if provider expects that:
        // headers["x-api-key"] = process.env.QCALL_TTS_API_KEY;
      }
      if (ttsTenantId) headers["X-Tenant-Id"] = String(ttsTenantId);

      if (qcallPayload.stream) {
        // Stream response and pipe to client
        const providerResp = await axios({
          method: "post",
          url: qcallUrl,
          data: qcallPayload,
          headers,
          responseType: "stream",
          timeout: 120000,
        });

        // Forward status and relevant headers
        res.status(providerResp.status);
        // forward content-type and content-length if present
        if (providerResp.headers["content-type"]) {
          res.setHeader("Content-Type", providerResp.headers["content-type"]);
        }
        if (providerResp.headers["content-length"]) {
          res.setHeader(
            "Content-Length",
            providerResp.headers["content-length"],
          );
        }
        // optionally forward other safe headers (e.g. cache-control)
        if (providerResp.headers["cache-control"]) {
          res.setHeader("Cache-Control", providerResp.headers["cache-control"]);
        }

        // Pipe provider stream directly to the client response
        providerResp.data.pipe(res);

        // handle provider stream errors
        providerResp.data.on("error", (err) => {
          console.error("Provider stream error:", err);
          // if headers not sent, send 502
          if (!res.headersSent) {
            res
              .status(502)
              .json({ success: false, message: "Provider stream error" });
          } else {
            // if headers already sent, forcibly end connection
            try {
              res.end();
            } catch (e) {
              console.warn("Error ending response after stream error:", e);
            }
          }
        });

        return; // streaming response is being piped
      } else {
        // Non-streaming: get arraybuffer and forward binary + headers
        const providerResp = await axios({
          method: "post",
          url: qcallUrl,
          data: qcallPayload,
          headers,
          responseType: "arraybuffer",
          timeout: 120000,
        });

        // If provider returned JSON (e.g. error), try to parse and forward it
        const contentType = providerResp.headers["content-type"] || "";
        if (contentType.includes("application/json")) {
          // parse JSON and forward with provider status
          const text = Buffer.from(providerResp.data).toString("utf8");
          let json;
          try {
            json = JSON.parse(text);
          } catch (e) {
            json = { raw: text };
          }
          return res.status(providerResp.status).json({
            success: true,
            message: "TTS generated successfully",
            json,
          });
        }

        // otherwise respond with binary audio
        res.status(providerResp.status);
        if (providerResp.headers["content-type"]) {
          res.setHeader("Content-Type", providerResp.headers["content-type"]);
        } else {
          res.setHeader("Content-Type", `audio/${response_format}`);
        }
        if (providerResp.headers["content-length"]) {
          res.setHeader(
            "Content-Length",
            providerResp.headers["content-length"],
          );
        }

        return res.send(Buffer.from(providerResp.data));
      }
    } catch (err) {
      console.error(
        "generateSpeech (simple) error:",
        err?.response?.data || err.message || err,
      );
      // If provider returned an error body, forward it
      if (err.response) {
        const status = err.response.status || 502;
        // If provider returned JSON error, forward it
        const ct = err.response.headers?.["content-type"] || "";
        if (ct.includes("application/json")) {
          return res.status(status).json(err.response.data);
        }
        // otherwise return provider raw text
        const raw = err.response.data
          ? Buffer.isBuffer(err.response.data)
            ? err.response.data.toString("utf8")
            : err.response.data
          : err.message;
        return res.status(status).json({ success: false, message: raw });
      }

      return res.status(502).json({
        success: false,
        message: "Failed to call TTS provider",
        details: err.message,
      });
    }
  }

  _calculateCost(provider, textLength) {
    return textLength * SERVICE_PRICES.TTS.RATE_PER_CHAR;
  }

  // This one does not use streams, returns base64 as per new API (synthesize-json api)
  // This one does not use streams, returns base64 as per new API (synthesize-json api)
  async synthesizeTTS(req, res) {
    const client = await db.pool.connect();
    const userId = req.user.id; // Store user ID for later use in credit deduction
    let cancelled = false;
    let ttsLog = null;

    try {
      const {
        text,
        voice_id,
        sample_rate = 48000,
        speed = 1,
        stability = 50,
        similarity = 75,
        model_id = "indic_tts_v1",
        audio_encoding = "LINEAR16",
      } = req.body;

      if (!text) {
        return res
          .status(400)
          .json({ success: false, message: "text is required" });
      }

      // 1. Determine Identity for External API
      const externalVoiceId = voice_id;

      // 2. Determine Identity for Internal DB Log
      let dbVoiceId = null;

      try {
        if (
          !isNaN(externalVoiceId) &&
          Number.isInteger(Number(externalVoiceId))
        ) {
          const checkRes = await client.query(
            "SELECT id FROM voices WHERE id = $1",
            [externalVoiceId],
          );
          if (checkRes.rows.length > 0) dbVoiceId = parseInt(externalVoiceId);
        } else {
          const checkRes = await client.query(
            "SELECT id FROM voices WHERE name = $1 LIMIT 1",
            [externalVoiceId],
          );
          if (checkRes.rows.length > 0) dbVoiceId = checkRes.rows[0].id;
        }
      } catch (lookupErr) {}

      const executorUserId = req.user.id;
      const workspaceId = req.cerbosPrincipal?.attr?.workspace_id || req.user?.workspace_id || req.user?.current_workspace?.workspace_id || req.body?.workspace_id;

      if (!workspaceId) {
        return res
          .status(400)
          .json({ success: false, message: "Workspace required" });
      }

      const textLength = text.length;

      // =====================================
      // CREDIT CHECK — before upstream call
      // Uses the SAME rate as the actual deduction (textLength * 0.0002)
      // so the pre-flight check and the post-hoc deduction agree.
      // =====================================
      const ttsCost = creditDeduction.calculateTTSCost(textLength);
      const creditCheck = await creditDeduction.checkCredits(workspaceId, ttsCost);

      if (!creditCheck.sufficient) {
        return creditDeduction.insufficientCreditsResponse(
          res,
          ttsCost,
          creditCheck.currentBalance,
          creditCheck.shortfall
        );
      }

      await client.query("BEGIN");

      // =====================================
      // 1️⃣ Resolve billing owner
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
      // 2️⃣ Create TTS log (AUDIT = executor)
      // Pay-as-you-go: no plan-level character cap.
      // =====================================
      const logRes = await client.query(
        `
      INSERT INTO tts_logs (
        workspace_id,
        user_id,
        voice_id,
        input_text,
        characters,
        status,
        api_key_id
      )
      VALUES ($1, $2, $3, $4, $5, 'processing', $6)
      RETURNING id, hash_id
      `,
        [
          workspaceId,
          executorUserId,
          dbVoiceId,
          text,
          textLength,
          req.apiKey ? req.apiKey.id : null,
        ],
      );

      ttsLog = logRes.rows[0];

      await client.query("COMMIT");

      // =====================================
      // 5️⃣ Set up streaming headers
      // =====================================
      res.setHeader("Transfer-Encoding", "chunked");
      res.setHeader("Cache-Control", "no-cache, no-transform");
      res.setHeader("Connection", "keep-alive");
      res.setHeader("X-Accel-Buffering", "no");

      // =====================================
      // 6️⃣ Call external TTS provider and stream response
      // =====================================
      const apiPayload = {
        text: text,
        voice_id: externalVoiceId || "1a8c6331-c79b-47d3-9893-09160a245a3e",
        model_id: model_id || "indic_tts_v1",
        audio_config: {
          audio_encoding: audio_encoding || "LINEAR16",
          sample_rate_hertz: sample_rate || 48000,
        },
        speed: speed !== undefined ? speed : 1,
        stability: stability !== undefined ? stability : 50,
        similarity: similarity !== undefined ? similarity : 75,
      };

      const ttsResponse = await fetch(
        `${process.env.TTS_API_URL}/tts/v1/voice:stream`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify(apiPayload),
        },
      );

      if (!ttsResponse.ok || !ttsResponse.body) {
        const errorText = await ttsResponse.text();
        console.error("TTS Provider Error:", errorText);
        res.setHeader("Content-Type", "application/json");
        res.status(ttsResponse.status).json({
          success: false,
          message: `TTS provider failed with status ${ttsResponse.status}`,
        });
        return;
      }

      // Forward content-type from TTS provider
      const providerContentType = ttsResponse.headers.get("content-type");
      if (providerContentType) {
        res.setHeader("Content-Type", providerContentType);
      } else {
        // Default to WAV based on LINEAR16 encoding
        res.setHeader("Content-Type", "audio/wav");
      }

      // Handle client disconnection
      req.on("close", () => {
        cancelled = true;
        ttsResponse.body.destroy();
      });

      // =====================================
      // 7️⃣ Stream audio chunks to client
      // =====================================
      let totalBytes = 0;

      for await (const chunk of ttsResponse.body) {
        if (cancelled) break;

        totalBytes += chunk.length;

        // Forward raw chunks as received from TTS provider
        res.write(chunk);
      }

      if (cancelled) {
        console.log("Stream cancelled by client");
        return res.end();
      }

      // =====================================
      // 8️⃣ Calculate duration and finalize
      // =====================================
      const sampleRate = sample_rate || 48000;
      const durationSeconds = totalBytes / (sampleRate * 2);

      // =====================================
      // 9️⃣ Update Usage and TTS Log
      // =====================================
      const client2 = await db.pool.connect();
      try {
        await client2.query("BEGIN");

        const costUsd = creditDeduction.calculateTTSCost(textLength);
        const today = new Date().toISOString().split("T")[0];

        await client2.query(
          `
        UPDATE tts_logs
        SET status = 'completed',
            duration_seconds = $1,
            cost_usd = $2
        WHERE id = $3
        `,
          [durationSeconds, costUsd, ttsLog.id],
        );

        await client2.query(
          `
        INSERT INTO usage_summary (
          user_id,
          workspace_id,
          usage_date,
          tts_characters,
          cost_usd
        )
        VALUES ($1, $2, $3, $4, $5)
        ON CONFLICT (user_id, workspace_id, usage_date)
        DO UPDATE SET
          tts_characters = usage_summary.tts_characters + EXCLUDED.tts_characters,
          cost_usd = usage_summary.cost_usd + EXCLUDED.cost_usd
        `,
          [billingOwnerId, workspaceId, today, textLength, costUsd],
        );

        // =====================================
        // CREDIT DEDUCTION (Workspace Wallet)
        // Atomic with usage_summary on the same client2 transaction.
        // =====================================
        await creditDeduction.deductCredits({
          userId: executorUserId,
          serviceType: "TTS",
          amountDeducted: costUsd,
          unitsUsed: textLength,
          workspaceId: workspaceId,
          billingOwnerId: billingOwnerId,
          client: client2,
        });
        console.log(`Deducted $${costUsd.toFixed(6)} for TTS (${textLength} chars) from workspace ${workspaceId}`);

        await client2.query("COMMIT");
      } catch (err) {
        await client2.query("ROLLBACK");
        console.error("Failed to update TTS usage:", err);
      } finally {
        client2.release();
      }

      console.log("=== TTS Stream Complete ===");
      console.log("Total bytes streamed:", totalBytes);

      return res.end();
    } catch (error) {
      console.error("=== synthesizeTTS Error ===");
      console.error("Error type:", error.constructor.name);
      console.error("Error message:", error.message);
      console.error("Stack:", error.stack);

      // Update TTS log status to failed if we have a log ID
      if (ttsLog && ttsLog.id) {
        try {
          await client.query(
            "UPDATE tts_logs SET status = 'failed' WHERE id = $1",
            [ttsLog.id],
          );
        } catch (updateErr) {
          console.error("Failed to update TTS log status:", updateErr);
        }
      }

      if (!res.headersSent) {
        res.status(500).json({
          success: false,
          message: "Internal error",
          error: error.message,
        });
      }
    } finally {
      client.release();
    }
  }

  // updated streamTTS function for stream-json
  async streamTTS(req, res) {
    const client = await db.pool.connect();
    let cancelled = false;

    try {
      const {
        text,
        voice_id,
        sample_rate = 44100,
        output_format = "wav",
        cfg_value = 3,
        encoding = "linear",
        inference_timesteps = 30,
        speed = 1,
      } = req.body;

      if (!text) {
        return res
          .status(400)
          .json({ success: false, message: "text is required" });
      }

      const executorUserId = req.user.id;
      const workspaceId = req.cerbosPrincipal?.attr?.workspace_id || req.user?.workspace_id || req.user?.current_workspace?.workspace_id || req.body?.workspace_id;

      if (!workspaceId) {
        return res
          .status(400)
          .json({ success: false, message: "Workspace required" });
      }

      const textLength = text.length;

      // =====================================
      // CREDIT CHECK (New System)
      // =====================================
      const ttsCost = creditDeduction.calculateTTSCost(textLength);

      // Check if workspace has sufficient credits
      const creditCheck = await creditDeduction.checkCredits(workspaceId, ttsCost);

      if (!creditCheck.sufficient) {
        return creditDeduction.insufficientCreditsResponse(
          res,
          ttsCost,
          creditCheck.currentBalance,
          creditCheck.shortfall
        );
      }

      await client.query("BEGIN");

      // =====================================
      // 1️⃣ Resolve billing owner
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
      // 2️⃣ Create TTS log (AUDIT = executor)
      // Pay-as-you-go: no plan-level character cap.
      // =====================================
      const logRes = await client.query(
        `
      INSERT INTO tts_logs (
        workspace_id,
        user_id,
        input_text,
        characters,
        status
      )
      VALUES ($1, $2, $3, $4, 'processing')
      RETURNING id, hash_id
      `,
        [workspaceId, executorUserId, text, textLength],
      );

      ttsLog = logRes.rows[0];

      await client.query("COMMIT");

      // =====================================
      // 5️⃣ Streaming headers
      // =====================================
      res.setHeader("Content-Type", "application/json");
      res.setHeader("Transfer-Encoding", "chunked");
      res.setHeader("Cache-Control", "no-cache, no-transform");
      res.setHeader("Connection", "keep-alive");
      res.setHeader("X-Accel-Buffering", "no");

      // res.write(
      //   JSON.stringify({
      //     type: "meta",
      //     characters: textLength,
      //     log_id: ttsLog.hash_id,
      //   }) + "\n"
      // );

      // =====================================
      // 6️⃣ Call external TTS provider
      // =====================================
      const ttsResponse = await fetch(
        `${process.env.TTS_API_URL}/v1/tts/stream-json`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${process.env.QCALL_TTS_API_KEY}`,
            "X-Tenant-Id": String(workspaceId),
          },
          body: JSON.stringify({
            text,
            voice_id,
            sample_rate,
            output_format,
            cfg_value,
            encoding,
            inference_timesteps,
            speed,
          }),
        },
      );

      if (!ttsResponse.ok || !ttsResponse.body) {
        res.write(
          JSON.stringify({ type: "error", message: "TTS provider error" }) +
            "\n",
        );
        return res.end();
      }

      req.on("close", () => {
        cancelled = true;
        ttsResponse.body.destroy();
      });

      let buffer = "";

      ttsResponse.body.on("data", (chunk) => {
        if (cancelled) return;

        buffer += chunk.toString("utf8");
        const lines = buffer.split("\n");
        buffer = lines.pop() || "";

        for (const line of lines) {
          if (line.trim()) res.write(line + "\n");
        }
      });

      // =====================================
      // 7️⃣ On stream end → update usage
      // =====================================
      ttsResponse.body.on("end", async () => {
        if (buffer.trim()) res.write(buffer + "\n");

        if (!cancelled) {
          const client2 = await db.pool.connect();
          try {
            await client2.query("BEGIN");

            const durationEstimate = textLength * 0.05;
            const costUsd = ttsCost;
            const today = new Date().toISOString().split("T")[0];

            await client2.query(
              `
            UPDATE tts_logs
            SET status = 'completed',
                duration_seconds = $1,
                cost_usd = $2
            WHERE id = $3
            `,
              [durationEstimate, costUsd, ttsLog.id],
            );

            await client2.query(
              `
            INSERT INTO usage_summary (
              user_id,
              workspace_id,
              usage_date,
              tts_characters,
              cost_usd
            )
            VALUES ($1, $2, $3, $4, $5)
            ON CONFLICT (user_id, workspace_id, usage_date)
            DO UPDATE SET
              tts_characters = usage_summary.tts_characters + EXCLUDED.tts_characters,
              cost_usd = usage_summary.cost_usd + EXCLUDED.cost_usd
            `,
              [billingOwnerId, workspaceId, today, textLength, costUsd],
            );

            // =====================================
            // CREDIT DEDUCTION (Workspace Wallet)
            // Atomic with usage_summary on the same client2 transaction.
            // =====================================
            await creditDeduction.deductCredits({
              userId: executorUserId,
              serviceType: "TTS",
              amountDeducted: ttsCost,
              unitsUsed: textLength,
              workspaceId: workspaceId,
              billingOwnerId: billingOwnerId,
              client: client2,
            });
            console.log(`Deducted $${ttsCost.toFixed(6)} for TTS (${textLength} chars) from workspace ${workspaceId}`);

            // =====================================
            // 8️⃣ Professional Cloning: record synth event for the settler
            // Revenue share (12% of paid_portion) is computed by
            // cron/voiceRevenueSettler.js once per minute. No synchronous
            // Stripe transfer here — the manual payout flow handles
            // disbursement on the 1st of each month.
            //
            // TODO: bucket attribution. Until creditDeduction middleware
            // reports per-bucket spend (paid top-up vs signup vs referral),
            // we pass the full cost as paid_portion_cents. Once that's wired,
            // split values must come through so signup/referral credit
            // doesn't generate creator payouts (D/A6).
            // =====================================
            try {
              // Look up the numeric voice.id from the voice_id text handle.
              const voiceRes = await client2.query(
                "SELECT id FROM voices WHERE voice_id = $1 AND deleted_at IS NULL",
                [voice_id],
              );
              const numericVoiceId = voiceRes.rows[0]?.id ?? null;
              const paidCents = Math.round(costUsd * 100);

              await client2.query(
                `INSERT INTO synth_events (
                   user_id, workspace_id, voice_id,
                   chars_synthesized, paid_portion_cents,
                   signup_credit_portion_cents, referral_credit_portion_cents
                 ) VALUES ($1, $2, $3, $4, $5, 0, 0)`,
                [executorUserId, workspaceId, numericVoiceId, textLength, paidCents],
              );
            } catch (synthLogErr) {
              console.error("synth_events insert error:", synthLogErr);
              // Do not fail the request — settler runs next minute
            }

            await client2.query("COMMIT");
          } catch (err) {
            await client2.query("ROLLBACK");
            console.error("Failed to update TTS usage:", err);
          } finally {
            client2.release();
          }
        }

        res.end();
      });

      ttsResponse.body.on("error", () => {
        if (!res.headersSent) {
          res
            .status(502)
            .json({ success: false, message: "TTS provider stream error" });
        }
      });
    } catch (error) {
      console.error("streamTTS error:", error);

      if (!res.headersSent) {
        res.status(500).json({ success: false, message: "Internal error" });
      }
    } finally {
      client.release();
    }
  }

  // GET /tts/logs
  async getTTSLogs(req, res) {
    try {
      const userId = req.user.id;
      const {
        workspace_id,
        page = 1,
        limit = 20,
        voice_id,
        date_from,
        date_to,
        status,
      } = req.query;

      const offset = (page - 1) * limit;

      let query = `
        SELECT tl.id, tl.hash_id, tl.input_text, tl.output_url,
               tl.characters, tl.duration_seconds, tl.cost_usd,
               tl.status, tl.error_message, tl.created_at, tl.updated_at,
               v.name as voice_name, v.language as voice_language,
               v.provider, w.name as workspace_name
        FROM tts_logs tl
        LEFT JOIN voices v ON tl.voice_id = v.id
        JOIN workspace w ON tl.workspace_id = w.id
        WHERE tl.user_id = $1 AND tl.deleted_at IS NULL
      `;

      const params = [userId];
      let paramIndex = 2;

      if (workspace_id) {
        query += ` AND tl.workspace_id = $${paramIndex}`;
        params.push(workspace_id);
        paramIndex++;
      }

      if (voice_id) {
        query += ` AND tl.voice_id = $${paramIndex}`;
        params.push(voice_id);
        paramIndex++;
      }

      if (status) {
        query += ` AND tl.status = $${paramIndex}`;
        params.push(status);
        paramIndex++;
      }

      if (date_from) {
        query += ` AND tl.created_at >= $${paramIndex}`;
        params.push(date_from);
        paramIndex++;
      }

      if (date_to) {
        query += ` AND tl.created_at <= $${paramIndex}`;
        params.push(date_to);
        paramIndex++;
      }

      query += ` ORDER BY tl.created_at DESC LIMIT $${paramIndex} OFFSET $${
        paramIndex + 1
      }`;
      params.push(limit, offset);

      const result = await db.query(query, params);

      // Get total count for pagination
      let countQuery = `
        SELECT COUNT(*) as total
        FROM tts_logs tl
        WHERE tl.user_id = $1 AND tl.deleted_at IS NULL
      `;

      const countParams = [userId];
      let countParamIndex = 2;

      if (workspace_id) {
        countQuery += ` AND tl.workspace_id = $${countParamIndex}`;
        countParams.push(workspace_id);
        countParamIndex++;
      }

      if (voice_id) {
        countQuery += ` AND tl.voice_id = $${countParamIndex}`;
        countParams.push(voice_id);
        countParamIndex++;
      }

      if (status) {
        countQuery += ` AND tl.status = $${countParamIndex}`;
        countParams.push(status);
        countParamIndex++;
      }

      if (date_from) {
        countQuery += ` AND tl.created_at >= $${countParamIndex}`;
        countParams.push(date_from);
        countParamIndex++;
      }

      if (date_to) {
        countQuery += ` AND tl.created_at <= $${countParamIndex}`;
        countParams.push(date_to);
        countParamIndex++;
      }

      const countResult = await db.query(countQuery, countParams);
      const total = parseInt(countResult.rows[0].total);

      res.status(200).json({
        success: true,
        message: "TTS logs retrieved successfully",
        logs: result.rows,
        pagination: {
          page: parseInt(page),
          limit: parseInt(limit),
          total,
          pages: Math.ceil(total / limit),
        },
      });
    } catch (error) {
      console.error("Get TTS logs error:", error);
      res
        .status(500)
        .json({ success: false, message: "Internal server error" });
    }
  }

  // GET /tts/:id
  async getTTSDetail(req, res) {
    try {
      const { id } = req.params;
      const userId = req.user.id;

      const result = await db.query(
        `
        SELECT tl.*, v.name as voice_name, v.language as voice_language,
               v.dialect as voice_dialect, v.provider, w.name as workspace_name
        FROM tts_logs tl
        JOIN voices v ON tl.voice_id = v.id
        JOIN workspace w ON tl.workspace_id = w.id
        WHERE (tl.hash_id = $1 OR tl.id = $1)
              AND tl.user_id = $2 AND tl.deleted_at IS NULL
      `,
        [id, userId],
      );

      if (result.rows.length === 0) {
        return res
          .status(404)
          .json({ success: false, message: "TTS record not found" });
      }

      res.status(200).json({
        success: true,
        message: "TTS record retrieved successfully",
        data: result.rows[0],
      });
    } catch (error) {
      console.error("Get TTS detail error:", error);
      res
        .status(500)
        .json({ success: false, message: "Internal server error" });
    }
  }

  // DELETE /tts/:id
  async deleteTTS(req, res) {
    try {
      const { id } = req.params;
      const userId = req.user.id;

      const result = await db.query(
        `
        UPDATE tts_logs
        SET deleted_at = NOW()
        WHERE (hash_id = $1 OR id = $1) AND user_id = $2 AND deleted_at IS NULL
        RETURNING id, output_url
      `,
        [id, userId],
      );

      if (result.rows.length === 0) {
        return res.status(404).json({ error: "TTS record not found" });
      }

      // Delete the audio file (S3 or legacy local)
      const { output_url } = result.rows[0];
      if (output_url) {
        try {
          const s3Key = s3Service.keyFromUrl(output_url);
          if (s3Key) {
            await s3Service.deleteObject(s3Key);
            console.log(`Deleted S3 object: ${s3Key}`);
          } else if (output_url.startsWith("/uploads/")) {
            const filePath = path.join(process.cwd(), output_url);
            await fs.promises.unlink(filePath);
            console.log(`Deleted legacy audio file: ${filePath}`);
          }
        } catch (err) {
          console.error("Error deleting audio file:", err);
          // Don't fail the request if file deletion fails
        }
      }

      res.status(200).json({
        success: true,
        message: "TTS record deleted successfully",
        status: "deleted",
      });
    } catch (error) {
      console.error("Delete TTS error:", error);
      res
        .status(500)
        .json({ success: false, message: "Internal server error" });
    }
  }

  // GET /tts/languages — lists the 30 voice languages supported by the TTS
  // service. Distinct from /stt/languages which lists the 39 STT languages.
  async getTTSLanguages(req, res) {
    try {
      const response = await axios.get(`${process.env.TTS_API_URL}/v1/languages`, {
        headers: { accept: "application/json" },
      });
      // TTS backend returns a flat array `[{language_id, name}, ...]`.
      // Pass it through so existing voice-selection UIs keep working.
      res.status(200).json({
        success: true,
        message: "TTS languages retrieved successfully",
        data: response.data,
      });
    } catch (error) {
      console.error("Get TTS languages error:", error.message);
      res.status(502).json({
        success: false,
        message: "Failed to fetch TTS languages from external provider",
        error: error.message,
      });
    }
  }

  async categories(req, res) {
    try {
      const qcallUrl = `${process.env.TTS_API_URL}/v1/categories`;

      const providerResp = await axios({
        method: "get",
        url: qcallUrl,
        timeout: 30000,
      });

      return res.status(providerResp.status).json({
        success: true,
        data: providerResp.data,
      });
    } catch (err) {
      console.error("categories error:", err?.response?.data || err.message || err);

      if (err.response) {
        const status = err.response.status || 502;
        const ct = err.response.headers?.["content-type"] || "";
        if (ct.includes("application/json")) {
          return res.status(status).json(err.response.data);
        }
        const raw = err.response.data
          ? Buffer.isBuffer(err.response.data)
            ? err.response.data.toString("utf8")
            : err.response.data
          : err.message;
        return res.status(status).json({ success: false, message: raw });
      }

      return res.status(502).json({
        success: false,
        message: "Failed to fetch categories",
        details: err.message,
      });
    }
  }
}

module.exports = new TTSController();
