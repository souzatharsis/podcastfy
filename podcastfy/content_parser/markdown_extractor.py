"""
Markdown Extractor Module

This module provides functionality to extract content from Markdown files.
"""

import logging
import markdown
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

class MarkdownExtractor:
    def extract_content(self, file_path: str) -> str:
        """
        Extract content from a markdown file.

        Args:
            file_path (str): Path to the markdown file.

        Returns:
            str: Extracted text content.

        Raises:
            Exception: If an error occurs during extraction.
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                md_content = file.read()
            
            # Convert Markdown to HTML
            html_content = markdown.markdown(md_content, extensions=['extra'])
            
            # Use BeautifulSoup to extract text from HTML
            soup = BeautifulSoup(html_content, 'html.parser')
            text_content = soup.get_text(separator='\n', strip=True)
            
            return text_content
        except Exception as e:
            logger.error(f"Failed to extract content from markdown file {file_path}: {str(e)}")
            raise

def main(seed: int = 42) -> None:
    """
    Test the MarkdownExtractor class with a sample markdown file.

    Args:
        seed (int): Random seed for reproducibility. Defaults to 42.
    """
    import os
    import random
    
    random.seed(seed)

    # Get the absolute path of the script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Construct the path to a sample markdown file
    md_path = os.path.join(script_dir, '..', '..', 'tests', 'data', 'file.md')
    
    extractor = MarkdownExtractor()

    try:
        content = extractor.extract_content(md_path)
        print("Markdown content extracted successfully:")
        print(content[:500] + "..." if len(content) > 500 else content)
    except Exception as e:
        print(f"An error occurred: {str(e)}")

if __name__ == "__main__":
    main()
