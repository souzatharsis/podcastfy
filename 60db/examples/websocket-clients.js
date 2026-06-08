/**
 * WebSocket Client Examples for QLabs API
 *
 * This file demonstrates how to connect to the QLabs WebSocket endpoints
 * for STT (Speech-to-Text) and TTS (Text-to-Speech) services.
 *
 * Prerequisites:
 * - Node.js with ws package: npm install ws
 * - Valid JWT token or API key
 */

const WebSocket = require('ws');

// Configuration
const API_BASE_URL = process.env.API_BASE_URL || 'ws://localhost:3000';
const JWT_TOKEN = process.env.JWT_TOKEN || 'YOUR_JWT_TOKEN';
const API_KEY = process.env.API_KEY || 'sk_your_api_key';

// ============================================================================
// STT (Speech-to-Text) Example
// ============================================================================

/**
 * Example 1: Basic STT session with JSON audio chunks (browser mode)
 */
function sttBasicExample() {
  const ws = new WebSocket(`${API_BASE_URL}/ws/stt?token=${JWT_TOKEN}`);

  ws.on('open', () => {
    console.log('[STT] Connected');

    // Start STT session
    ws.send(JSON.stringify({
      type: 'start',
      languages: ['en', 'hi'], // Auto-detect between English and Hindi
      config: {
        encoding: 'linear',     // Use 'mulaw' for telephony
        sample_rate: 48000,     // Match your audio source
        utterance_end_ms: 500,  // Silence duration before finalizing
        continuous_mode: true,  // Keep session alive between utterances
        interim_results_frequency: 300  // Send partial results every 300ms
      }
    }));
  });

  ws.on('message', (data) => {
    const message = JSON.parse(data);

    switch (message.type) {
      case 'connected':
        console.log('[STT] Server connected:', message.server_info);
        break;

      case 'session_started':
        console.log('[STT] Session started:', message.session_id);
        // Now you can start sending audio
        break;

      case 'speech_started':
        console.log('[STT] Speech detected at:', message.timestamp);
        break;

      case 'transcription':
        if (message.is_final) {
          console.log('[STT] Final:', message.text, '(confidence:', message.confidence + ')');
        } else {
          console.log('[STT] Interim:', message.text);
        }
        break;

      case 'error':
        console.error('[STT] Error:', message.error);
        break;

      case 'session_stopped':
        console.log('[STT] Session stopped');
        console.log('[STT] Billing:', message.billing_summary);
        ws.close();
        break;
    }
  });

  ws.on('error', (error) => {
    console.error('[STT] WebSocket error:', error);
  });

  ws.on('close', () => {
    console.log('[STT] Connection closed');
  });

  // Example: Send audio chunk (base64 encoded)
  // In a real application, you would capture audio from microphone or file
  // function sendAudioChunk(audioBase64) {
  //   ws.send(JSON.stringify({
  //     type: 'audio',
  //     audio: audioBase64,
  //     encoding: 'linear',
  //     sample_rate: 48000,
  //     timestamp: Date.now()
  //   }));
  // }

  // Stop session after some time
  // setTimeout(() => {
  //   ws.send(JSON.stringify({ type: 'stop' }));
  // }, 30000);
}

/**
 * Example 2: STT with binary audio (telephony mode)
 */
function sttBinaryExample() {
  const ws = new WebSocket(`${API_BASE_URL}/ws/stt?apiKey=${API_KEY}`, {
    binaryType: 'arraybuffer'
  });

  ws.on('open', () => {
    console.log('[STT Binary] Connected');

    // Start session
    ws.send(JSON.stringify({
      type: 'start',
      languages: ['en'],
      config: {
        encoding: 'mulaw',      // μ-law for telephony
        sample_rate: 8000,      // 8kHz for telephony
        continuous_mode: true
      }
    }));
  });

  ws.on('message', (data) => {
    try {
      const message = JSON.parse(data);
      if (message.type === 'transcription' && message.is_final) {
        console.log('[STT Binary] Transcription:', message.text);
      }
    } catch {
      // Binary data received (not expected in STT response)
    }
  });

  // Send binary μ-law audio chunks directly
  // function sendMulawChunk(mulawBuffer) {
  //   ws.send(mulawBuffer); // Send as binary frame
  // }

  return ws;
}

// ============================================================================
// TTS (Text-to-Speech) Example
// ============================================================================

/**
 * Example 3: Basic TTS session
 */
