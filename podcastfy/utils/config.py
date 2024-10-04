import os
from dotenv import load_dotenv

class Config:
	def __init__(self):
		load_dotenv()
		
		self.JINA_API_KEY = os.getenv("JINA_API_KEY")
		self.GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
		self.OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
		self.ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
		
		# Default output directories
		self.TRANSCRIPT_OUTPUT_DIR = os.getenv("TRANSCRIPT_OUTPUT_DIR", "./")
		self.AUDIO_OUTPUT_DIR = os.getenv("AUDIO_OUTPUT_DIR", "./")
		
		# Ensure output directories exist
		os.makedirs(self.TRANSCRIPT_OUTPUT_DIR, exist_ok=True)
		os.makedirs(self.AUDIO_OUTPUT_DIR, exist_ok=True)

def load_config():
	"""
	Load and return a Config instance.

	Returns:
		Config: An instance of the Config class.
	"""
	return Config()

def main(seed=42):
	"""
	Test the Config class and print configuration status.

	Args:
		seed (int): Random seed for reproducibility. Defaults to 42.
	"""
	# Create an instance of the Config class
	config = load_config()
	
	# Test each configuration value
	print("Testing Config class:")
	print(f"EMAIL_ADDRESS: {'Set' if config.get('EMAIL_ADDRESS') else 'Not set'}")
	print(f"EMAIL_PASSWORD: {'Set' if config.get('EMAIL_PASSWORD') else 'Not set'}")
	print(f"JINA_API_KEY: {'Set' if config.get('JINA_API_KEY') else 'Not set'}")
	print(f"GEMINI_API_KEY: {'Set' if config.get('GEMINI_API_KEY') else 'Not set'}")
	print(f"ELEVENLABS_API_KEY: {'Set' if config.get('ELEVENLABS_API_KEY') else 'Not set'}")
	print(f"OPENAI_API_KEY: {'Set' if config.get('OPENAI_API_KEY') else 'Not set'}")

	# Print a warning for any missing configuration
	missing_config = []
	for key in ['EMAIL_ADDRESS', 'EMAIL_PASSWORD', 'JINA_API_KEY', 'GEMINI_API_KEY', 'ELEVENLABS_API_KEY', 'OPENAI_API_KEY']:
		if not config.get(key):
			missing_config.append(key)

	if missing_config:
		print("\nWarning: The following configuration values are missing:")
		for config_name in missing_config:
			print(f"- {config_name}")
		print("Please ensure these are set in your .env file.")
	else:
		print("\nAll configuration values are set.")

	# Test the get method with a default value
	print(f"\nTesting get method with default value:")
	print(f"NON_EXISTENT_KEY: {config.get('NON_EXISTENT_KEY', 'Default Value')}")

if __name__ == "__main__":
	main()