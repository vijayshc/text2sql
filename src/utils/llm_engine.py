from openai import OpenAI
import json
import sys
import logging
import time
from config.config import (
    OPENROUTER_API_KEY, OPENROUTER_BASE_URL, OPENROUTER_MODEL,
    MAX_TOKENS, TEMPERATURE
)


class LLMEngine:
    """
    A centralized engine for handling LLM interactions across the application.
    This class manages the connection to the LLM provider and provides a unified
    interface for making LLM calls.
    """
    
    def __init__(self):
        """Initialize the LLM Engine with OpenRouter API key"""
        self.logger = logging.getLogger('text2sql.llm_engine')
        
        if not OPENROUTER_API_KEY:
            self.logger.critical("OPENROUTER_API_KEY environment variable not set")
            print("Error: OPENROUTER_API_KEY environment variable not set")
            sys.exit(1)
            
        self.logger.info(f"Initializing LLM Engine with endpoint: {OPENROUTER_BASE_URL}")
        self.logger.info(f"Using model: {OPENROUTER_MODEL}")
        
        try:
            self.client = OpenAI(
                base_url=OPENROUTER_BASE_URL,
                api_key=OPENROUTER_API_KEY,
            )
            self.model_name = OPENROUTER_MODEL
            self.logger.info("LLM Engine initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize LLM Engine: {str(e)}", exc_info=True)
            raise
    
    def generate_completion(self, messages, log_prefix="LLM", max_tokens=None, temperature=None):
        """
        Generate a completion using the LLM
        
        Args:
            messages (list): List of SystemMessage and UserMessage objects
            log_prefix (str, optional): Prefix for logging to identify the caller
            max_tokens (int, optional): Maximum tokens to generate, defaults to config value
            temperature (float, optional): Temperature for generation, defaults to config value
            
        Returns:
            str: The generated completion text
        """
        start_time = time.time()
        self.logger.info(f"[{log_prefix}] Completion generation started")
        
        # Convert Azure AI message format to OpenAI format
        openai_messages = []
        for msg in messages:
            if hasattr(msg, 'role') and hasattr(msg, 'content'):
                # If message already has role and content attributes
                role = msg.role
                content = msg.content
            elif isinstance(msg, dict) and 'role' in msg and 'content' in msg:
                # If message is already in OpenAI format
                role = msg['role']
                content = msg['content']
            else:
                # Convert Azure format to OpenAI format
                if msg.__class__.__name__ == 'SystemMessage':
                    role = 'system'
                elif msg.__class__.__name__ == 'UserMessage':
                    role = 'user'
                else:
                    role = 'user'  # Default to user if unknown
                content = msg.content
                
            openai_messages.append({
                "role": role,
                "content": content
            })
        
        # Log the prompt message but truncate if too large
        prompt_str = str(openai_messages)
        if len(prompt_str) > 500:
            self.logger.debug(f"[{log_prefix}] Prompt: {prompt_str[:500]}... (truncated)")
        else:
            self.logger.debug(f"[{log_prefix}] Prompt: {prompt_str}")
        
        # Use provided values or defaults from config
        max_tokens = max_tokens or MAX_TOKENS
        temperature = temperature or TEMPERATURE
        
        try:
            self.logger.debug(f"[{log_prefix}] Sending request to {self.model_name} with max_tokens={max_tokens}, temperature={temperature}")
            call_start = time.time()
            
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=openai_messages,
                max_tokens=max_tokens,
                temperature=temperature
            )
            
            call_duration = time.time() - call_start
            self.logger.debug(f"[{log_prefix}] Model response received in {call_duration:.2f}s")
            
            # Extract response text
            completion_text = response.choices[0].message.content
            
            # Log truncated response if large
            if len(completion_text) > 500:
                self.logger.debug(f"[{log_prefix}] Raw model response: '{completion_text[:500]}...' (truncated)")
            else:
                self.logger.debug(f"[{log_prefix}] Raw model response: '{completion_text}'")
                
            processing_time = time.time() - start_time
            self.logger.info(f"[{log_prefix}] Completion generation completed in {processing_time:.2f}s")
            self.logger.info(f"**************************")
            return completion_text
            
        except Exception as e:
            processing_time = time.time() - start_time
            self.logger.error(f"[{log_prefix}] Completion generation error after {processing_time:.2f}s: {str(e)}", exc_info=True)
            raise
    
    def close(self):
        """Close the LLM Engine client connection"""
        self.logger.debug("Closing LLM Engine client connection")
        # No explicit close method needed for OpenAI client