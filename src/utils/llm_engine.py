from azure.ai.inference import ChatCompletionsClient
from azure.ai.inference.models import SystemMessage, UserMessage
from azure.core.credentials import AzureKeyCredential
import json
import sys
import logging
import time
from config.config import AZURE_ENDPOINT, AZURE_MODEL_NAME, GITHUB_TOKEN, MAX_TOKENS, TEMPERATURE


class LLMEngine:
    """
    A centralized engine for handling LLM interactions across the application.
    This class manages the connection to the LLM provider and provides a unified
    interface for making LLM calls.
    """
    
    def __init__(self):
        """Initialize the LLM Engine with the GitHub token for authentication"""
        self.logger = logging.getLogger('text2sql.llm_engine')
        
        if not GITHUB_TOKEN:
            self.logger.critical("GITHUB_TOKEN environment variable not set")
            print("Error: GITHUB_TOKEN environment variable not set")
            sys.exit(1)
            
        self.logger.info(f"Initializing LLM Engine with endpoint: {AZURE_ENDPOINT}")
        self.logger.info(f"Using model: {AZURE_MODEL_NAME}")
        
        try:
            self.client = ChatCompletionsClient(
                endpoint=AZURE_ENDPOINT,
                credential=AzureKeyCredential(GITHUB_TOKEN),
            )
            self.model_name = AZURE_MODEL_NAME
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
        
        # Log the prompt message but truncate if too large
        prompt_str = str([m.content for m in messages])
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
            
            response = self.client.complete(
                model=self.model_name,
                messages=messages,
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
        try:
            self.client.close()
        except Exception as e:
            self.logger.warning(f"Error closing LLM Engine client: {str(e)}")