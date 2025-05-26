# Podcastfy REST API Documentation

## Overview

The Podcastfy API allows you to programmatically generate AI podcasts from various input sources. This document outlines the API endpoints and their usage.

## Environment Variables

The following environment variables must be set before using the API:

- `GEMINI_API_KEY`: Your Google Gemini API key (required for transcript generation and default TTS)
- `OPENAI_API_KEY`: Your OpenAI API key (required for OpenAI TTS)
- `ELEVENLABS_API_KEY`: Your ElevenLabs API key (required for ElevenLabs TTS)

These keys should be set in your environment or in a `.env` file. They should not be passed in the request body.

## Using cURL with Podcastfy API

### Prerequisites

1. Confirm cURL installation:

```bash
curl --version
```

### API Request Flow

Making a prediction requires two sequential requests:

1. POST request to initiate processing - returns an `EVENT_ID`
2. GET request to fetch results - uses the `EVENT_ID` to fetch results

Between step 1 and 2, there is a delay of 1-3 minutes. We are working on reducing this delay and implementing a way to notify the user when the podcast is ready. Thanks for your patience!

### Basic Request Structure

```bash
# Step 1: POST request to initiate processing
# Make sure to include http:// or https:// in the URL
curl -X POST https://thatupiso-podcastfy-ai-demo.hf.space/gradio_api/call/process_inputs \
  -H "Content-Type: application/json" \
  -d '{
    "data": [
      "text_input",
      "https://yourwebsite.com",
      [],  # pdf_files
      [],  # image_files
      2000,  # word_count
      "engaging,fast-paced",  # conversation_style
      "main summarizer",  # roles_person1
      "questioner",  # roles_person2
      "Introduction,Content,Conclusion",  # dialogue_structure
      "PODCASTFY",  # podcast_name
      "YOUR PODCAST",  # podcast_tagline
      "gemini",  # tts_model
      0.7,  # creativity_level
      ""  # user_instructions
    ]
  }'

# Step 2: GET request to fetch results
curl -N https://thatupiso-podcastfy-ai-demo.hf.space/gradio_api/call/process_inputs/$EVENT_ID
```

### Parameter Details

| Index | Parameter          | Type   | Description                                                        |
| ----- | ------------------ | ------ | ------------------------------------------------------------------ |
| 0     | text_input         | string | Direct text input for podcast generation                           |
| 1     | urls_input         | string | URLs to process (include http:// or https://)                      |
| 2     | pdf_files          | array  | List of PDF files to process                                       |
| 3     | image_files        | array  | List of image files to process                                     |
| 4     | word_count         | number | Target word count for podcast                                      |
| 5     | conversation_style | string | Conversation style descriptors (e.g. "engaging,fast-paced")        |
| 6     | roles_person1      | string | Role of first speaker                                              |
| 7     | roles_person2      | string | Role of second speaker                                             |
| 8     | dialogue_structure | string | Structure of dialogue (e.g. "Introduction,Content,Conclusion")     |
| 9     | podcast_name       | string | Name of the podcast                                                |
| 10    | podcast_tagline    | string | Podcast tagline                                                    |
| 11    | tts_model          | string | Text-to-speech model ("gemini", "openai", "elevenlabs", or "edge") |
| 12    | creativity_level   | number | Level of creativity (0-1)                                          |
| 13    | user_instructions  | string | Custom instructions for generation                                 |

## Using Python

### Installation

```bash
pip install gradio_client
```

### Quick Start

```python
from gradio_client import Client, handle_file

client = Client("thatupiso/Podcastfy.ai_demo")
```

### API Endpoints

#### Generate Podcast

Generates a podcast from the provided input.

**Endpoint:** `/generate`

**Method:** POST

**Request Body:**

| Parameter             | Type    | Required | Default                                                     | Description                             |
| --------------------- | ------- | -------- | ----------------------------------------------------------- | --------------------------------------- |
| urls                  | array   | Yes      | []                                                          | List of URLs to generate podcast from   |
| name                  | string  | No       | "PODCASTIFY"                                                | Name of the podcast                     |
| tagline               | string  | No       | "Your Personal Generative AI Podcast"                       | Tagline for the podcast                 |
| creativity            | float   | No       | 0.7                                                         | Creativity level (0.0 to 1.0)           |
| conversation_style    | array   | No       | ["engaging", "fast-paced", "enthusiastic"]                  | Style of conversation                   |
| roles_person1         | string  | No       | "main summarizer"                                           | Role of first person                    |
| roles_person2         | string  | No       | "questioner/clarifier"                                      | Role of second person                   |
| dialogue_structure    | array   | No       | ["Introduction", "Main Content Summary", "Conclusion"]      | Structure of dialogue                   |
| tts_model             | string  | No       | "gemini"                                                    | Text-to-speech model to use             |
| is_long_form          | boolean | No       | false                                                       | Whether to generate a long-form podcast |
| engagement_techniques | array   | No       | ["rhetorical questions", "anecdotes", "analogies", "humor"] | Techniques to engage listeners          |
| user_instructions     | string  | No       | ""                                                          | Additional instructions for generation  |
| output_language       | string  | No       | "English"                                                   | Language of the output                  |

**Example Request:**

```python
result = client.predict(
    text_input="",
    urls_input="https://example.com/article",
    pdf_files=[],
    image_files=[],
    word_count=1500,
    conversation_style="casual,informative",
    podcast_name="Tech Talk",
    tts_model="gemini",
    creativity_level=0.8
)

print(f"Generated podcast: {result}")
```

### Error Handling

The API will return appropriate error messages for:

- Missing environment variables
- Malformed input
- Failed file processing
- TTS generation errors

### Rate Limits

Please be aware of the rate limits for the underlying services:

- Gemini API
- OpenAI API
- ElevenLabs API

## Notes

- At least one input source (text, URL, PDF, or image) must be provided
- API keys must be set as environment variables
- The generated audio file format is MP3
