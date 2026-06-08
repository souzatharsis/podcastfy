const express = require('express');
const http = require('http');
const WebSocket = require('ws');
const { STTProxySession, TTSProxySession } = require('../services/websocketProxyService');
const { authenticateWebSocketAny, checkWebSocketCredits } = require('../middleware/websocketAuth');
const { tryAcquire, limits: concurrencyLimits } = require('../middleware/concurrencyLimiter');

const router = express.Router();

/**
 * Initialize WebSocket server on the main HTTP server
 * This should be called from server.js after the HTTP server is created
 */
function initializeWebSocketServer(server) {
  console.log('[WebSocket] Initializing WebSocket server on path /ws...');

  const wss = new WebSocket.Server({
    server,
    // Don't set path - handle it manually
    verifyClient: async (info, cb) => {
      // Check if the path starts with /ws
      const pathname = new URL(info.req.url, `http://${info.req.headers.host}`).pathname;
      if (!pathname.startsWith('/ws')) {
        console.log('[WebSocket] Rejecting connection to non-/ws path:', pathname);
        return cb(false, 403, 'Path not allowed');
      }
      cb(true);
    }
  });

  console.log('[WebSocket] WebSocket server created successfully');

  // Track active connections
  const activeConnections = new Map();

  wss.on('connection', (ws, req) => {
    console.log('[WebSocket] Raw URL:', req.url);
    console.log('[WebSocket] Headers:', JSON.stringify(req.headers, null, 2));

    const pathname = new URL(req.url, `http://${req.headers.host}`).pathname;

    console.log(`[WebSocket] New connection to ${pathname}`);

    // Handle based on path
    if (pathname === '/ws/stt') {
      handleSTTConnection(ws, req, activeConnections);
    } else if (pathname === '/ws/tts') {
      handleTTSConnection(ws, req, activeConnections);
    } else if (pathname === '/ws/health') {
      handleHealthCheck(ws);
    } else {
      console.log('[WebSocket] Unknown path, closing connection');
      ws.close(1008, 'Unknown WebSocket path');
    }
  });

  // Cleanup interval
  setInterval(() => {
    const now = Date.now();
    for (const [id, session] of activeConnections.entries()) {
      if (session.isStale && now - session.lastActivity > 300000) { // 5 minutes
        console.log(`[WebSocket] Cleaning up stale connection ${id}`);
        session.cleanup();
        activeConnections.delete(id);
      }
    }
  }, 60000); // Check every minute

  console.log('[WebSocket] WebSocket server initialized on path /ws');
  return wss;
}

/**
 * Handle STT WebSocket connection
 */
