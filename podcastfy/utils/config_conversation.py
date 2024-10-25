"""
Conversation Configuration Module

This module handles the loading and management of conversation configuration settings
for the Podcastfy application. It uses a YAML file for conversation-specific configuration settings.
"""

import os
import sys
from typing import Any, Dict, Optional, List
import yaml

def get_conversation_config_path(config_file: str = 'conversation_config.yaml'):
	"""
	Get the path to the conversation_config.yaml file.
	
	Returns:
		str: The path to the conversation_config.yaml file.
	"""
	try:
		# Check if the script is running in a PyInstaller bundle
		if getattr(sys, 'frozen', False):
			base_path = sys._MEIPASS
		else:
			base_path = os.path.dirname(os.path.abspath(__file__))
		
		# Look for conversation_config.yaml in the same directory as the script
		config_path = os.path.join(base_path, config_file)
		if os.path.exists(config_path):
			return config_path
		
		# If not found, look in the parent directory (package root)
		config_path = os.path.join(os.path.dirname(base_path), config_file)
		if os.path.exists(config_path):
			return config_path
		
		# If still not found, look in the current working directory
		config_path = os.path.join(os.getcwd(), config_file)
		if os.path.exists(config_path):
			return config_path
		
		raise FileNotFoundError(f"{config_file} not found")
	
	except Exception as e:
		print(f"Error locating {config_file}: {str(e)}")
		return None

class ConversationConfig:
	def __init__(self, config_conversation: Optional[Dict[str, Any]] = None):
		"""
		Initialize the ConversationConfig class with a dictionary configuration.

		Args:
			config_conversation (Optional[Dict[str, Any]]): Configuration dictionary. If None, default config will be used.
		"""
		# Load default configuration
		self.config_conversation = self._load_default_config()
		if config_conversation is not None:
			import copy
			
			# Create a deep copy of the default configuration
			self.config_conversation = copy.deepcopy(self.config_conversation)
			
			# Update the configuration with provided values
			if isinstance(config_conversation, dict):
				self._deep_update(self.config_conversation, config_conversation)
			else:
				print("Warning: config_conversation should be a dictionary.")
		
		# Set attributes based on the final configuration
		self._set_attributes()

	def _load_default_config(self) -> Dict[str, Any]:
		"""Load the default configuration from conversation_config.yaml."""
		config_path = get_conversation_config_path()
		if config_path:
			with open(config_path, 'r') as file:
				return yaml.safe_load(file)
		else:
			raise FileNotFoundError("conversation_config.yaml not found")

	def _set_attributes(self):
		"""
		Set attributes based on the current configuration, creating proper nested objects.
		"""
		def _set_nested_attributes(obj, config_dict):
			for key, value in config_dict.items():
				if isinstance(value, dict):
					# Create a new class instance for nested dictionaries
					nested_obj = type('NestedConfig', (), value)
					setattr(obj, key, nested_obj)
					_set_nested_attributes(nested_obj, value)
				else:
					setattr(obj, key, value)

		_set_nested_attributes(self, self.config_conversation)

	def _deep_update(self, target: Dict[str, Any], source: Dict[str, Any]) -> None:
		"""
		Recursively update a nested dictionary.

		Args:
			target (Dict[str, Any]): The dictionary to update
			source (Dict[str, Any]): The dictionary containing updates
		"""
		for key, value in source.items():
			if key == 'config_conversation':
				self._deep_update(target, value)
			elif isinstance(value, dict) and key in target and isinstance(target[key], dict):
				self._deep_update(target[key], value)
			else:
				target[key] = value

	def configure(self, config_conversation: Dict[str, Any]):
		"""
		Configure the conversation settings with the provided dictionary.

		Args:
			config_conversation (Dict[str, Any]): Configuration dictionary to update the settings.
			"""
		# Implementation of the configure method
		for key, value in config_conversation.items():
			if hasattr(self, key):
				setattr(self, key, value)
			else:
				raise ValueError(f"Invalid configuration key: {key}")

	def get(self, key: str, default: Optional[Any] = None) -> Any:
		"""
		Get a configuration value by key, supporting nested keys with dot notation.

		Args:
			key (str): The configuration key to retrieve (e.g., 'parent.child.value')
			default (Optional[Any]): The default value if the key is not found.

		Returns:
			Any: The value associated with the key, or the default value if not found.
		"""
		try:
			value = self.config_conversation
			for k in key.split('.'):
				value = value[k]
			return value
		except (KeyError, TypeError):
			return default

	def get_list(self, key: str, default: Optional[List[str]] = None) -> List[str]:
		"""
		Get a list configuration value by key, supporting nested keys with dot notation.

		Args:
			key (str): The configuration key to retrieve (e.g., 'parent.child.list')
			default (Optional[List[str]]): The default value if the key is not found.

		Returns:
			List[str]: The list associated with the key, or the default value if not found.
		"""
		value = self.get(key, default)
		if isinstance(value, str):
			return [item.strip() for item in value.split(',')]
		return value if isinstance(value, list) else default or []

	def to_dict(self) -> Dict[str, Any]:
		"""
		Convert the ConversationConfig object to a dictionary, preserving nested structure.

		Returns:
			Dict[str, Any]: A dictionary representation of the configuration
		"""
		def _to_dict(obj):
			if not hasattr(obj, '__dict__'):
				return obj
			result = {}
			for key, value in obj.__dict__.items():
				if not key.startswith('_'):
					if isinstance(value, type('NestedConfig', (), {})):
						result[key] = _to_dict(value)
					else:
						result[key] = value
			return result
		
		return _to_dict(self)

def load_conversation_config(config_conversation: Optional[Dict[str, Any]] = None) -> ConversationConfig:
	"""
	Load and return a ConversationConfig instance.

	Args:
		config_conversation (Optional[Dict[str, Any]]): Configuration dictionary to use. If None, default config will be used.

	Returns:
		ConversationConfig: An instance of the ConversationConfig class.
	"""
	return ConversationConfig(config_conversation)

def main() -> None:
	"""
	Test the ConversationConfig class and print configuration status.
	"""
	try:
		# Create an instance of the ConversationConfig class with default settings
		default_config = load_conversation_config()
		
		print("Default Configuration:")
		for key, value in default_config.config_conversation.items():
			print(f"{key}: {value}")

		# Test with custom configuration
		custom_config = {
			"word_count": 1500,
			"podcast_name": "Custom Podcast",
			"output_language": "Spanish"
		}
		custom_config_instance = load_conversation_config(custom_config)

		print("\nCustom Configuration:")
		for key, value in custom_config_instance.config_conversation.items():
			print(f"{key}: {value}")

		# Test the get method with a default value
		print(f"\nTesting get method with default value:")
		print(f"NON_EXISTENT_KEY: {custom_config_instance.get('NON_EXISTENT_KEY', 'Default Value')}")

	except FileNotFoundError as e:
		print(f"Error: {str(e)}")
	except Exception as e:
		print(f"An unexpected error occurred: {str(e)}")

if __name__ == "__main__":
	main()
