/**
 * Centralized Service Pricing
 *
 * Single source of truth for every service rate (USD).
 * Update prices HERE — all consumers reference this file.
 */

const SERVICE_PRICES = {
  TTS: {
    RATE_PER_CHAR: 0.00002, // Default rate: $20 per 1M characters
  },
  STT: {
    RATE_PER_MINUTE: 0.006,       // $0.006 per minute
    RATE_PER_SECOND: 0.006 / 60, // derived from per-minute rate
    DIARIZE_SURCHARGE: 0.3,     // +30% surcharge when diarization is used
  },
  LLM: {
    RATE_PER_TOKEN: 0.00002, // ~$0.02 per 1,000 tokens
    INPUT_RATE_PER_MILLION: 0.01, // $0.01 per 1M input tokens
    OUTPUT_RATE_PER_MILLION: 0.01, // $0.01 per 1M output tokens
  },
  MEMORY: {
    INGEST_PER_1K_CHARS: 0.0001, // $0.10 per 1M chars
    EXTRACT_PER_MB: 0.003, // $0.003 per MB
    RECALL_PER_QUERY: 0.0003, // $0.30 per 1,000 queries
    CONTEXT_PER_QUERY: 0.0005, // $0.50 per 1,000 queries
  },
  SIGNUP_BONUS_CREDITS: 10.0,
};

module.exports = SERVICE_PRICES;