function handleSTTConnection(ws, req, activeConnections) {
  console.log(`[STT WebSocket] New connection, WS state: ${ws.readyState}`);

  // Send acknowledgment immediately
  setImmediate(() => {
    if (ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({
        type: 'connecting',
        message: 'Authenticating...',
        timestamp: Date.now()
      }), (err) => {
        if (err) {
          console.error(`[STT WebSocket] Error sending connecting message:`, err);
        } else {
          console.log(`[STT WebSocket] Sent connecting message successfully`);
        }
      });
    }
  });

  // Run authentication asynchronously
  (async () => {
    let releaseSlot = null;
    let slotReleased = false;
    const safeReleaseSlot = () => {
      if (slotReleased || !releaseSlot) return;
      slotReleased = true;
      releaseSlot();
    };

    try {
      // Authenticate connection
      const authenticated = await authenticateWebSocketAny(ws, req);

      if (!authenticated || !ws.user) {
        console.log(`[STT WebSocket] Authentication failed`);
        if (ws.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify({
            type: 'error',
            error: 'Authentication failed',
            error_code: 'AUTH_FAILED'
          }));
          ws.close(1008, 'Authentication failed');
        }
        return;
      }

      console.log(`[STT WebSocket] User ${ws.user.id} authenticated, WS state: ${ws.readyState}`);

      // Check if client still connected
      if (ws.readyState !== WebSocket.OPEN) {
        console.log(`[STT WebSocket] Client disconnected during auth`);
        return;
      }

      // Check credits
      const hasCredits = await checkWebSocketCredits(ws);
      if (!hasCredits) {
        return;
      }

      // Acquire a concurrency slot (counted across REST + WS)
      releaseSlot = tryAcquire('stt', ws.user.id);
      if (!releaseSlot) {
        if (ws.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify({
            type: 'error',
            error: 'Too many concurrent STT sessions for this user',
            error_code: 'STT_CONCURRENCY_LIMIT',
            details: { limit: concurrencyLimits.stt },
          }));
          ws.close(1008, 'Concurrency limit exceeded');
        }
        return;
      }

      console.log(`[STT WebSocket] User ${ws.user.id} passed checks, WS state: ${ws.readyState}`);

      // Create STT proxy session — resolve workspace from auth context or query params
      const sttWsParams = new URL(req.url, `http://${req.headers.host}`).searchParams;
      const sttWorkspaceId = ws.user.current_workspace?.workspace_id || sttWsParams.get('workspace_id') || null;
      const session = new STTProxySession(
        ws,
        ws.user.id,
        sttWorkspaceId
      );

      // Track session
      const connectionId = `stt-${ws.user.id}-${Date.now()}`;
      activeConnections.set(connectionId, {
        type: 'STT',
        userId: ws.user.id,
        session,
        lastActivity: Date.now(),
        isStale: false,
        cleanup: () => { safeReleaseSlot(); session.cleanup(); },
      });

      // Start session and wait for 60db connection
      console.log(`[STT WebSocket] Starting 60db connection...`);
      try {
        await session.start();
        console.log(`[STT WebSocket] 60db connection established`);

        // Send welcome message AFTER session is ready
        if (ws.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify({
            type: 'connection_established',
            service: 'stt',
            user_id: ws.user.id,
            credit_balance: ws.user.credit_balance,
            workspace: ws.user.current_workspace?.workspace_name || null
          }));
          console.log(`[STT WebSocket] Welcome message sent, WS state: ${ws.readyState}`);
        } else {
          console.log(`[STT WebSocket] Client closed before welcome could be sent`);
          return;
        }
      } catch (error) {
        console.error(`[STT WebSocket] Session start failed:`, error.message);
        safeReleaseSlot();
        if (ws.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify({
            type: 'error',
            error: 'Failed to connect to STT service',
            details: error.message
          }));
        }
        return;
      }

      // Handle cleanup on close
      ws.on('close', () => {
        safeReleaseSlot();
        activeConnections.delete(connectionId);
        console.log(`[STT WebSocket] User ${ws.user.id} disconnected`);
      });

    } catch (error) {
      console.error(`[STT WebSocket] Handler error:`, error);
      safeReleaseSlot();
      if (ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({
          type: 'error',
          error: 'Internal server error',
          details: error.message
        }));
        ws.close(1011, 'Internal server error');
      }
    }
  })();
}

/**
 * Handle TTS WebSocket connection
 */
