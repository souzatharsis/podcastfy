# from podcastfy.client import generate_podcast
# from colorama import Fore, Style, init

# # Initialize colorama
# init(autoreset=True)

# # Replace <url1> and <url2> with actual URLs you want to convert to audio
# urls = [
#     "https://blog.google/technology/ai/notebooklm-audio-overviews/"
#     ]

# # markdown_file = "data/markdown/NVIDIA - Form 10-Q Form 10-K.md"
# markdown_file = "data/markdown/02-TBV User Policy.md"

# # # Generate the podcast
# # audio_file = generate_podcast(urls=urls)

# # Generate the podcast
# audio_file = generate_podcast(urls=[markdown_file])

# # Print formatted output with bold blue text
# print(f"{Fore.BLUE}{Style.BRIGHT}Podcast generated successfully: {audio_file}")

import os
import subprocess

def run_command(command):
    subprocess.run(command, shell=True, check=True)

def main():
    run_command("sphinx-apidoc -f -o ./docs/source ./podcastfy")
    os.chdir("./docs")
    run_command("make clean")
    run_command("make html")
    os.chdir("..")

if __name__ == "__main__":
    main()