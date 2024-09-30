import os
from dotenv import load_dotenv

load_dotenv()

class Config:
	EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS")
	EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
	JINA_API_KEY = os.getenv("JINA_API_KEY")
	GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
	ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")

	@classmethod
	def get(cls, key, default=None):
		"""
		Get a configuration value by key.

		Args:
			key (str): The configuration key to retrieve.
			default: The default value to return if the key is not found.

		Returns:
			The value associated with the key, or the default value if not found.
		"""
		return getattr(cls, key, default)

def load_config():
	"""
	Load and return a Config instance.

	Returns:
		Config: An instance of the Config class.
	"""
	return Config()

def main():
	# Create an instance of the Config class
	config = load_config()
	
	# Test each configuration value
	print("Testing Config class:")
	print(f"EMAIL_ADDRESS: {'Set' if config.get('EMAIL_ADDRESS') else 'Not set'}")
	print(f"EMAIL_PASSWORD: {'Set' if config.get('EMAIL_PASSWORD') else 'Not set'}")
	print(f"JINA_API_KEY: {'Set' if config.get('JINA_API_KEY') else 'Not set'}")
	print(f"GEMINI_API_KEY: {'Set' if config.get('GEMINI_API_KEY') else 'Not set'}")
	print(f"ELEVENLABS_API_KEY: {'Set' if config.get('ELEVENLABS_API_KEY') else 'Not set'}")

	# Print a warning for any missing configuration
	missing_config = []
	for key in ['EMAIL_ADDRESS', 'EMAIL_PASSWORD', 'JINA_API_KEY', 'GEMINI_API_KEY', 'ELEVENLABS_API_KEY']:
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