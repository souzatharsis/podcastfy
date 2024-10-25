"""
Content Generator Module

This module is responsible for generating Q&A content based on input texts using
LangChain and various LLM backends. It handles the interaction with the AI model and
provides methods to generate and save the generated content.
"""

import os
from typing import Optional, Dict, Any, List

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_community.llms.llamafile import Llamafile
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import StrOutputParser
from langchain import hub
from podcastfy.utils.config_conversation import load_conversation_config
from podcastfy.utils.config import load_config
import logging
from langchain.prompts import HumanMessagePromptTemplate, SystemMessagePromptTemplate
from langchain.schema import SystemMessage

logger = logging.getLogger(__name__)


class LLMBackend:
    def __init__(
        self,
        is_local: bool,
        temperature: float,
        max_output_tokens: int,
        model_name: str
    ):
        """
        Initialize the LLMBackend.

        Args:
                is_local (bool): Whether to use a local LLM or not.
                temperature (float): The temperature for text generation.
                max_output_tokens (int): The maximum number of output tokens.
                model_name (str): The name of the model to use.
        """
        self.is_local = is_local
        self.temperature = temperature
        self.max_output_tokens = max_output_tokens
        self.model_name = model_name
        self.is_multimodal = not is_local  # Does not assume local LLM is multimodal

        if is_local:
            self.llm = Llamafile()
        else:
            self.llm = ChatGoogleGenerativeAI(
                model=model_name,
                temperature=temperature,
                max_output_tokens=max_output_tokens,
            )


