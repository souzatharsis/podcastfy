import logging
import argparse
from podcastfy.user_bookmarks.bookmark_manager import BookmarkManager
from podcastfy.content_parser.content_extractor import ContentExtractor
from podcastfy.genai_podcast.content_generator import ContentGenerator
from podcastfy.audio.text_to_speech import TextToSpeech
from podcastfy.audio.audio_processor import AudioProcessor
from podcastfy.utils.config import Config
from podcastfy.utils.logger import setup_logger

logger = setup_logger(__name__)

def process_links(links, user="test_user"):
	"""
	Process a list of links to generate a podcast.

	Args:
		links (list): A list of URLs to process.
		user (str): Username for the podcast file naming.

	Returns:
		str: Path to the final podcast audio file.
	"""
	try:
		# Initialize components
		content_extractor = ContentExtractor(Config.JINA_API_KEY)
		content_generator = ContentGenerator(Config.GEMINI_API_KEY)
		text_to_speech = TextToSpeech(Config.ELEVENLABS_API_KEY)
		audio_processor = AudioProcessor()

		logger.info(f"Processing {len(links)} links for user: {user}")

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
		return final_audio_file

	except Exception as e:
		logger.error(f"An error occurred in the process_links function: {str(e)}")
		raise

def main():
	parser = argparse.ArgumentParser(description="Generate a podcast from bookmarks or a list of links.")
	parser.add_argument("--links", nargs="+", help="Optional: List of URLs to process")
	args = parser.parse_args()

	try:
		if args.links:
			final_podcast = process_links(args.links)
			print(f"Podcast generated successfully: {final_podcast}")
		else:
			# Use BookmarkManager by default
			bookmark_manager = BookmarkManager(Config.EMAIL_ADDRESS, Config.EMAIL_PASSWORD)
			bookmarks = bookmark_manager.fetch_bookmarks()

			for user, links in bookmarks.items():
				logger.info(f"Processing bookmarks for user: {user}")
				final_podcast = process_links(links, user)
				logger.info(f"Podcast generated for user {user}: {final_podcast}")

				# TODO: Implement email sending functionality to send the final podcast to the user

	except Exception as e:
		logger.error(f"An error occurred in the main process: {str(e)}")

if __name__ == "__main__":
	main()