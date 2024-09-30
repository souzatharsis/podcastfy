import google.generativeai as genai
import logging

logger = logging.getLogger(__name__)

class ContentGenerator:
	def __init__(self, api_key):
		self.api_key = api_key
		genai.configure(api_key=self.api_key)
		self.model = genai.GenerativeModel('gemini-pro')

	def generate_qa_content(self, input_texts, duration_minutes=5):
		try:
			combined_input = "\n\n".join(input_texts)
			prompt = f"""
			Generate a Q&A conversation that summarizes the following content in a fun, engaging, and informative way.
			The conversation should last about {duration_minutes} minutes when spoken.
			Use <Question> and <Answer> tags to delimit question and answer blocks.

			Content to summarize:
			{combined_input}
			"""

			response = self.model.generate_content(prompt)
			return self.format_qa_content(response.text)
		except Exception as e:
			logger.error(f"Error generating content: {str(e)}")
			raise

	def format_qa_content(self, content):
		formatted_content = content.replace("Question:", "<Question>")
		formatted_content = formatted_content.replace("Answer:", "<Answer>")
		formatted_content = formatted_content.replace("\n<Question>", "</Answer>\n<Question>")
		formatted_content = formatted_content.replace("\n<Answer>", "</Question>\n<Answer>")
		return f"{formatted_content}</Answer>"

# ... (add more methods as needed)