"""
FastAPI implementation for Podcastify podcast generation service.

This module provides REST endpoints for podcast generation and audio serving,
with configuration management and temporary file handling.
"""

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import Response, JSONResponse
import os
import yaml
from typing import Dict, Any
from pathlib import Path
from ..client import generate_podcast
import uvicorn
import logging
import sys
import signal

# Configure logging to stdout
logging.basicConfig(stream=sys.stdout, level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def load_base_config() -> Dict[Any, Any]:
    config_path = Path(__file__).parent / "podcastfy" / "conversation_config.yaml"
    try:
        with open(config_path, 'r') as file:
            return yaml.safe_load(file)
    except Exception as e:
        print(f"Warning: Could not load base config: {e}")
        return {}

def merge_configs(base_config: Dict[Any, Any], user_config: Dict[Any, Any]) -> Dict[Any, Any]:
    """Merge user configuration with base configuration, preferring user values."""
    merged = base_config.copy()
    
    # Handle special cases for nested dictionaries
    if 'text_to_speech' in merged and 'text_to_speech' in user_config:
        merged['text_to_speech'].update(user_config.get('text_to_speech', {}))
    
    # Update top-level keys
    for key, value in user_config.items():
        if key != 'text_to_speech':  # Skip text_to_speech as it's handled above
            if value is not None:  # Only update if value is not None
                merged[key] = value
                
    return merged

def handle_sigterm(signum, frame):
    logger.info("Received SIGTERM, shutting down gracefully.")
    sys.exit(0)

signal.signal(signal.SIGTERM, handle_sigterm)

print("=== fast_app.py is being loaded ===")

app = FastAPI()
print("=== FastAPI app object created ===")

TEMP_DIR = os.path.join(os.path.dirname(__file__), "temp_audio")
os.makedirs(TEMP_DIR, exist_ok=True)

@app.middleware("http")
async def verify_token(request: Request, call_next):
    # Skip token verification for health check endpoint
    if request.url.path == "/health":
        return await call_next(request)
        
    token = request.headers.get("X-Podpod-Access-Token")
    if not token or token != os.getenv("PODPOD_API_ACCESS_TOKEN"):
        return JSONResponse(
            status_code=401,
            content={"message": "Invalid or missing access token"}
        )
    return await call_next(request)


@app.post("/generate")
async def generate_podcast_endpoint(data: dict):
    """"""
    try:
        # Load base configuration
        base_config = load_base_config()
        
        # Get TTS model and its configuration from base config
        tts_model = data.get('tts_model', base_config.get('text_to_speech', {}).get('default_tts_model', 'openai'))
        tts_base_config = base_config.get('text_to_speech', {}).get(tts_model, {})

        # Get voices (use user-provided voices or fall back to defaults)
        voices = data.get('voices', {})
        default_voices = tts_base_config.get('default_voices', {})

        logger.info(f"Using TTS model: {tts_model}")
        logger.info(f"Voices - Question: {voices.get('question', default_voices.get('question'))}, Answer: {voices.get('answer', default_voices.get('answer'))}")
        
        # Prepare user configuration
        user_config = {
            'creativity': float(data.get('creativity', base_config.get('creativity', 0.7))),
            'conversation_style': data.get('conversation_style', base_config.get('conversation_style', [])),
            'roles_person1': data.get('roles_person1', base_config.get('roles_person1')),
            'roles_person2': data.get('roles_person2', base_config.get('roles_person2')),
            'dialogue_structure': data.get('dialogue_structure', base_config.get('dialogue_structure', [])),
            'podcast_name': data.get('name', base_config.get('podcast_name')),
            'podcast_tagline': data.get('tagline', base_config.get('podcast_tagline')),
            'output_language': data.get('output_language', base_config.get('output_language', 'English')),
            'user_instructions': data.get('user_instructions', base_config.get('user_instructions', '')),
            'engagement_techniques': data.get('engagement_techniques', base_config.get('engagement_techniques', [])),
            'text_to_speech': {
                'default_tts_model': tts_model,
                'model': tts_base_config.get('model'),
                'default_voices': {
                    'question': voices.get('question', default_voices.get('question')),
                    'answer': voices.get('answer', default_voices.get('answer'))
                }
            }
        }

        # Merge configurations
        conversation_config = merge_configs(base_config, user_config)

        # Generate podcast
        result = generate_podcast(
            urls=data.get('urls', []),
            conversation_config=conversation_config,
            tts_model=tts_model,
            longform=bool(data.get('is_long_form', False)),
        )

        # Handle the result and return raw audio data
        if isinstance(result, str) and os.path.isfile(result):
            with open(result, 'rb') as audio_file:
                audio_data = audio_file.read()
                # Clean up the temporary file
                os.remove(result)
                return Response(
                    content=audio_data,
                    media_type="audio/mpeg",
                    headers={
                        "Content-Type": "audio/mpeg",
                        "Content-Length": str(len(audio_data))
                    }
                )
        elif hasattr(result, 'audio_path'):
            with open(result.audio_path, 'rb') as audio_file:
                audio_data = audio_file.read()
                # Clean up the temporary file
                os.remove(result.audio_path)
                return Response(
                    content=audio_data,
                    media_type="audio/mpeg",
                    headers={
                        "Content-Type": "audio/mpeg",
                        "Content-Length": str(len(audio_data))
                    }
                )
        else:
            raise HTTPException(status_code=500, detail="Invalid result format")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def healthcheck():
    logger.info("/health endpoint called")
    try:
        # Check if temp directory exists and is writable
        if not os.path.exists(TEMP_DIR):
            os.makedirs(TEMP_DIR, exist_ok=True)
        
        # Try to write a test file
        test_file = os.path.join(TEMP_DIR, "health_check.txt")
        with open(test_file, "w") as f:
            f.write("health check")
        os.remove(test_file)
        
        return {
            "status": "healthy",
            "temp_dir": TEMP_DIR,
            "temp_dir_writable": True,
            "environment": {
                "python_version": os.sys.version,
                "working_directory": os.getcwd(),
                "environment_variables": {
                    "OPENAI_API_KEY": bool(os.getenv("OPENAI_API_KEY")),
                    "GEMINI_API_KEY": bool(os.getenv("GEMINI_API_KEY"))
                }
            }
        }
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    logger.info("Starting FastAPI application...")
    logger.info(f"Current working directory: {os.getcwd()}")
    logger.info(f"Environment variables loaded: {bool(os.getenv('OPENAI_API_KEY'))}")
    
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", 8080))
    
    logger.info(f"Starting server on {host}:{port}")
    uvicorn.run(app, host=host, port=port)
