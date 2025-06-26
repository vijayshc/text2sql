from openai import OpenAI
import json
import sys
import logging
import time
import numpy as np
from config.config import (
    OPENROUTER_API_KEY, OPENROUTER_BASE_URL, OPENROUTER_MODEL,
    MAX_TOKENS, TEMPERATURE, MESSAGE_FORMAT
)
from src.utils.message_formatter import MessageFormatter


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
        self.logger.info(f"[{log_prefix}] Completion generation started (format: {MESSAGE_FORMAT})")
        
        # Convert message formats to OpenAI format
        openai_messages = []
        for msg in messages:
            if isinstance(msg, dict):
                # Message is already in dictionary format
                if 'role' in msg and 'content' in msg:
                    openai_messages.append({
                        "role": msg['role'],
                        "content": msg['content']
                    })
                elif 'role' in msg:
                    # Handle cases where content might be None or missing
                    openai_messages.append({
                        "role": msg['role'],
                        "content": msg.get('content', '')
                    })
                else:
                    # Invalid message format, skip
                    self.logger.warning(f"[{log_prefix}] Skipping invalid message format: {msg}")
                    continue
            elif hasattr(msg, 'role') and hasattr(msg, 'content'):
                # Message object with attributes
                openai_messages.append({
                    "role": msg.role,
                    "content": msg.content
                })
            else:
                # Convert Azure/other format to OpenAI format
                if hasattr(msg, '__class__'):
                    if msg.__class__.__name__ == 'SystemMessage':
                        role = 'system'
                    elif msg.__class__.__name__ == 'UserMessage':
                        role = 'user'
                    else:
                        role = 'user'  # Default to user if unknown
                    
                    content = getattr(msg, 'content', '')
                    openai_messages.append({
                        "role": role,
                        "content": content
                    })
                else:
                    self.logger.warning(f"[{log_prefix}] Skipping unknown message format: {type(msg)}")
                    continue
        
        # Use provided values or defaults from config
        max_tokens = max_tokens or MAX_TOKENS
        temperature = temperature or TEMPERATURE
        
        try:
            # Handle different message formats
            if MESSAGE_FORMAT == 'llama':
                # Format messages for Llama (no tools)
                formatted_prompt = MessageFormatter.format_messages(openai_messages, None, 'llama')
                request_messages = [{"role": "user", "content": formatted_prompt}]
            else:
                # Use OpenAI format as-is
                request_messages = openai_messages
            
            # Log the prompt message but truncate if too large
            prompt_str = str(request_messages)
            
            if len(prompt_str) > 500:
                self.logger.debug(f"[{log_prefix}] Prompt: {prompt_str[:500]}... (truncated)")
            else:
                self.logger.debug(f"[{log_prefix}] Prompt: {prompt_str}")
            
            self.logger.debug(f"[{log_prefix}] Sending request to {self.model_name} with max_tokens={max_tokens}, temperature={temperature}, stream={stream}")
            call_start = time.time()
            
            # Handle streaming case
            self.logger.info(f"message {request_messages}")
            if stream:
                response = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=request_messages,
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
                    messages=request_messages,
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
    
    def generate_completion_with_tools(self, messages, tools=None, tool_choice="auto", log_prefix="LLM", max_tokens=None, temperature=None):
        """
        Generate a completion using the LLM with tool calling support
        
        Args:
            messages (list): List of messages in OpenAI format
            tools (list, optional): List of tool definitions for function calling
            tool_choice (str, optional): Tool choice strategy ("auto", "none", or specific tool)
            log_prefix (str, optional): Prefix for logging to identify the caller
            max_tokens (int, optional): Maximum tokens to generate, defaults to config value
            temperature (float, optional): Temperature for generation, defaults to config value
            
        Returns:
            OpenAI completion response object with tool calls if any
        """
        start_time = time.time()
        self.logger.info(f"[{log_prefix}] Tool-enabled completion generation started (format: {MESSAGE_FORMAT})")
        
        # Convert message format if needed
        openai_messages = []
        for msg in messages:
            if isinstance(msg, dict):
                # Message is already in dictionary format
                if 'role' in msg and 'content' in msg:
                    openai_messages.append(msg)
                elif 'role' in msg:
                    # Handle cases where content might be None or missing
                    openai_messages.append({
                        "role": msg['role'],
                        "content": msg.get('content', ''),
                        **{k: v for k, v in msg.items() if k not in ['role', 'content']}  # Preserve other fields like tool_calls
                    })
                else:
                    # Invalid message format, skip
                    self.logger.warning(f"[{log_prefix}] Skipping invalid message format: {msg}")
                    continue
            elif hasattr(msg, 'role') and hasattr(msg, 'content'):
                # Message object with attributes
                openai_messages.append({
                    "role": msg.role,
                    "content": msg.content
                })
            else:
                # Convert Azure/other format to OpenAI format
                if hasattr(msg, '__class__'):
                    if msg.__class__.__name__ == 'SystemMessage':
                        role = 'system'
                    elif msg.__class__.__name__ == 'UserMessage':
                        role = 'user'
                    else:
                        role = 'user'  # Default to user if unknown
                    
                    content = getattr(msg, 'content', '')
                    openai_messages.append({
                        "role": role,
                        "content": content
                    })
                else:
                    self.logger.warning(f"[{log_prefix}] Skipping unknown message format: {type(msg)}")
                    continue
        
        # Use provided values or defaults from config
        max_tokens = max_tokens or MAX_TOKENS
        temperature = temperature or TEMPERATURE
        
        try:
            # Handle different message formats
            if MESSAGE_FORMAT == 'llama':
                return self._generate_llama_completion(openai_messages, tools, tool_choice, log_prefix, max_tokens, temperature, start_time)
            else:
                return self._generate_openai_completion(openai_messages, tools, tool_choice, log_prefix, max_tokens, temperature, start_time)
                
        except Exception as e:
            processing_time = time.time() - start_time
            self.logger.error(f"[{log_prefix}] Tool-enabled completion generation error after {processing_time:.2f}s: {str(e)}", exc_info=True)
            raise

    def _generate_openai_completion(self, openai_messages, tools, tool_choice, log_prefix, max_tokens, temperature, start_time):
        """Generate completion using OpenAI format."""
        # Log the prompt message but truncate if too large
        prompt_str = str(openai_messages)
        
        if len(prompt_str) > 500:
            self.logger.debug(f"[{log_prefix}] Prompt: {prompt_str[:500]}... (truncated)")
        else:
            self.logger.debug(f"[{log_prefix}] Prompt: {prompt_str}")
        
        # Prepare request parameters
        request_params = {
            "model": self.model_name,
            "messages": openai_messages,
            "max_tokens": max_tokens,
            "temperature": temperature
        }
        
        # Add tools if provided
        if tools:
            request_params["tools"] = tools
            request_params["tool_choice"] = tool_choice
            self.logger.debug(f"[{log_prefix}] Including {len(tools)} tools with choice: {tool_choice}")
        
        self.logger.debug(f"[{log_prefix}] Sending request to {self.model_name} with max_tokens={max_tokens}, temperature={temperature}")
        call_start = time.time()
        
        response = self.client.chat.completions.create(**request_params)
        
        call_duration = time.time() - call_start
        self.logger.debug(f"[{log_prefix}] Model response received in {call_duration:.2f}s")
        
        message = response.choices[0].message
        
        # Log response details
        if message.content:
            if len(message.content) > 500:
                self.logger.debug(f"[{log_prefix}] Raw model response: '{message.content[:500]}...' (truncated)")
            else:
                self.logger.debug(f"[{log_prefix}] Raw model response: '{message.content}'")
        
        if hasattr(message, 'tool_calls') and message.tool_calls:
            self.logger.debug(f"[{log_prefix}] Model requested {len(message.tool_calls)} tool calls")
            
        processing_time = time.time() - start_time
        self.logger.info(f"[{log_prefix}] Tool-enabled completion generation completed in {processing_time:.2f}s")
        self.logger.info(f"**************************")
        
        return response

    def _generate_llama_completion(self, openai_messages, tools, tool_choice, log_prefix, max_tokens, temperature, start_time):
        """Generate completion using Llama format."""
        # Format messages for Llama
        formatted_prompt = MessageFormatter.format_messages(openai_messages, tools, 'llama')
        
        if len(formatted_prompt) > 500:
            self.logger.debug(f"[{log_prefix}] Llama prompt: {formatted_prompt[:500]}... (truncated)")
        else:
            self.logger.debug(f"[{log_prefix}] Llama prompt: {formatted_prompt}")
        
        # Prepare request for Llama (no tools in request params, they're in the prompt)
        request_params = {
            "model": self.model_name,
            "messages": [{"role": "user", "content": formatted_prompt}],
            "max_tokens": max_tokens,
            "temperature": temperature
        }
        
        if tools:
            self.logger.debug(f"[{log_prefix}] Including {len(tools)} tools in Llama prompt")
        
        self.logger.debug(f"[{log_prefix}] Sending Llama request to {self.model_name} with max_tokens={max_tokens}, temperature={temperature}")
        call_start = time.time()

        self.logger.info(f"message {request_params}")
        
        response = self.client.chat.completions.create(**request_params)
        
        call_duration = time.time() - call_start
        self.logger.debug(f"[{log_prefix}] Llama model response received in {call_duration:.2f}s")
        
        # Parse Llama response and convert to OpenAI format
        raw_content = response.choices[0].message.content
        
        if raw_content:
            if len(raw_content) > 500:
                self.logger.debug(f"[{log_prefix}] Raw Llama response: '{raw_content[:500]}...' (truncated)")
            else:
                self.logger.debug(f"[{log_prefix}] Raw Llama response: '{raw_content}'")
        
        # Parse the response to extract tool calls or regular content
        parsed_message = MessageFormatter.parse_llama_response(raw_content, tools)
        
        # Log what we parsed
        if 'tool_calls' in parsed_message and parsed_message['tool_calls']:
            self.logger.info(f"[{log_prefix}] Parsed {len(parsed_message['tool_calls'])} tool calls from LLaMA response")
            for i, tool_call in enumerate(parsed_message['tool_calls']):
                self.logger.debug(f"[{log_prefix}] Tool call {i+1}: {tool_call['function']['name']}({tool_call['function']['arguments']})")
        else:
            self.logger.debug(f"[{log_prefix}] No tool calls found in LLaMA response, treating as regular content")
        
        # Create a mock response object similar to OpenAI's structure
        class LlamaResponse:
            def __init__(self, message_data):
                self.choices = [LlamaChoice(message_data)]
        
        class LlamaChoice:
            def __init__(self, message_data):
                self.message = LlamaMessage(message_data)
        
        class LlamaMessage:
            def __init__(self, message_data):
                self.content = message_data.get('content')
                self.role = message_data.get('role', 'assistant')
                if 'tool_calls' in message_data:
                    self.tool_calls = [LlamaToolCall(tc) for tc in message_data['tool_calls']]
                else:
                    self.tool_calls = None
        
        class LlamaToolCall:
            def __init__(self, tool_call_data):
                self.id = tool_call_data['id']
                self.type = tool_call_data['type']
                self.function = LlamaFunction(tool_call_data['function'])
        
        class LlamaFunction:
            def __init__(self, function_data):
                self.name = function_data['name']
                self.arguments = function_data['arguments']
        
        llama_response = LlamaResponse(parsed_message)
        
        if llama_response.choices[0].message.tool_calls:
            self.logger.debug(f"[{log_prefix}] Llama model requested {len(llama_response.choices[0].message.tool_calls)} tool calls")
        
        processing_time = time.time() - start_time
        self.logger.info(f"[{log_prefix}] Llama tool-enabled completion generation completed in {processing_time:.2f}s")
        self.logger.info(f"**************************")
        
        return llama_response

    def close(self):
        """Close the LLM Engine client connection"""
        self.logger.debug("Closing LLM Engine client connection")
        # No explicit close method needed for OpenAI client