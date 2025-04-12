from openai import OpenAI
import json
import sys
import logging
import time
import numpy as np
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
            # Initialize models as None initially - they will be loaded on demand
            self.embedding_model = None
            self.reranking_model = None
        except Exception as e:
            self.logger.error(f"Failed to initialize LLM Engine: {str(e)}", exc_info=True)
            raise
    
    def get_embedding_model(self):
        """Get or initialize the sentence transformer model for embeddings
        
        Returns:
            SentenceTransformer: The initialized embedding model
        """
        if self.embedding_model is None:
            start_time = time.time()
            self.logger.info("Loading embedding model 'sentence-transformers/all-MiniLM-L12-v2'")
            try:
                from sentence_transformers import SentenceTransformer
                self.embedding_model = SentenceTransformer('all-MiniLM-L12-v2')
                self.logger.info(f"Embedding model loaded in {time.time() - start_time:.2f}s")
            except Exception as e:
                self.logger.error(f"Failed to load embedding model: {str(e)}", exc_info=True)
                # Return None if failed to load model
                return None
        return self.embedding_model
    
    def generate_embedding(self, text: str):
        """Generate embedding for the given text
        
        Args:
            text (str): Text to generate embedding for
            
        Returns:
            numpy.ndarray or list: Embedding vector or None if failed
        """
        model = self.get_embedding_model()
        if not model or not text:
            self.logger.warning("Embedding model not available or empty text, using random embedding as fallback")
            return np.random.randn(384).tolist()
            
        try:
            start_time = time.time()
            # Generate embedding vector
            embedding = model.encode(text)
            
            self.logger.debug(f"Generated embedding in {time.time() - start_time:.2f}s " +
                             f"with shape {embedding.shape}")
            return embedding
            
        except Exception as e:
            self.logger.error(f"Error generating embedding: {str(e)}", exc_info=True)
            # Fallback to random embeddings
            return np.random.randn(384).tolist()
    
    def get_reranking_model(self):
        """Get or initialize a cross-encoder model for more accurate reranking
        
        Returns:
            CrossEncoder: The initialized reranking model (cross-encoder)
        """
        if self.reranking_model is None:
            start_time = time.time()
            self.logger.info("Loading reranking model 'cross-encoder/ms-marco-MiniLM-L-6-v2'")
            try:
                from sentence_transformers import CrossEncoder
                self.reranking_model = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')
                self.logger.info(f"Reranking model loaded in {time.time() - start_time:.2f}s")
            except Exception as e:
                self.logger.error(f"Failed to load reranking model: {str(e)}", exc_info=True)
                return None
        return self.reranking_model
    
    def generate_completion(self, messages, log_prefix="LLM", max_tokens=None, temperature=None, stream=False):
        """
        Generate a completion using the LLM
        
        Args:
            messages (list): List of SystemMessage and UserMessage objects
            log_prefix (str, optional): Prefix for logging to identify the caller
            max_tokens (int, optional): Maximum tokens to generate, defaults to config value
            temperature (float, optional): Temperature for generation, defaults to config value
            stream (bool, optional): Whether to stream the response, defaults to False
            
        Returns:
            If stream=False: str: The generated completion text
            If stream=True: generator: A generator yielding text chunks
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
            self.logger.debug(f"[{log_prefix}] Sending request to {self.model_name} with max_tokens={max_tokens}, temperature={temperature}, stream={stream}")
            call_start = time.time()
            
            # Handle streaming case
            if stream:
                response = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=openai_messages,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    stream=True
                )
                
                def response_generator():
                    collected_content = []
                    for chunk in response:
                        if chunk.choices and len(chunk.choices) > 0:
                            content = chunk.choices[0].delta.content
                            if content:
                                collected_content.append(content)
                                yield content
                    
                    # Log at the end of streaming
                    call_duration = time.time() - call_start
                    full_response = "".join(collected_content)
                    self.logger.debug(f"[{log_prefix}] Model streaming completed in {call_duration:.2f}s")
                    if len(full_response) > 500:
                        self.logger.debug(f"[{log_prefix}] Raw model response: '{full_response[:500]}...' (truncated)")
                    else:
                        self.logger.debug(f"[{log_prefix}] Raw model response: '{full_response}'")
                    
                    processing_time = time.time() - start_time
                    self.logger.info(f"[{log_prefix}] Completion generation completed in {processing_time:.2f}s")
                    self.logger.info(f"**************************")
                
                return response_generator()
            
            # Handle non-streaming case (original behavior)
            else:
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