function handleTTSConnection(ws, req, activeConnections) {
  console.log(`[TTS WebSocket] New connection, WS state: ${ws.readyState}`);

  // Send acknowledgment immediately
  setImmediate(() => {
    if (ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({
        connecting: true,
        message: 'Authenticating...',
        timestamp: Date.now()
      }), (err) => {
        if (err) {
          console.error(`[TTS WebSocket] Error sending connecting message:`, err);
        } else {
          console.log(`[TTS WebSocket] Sent connecting message successfully`);
        }
      });
    }
  });

  // Run authentication asynchronously
  (async () => {
    let releaseSlot = null;
    let slotReleased = false;
    const safeReleaseSlot = () => {
      if (slotReleased || !releaseSlot) return;
      slotReleased = true;
      releaseSlot();
    };

    try {
      // Authenticate connection
      const authenticated = await authenticateWebSocketAny(ws, req);

      if (!authenticated || !ws.user) {
        console.log(`[TTS WebSocket] Authentication failed`);
        if (ws.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify({
            error: {
              message: 'Authentication failed',
              code: 'AUTH_FAILED'
            }
          }));
          ws.close(1008, 'Authentication failed');
        }
        return;
      }

      console.log(`[TTS WebSocket] User ${ws.user.id} (${ws.user.email}) authenticated, WS state: ${ws.readyState}`);

      // Check if client still connected
      if (ws.readyState !== WebSocket.OPEN) {
        console.log(`[TTS WebSocket] Client disconnected during auth`);
        return;
      }

      // Check credits
      const hasCredits = await checkWebSocketCredits(ws);
      if (!hasCredits) {
        return;
      }

      // Acquire a concurrency slot (counted across REST + WS)
      releaseSlot = tryAcquire('tts', ws.user.id);
      if (!releaseSlot) {
        if (ws.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify({
            error: {
              message: 'Too many concurrent TTS sessions for this user',
              code: 'TTS_CONCURRENCY_LIMIT',
              details: { limit: concurrencyLimits.tts },
            },
          }));
          ws.close(1008, 'Concurrency limit exceeded');
        }
        return;
      }

      console.log(`[TTS WebSocket] User ${ws.user.id} passed checks, WS state: ${ws.readyState}`);

      // Create TTS proxy session — resolve workspace from auth context or query params
      const ttsWsParams = new URL(req.url, `http://${req.headers.host}`).searchParams;
      const ttsWorkspaceId = ws.user.current_workspace?.workspace_id || ttsWsParams.get('workspace_id') || null;
      const session = new TTSProxySession(
        ws,
        ws.user.id,
        ttsWorkspaceId
      );

      // Track session
      const connectionId = `tts-${ws.user.id}-${Date.now()}`;
      activeConnections.set(connectionId, {
        type: 'TTS',
        userId: ws.user.id,
        session,
        lastActivity: Date.now(),
        isStale: false,
        cleanup: () => { safeReleaseSlot(); session.cleanup(); },
      });

      // Start session and wait for 60db connection
      console.log(`[TTS WebSocket] Starting 60db connection...`);
      try {
        await session.start();
        console.log(`[TTS WebSocket] 60db connection established`);

        // Send welcome message AFTER session is ready
        if (ws.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify({
            connection_established: {
              service: 'tts',
              user_id: ws.user.id,
              credit_balance: ws.user.credit_balance,
              workspace: ws.user.current_workspace?.workspace_name || null
            }
          }));
          console.log(`[TTS WebSocket] Welcome message sent, WS state: ${ws.readyState}`);
        } else {
          console.log(`[TTS WebSocket] Client closed before welcome could be sent`);
          return;
        }
      } catch (error) {
        console.error(`[TTS WebSocket] Session start failed:`, error.message);
        safeReleaseSlot();
        if (ws.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify({
            error: {
              message: 'Failed to connect to TTS service',
              details: error.message
            }
          }));
        }
        return;
      }

      // Handle cleanup on close
      ws.on('close', () => {
        safeReleaseSlot();
        activeConnections.delete(connectionId);
        console.log(`[TTS WebSocket] User ${ws.user.id} disconnected`);
      });

    } catch (error) {
      console.error(`[TTS WebSocket] Handler error:`, error);
      safeReleaseSlot();
      if (ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({
          error: {
            message: 'Internal server error',
            details: error.message
          }
        }));
        ws.close(1011, 'Internal server error');
      }
    }
  })();
}

/**
 * Handle health check connection
 */
function handleHealthCheck(ws) {
  ws.send(JSON.stringify({
    status: 'healthy',
    services: {
      stt: 'available',
      tts: 'available'
    },
    timestamp: new Date().toISOString()
  }));
  ws.close();
}

// Test endpoint to verify WebSocket server status
router.get('/ws/status', (req, res) => {
  // This will be set by initializeWebSocketServer
  const wsServerStatus = req.app.get('wsServer') ? 'initialized' : 'not initialized';
  res.json({
    success: true,
    websocket_server: wsServerStatus,
    timestamp: new Date().toISOString()
  });
});

