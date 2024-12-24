import os
import pytest
from fastapi.testclient import TestClient
from podcastfy.api.fast_app import app

client = TestClient(app)

@pytest.fixture
def sample_config():
    return {
        "generate_podcast": True,
        "urls": ["https://www.phenomenalworld.org/interviews/swap-structure/"],
        "name": "Central Clearing Risks",
        "tagline": "Exploring the complexities of financial systemic risk",
        "creativity": 0.8,
        "conversation_style": ["engaging", "informative"],
        "roles_person1": "main summarizer",
        "roles_person2": "questioner",
        "dialogue_structure": ["Introduction", "Content", "Conclusion"],
        "tts_model": "edge",
        "is_long_form": False,
        "engagement_techniques": ["questions", "examples", "analogies"],
        "user_instructions": "Don't use the word Dwelve",
        "output_language": "English"
    }

pytest.mark.skip(reason="Trying to understand if other tests are passing")
def test_generate_podcast_with_edge_tts(sample_config):
    response = client.post("/generate", json=sample_config)
    assert response.status_code == 200
    assert "audioUrl" in response.json()
    assert response.json()["audioUrl"].startswith("http://localhost:8080")

def test_generate_podcast_invalid_data():
    response = client.post("/generate", json={})
    assert response.status_code == 422

def test_healthcheck():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}

def test_generate_podcast_with_empty_urls(sample_config):
    sample_config["urls"] = []
    response = client.post("/generate", json=sample_config)
    assert response.status_code == 422

def test_generate_podcast_with_invalid_tts_model(sample_config):
    sample_config["tts_model"] = "invalid"
    response = client.post("/generate", json=sample_config)
    assert response.status_code == 422

if __name__ == "__main__":
    pytest.main()