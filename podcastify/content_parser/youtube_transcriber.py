from youtube_transcript_api import YouTubeTranscriptApi
import logging

logger = logging.getLogger(__name__)

class YouTubeTranscriber:
	def extract_transcript(self, url):
		"""
		Extract transcript from a YouTube video and remove '[music]' tags (case-insensitive).

		Args:
			url (str): YouTube video URL.

		Returns:
			str: Cleaned and extracted transcript.
		"""
		try:
			video_id = url.split("v=")[-1]
			transcript = YouTubeTranscriptApi.get_transcript(video_id)
			cleaned_transcript = " ".join([entry['text'] for entry in transcript if entry['text'].lower() != '[music]'])
			return cleaned_transcript
		except Exception as e:
			logger.error(f"Error extracting YouTube transcript: {str(e)}")
			raise

def main():
	"""
	Test the YouTubeTranscriber class with a specific URL.
	"""
	url = "https://www.youtube.com/watch?v=m3kJo5kEzTQ"
	transcriber = YouTubeTranscriber()

	try:
		transcript = transcriber.extract_transcript(url)
		print("Transcript extracted successfully:")
		print(transcript[:500] + "..." if len(transcript) > 500 else transcript)
	except Exception as e:
		print(f"An error occurred: {str(e)}")

if __name__ == "__main__":
	main()