// HTTP routes for WebSocket info
router.get('/ws/info', (req, res) => {
  res.json({
    success: true,
    websocket_endpoints: {
      stt: {
        url: process.env.API_BASE_URL
          ? `${process.env.API_BASE_URL.replace('http', 'ws')}/ws/stt`
          : 'ws://localhost:3000/ws/stt',
        protocol: 'WebSocket',
        authentication: 'JWT Bearer token or API key',
        description: 'Speech-to-Text bidirectional streaming',
        pricing: {
          rate_per_second: 0.00000833,
          rate_per_minute: 0.0005,
          currency: 'USD'
        },
        concurrency_limit: {
          per_user: concurrencyLimits.stt,
          scope: 'Counted across REST /stt and WebSocket /ws/stt combined.',
          rejection_code: 'STT_CONCURRENCY_LIMIT',
          rejection_status: 429,
        },
        documentation: '/docs/websocket-stt'
      },
      tts: {
        url: process.env.API_BASE_URL
          ? `${process.env.API_BASE_URL.replace('http', 'ws')}/ws/tts`
          : 'ws://localhost:3000/ws/tts',
        protocol: 'WebSocket',
        authentication: 'JWT Bearer token or API key',
        description: 'Text-to-Speech bidirectional streaming',
        pricing: {
          rate_per_character: 0.00002,
          rate_per_million_characters: 20,
          currency: 'USD'
        },
        concurrency_limit: {
          per_user: concurrencyLimits.tts,
          scope: 'Counted across REST /tts, /tts-synthesize, /tts-stream, and WebSocket /ws/tts combined.',
          rejection_code: 'TTS_CONCURRENCY_LIMIT',
          rejection_status: 429,
        },
        documentation: '/docs/websocket-tts'
      },
      health: {
        url: process.env.API_BASE_URL
          ? `${process.env.API_BASE_URL.replace('http', 'ws')}/ws/health`
          : 'ws://localhost:3000/ws/health',
        description: 'Health check endpoint'
      }
    },
    authentication: {
      jwt: {
        header: 'Authorization: Bearer <token>',
        query_param: '?token=<token>'
      },
      api_key: {
        query_param: '?apiKey=<api_key>'
      }
    },
    examples: {
      javascript: `
// STT Example
const sttWs = new WebSocket('wss://api.qallabs.ai/ws/stt?token=YOUR_JWT_TOKEN');

sttWs.onopen = () => {
  // Start STT session
  sttWs.send(JSON.stringify({
    type: 'start',
    languages: ['en', 'hi'],
    config: {
      encoding: 'mulaw',
      sample_rate: 8000,
      continuous_mode: true
    }
  }));
};

sttWs.onmessage = (event) => {
  const data = JSON.parse(event.data);
  if (data.type === 'transcription' && data.is_final) {
    console.log('Transcription:', data.text);
  }
};

// Send audio
sttWs.send(audioData);

// TTS Example
const ttsWs = new WebSocket('wss://api.qallabs.ai/ws/tts?token=YOUR_JWT_TOKEN');

ttsWs.onopen = () => {
  // Create TTS context
  ttsWs.send(JSON.stringify({
    create_context: {
      context_id: 'session-1',
      voice_id: '7911a3e8',
      audio_config: {
        audio_encoding: 'LINEAR16',
        sample_rate_hertz: 16000
      }
    }
  }));
};

ttsWs.onmessage = (event) => {
  const data = JSON.parse(event.data);
  if (data.audio_chunk) {
    // Process audio chunk
    const audioData = atob(data.audio_chunk.audioContent);
    // Play audio...
  }
};

// Send text for synthesis
ttsWs.send(JSON.stringify({
  send_text: {
    context_id: 'session-1',
    text: 'Hello, how are you?'
  }
}));

ttsWs.send(JSON.stringify({
  flush_context: { context_id: 'session-1' }
}));
      `
    }
  });
});

module.exports = {
  router,
  initializeWebSocketServer
};
