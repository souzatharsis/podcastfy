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

def main(seed=42):
	"""
	Test the YouTubeTranscriber class with a specific URL and save the transcript.

	Args:
		seed (int): Random seed for reproducibility. Defaults to 42.
	"""
	url = "https://www.youtube.com/watch?v=nFbJCoTK0_g"
	transcriber = YouTubeTranscriber()

	try:
		transcript = transcriber.extract_transcript(url)
		print("Transcript extracted successfully.")
		
		# Save transcript to file
		output_file = 'tests/data/transcripts/youtube_transcript2.txt'
		with open(output_file, 'w') as file:
			file.write(transcript)
		
		print(f"Transcript saved to {output_file}")
		print("First 500 characters of the transcript:")
		print(transcript[:500] + "..." if len(transcript) > 500 else transcript)
	except Exception as e:
		logger.error(f"An error occurred: {str(e)}")
		raise

if __name__ == "__main__":
	main()