import logging
from podcastify.user_bookmarks.bookmark_manager import BookmarkManager
from podcastify.content_parser.content_extractor import ContentExtractor
from podcastify.genai_podcast.content_generator import ContentGenerator
from podcastify.audio.text_to_speech import TextToSpeech
from podcastify.audio.audio_processor import AudioProcessor
from podcastify.utils.config import Config
from podcastify.utils.logger import setup_logger

logger = setup_logger(__name__)

def main():
	try:
		# Initialize components
		bookmark_manager = BookmarkManager(Config.EMAIL_ADDRESS, Config.EMAIL_PASSWORD)
		content_extractor = ContentExtractor(Config.JINA_API_KEY)
		content_generator = ContentGenerator(Config.GEMINI_API_KEY)
		text_to_speech = TextToSpeech(Config.ELEVENLABS_API_KEY)
		audio_processor = AudioProcessor()

		# Fetch bookmarks
		bookmarks = bookmark_manager.fetch_bookmarks()

		for user, links in bookmarks.items():
			logger.info(f"Processing bookmarks for user: {user}")

			# Extract content from links
			contents = []
			for link in links:
				content = content_extractor.extract_content(link)
				contents.append(content)

			# Generate Q&A content
			qa_content = content_generator.generate_qa_content(contents)

			# Convert text to speech
			audio_file = f"podcast_{user}.mp3"
			text_to_speech.convert_to_speech(qa_content, audio_file)

			# Process audio
			final_audio_file = f"final_podcast_{user}.mp3"
			audio_processor.process_audio(audio_file, final_audio_file)

			logger.info(f"Podcast generated for user: {user}")

			# TODO: Implement email sending functionality to send the final podcast to the user

	except Exception as e:
		logger.error(f"An error occurred in the main process: {str(e)}")

if __name__ == "__main__":
	main()