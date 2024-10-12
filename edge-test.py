from podcastfy.client import generate_podcast

audio_file = generate_podcast(urls=["https://en.wikipedia.org/wiki/Podcast"], tts_model="edge-tts")