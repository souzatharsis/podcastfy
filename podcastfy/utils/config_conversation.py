"""
Conversation Configuration Module

This module handles the loading and management of conversation configuration settings
for the Podcastfy application. It uses a YAML file for conversation-specific configuration settings.
"""

import os
import sys
import logging
from typing import Any, Dict, Optional, List
import yaml

# Configure logging
logging.basicConfig(level=logging.INFO)

def get_conversation_config_path(config_file: str = 'conversation_config.yaml'):
    """
    Get the path to the conversation_config.yaml file.
    
    Returns:
        str: The path to the conversation_config.yaml file.
    """
    config_locations = [
        os.path.join(sys._MEIPASS, config_file) if getattr(sys, 'frozen', False) else os.path.join(os.path.dirname(os.path.abspath(__file__)), config_file),
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), config_file),
        os.path.join(os.getcwd(), config_file),
    ]

    for config_path in config_locations:
        if os.path.exists(config_path):
            return config_path

    logging.error(f"{config_file} not found in expected locations.")
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
            # Update the configuration with provided values
            if isinstance(config_conversation, dict):
                self.config_conversation.update(config_conversation)
                for key in config_conversation.keys():
                    if key not in self.config_conversation:
                        logging.warning(f"Unknown configuration key '{key}' will be ignored.")
            else:
                logging.warning("config_conversation should be a dictionary.")

        # Set attributes based on the final configuration
        self._set_attributes()

    def _load_default_config(self) -> Dict[str, Any]:
        """Load the default configuration from conversation_config.yaml."""
        config_path = get_conversation_config_path()
        if config_path:
            try:
                with open(config_path, 'r') as file:
                    return yaml.safe_load(file)
            except yaml.YAMLError as e:
                logging.error(f"Error parsing YAML file: {e}")
                raise
        else:
            raise FileNotFoundError("conversation_config.yaml not found")

    def _set_attributes(self):
        """Set attributes based on the current configuration."""
        for key, value in self.config_conversation.items():
            setattr(self, key, value)

    def configure(self, config_conversation: Dict[str, Any]):
        """
        Configure the conversation settings with the provided dictionary.

        Args:
            config_conversation (Dict[str, Any]): Configuration dictionary to update the settings.
        """
        for key, value in config_conversation.items():
            if hasattr(self, key):
                setattr(self, key, value)
            else:
                raise ValueError(f"Invalid configuration key: {key}")

    def get(self, key: str, default: Optional[Any] = None) -> Any:
        """
        Get a configuration value by key.

        Args:
            key (str): The configuration key to retrieve.
            default (Optional[Any]): The default value if the key is not found.

        Returns:
            Any: The value associated with the key, or the default value if not found.
        """
        return self.config_conversation.get(key, default)

    def get_list(self, key: str, default: Optional[List[str]] = None) -> List[str]:
        """
        Get a list configuration value by key.

        Args:
            key (str): The configuration key to retrieve.
            default (Optional[List[str]]): The default value if the key is not found.

        Returns:
            List[str]: The list associated with the key, or the default value if not found.
        """
        value = self.config_conversation.get(key, default)
        if isinstance(value, str):
            return [item.strip() for item in value.split(',')]
        return value if isinstance(value, list) else default or []

    def to_dict(self):
        """
        Convert the ConversationConfig object to a dictionary.
        """
        return {
            key: value for key, value in self.__dict__.items()
            if not key.startswith('_')
        }

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
        
        logging.info("Default Configuration:")
        for key, value in default_config.config_conversation.items():
            logging.info(f"{key}: {value}")

        # Test with custom configuration
        custom_config = {
            "word_count": 1500,
            "podcast_name": "Custom Podcast",
            "output_language": "Spanish"
        }
        custom_config_instance = load_conversation_config(custom_config)

        logging.info("\nCustom Configuration:")
        for key, value in custom_config_instance.config_conversation.items():
            logging.info(f"{key}: {value}")

        # Test the get method with a default value
        logging.info(f"\nTesting get method with default value:")
        logging.info(f"NON_EXISTENT_KEY: {custom_config_instance.get('NON_EXISTENT_KEY', 'Default Value')}")

    except FileNotFoundError as e:
        logging.error(f"Error: {str(e)}")
    except Exception as e:
        logging.error(f"An unexpected error occurred: {str(e)}")

if __name__ == "__main__":
    main()
