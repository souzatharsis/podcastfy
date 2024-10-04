"""
Logger Module

This module provides a utility function to set up and configure a logger for the Podcastfy application.
It ensures consistent logging format and configuration across the application.
"""

import logging
from typing import Any
from podcastfy.utils.config import load_config

def setup_logger(name: str) -> logging.Logger:
    """
    Set up and configure a logger.

    Args:
        name (str): The name of the logger.

    Returns:
        logging.Logger: A configured logger instance.
    """
    config = load_config()
    logging_config = config.get('logging')

    logger = logging.getLogger(name)
    logger.setLevel(logging_config['level'])
    
    formatter = logging.Formatter(logging_config['format'])
    
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    
    logger.addHandler(console_handler)
    
    return logger