import logging
import argparse
from podcastfy.content_parser.content_extractor import ContentExtractor
from podcastfy.genai_podcast.content_generator import ContentGenerator
from podcastfy.audio.text_to_speech import TextToSpeech
from podcastfy.utils.config import Config
from podcastfy.utils.logger import setup_logger
import os
import uuid

logger = setup_logger(__name__)

def process_links(links, transcript_file=None, tts_model='openai'):
	"""
	Process a list of links or a transcript file to generate a podcast.

	Args:
		links (list): A list of URLs to process.
		transcript_file (str): Path to a transcript file (optional).
		tts_model (str): The TTS model to use ('openai' or 'elevenlabs'). Defaults to 'openai'.

	Returns:
		str: Path to the final podcast audio file.
	"""
	try:
		config = Config()
		text_to_speech = TextToSpeech(model=tts_model, api_key=getattr(config, f'{tts_model.upper()}_API_KEY'))

		if transcript_file:
			logger.info(f"Using transcript file: {transcript_file}")
			with open(transcript_file, 'r') as file:
				qa_content = file.read()
		else:
			logger.info(f"Processing {len(links)} links")
			content_extractor = ContentExtractor(config.JINA_API_KEY)
			content_generator = ContentGenerator(config.GEMINI_API_KEY)

			# Extract content from links
			contents = []
			for link in links:
				content = content_extractor.extract_content(link)
				contents.append(content)

			# Combine all extracted content
			combined_content = "\n\n".join(contents)

			# Generate Q&A content
			random_filename = f"transcript_{uuid.uuid4().hex}.txt"
			output_filepath = os.path.join("tests", "data", "transcripts", random_filename)
			qa_content = content_generator.generate_qa_content(combined_content, output_filepath=output_filepath)

		# Convert text to speech using the specified model
		random_filename = f"podcast_{uuid.uuid4().hex}.mp3"
		text_to_speech.convert_to_speech(qa_content, random_filename)

		logger.info(f"Podcast generated successfully using {tts_model} TTS model")
		return random_filename

	except Exception as e:
		logger.error(f"An error occurred in the process_links function: {str(e)}")
		raise

def main():
	parser = argparse.ArgumentParser(description="Generate a podcast from a list of URLs or a transcript file.")
	parser.add_argument("-f", "--file", help="File containing URLs, one per line")
	parser.add_argument("-t", "--transcript", help="Path to a transcript file")
	parser.add_argument("-m", "--tts-model", choices=['openai', 'elevenlabs'], default='openai',
						help="TTS model to use (openai or elevenlabs)")
	parser.add_argument("urls", nargs="*", help="List of URLs to process")
	args = parser.parse_args()

	try:
		if args.transcript:
			if not os.path.exists(args.transcript):
				raise FileNotFoundError(f"Transcript file not found: {args.transcript}")
			final_podcast = process_links([], transcript_file=args.transcript, tts_model=args.tts_model)
		else:
			urls = []
			if args.file:
				with open(args.file, 'r') as f:
					urls = [line.strip() for line in f if line.strip()]
			urls.extend(args.urls)

			if not urls:
				raise ValueError("No URLs provided. Use -f to specify a file, provide URLs as arguments, or use -t for a transcript file.")

			final_podcast = process_links(urls, tts_model=args.tts_model)

		print(f"Podcast generated successfully using {args.tts_model} TTS model: {final_podcast}")

	except Exception as e:
		logger.error(f"An error occurred in the main process: {str(e)}")

if __name__ == "__main__":
	main()