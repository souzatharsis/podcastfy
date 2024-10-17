from podcastfy.client import generate_podcast

# Replace <url1> and <url2> with actual URLs you want to convert to audio
urls = ["https://blog.google/technology/ai/notebooklm-audio-overviews/", 
        "https://blog.google/technology/ai/notebooklm-audio-overviews/",
        "https://darioamodei.com/machines-of-loving-grace"]

# Generate the podcast
audio_file = generate_podcast(urls=urls)

print(f"Podcast generated successfully: {audio_file}")