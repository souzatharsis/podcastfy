import os
import pytest
from fastapi.testclient import TestClient
from podcastfy.main import app  # Adjust the import based on your FastAPI app location

client = TestClient(app)

@pytest.fixture
def sample_config():
    # Load your sample configuration here
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
        "tts_model": "edge",  # Specify the edge_tts model here
        "is_long_form": False,
        "engagement_techniques": ["questions", "examples", "analogies"],
        "user_instructions": "Dont use the world Dwelve",
        "output_language": "English"
    }

def test_generate_podcast_with_edge_tts(sample_config):
    """Test the podcast generation endpoint using the edge_tts model."""
    response = client.post("/generate", json=sample_config)
    
    assert response.status_code == 200
    assert "audioUrl" in response.json()
    assert response.json()["audioUrl"].startswith("http://localhost:8080")  # Adjust based on your actual URL

def test_generate_podcast_invalid_data():
    """Test the podcast generation with invalid data."""
    response = client.post("/generate", json={})  # Sending empty data
    assert response.status_code == 422  # Unprocessable Entity

def test_healthcheck():
    """Test the healthcheck endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}  # Adjust based on your actual healthcheck response

# Add more tests as needed for other endpoints or functionalities

if __name__ == "__main__":
    pytest.main()