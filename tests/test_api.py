import os
import pytest
from podcastfy.api.fast_app import app
from httpx import WSGITransport
from fastapi.testclient import TestClient

client = TestClient(app, transport=WSGITransport(app=app))

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

@pytest.mark.skip(reason="Trying to understand if other tests are passing")
def test_generate_podcast_with_edge_tts(sample_config):
    response = client.post("/generate", json=sample_config)
    assert response.status_code == 200
    assert "audioUrl" in response.json()
    assert response.json()["audioUrl"].startswith("http://testserver")

def test_healthcheck():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


if __name__ == "__main__":
    pytest.main()