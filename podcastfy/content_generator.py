"""
Content Generator Module

This module is responsible for generating Q&A content based on input texts using
LangChain and various LLM backends. It handles the interaction with the AI model and
provides methods to generate and save the generated content.
"""

import os
from typing import Optional, Dict, Any, List
import re


from langchain_community.chat_models import ChatLiteLLM
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_community.llms.llamafile import Llamafile
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain import hub
from podcastfy.utils.config_conversation import load_conversation_config
from podcastfy.utils.config import load_config
import logging
from langchain.prompts import HumanMessagePromptTemplate
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class LLMBackend:
    def __init__(
        self,
        is_local: bool,
        temperature: float,
        max_output_tokens: int,
        model_name: str,
        api_key_label: str = "GEMINI_API_KEY",
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

        common_params = {
            "temperature": temperature,
            "presence_penalty": 0.75,  # Encourage diverse content
            "frequency_penalty": 0.75,  # Avoid repetition
        }

        if is_local:
            self.llm = Llamafile() # replace with ollama
        elif (
            "gemini" in self.model_name.lower()
        ):  # keeping original gemini as a special case while we build confidence on LiteLLM

            self.llm = ChatGoogleGenerativeAI(
                api_key=os.environ["GEMINI_API_KEY"],
                model=model_name,
                max_output_tokens=max_output_tokens,
                **common_params,
            )
        else:  # user should set api_key_label from input
            self.llm = ChatLiteLLM(
                model=self.model_name,
                temperature=temperature,
                api_key=os.environ[api_key_label],
            )


class LongFormContentGenerator:
    """
    Handles generation of long-form podcast conversations by breaking content into manageable chunks.
    
    Uses a "Content Chunking with Contextual Linking" strategy to maintain context between segments
    while generating longer conversations.
    
    Attributes:
        LONGFORM_INSTRUCTIONS (str): Constant containing instructions for long-form generation
        llm_chain: The LangChain chain used for content generation
    """
    # Add constant for long-form instructions
    LONGFORM_INSTRUCTIONS = """
    Additional Instructions:
        1. Provide extensive examples and real-world applications
        2. Include detailed analysis and multiple perspectives
        3. Use the "yes, and" technique to build upon points
        4. Incorporate relevant anecdotes and case studies
        5. Balance detailed explanations with engaging dialogue
        6. Maintain consistent voice throughout the extended discussion
        7. Generate a long conversation - output max_output_tokens tokens
    """
    
    def __init__(self, chain, llm, config_conversation: Dict[str, Any], ):
        """
        Initialize ConversationGenerator.
        
        Args:
            llm_chain: The LangChain chain to use for generation
            config_conversation: Conversation configuration dictionary
        """
        self.llm_chain = chain
        self.llm = llm
        self.max_num_chunks = config_conversation.get("max_num_chunks", 10)  # Default if not in config
        self.min_chunk_size = config_conversation.get("min_chunk_size", 200)  # Default if not in config

    def __calculate_chunk_size(self, input_content: str) -> int:
        """
        Calculate chunk size based on input content length.
        
        Args:
            input_content: Input text content
                
        Returns:
            Calculated chunk size that ensures:
            - Returns 1 if content length <= min_chunk_size
            - Each chunk has at least min_chunk_size characters
            - Number of chunks is at most max_num_chunks
        """
        input_length = len(input_content)
        if input_length <= self.min_chunk_size:
            return input_length
        
        maximum_chunk_size = input_length // self.max_num_chunks
        if maximum_chunk_size >= self.min_chunk_size:
            return maximum_chunk_size
        
        # Calculate chunk size that maximizes size while maintaining minimum chunks
        return input_length // (input_length // self.min_chunk_size)

    def chunk_content(self, input_content: str, chunk_size: int) -> List[str]:
        """
        Split input content into manageable chunks while preserving context.
        
        Args:
            input_content (str): The input text to chunk
            chunk_size (int): Maximum size of each chunk
            
        Returns:
            List[str]: List of content chunks
        """
        sentences = input_content.split('. ')
        chunks = []
        current_chunk = []
        current_length = 0
        
        for sentence in sentences:
            sentence_length = len(sentence)
            if current_length + sentence_length > chunk_size and current_chunk:
                chunks.append('. '.join(current_chunk) + '.')
                current_chunk = []
                current_length = 0
            current_chunk.append(sentence)
            current_length += sentence_length
            
        if current_chunk:
            chunks.append('. '.join(current_chunk) + '.')
        return chunks

    def enhance_prompt_params(self, prompt_params: Dict, 
                              part_idx: int, 
                              total_parts: int,
                              chat_context: str) -> Dict:
        """
        Enhance prompt parameters for long-form content generation.
        
        Args:
            prompt_params (Dict): Original prompt parameters
            part_idx (int): Index of current conversation part
            total_parts (int): Total number of conversation parts
            chat_context (str): Chat context from previous parts
            
        Returns:
            Dict: Enhanced prompt parameters with part-specific instructions
        """
        enhanced_params = prompt_params.copy()
		# Initialize part_instructions with chat context
        enhanced_params["context"] = chat_context
        
        COMMON_INSTRUCTIONS = """
            Podcast conversation so far is given in CONTEXT.
            Continue the natural flow of conversation. Follow-up on the very previous point/question without repeating topics or points already discussed!
            Hence, the transition should be smooth and natural. Avoid abrupt transitions.
            Make sure the first to speak is different from the previous speaker. Look at the last tag in CONTEXT to determine the previous speaker. 
            If last tag in CONTEXT is <Person1>, then the first to speak now should be <Person2>.
            If last tag in CONTEXT is <Person2>, then the first to speak now should be <Person1>.
            This is a live conversation without any breaks.
            Hence, avoid statemeents such as "we'll discuss after a short break.  Stay tuned" or "Okay, so, picking up where we left off".
        """ 

        # Add part-specific instructions
        if part_idx == 0:
            enhanced_params["instruction"] = f"""
            ALWAYS START THE CONVERSATION GREETING THE AUDIENCE: Welcome to {enhanced_params["podcast_name"]} - {enhanced_params["podcast_tagline"]}.
            You are generating the Introduction part of a long podcast conversation.
            Don't cover any topics yet, just introduce yourself and the topic. Leave the rest for later parts, following these guidelines:
            """
        elif part_idx == total_parts - 1:
            enhanced_params["instruction"] = f"""
            You are generating the last part of a long podcast conversation. 
            {COMMON_INSTRUCTIONS}
            For this part, discuss the below INPUT and then make concluding remarks in a podcast conversation format and END THE CONVERSATION GREETING THE AUDIENCE WITH PERSON1 ALSO SAYING A GOOD BYE MESSAGE, following these guidelines:
            """
        else:
            enhanced_params["instruction"] = f"""
            You are generating part {part_idx+1} of {total_parts} parts of a long podcast conversation.
            {COMMON_INSTRUCTIONS}
            For this part, discuss the below INPUT in a podcast conversation format, following these guidelines:
            """
        
        return enhanced_params

    def generate_long_form(
        self, 
        input_content: str, 
        prompt_params: Dict
    ) -> str:
        """
        Generate a complete long-form conversation using chunked content.
        
        Args:
            input_content (str): Input text for conversation
            prompt_params (Dict): Base prompt parameters
            
        Returns:
            str: Generated long-form conversation
        """
        # Add long-form instructions once at the beginning
        prompt_params["user_instructions"] = prompt_params.get("user_instructions", "") + self.LONGFORM_INSTRUCTIONS
        
        # Get chunk size
        chunk_size = self.__calculate_chunk_size(input_content)

        chunks = self.chunk_content(input_content, chunk_size)
        conversation_parts = []
        chat_context = input_content
        num_parts = len(chunks)
        print(f"Generating {num_parts} parts")
        
        for i, chunk in enumerate(chunks):
            enhanced_params = self.enhance_prompt_params(
                prompt_params,
                part_idx=i,
                total_parts=num_parts,
                chat_context=chat_context
            )
            enhanced_params["input_text"] = chunk
            response = self.llm_chain.invoke(enhanced_params)
            if i == 0:
                chat_context = response
            else:
                chat_context = chat_context + response
            print(f"Generated part {i+1}/{num_parts}: Size {len(chunk)} characters.")
            #print(f"[LLM-START] Step: {i+1} ##############################")
            #print(response)
            #print(f"[LLM-END] Step: {i+1} ##############################")
            conversation_parts.append(response)

        return self.stitch_conversations(conversation_parts)
    
    def stitch_conversations(self, parts: List[str]) -> str:
        """
        Combine conversation parts with smooth transitions.
        
        Args:
            parts (List[str]): List of conversation parts
            
        Returns:
            str: Combined conversation
        """
        # Simply join the parts, preserving all markup
        return "\n".join(parts)


# Make BaseContentCleaner a mixin class
class ContentCleanerMixin:
    """
    Mixin class containing common transcript cleaning operations.
    
    Provides reusable cleaning methods that can be used by different content generation strategies.
    Methods use protected naming convention (_method_name) as they are intended for internal use
    by the strategies.
    """
    
    @staticmethod
    def _clean_scratchpad(text: str) -> str:
        """
        Remove scratchpad blocks, plaintext blocks, standalone triple backticks, any string enclosed in brackets, and underscores around words.
        """
        try:
            import re
            pattern = r'```scratchpad\n.*?```\n?|```plaintext\n.*?```\n?|```\n?|\[.*?\]'
            cleaned_text = re.sub(pattern, '', text, flags=re.DOTALL)
            # Remove "xml" if followed by </Person1> or </Person2>
            cleaned_text = re.sub(r"xml(?=\s*</Person[12]>)", "", cleaned_text)
            # Remove underscores around words
            cleaned_text = re.sub(r'_(.*?)_', r'\1', cleaned_text)
            return cleaned_text.strip()
        except Exception as e:
            logger.error(f"Error cleaning scratchpad content: {str(e)}")
            return text

    @staticmethod
    def _clean_tss_markup(
        input_text: str, 
        additional_tags: List[str] = ["Person1", "Person2"]
    ) -> str:
        """
        Remove unsupported TSS markup tags while preserving supported ones.
        """
        try:
            input_text = ContentCleanerMixin._clean_scratchpad(input_text)
            supported_tags = ["speak", "lang", "p", "phoneme", "s", "sub"]
            supported_tags.extend(additional_tags)

            pattern = r"</?(?!(?:" + "|".join(supported_tags) + r")\b)[^>]+>"
            cleaned_text = re.sub(pattern, "", input_text)
            cleaned_text = re.sub(r"\n\s*\n", "\n", cleaned_text)
            cleaned_text = re.sub(r"\*", "", cleaned_text)

            for tag in additional_tags:
                cleaned_text = re.sub(
                    f'<{tag}>(.*?)(?=<(?:{"|".join(additional_tags)})>|$)',
                    f"<{tag}>\\1</{tag}>",
                    cleaned_text,
                    flags=re.DOTALL,
                )
            


            return cleaned_text.strip()
            
        except Exception as e:
            logger.error(f"Error cleaning TSS markup: {str(e)}")
            return input_text


class ContentGenerationStrategy(ABC):
    """
    Abstract base class defining the interface for content generation strategies.
    
    Defines the contract that all concrete strategies must implement, including
    validation, generation, and cleaning operations.
    """
    
    @abstractmethod
    def validate(self, input_texts: str, image_file_paths: List[str]) -> None:
        """Validate inputs for this strategy."""
        pass
        
    @abstractmethod
    def generate(self, 
                chain,
                input_texts: str,
                prompt_params: Dict[str, Any],
                **kwargs) -> str:
        """Generate content using this strategy."""
        pass
        
    @abstractmethod
    def clean(self, 
             response: str,
             config: Dict[str, Any]) -> str:
        """Clean the generated response according to strategy."""
        pass

    @abstractmethod
    def compose_prompt_params(self,
                            config_conversation: Dict[str, Any],
                            image_file_paths: List[str] = [],
                            image_path_keys: List[str] = [],
                            input_texts: str = "") -> Dict[str, Any]:
        """Compose prompt parameters according to strategy."""
        pass


class StandardContentStrategy(ContentGenerationStrategy, ContentCleanerMixin):
    """
    Strategy for generating standard-length content.
    
    Implements basic content generation without chunking or special handling.
    Uses common cleaning operations from ContentCleanerMixin.
    """
    
    def __init__(self, llm, content_generator_config: Dict[str, Any], config_conversation: Dict[str, Any]):
        """
        Initialize StandardContentStrategy.
        
        Args:
            content_generator_config (Dict[str, Any]): Configuration for content generation
            config_conversation (Dict[str, Any]): Conversation configuration
        """
        self.llm = llm
        self.content_generator_config = content_generator_config
        self.config_conversation = config_conversation
    
    def validate(self, input_texts: str, image_file_paths: List[str]) -> None:
        """No specific validation needed for standard content."""
        pass
        
    def generate(self, 
                chain,
                input_texts: str,
                prompt_params: Dict[str, Any],
                **kwargs) -> str:
        """Generate standard-length content."""
        return chain.invoke(prompt_params)
        
    def clean(self, 
             response: str,
             config: Dict[str, Any]) -> str:
        """Apply basic TSS markup cleaning."""
        return self._clean_tss_markup(response)

    def compose_prompt_params(self,
                            config_conversation: Dict[str, Any],
                            image_file_paths: List[str] = [],
                            image_path_keys: List[str] = [],
                            input_texts: str = "") -> Dict[str, Any]:
        """Compose prompt parameters for standard content generation."""
        prompt_params = {
            "input_text": input_texts,
            "conversation_style": ", ".join(
                config_conversation.get("conversation_style", [])
            ),
            "roles_person1": config_conversation.get("roles_person1"),
            "roles_person2": config_conversation.get("roles_person2"),
            "dialogue_structure": ", ".join(
                config_conversation.get("dialogue_structure", [])
            ),
            "podcast_name": config_conversation.get("podcast_name"),
            "podcast_tagline": config_conversation.get("podcast_tagline"),
            "output_language": config_conversation.get("output_language"),
            "engagement_techniques": ", ".join(
                config_conversation.get("engagement_techniques", [])
            ),
        }

        # Add image paths to parameters if any
        for key, path in zip(image_path_keys, image_file_paths):
            prompt_params[key] = path

        return prompt_params


class LongFormContentStrategy(ContentGenerationStrategy, ContentCleanerMixin):
    """
    Strategy for generating long-form content.
    
    Implements advanced content generation using chunking and context maintenance.
    Includes additional cleaning operations specific to long-form content.
    
    Note:
        - Only works with text input (no images)
        - Requires non-empty input text
    """
    
    def __init__(self, llm, content_generator_config: Dict[str, Any], config_conversation: Dict[str, Any]):
        """
        Initialize LongFormContentStrategy.
        
        Args:
            content_generator_config (Dict[str, Any]): Configuration for content generation
            config_conversation (Dict[str, Any]): Conversation configuration
        """
        self.llm = llm
        self.content_generator_config = content_generator_config
        self.config_conversation = config_conversation
    
    def validate(self, input_texts: str, image_file_paths: List[str]) -> None:
        """Validate inputs for long-form generation."""
        if not input_texts.strip():
            raise ValueError("Long-form generation requires non-empty input text")
        if image_file_paths:
            raise ValueError("Long-form generation is not available with image inputs")
            
    def generate(self, 
                chain,
                input_texts: str,
                prompt_params: Dict[str, Any],
                **kwargs) -> str:
        """Generate long-form content."""
        generator = LongFormContentGenerator(chain, self.llm, self.config_conversation)
        return generator.generate_long_form(
            input_texts,
            prompt_params
        )
        
    def clean(self, 
             response: str,
             config: Dict[str, Any]) -> str:
        """Apply enhanced cleaning for long-form content."""
        # First apply standard cleaning using common method
        standard_clean = self._clean_tss_markup(response)
        # Then apply additional long-form specific cleaning
        return self._clean_transcript_response(standard_clean, config)
    
    def _clean_transcript_response(self, transcript: str, config: Dict[str, Any]) -> str:
        """
        Clean transcript using a two-step process with LLM-based cleaning.
        
        First cleans the markup using a specialized prompt template, then rewrites
        for better flow and consistency using a second prompt template.
        
        Args:
            transcript (str): Raw transcript text that may contain scratchpad blocks
            config (Dict[str, Any]): Configuration dictionary containing LLM and prompt settings
            
        Returns:
            str: Cleaned and rewritten transcript with proper tags and improved flow
            
        Note:
            Falls back to original or partially cleaned transcript if any cleaning step fails
        """
        logger.debug("Starting transcript cleaning process")

        final_transcript = self._fix_alternating_tags(transcript)
        
        logger.debug("Completed transcript cleaning process")
        
        return final_transcript

         
    def _clean_transcript_response_DEPRECATED(self, transcript: str, config: Dict[str, Any]) -> str:
        """
        Clean transcript using a two-step process with LLM-based cleaning.
        
        First cleans the markup using a specialized prompt template, then rewrites
        for better flow and consistency using a second prompt template.
        
        Args:
            transcript (str): Raw transcript text that may contain scratchpad blocks
            config (Dict[str, Any]): Configuration dictionary containing LLM and prompt settings
            
        Returns:
            str: Cleaned and rewritten transcript with proper tags and improved flow
            
        Note:
            Falls back to original or partially cleaned transcript if any cleaning step fails
        """
        logger.debug("Starting transcript cleaning process")
        try:
            logger.debug("Initializing LLM model for cleaning")
            # Initialize model with config values for consistent cleaning
            #llm = ChatGoogleGenerativeAI(
            #    model=self.content_generator_config["meta_llm_model"],
            #    temperature=0,
            #    presence_penalty=0.75,  # Encourage diverse content
            #    frequency_penalty=0.75  # Avoid repetition
            #)
            llm = self.llm
            logger.debug("LLM model initialized successfully")

            # Get prompt templates from hub
            logger.debug("Pulling prompt templates from hub")
            try:
                clean_transcript_prompt = hub.pull(f"{self.content_generator_config['cleaner_prompt_template']}:{self.content_generator_config['cleaner_prompt_commit']}")
                rewrite_prompt = hub.pull(f"{self.content_generator_config['rewriter_prompt_template']}:{self.content_generator_config['rewriter_prompt_commit']}")
                logger.debug("Successfully pulled prompt templates")
            except Exception as e:
                logger.error(f"Error pulling prompt templates: {str(e)}")
                return transcript
            
            logger.debug("Creating cleaning and rewriting chains")
            # Create chains
            clean_chain = clean_transcript_prompt | llm | StrOutputParser()
            rewrite_chain = rewrite_prompt | llm | StrOutputParser()
            
            # Run cleaning chain
            logger.debug("Executing cleaning chain")
            try:
                cleaned_response = clean_chain.invoke({"transcript": transcript})
                if not cleaned_response:
                    logger.warning("Cleaning chain returned empty response")
                    return transcript
                logger.debug("Successfully cleaned transcript")
            except Exception as e:
                logger.error(f"Error in cleaning chain: {str(e)}")
                return transcript
            
            # Run rewriting chain
            logger.debug("Executing rewriting chain")
            try:
                rewritten_response = rewrite_chain.invoke({"transcript": cleaned_response})
                if not rewritten_response:
                    logger.warning("Rewriting chain returned empty response")
                    return cleaned_response  # Fall back to cleaned version
                logger.debug("Successfully rewrote transcript")
            except Exception as e:
                logger.error(f"Error in rewriting chain: {str(e)}")
                return cleaned_response  # Fall back to cleaned version
                
            # Fix alternating tags in the final response
            logger.debug("Fixing alternating tags")
            final_transcript = self._fix_alternating_tags(rewritten_response)
            logger.debug("Completed transcript cleaning process")
            
            return final_transcript
            
        except Exception as e:
            logger.error(f"Error in transcript cleaning process: {str(e)}")
            return transcript  # Return original if cleaning fails

    def _fix_alternating_tags(self, transcript: str) -> str:
        """
        Ensures transcript has properly alternating Person1 and Person2 tags.
        
        Merges consecutive same-person tags and ensures proper tag alternation
        throughout the transcript.
        
        Args:
            transcript (str): Input transcript text that may have consecutive same-person tags
            
        Returns:
            str: Transcript with properly alternating tags and merged content
            
        Example:
            Input:
                <Person1>Hello</Person1>
                <Person1>World</Person1>
                <Person2>Hi</Person2>
            Output:
                <Person1>Hello World</Person1>
                <Person2>Hi</Person2>
                
        Note:
            Returns original transcript if cleaning fails
        """
        try:
            # Split into individual tag blocks while preserving tags
            pattern = r'(<Person[12]>.*?</Person[12]>)'
            blocks = re.split(pattern, transcript, flags=re.DOTALL)
            
            # Filter out empty/whitespace blocks
            blocks = [b.strip() for b in blocks if b.strip()]
            
            merged_blocks = []
            current_content = []
            current_person = None
            
            for block in blocks:
                # Extract person number and content
                match = re.match(r'<Person([12])>(.*?)</Person\1>', block, re.DOTALL)
                if not match:
                    continue
                    
                person_num, content = match.groups()
                content = content.strip()
                
                if current_person == person_num:
                    # Same person - append content
                    current_content.append(content)
                else:
                    # Different person - flush current content if any
                    if current_content:
                        merged_text = " ".join(current_content)
                        merged_blocks.append(f"<Person{current_person}>{merged_text}</Person{current_person}>")
                    # Start new person
                    current_person = person_num
                    current_content = [content]
            
            # Flush final content
            if current_content:
                merged_text = " ".join(current_content)
                merged_blocks.append(f"<Person{current_person}>{merged_text}</Person{current_person}>")
                
            return "\n".join(merged_blocks)
            
        except Exception as e:
            logger.error(f"Error fixing alternating tags: {str(e)}")
            return transcript  # Return original if fixing fails

    def compose_prompt_params(self,
                            config_conversation: Dict[str, Any],
                            image_file_paths: List[str] = [],
                            image_path_keys: List[str] = [],
                            input_texts: str = "") -> Dict[str, Any]:
        """Compose prompt parameters for long-form content generation."""
        return {
            "conversation_style": ", ".join(
                config_conversation.get("conversation_style", [])
            ),
            "roles_person1": config_conversation.get("roles_person1"),
            "roles_person2": config_conversation.get("roles_person2"),
            "dialogue_structure": ", ".join(
                config_conversation.get("dialogue_structure", [])
            ),
            "podcast_name": config_conversation.get("podcast_name"),
            "podcast_tagline": config_conversation.get("podcast_tagline"),
            "output_language": config_conversation.get("output_language"),
            "engagement_techniques": ", ".join(
                config_conversation.get("engagement_techniques", [])
            ),
        }


class ContentGenerator:
    def __init__(
        self, 
        is_local: bool=False, 
        model_name: str="gemini-1.5-pro-latest", 
        api_key_label: str="GEMINI_API_KEY",
        conversation_config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize the ContentGenerator.

        Args:
                api_key (str): API key for Google's Generative AI.
                conversation_config (Optional[Dict[str, Any]]): Custom conversation configuration.
        """
        #os.environ["GOOGLE_API_KEY"] = api_key
        self.config = load_config()
        self.content_generator_config = self.config.get("content_generator", {})

        self.config_conversation = load_conversation_config(conversation_config)
        self.tts_config = self.config_conversation.get("text_to_speech", {})

        # Get output directories from conversation config
        self.output_directories = self.tts_config.get("output_directories", {})

        # Create output directories if they don't exist
        transcripts_dir = self.output_directories.get("transcripts")

        if transcripts_dir and not os.path.exists(transcripts_dir):
            os.makedirs(transcripts_dir)
        
        self.is_local = is_local

                # Initialize LLM backend
        if not model_name:
            model_name = self.content_generator_config.get("llm_model")
        if is_local:
            model_name = "User provided local model"

        llm_backend = LLMBackend(
            is_local=is_local,
            temperature=self.config_conversation.get("creativity", 1),
            max_output_tokens=self.content_generator_config.get(
                "max_output_tokens", 8192
            ),
            model_name=model_name,
            api_key_label=api_key_label,
        )

        self.llm = llm_backend.llm



        # Initialize strategies with configs
        self.strategies = {
            True: LongFormContentStrategy(
                self.llm,
                self.content_generator_config,
                self.config_conversation
            ),
            False: StandardContentStrategy(
                self.llm,
                self.content_generator_config,
                self.config_conversation
            )
        }

    def __compose_prompt(self, num_images: int, longform: bool=False):
        """
        Compose the prompt for the LLM based on the content list.
        """
        content_generator_config = self.config.get("content_generator", {})
        
        # Get base template and commit values
        base_template = content_generator_config.get("prompt_template")
        base_commit = content_generator_config.get("prompt_commit")
        
        # Modify template and commit for longform if configured
        if longform:
            template = content_generator_config.get("longform_prompt_template")
            commit = content_generator_config.get("longform_prompt_commit")
        else:
            template = base_template
            commit = base_commit

        prompt_template = hub.pull(f"{template}:{commit}")

        image_path_keys = []
        messages = []

        # Only add text content if input_text is not empty
        text_content = {
            "type": "text",
            "text": "Please analyze this input and generate a conversation. {input_text}",
        }
        messages.append(text_content)

        for i in range(num_images):
            key = f"image_path_{i}"
            image_content = {
                "image_url": {"url": f"{{{key}}}", "detail": "high"},
                "type": "image_url",
            }
            image_path_keys.append(key)
            messages.append(image_content)

        user_prompt_template = ChatPromptTemplate.from_messages(
            messages=[HumanMessagePromptTemplate.from_template(messages)]
        )
        user_instructions = self.config_conversation.get("user_instructions", "")

        user_instructions = (
            "[[MAKE SURE TO FOLLOW THESE INSTRUCTIONS OVERRIDING THE PROMPT TEMPLATE IN CASE OF CONFLICT: "
            + user_instructions
            + "]]"
        )

        new_system_message = (
            prompt_template.messages[0].prompt.template + "\n" + user_instructions
        )

        # Compose messages from podcastfy_prompt_template and user_prompt_template
        combined_messages = (
            ChatPromptTemplate.from_messages([new_system_message]).messages
            + user_prompt_template.messages
        )

        # Create a new ChatPromptTemplate object with the combined messages
        composed_prompt_template = ChatPromptTemplate.from_messages(combined_messages)

        return composed_prompt_template, image_path_keys

    def generate_qa_content(
        self,
        input_texts: str = "",
        image_file_paths: List[str] = [],
        output_filepath: Optional[str] = None,
        longform: bool = False
    ) -> str:
        """
        Generate Q&A content based on input texts.

        Args:
            input_texts (str): Input texts to generate content from.
            image_file_paths (List[str]): List of image file paths.
            output_filepath (Optional[str]): Filepath to save the response content.
            is_local (bool): Whether to use a local LLM or not.
            model_name (str): Model name to use for generation.
            api_key_label (str): Environment variable name for API key.
            longform (bool): Whether to generate long-form content. Defaults to False.

        Returns:
            str: Generated conversation content

        Raises:
            ValueError: If strategy validation fails
            Exception: If there's an error in generating content.
        """
        try:
            # Get appropriate strategy
            strategy = self.strategies[longform]
            
            # Validate inputs for chosen strategy
            strategy.validate(input_texts, image_file_paths)

            # Setup chain
            num_images = 0 if self.is_local else len(image_file_paths)
            self.prompt_template, image_path_keys = self.__compose_prompt(num_images, longform)
            self.parser = StrOutputParser()
            self.chain = self.prompt_template | self.llm | self.parser


            # Prepare parameters using strategy
            prompt_params = strategy.compose_prompt_params(
                self.config_conversation,
                image_file_paths,
                image_path_keys,
                input_texts
            )

            # Generate content using selected strategy
            self.response = strategy.generate(
                self.chain,
                input_texts,
                prompt_params
            )

            # Clean response using the same strategy
            self.response = strategy.clean(
                self.response,
                self.content_generator_config
            )
                
            logger.info(f"Content generated successfully")

            # Save output if requested
            if output_filepath:
                with open(output_filepath, "w") as file:
                    file.write(self.response)
                logger.info(f"Response content saved to {output_filepath}")
                print(f"Transcript saved to {output_filepath}")

            return self.response
            
        except Exception as e:
            logger.error(f"Error generating content: {str(e)}")
            raise