class ContentGenerator:
    def __init__(
        self, api_key: str, conversation_config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize the ContentGenerator.

        Args:
                api_key (str): API key for Google's Generative AI.
                conversation_config (Optional[Dict[str, Any]]): Custom conversation configuration.
        """
        os.environ["GOOGLE_API_KEY"] = api_key
        self.config = load_config()
        self.content_generator_config = self.config.get("content_generator", {})

        self.config_conversation = load_conversation_config(conversation_config)

    def __compose_prompt(self, num_images: int):
        """
        Compose the prompt for the LLM based on the content list.
        """
        prompt_template = hub.pull(
            self.config.get("content_generator", {}).get(
                "prompt_template", "souzatharsis/podcastfy_multimodal"
            ) + ":" + self.config.get("content_generator", {}).get(
                "prompt_commit", "c67bea9c"
            )
        )

        image_path_keys = []
        messages = []
        
        # Only add text content if input_text is not empty
        text_content = {"type": "text", "text": "Please analyze this input and generate a conversation. {input_text}"}
        messages.append(text_content)
        
        for i in range(num_images):
            key = f"image_path_{i}"
            image_content = {
                "image_url": {"path": f"{{{key}}}", "detail": "high"},
                "type": "image_url",
            }
            image_path_keys.append(key)
            messages.append(image_content)

        user_prompt_template = ChatPromptTemplate.from_messages(
            messages=[HumanMessagePromptTemplate.from_template(messages)]
        )
        user_instructions = self.config_conversation.get("user_instructions", "")
        
        user_instructions = "[[MAKE SURE TO FOLLOW THESE INSTRUCTIONS OVERRIDING THE PROMPT TEMPLATE IN CASE OF CONFLICT: " + user_instructions  + "]]"
        
        new_system_message = prompt_template.messages[0].prompt.template + "\n" + user_instructions

        # Create new prompt with updated system message
        #prompt_template = ChatPromptTemplate.from_messages([
        #    SystemMessagePromptTemplate.from_template(new_system_message),
        #    HumanMessagePromptTemplate.from_template(messages)
        #])

        # Compose messages from podcastfy_prompt_template and user_prompt_template
        combined_messages = ChatPromptTemplate.from_messages([new_system_message]).messages + user_prompt_template.messages

        # Create a new ChatPromptTemplate object with the combined messages
        composed_prompt_template = ChatPromptTemplate.from_messages(combined_messages)

        return composed_prompt_template, image_path_keys

    def __compose_prompt_params(
        self, image_file_paths: List[str], image_path_keys: List[str], input_texts: str
    ):
        prompt_params = {
            "input_text": input_texts,
            "word_count": self.config_conversation.get("word_count"),
            "conversation_style": ", ".join(
                self.config_conversation.get("conversation_style", [])
            ),
            "roles_person1": self.config_conversation.get("roles_person1"),
            "roles_person2": self.config_conversation.get("roles_person2"),
            "dialogue_structure": ", ".join(
                self.config_conversation.get("dialogue_structure", [])
            ),
            "podcast_name": self.config_conversation.get("podcast_name"),
            "podcast_tagline": self.config_conversation.get("podcast_tagline"),
            "output_language": self.config_conversation.get("output_language"),
            "engagement_techniques": ", ".join(
                self.config_conversation.get("engagement_techniques", [])
            ),
        }

        # for each image_path_key, add the corresponding image_file_path to the prompt_params
        for key, path in zip(image_path_keys, image_file_paths):
            prompt_params[key] = path

        return prompt_params

    def generate_qa_content(
        self,
        input_texts: str = "",
        image_file_paths: List[str] = [],
        output_filepath: Optional[str] = None,
        is_local: bool = False,
    ) -> str:
        """
        Generate Q&A content based on input texts.

        Args:
                input_texts (str): Input texts to generate content from.
                image_file_paths (List[str]): List of image file paths.
                output_filepath (Optional[str]): Filepath to save the response content. Defaults to None.
                is_local (bool): Whether to use a local LLM or not. Defaults to False.

        Returns:
                str: Formatted Q&A content.

        Raises:
                Exception: If there's an error in generating content.
        """
        try:
            llmbackend = LLMBackend(
                is_local=is_local,
                temperature=self.config_conversation.get("creativity", 0),
                max_output_tokens=self.content_generator_config.get(
                    "max_output_tokens", 8192
                ),
                model_name=(
                    self.content_generator_config.get(
                        "gemini_model", "gemini-1.5-pro-latest"
                    )
                    if not is_local
                    else "User provided model"
                )
            )

            num_images = 0 if is_local else len(image_file_paths)
            self.prompt_template, image_path_keys = self.__compose_prompt(num_images)
            self.parser = StrOutputParser()
            self.chain = self.prompt_template | llmbackend.llm | self.parser

            prompt_params = self.__compose_prompt_params(
                image_file_paths, image_path_keys, input_texts
            )

            self.response = self.chain.invoke(prompt_params)

            logger.info(f"Content generated successfully")

            if output_filepath:
                with open(output_filepath, "w") as file:
                    file.write(self.response)
                logger.info(f"Response content saved to {output_filepath}")

            return self.response
        except Exception as e:
            logger.error(f"Error generating content: {str(e)}")
            raise


def main(seed: int = 42, is_local: bool = False) -> None:
    """
    Generate Q&A content based on input text from input_text.txt using the specified LLM backend.

    Args:
            seed (int): Random seed for reproducibility. Defaults to 42.
            is_local (bool): Whether to use a local LLM or not. Defaults to False.

    Returns:
            None
    """
    try:
        config = load_config()
        api_key = config.GEMINI_API_KEY if not is_local else ""
        if not is_local and not api_key:
            raise ValueError("GEMINI_API_KEY not found in configuration")

        content_generator = ContentGenerator(api_key)

        input_text = ""
        transcript_dir = config.get("output_directories", {}).get(
            "transcripts", "data/transcripts"
        )
        for filename in os.listdir(transcript_dir):
            if filename.endswith(".txt"):
                with open(os.path.join(transcript_dir, filename), "r") as file:
                    input_text += file.read() + "\n\n"

        response = content_generator.generate_qa_content(input_text, is_local=is_local)

        print("Generated Q&A Content:")
        output_file = os.path.join(
            config.get("output_directories", {}).get("transcripts", "data/transcripts"),
            "response.txt",
        )
        with open(output_file, "w") as file:
            file.write(response)

    except Exception as e:
        logger.error(f"An error occurred while generating Q&A content: {str(e)}")
        raise


if __name__ == "__main__":
    main()
