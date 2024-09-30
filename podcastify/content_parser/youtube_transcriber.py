from youtube_transcript_api import YouTubeTranscriptApi
import logging

logger = logging.getLogger(__name__)

class YouTubeTranscriber:
	def extract_transcript(self, url):
		"""
		Extract transcript from a YouTube video.

		Args:
			url (str): YouTube video URL.

		Returns:
			str: Extracted transcript.
		"""
		try:
			video_id = url.split("v=")[-1]
			transcript = YouTubeTranscriptApi.get_transcript(video_id)
			return " ".join([entry['text'] for entry in transcript])
		except Exception as e:
			logger.error(f"Error extracting YouTube transcript: {str(e)}")
			raise