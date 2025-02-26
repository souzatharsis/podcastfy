"""
FastAPI implementation for Podcastify podcast generation service.

This module provides REST endpoints for podcast generation and audio serving,
with configuration management and temporary file handling.
"""

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse
import os
import shutil
import yaml
from typing import Dict, Any
from pathlib import Path
from ..client import generate_podcast
import uvicorn


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

app = FastAPI()

TEMP_DIR = os.path.join(os.path.dirname(__file__), "temp_audio")
os.makedirs(TEMP_DIR, exist_ok=True)

@app.post("/generate")
async def generate_podcast_endpoint(data: dict):
    """"""
    try:
        # Set environment variables
        os.environ['OPENAI_API_KEY'] = data.get('openai_key')
        os.environ['GEMINI_API_KEY'] = data.get('google_key')
        os.environ['ELEVENLABS_API_KEY'] = data.get('elevenlabs_key')

        # Load base configuration
        base_config = load_base_config()
        
        # Get TTS model and its configuration from base config
        tts_model = data.get('tts_model', base_config.get('text_to_speech', {}).get('default_tts_model', 'openai'))
        tts_base_config = base_config.get('text_to_speech', {}).get(tts_model, {})
        
        # Get voices (use user-provided voices or fall back to defaults)
        voices = data.get('voices', {})
        default_voices = tts_base_config.get('default_voices', {})
        
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

        # print(user_config)

        # Merge configurations
        conversation_config = merge_configs(base_config, user_config)

        # print(conversation_config)
        

        # Generate podcast
        result = generate_podcast(
            urls=data.get('urls', []),
            conversation_config=conversation_config,
            tts_model=tts_model,
            longform=bool(data.get('is_long_form', False)),
        )
        # Handle the result
        if isinstance(result, str) and os.path.isfile(result):
            filename = f"podcast_{os.urandom(8).hex()}.mp3"
            output_path = os.path.join(TEMP_DIR, filename)
            shutil.copy2(result, output_path)
            return {"audioUrl": f"/audio/{filename}"}
        elif hasattr(result, 'audio_path'):
            filename = f"podcast_{os.urandom(8).hex()}.mp3"
            output_path = os.path.join(TEMP_DIR, filename)
            shutil.copy2(result.audio_path, output_path)
            return {"audioUrl": f"/audio/{filename}"}
        else:
            raise HTTPException(status_code=500, detail="Invalid result format")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/audio/{filename}")
async def serve_audio(filename: str):
    """ Get File Audio From ther Server"""
    file_path = os.path.join(TEMP_DIR, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(file_path)

@app.get("/health")
async def healthcheck():
    return {"status": "healthy"}

if __name__ == "__main__":
    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", 8080))
    uvicorn.run(app, host=host, port=port)