function ttsBasicExample() {
  const ws = new WebSocket(`${API_BASE_URL}/ws/tts?token=${JWT_TOKEN}`);

  const audioChunks = [];
  let contextId = 'my-session-' + Date.now();

  ws.on('open', () => {
    console.log('[TTS] Connected');

    // Create TTS context
    ws.send(JSON.stringify({
      create_context: {
        context_id: contextId,
        voice_id: '7911a3e8',  // Replace with your voice_id
        audio_config: {
          audio_encoding: 'LINEAR16',
          sample_rate_hertz: 16000
        },
        speed: 1,
        stability: 50,
        similarity: 75
      }
    }));
  });

  ws.on('message', (data) => {
    const message = JSON.parse(data);

    if (message.context_created) {
      console.log('[TTS] Context created:', message.context_created.context_id);

      // Send text for synthesis
      ws.send(JSON.stringify({
        send_text: {
          context_id: contextId,
          text: 'Hello, this is a test of the text-to-speech service.'
        }
      }));

      // Flush to start synthesis
      ws.send(JSON.stringify({
        flush_context: { context_id: contextId }
      }));
    }

    if (message.audio_chunk) {
      console.log('[TTS] Received audio chunk');
      // Collect audio chunks
      const binary = Buffer.from(message.audio_chunk.audioContent, 'base64');
      audioChunks.push(binary);
    }

    if (message.flush_completed) {
      console.log('[TTS] Synthesis completed, received', audioChunks.length, 'chunks');

      // Combine and save audio
      const combined = Buffer.concat(audioChunks);
      require('fs').writeFileSync('output.pcm', combined);
      console.log('[TTS] Audio saved to output.pcm');

      // Close context
      ws.send(JSON.stringify({
        close_context: { context_id: contextId }
      }));
    }

    if (message.context_closed) {
      console.log('[TTS] Context closed');
      ws.close();
    }

    if (message.error) {
      console.error('[TTS] Error:', message.error.message);
      ws.close();
    }
  });

  ws.on('error', (error) => {
    console.error('[TTS] WebSocket error:', error);
  });

  ws.on('close', () => {
    console.log('[TTS] Connection closed');
  });
}

/**
 * Example 4: TTS with streaming text (LLM token streaming)
 */
function ttsStreamingExample() {
  const ws = new WebSocket(`${API_BASE_URL}/ws/tts?token=${JWT_TOKEN}`);

  const audioChunks = [];
  let contextId = 'streaming-session-' + Date.now();

  ws.on('open', () => {
    console.log('[TTS Streaming] Connected');

    // Create context
    ws.send(JSON.stringify({
      create_context: {
        context_id: contextId,
        voice_id: '7911a3e8',
        audio_config: {
          audio_encoding: 'LINEAR16',
          sample_rate_hertz: 24000
        }
      }
    }));
  });

  ws.on('message', (data) => {
    const message = JSON.parse(data);

    if (message.context_created) {
      // Simulate LLM token streaming
      const tokens = ['Hello, ', 'how ', 'are ', 'you ', 'doing ', 'today?'];

      let i = 0;
      const interval = setInterval(() => {
        if (i < tokens.length) {
          ws.send(JSON.stringify({
            send_text: {
              context_id: contextId,
              text: tokens[i]
            }
          }));
          i++;
        } else {
          clearInterval(interval);
          // Flush after all tokens sent
          ws.send(JSON.stringify({
            flush_context: { context_id: contextId }
          }));
        }
      }, 100); // Send tokens every 100ms
    }

    if (message.audio_chunk) {
      audioChunks.push(Buffer.from(message.audio_chunk.audioContent, 'base64'));
    }

    if (message.flush_completed) {
      console.log('[TTS Streaming] Completed, received', audioChunks.length, 'chunks');
      ws.send(JSON.stringify({
        close_context: { context_id: contextId }
      }));
    }

    if (message.error) {
      console.error('[TTS Streaming] Error:', message.error.message);
    }
  });
}

// ============================================================================
// Browser Example (JavaScript)
// ============================================================================

/**
 * Example 5: Browser-based STT (copy this to your frontend code)
 */
function browserSTTExample() {
  /*
  // In your browser JavaScript:

  const sttWs = new WebSocket('wss://api.qallabs.ai/ws/stt?token=YOUR_JWT_TOKEN');

  // Audio recording setup
  navigator.mediaDevices.getUserMedia({ audio: true })
    .then(stream => {
      const mediaRecorder = new MediaRecorder(stream, {
        mimeType: 'audio/webm;codecs=opus',
        audioBitsPerSecond: 16000
      });

      mediaRecorder.ondataavailable = (event) => {
        // Convert to base64 and send
        const reader = new FileReader();
        reader.onloadend = () => {
          const base64 = reader.result.split(',')[1];
          sttWs.send(JSON.stringify({
            type: 'audio',
            audio: base64,
            encoding: 'linear',
            sample_rate: 48000,
            timestamp: Date.now()
          }));
        };
        reader.readAsDataURL(event.data);
      };

      // Start recording when STT session is ready
      sttWs.onmessage = (event) => {
        const data = JSON.parse(event.data);

        if (data.type === 'session_started') {
          mediaRecorder.start(250); // Send chunks every 250ms
        }

        if (data.type === 'transcription' && data.is_final) {
          console.log('Transcription:', data.text);
          // Display transcription in UI
        }
      };

      // Start STT session
      sttWs.onopen = () => {
        sttWs.send(JSON.stringify({
          type: 'start',
          languages: ['en'],
          config: {
            encoding: 'linear',
            sample_rate: 48000,
            continuous_mode: true
          }
        }));
      };
    });
  */
}

// ============================================================================
// Run Examples
// ============================================================================

// Uncomment to run examples:
// sttBasicExample();
// sttBinaryExample();
// ttsBasicExample();
// ttsStreamingExample();

module.exports = {
  sttBasicExample,
  sttBinaryExample,
  ttsBasicExample,
  ttsStreamingExample,
  browserSTTExample
};
