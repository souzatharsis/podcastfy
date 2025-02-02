"""
Example implementation of the Podcastify FastAPI client.

This module demonstrates how to interact with the Podcastify API
to generate and download podcasts.
"""

import asyncio
import aiohttp
import json
import os
from pathlib import Path
from typing import Dict, Any


def get_default_config() -> Dict[str, Any]:
	"""
	Returns default configuration for podcast generation.

	Returns:
		Dict[str, Any]: Default configuration dictionary
	"""
	return {
		"generate_podcast": True,
		"google_key": "YOUR_GEMINI_API_KEY",
		"openai_key": "YOUR_OPENAI_API_KEY",
		"urls": ["https://www.phenomenalworld.org/interviews/swap-structure/"],
		"name": "Central Clearing Risks",
		"tagline": "Exploring the complexities of financial systemic risk",
		"creativity": 0.8,
		"conversation_style": ["engaging", "informative"],
		"roles_person1": "main summarizer",
		"roles_person2": "questioner",
		"dialogue_structure": ["Introduction", "Content", "Conclusion"],
		"tts_model": "openai",
		"is_long_form": False,
		"engagement_techniques": ["questions", "examples", "analogies"],
		"user_instructions": "Dont use the world Dwelve",
		"output_language": "English"
	}


async def generate_podcast() -> None:
	"""
	Generates a podcast using the Podcastify API and downloads the result.
	"""
	async with aiohttp.ClientSession() as session:
		try:
			print("Starting podcast generation...")
			async with session.post(
				"http://localhost:8080/generate",
				json=get_default_config()
			) as response:
				if response.status != 200:
					print(f"Error: Server returned status {response.status}")
					return
				
				result = await response.json()
				if "error" in result:
					print(f"Error: {result['error']}")
					return

				await download_podcast(session, result)

		except aiohttp.ClientError as e:
			print(f"Network error: {str(e)}")
		except Exception as e:
			print(f"Unexpected error: {str(e)}")


async def download_podcast(session: aiohttp.ClientSession, result: Dict[str, str]) -> None:
	"""
	Downloads the generated podcast file.

	Args:
		session (aiohttp.ClientSession): Active client session
		result (Dict[str, str]): API response containing audioUrl
	"""
	audio_url = f"http://localhost:8080{result['audioUrl']}"
	print(f"Podcast generated! Downloading from: {audio_url}")

	async with session.get(audio_url) as audio_response:
		if audio_response.status == 200:
			filename = os.path.join(
				str(Path.home() / "Downloads"), 
				result['audioUrl'].split('/')[-1]
			)
			with open(filename, 'wb') as f:
				f.write(await audio_response.read())
			print(f"Downloaded to: {filename}")
		else:
			print(f"Failed to download audio. Status: {audio_response.status}")


if __name__ == "__main__":
	try:
		asyncio.run(generate_podcast())
	except KeyboardInterrupt:
		print("\nProcess interrupted by user")
	except Exception as e:
		print(f"Error: {str(e)}")