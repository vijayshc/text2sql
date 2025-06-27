# filepath: /home/vijay/text2sql_react/src/utils/mcp_client_manager.py
import asyncio
import json
import os
import sys
from typing import Optional, AsyncGenerator, Dict, Any, List, Union, Tuple
from contextlib import AsyncExitStack
from dotenv import load_dotenv
import logging
import uuid
import aiohttp
import traceback

# Set up logger
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
logger = logging.getLogger('text2sql.mcp_client')
load_dotenv(os.path.join(project_root, '.env'))

# Check if we need to modify any paths for MCP
if os.environ.get('MCP_LIBRARY_PATH'):
    sys.path.insert(0, os.environ.get('MCP_LIBRARY_PATH'))

# Import MCP components - with fallbacks for better error handling
MCP_AVAILABLE = False
try:
    # Try to import from the installed packages first
    from mcp import ClientSession
    from mcp.client.stdio import stdio_client, StdioServerParameters
    from mcp.client.sse import sse_client
    MCP_AVAILABLE = True
    logger.info("Successfully imported MCP library components")
except ImportError as e:
    logger.error(f"Failed to import MCP: {e}")

# Import common LLM engine
from src.utils.common_llm import get_llm_engine

# Global registry of active MCP clients
_mcp_clients = {}
_mcp_client_lock = None

def _get_or_create_lock():
    """Get or create an asyncio lock for the current event loop."""
    global _mcp_client_lock
    try:
        # Try to get the current event loop
        loop = asyncio.get_running_loop()
        
        # Always create a new lock for each event loop to avoid binding issues
        if _mcp_client_lock is None:
            _mcp_client_lock = asyncio.Lock()
        else:
            # Check if we need a new lock by testing if the current one is usable
            try:
                # Try to check if lock is bound to current loop
                # If this succeeds without error, the lock is good to use
                if hasattr(_mcp_client_lock, '_get_loop'):
                    lock_loop = _mcp_client_lock._get_loop()
                    if lock_loop != loop or lock_loop.is_closed():
                        _mcp_client_lock = asyncio.Lock()
                else:
                    # Fallback: just create a new lock if we can't check
                    _mcp_client_lock = asyncio.Lock()
            except (RuntimeError, AttributeError):
                # Lock is bound to different/closed loop or doesn't support _get_loop
                _mcp_client_lock = asyncio.Lock()
                
        return _mcp_client_lock
    except RuntimeError:
        # No running event loop - this should not happen in async contexts
        # Return None to indicate no lock available
        logger.warning("No running event loop found when creating lock")
        return None

class MCPClient:
    """Client for interacting with an MCP server (stdio or HTTP)."""
    
    def __init__(self, server_id=None, server_name=None, server_type=None, per_request_connection=True):
        """Initialize an MCP client.
        
        Args:
            server_id: Optional ID of the server (for multi-server management)
            server_name: Optional name of the server
            server_type: Either 'stdio' or 'http'
            per_request_connection: If True, establish fresh connections for each request
                                   If False, maintain persistent connections (legacy mode)
        """
        self.server_id = server_id
        self.server_name = server_name or f"server_{server_id}" if server_id else "unnamed_server"
        self.server_type = server_type
        self.server_config = None
        self.session = None
        self.exit_stack = None  # Will be created when needed
        self._is_connected = False
        self._connection_lock = None  # Will be created when needed
        self._available_tools_cache = None
        self.per_request_connection = per_request_connection  # New mode flag
        
        # Get the shared LLM engine instance
        self.llm_engine = get_llm_engine()

    def _ensure_connection_lock(self):
        """Ensure we have a connection lock for the current event loop."""
        if self._connection_lock is None:
            try:
                loop = asyncio.get_running_loop()
                self._connection_lock = asyncio.Lock()
            except RuntimeError:
                # No event loop running, can't create lock
                logger.warning(f"Cannot create connection lock for {self.server_name}: no event loop")
                return None
        else:
            # Check if lock is still valid for current event loop
            try:
                loop = asyncio.get_running_loop()
                if hasattr(self._connection_lock, '_get_loop'):
                    lock_loop = self._connection_lock._get_loop()
                    if lock_loop != loop or lock_loop.is_closed():
                        self._connection_lock = asyncio.Lock()
            except (RuntimeError, AttributeError):
                # Create new lock if current one is invalid
                try:
                    self._connection_lock = asyncio.Lock()
                except RuntimeError:
                    return None
        return self._connection_lock

    def _ensure_exit_stack(self):
        """Ensure we have a fresh exit stack."""
        if self.exit_stack is None:
            self.exit_stack = AsyncExitStack()
        return self.exit_stack

    async def connect_to_stdio_server(self, command, args=None, env=None):
        """Connect to an MCP server via stdio.
        
        Args:
            command: The command to execute (e.g. python path)
            args: List of arguments or a single string argument
            env: Optional environment variables dict
        """
        # Check if we can proceed
        if not MCP_AVAILABLE:
            logger.error(f"Cannot connect to stdio MCP server {self.server_name}: MCP library not available")
            return False
            
        async with self._ensure_connection_lock() or asyncio.Lock():
            if self._is_connected:
                logger.info(f"Already connected to MCP server {self.server_name}.")
                return True

            if not self.llm_engine:
                logger.error(f"LLM Engine not available for server {self.server_name}")
                return False
                
            if not command:
                logger.error(f"No command specified for stdio MCP server {self.server_name}")
                return False
                
            logger.info(f"Connecting to stdio MCP server: {self.server_name} with command: {command}")
            try:
                # Set up environment variables
                full_env = os.environ.copy()
                if env and isinstance(env, dict):
                    full_env.update(env)

                # Process arguments
                full_args = []
                if args:
                    if isinstance(args, list):
                        full_args.extend(args)
                    elif isinstance(args, str):
                        full_args.append(args)
                
                logger.debug(f"Creating StdioServerParameters with command={command}, args={full_args}")
                
                # Create server parameters - handling potential errors gracefully
                try:
                    server_params = StdioServerParameters(
                        command=command,
                        args=full_args,
                        env=full_env
                    )
                except Exception as param_err:
                    logger.error(f"Error creating StdioServerParameters: {param_err}")
                    return False

                # Set up the connection
                try:
                    # Ensure we have a clean exit stack
                    self._ensure_exit_stack()
                    
                    # Log before establishing stdio connection
                    logger.info(f"Establishing stdio connection with command: {command}")
                    stdio_transport = await self.exit_stack.enter_async_context(stdio_client(server_params))
                    logger.info("Stdio transport created successfully")
                    
                    # Unpack the transport
                    self.stdio, self.write = stdio_transport
                    logger.info("Creating ClientSession")
                    
                    # Create session
                    self.session = await self.exit_stack.enter_async_context(ClientSession(self.stdio, self.write))
                    logger.info("ClientSession created successfully")

                    # Initialize the session
                    logger.info("Initializing MCP session")
                    await self.session.initialize()
                    logger.info("MCP session initialized successfully")
                except Exception as conn_err:
                    logger.error(f"Error establishing stdio connection: {conn_err}")
                    await self._safe_cleanup()
                    return False

                # Get and cache tools
                try:
                    response = await self.session.list_tools()
                    self._available_tools_cache = [{
                        "type": "function",
                        "function": {
                            "name": tool.name,
                            "description": tool.description,
                            "parameters": tool.inputSchema
                        }
                    } for tool in response.tools]

                    self._is_connected = True
                    logger.info(f"Successfully connected to stdio MCP server {self.server_name} with {len(self._available_tools_cache)} tools")
                    return True
                except Exception as tool_err:
                    logger.error(f"Error getting tools from stdio server: {tool_err}")
                    await self._safe_cleanup()
                    return False
                    
            except Exception as e:
                logger.exception(f"Failed to connect to stdio MCP server {self.server_name}")
                await self._safe_cleanup()
                return False

    async def connect_to_http_server(self, base_url, headers=None):
        """Connect to an MCP server via HTTP/SSE.
        
        Args:
            base_url: The base URL of the HTTP MCP server
            headers: Optional headers to include in requests
        """
        # Check if we can proceed
        if not MCP_AVAILABLE:
            logger.error(f"Cannot connect to HTTP MCP server {self.server_name}: MCP library not available")
            return False
            
        async with self._ensure_connection_lock() or asyncio.Lock():
            if self._is_connected:
                logger.info(f"Already connected to HTTP MCP server {self.server_name}.")
                return True

            if not self.llm_engine:
                logger.error(f"LLM Engine not available for server {self.server_name}")
                return False
            
            logger.info(f"Connecting to HTTP MCP server: {self.server_name} at {base_url}")
            try:
                # Ensure we have a clean exit stack
                self._ensure_exit_stack()
                
                # Store the SSE client context manager to maintain reference
                logger.info(f"Creating SSE client for {base_url}")
                self._streams_context = sse_client(base_url, headers=headers)
                
                # Get SSE streams without timeout to avoid event loop issues
                logger.info("Entering SSE client async context")
                try:
                    streams = await self.exit_stack.enter_async_context(self._streams_context)
                except Exception as stream_err:
                    logger.error(f"Error connecting to SSE endpoint: {base_url} - {stream_err}")
                    await self._safe_cleanup()
                    return False
                
                # Create and store session explicitly
                logger.info("Creating ClientSession")
                if not streams:
                    logger.error("SSE streams not initialized properly")
                    await self._safe_cleanup()
                    return False
                
                # Check if we got a single stream or a tuple
                if isinstance(streams, tuple) and len(streams) >= 2:
                    logger.info("Got tuple of streams from SSE client")
                    read_stream, write_stream = streams
                    self._session_context = ClientSession(read_stream, write_stream)
                else:
                    logger.info("Got single stream from SSE client")
                    self._session_context = ClientSession(streams)
                
                # Enter session context without timeout
                logger.info("Entering ClientSession async context")
                try:
                    self.session = await self.exit_stack.enter_async_context(self._session_context)
                except Exception as session_err:
                    logger.error(f"Error creating ClientSession: {session_err}")
                    await self._safe_cleanup()
                    return False
                
                # Initialize the session without timeout
                logger.info("Initializing MCP session")
                try:
                    await self.session.initialize()
                except Exception as init_err:
                    logger.error(f"Error initializing MCP session: {init_err}")
                    await self._safe_cleanup()
                    return False
                
                # Get and cache tools without timeout
                logger.info("Fetching available tools")
                try:
                    response = await self.session.list_tools()
                    self._available_tools_cache = [{
                        "type": "function",
                        "function": {
                            "name": tool.name,
                            "description": tool.description,
                            "parameters": tool.inputSchema
                        }
                    } for tool in response.tools]
                except Exception as tools_err:
                    logger.error(f"Error fetching tools: {tools_err}")
                    await self._safe_cleanup()
                    return False

                self._is_connected = True
                logger.info(f"Successfully connected to HTTP MCP server {self.server_name} with {len(self._available_tools_cache)} tools")
                return True
                
            except Exception as e:
                logger.exception(f"Failed to connect to HTTP MCP server {self.server_name}")
                await self._safe_cleanup()
                return False

    def is_connected(self) -> bool:
        """Check if the client is connected to an MCP server."""
        return self._is_connected and self.session is not None

    async def get_available_tools(self) -> Optional[list]:
        """Get the list of available tools from the MCP server."""
        # Return cached tools if available
        if self._available_tools_cache:
            return self._available_tools_cache
        
        # Ensure we have a connection
        if not self.is_connected():
            logger.info(f"Establishing connection to get tools for {self.server_name}")
            if not await self._ensure_fresh_connection():
                logger.error(f"Cannot get tools: failed to connect to MCP server {self.server_name}")
                return None
            
        try:
            response = await self.session.list_tools()
            self._available_tools_cache = [{
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.inputSchema
                }
            } for tool in response.tools]
            return self._available_tools_cache
        except Exception as e:
            logger.exception(f"Failed to retrieve tools from MCP server {self.server_name}.")
            # Reset connection state on failure
            self._reset_state()
            return None

    async def process_query_stream(self, query: str) -> AsyncGenerator[Dict[str, Any], None]:
        """Process a query using OpenAI and the MCP server tools, streaming progress.
        
        Args:
            query: The user's query
            
        Returns:
            An async generator with streaming updates
        """
        # Check event loop availability first
        if not self._is_event_loop_available():
            yield {"type": "error", "message": f"No event loop available for query processing on {self.server_name}"}
            return
        
        if not self.llm_engine:
            yield {"type": "error", "message": "LLM Engine not configured."}
            return

        # For per-request connection pattern: Always establish fresh connection
        connection_success = await self._ensure_fresh_connection()
        if not connection_success:
            yield {"type": "error", "message": f"Failed to establish connection to MCP server {self.server_name}"}
            return

        # Handle either string query or structured query with conversation history
        if isinstance(query, dict) and 'query' in query:
            # Structured query with conversation history
            logger.info(f"Processing query on server {self.server_name} with conversation history: {query['query']}")
            yield {"type": "status", "message": f"Starting query processing on {self.server_name}..."}
        else:
            # Standard string query
            logger.info(f"Processing query on server {self.server_name}: {query}")
            yield {"type": "status", "message": f"Starting query processing on {self.server_name}..."}

        # Set up conversation with system message
        messages = [
            {
                "role": "system",
                "content": f"""You are an AI assistant using tools provided by the MCP server '{self.server_name}'.

CRITICAL FUNCTION CALLING RULES:
- When you need to use ANY tool/function, respond with ONLY the JSON format specified in the prompt
- Do NOT explain what you're doing before calling functions
- Do NOT mix explanations with function calls
- Use functions immediately when needed, then explain results after getting tool responses

Follow these guidelines:
1. Use tools proactively to solve user requests
2. SQL queries should be compatible with SQLite (avoid CTEs, use subqueries if needed)
3. After receiving tool results, provide a clear summary
4. Only retry failed steps if it makes logical sense
5. Provide a clear final answer when complete"""
            }
        ]
        
        # Add conversation history for context if available
        if hasattr(query, 'get') and isinstance(query, dict) and query.get('conversation_history'):
            # This is a dictionary query with conversation history
            conversation_history = query.get('conversation_history', [])
            current_query = query.get('query', '')
            
            # Add conversation history to messages
            messages.extend(conversation_history)
            
            # Add the current query
            messages.append({
                "role": "user",
                "content": current_query
            })
            logger.info(f"**************: {messages}")
            logger.info(f"Processing query with conversation history ({len(conversation_history)} previous messages)")
            
            # Use the current query for logging
            query_text = current_query
        else:
            # Standard string query without history
            messages.append({
                "role": "user",
                "content": query
            })
            query_text = query

        # Get available tools - ensure we have a connection
        available_tools = None
        if self._available_tools_cache:
            available_tools = self._available_tools_cache
        else:
            available_tools = await self.get_available_tools()
            
        if not available_tools:
            yield {"type": "error", "message": f"Could not retrieve tools from server {self.server_name}."}
            await self._cleanup_after_request()
            return

        try:
            yield {"type": "status", "message": "Generating initial plan..."}
            
            # First LLM call using the common LLM engine
            response = self.llm_engine.generate_completion_with_tools(
                messages=messages,
                tools=available_tools,
                tool_choice="auto",
                log_prefix=f"MCP-{self.server_name}",
                max_tokens=1500
            )

            message = response.choices[0].message
            logger.info(f"Initial LLM response from {self.server_name}: content='{message.content}', has_tool_calls={hasattr(message, 'tool_calls') and message.tool_calls is not None}")

            # Stream initial response if any
            if message.content:
                yield {"type": "llm_response", "content": message.content}
                messages.append({"role": "assistant", "content": message.content})

            # Tool calling loop
            tool_loop_counter = 0
            max_tool_loops = 5
            
            while hasattr(message, 'tool_calls') and message.tool_calls and tool_loop_counter < max_tool_loops:
                tool_loop_counter += 1
                logger.info(f"Tool calls on {self.server_name}: {len(message.tool_calls)} (Loop {tool_loop_counter}/{max_tool_loops})")
                
                assistant_message_with_calls = {
                    "role": "assistant",
                    "content": message.content,
                    "tool_calls": [
                        {"id": tc.id, "type": tc.type, "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
                        for tc in message.tool_calls
                    ]
                }
                
                if assistant_message_with_calls["content"] is None:
                    del assistant_message_with_calls["content"]
                    
                messages.append(assistant_message_with_calls)

                # Process each tool call
                tool_results_for_next_call = []
                for tool_call in message.tool_calls:
                    tool_name = tool_call.function.name
                    tool_args_str = tool_call.function.arguments
                    tool_call_id = tool_call.id

                    try:
                        # Parse and execute tool
                        tool_args = json.loads(tool_args_str)
                        logger.info(f"Calling tool '{tool_name}' with args: {tool_args}")

                        # Execute tool with robust error handling
                        tool_result = await self._execute_tool_with_recovery(tool_name, tool_args, tool_call_id)
                        tool_results_for_next_call.append(tool_result)

                    except json.JSONDecodeError:
                        logger.error(f"Failed to decode arguments for tool {tool_name}: {tool_args_str}")
                        # Don't yield error to user, handle gracefully in backend
                        tool_results_for_next_call.append({
                            "role": "tool",
                            "tool_call_id": tool_call_id,
                            "name": tool_name,
                            "content": json.dumps({"error": "Invalid arguments format provided by LLM."})
                        })
                    except Exception as tool_exc:
                        logger.exception(f"Unexpected error processing tool {tool_name} on {self.server_name}")
                        # Handle gracefully without exposing internal errors to LLM
                        tool_results_for_next_call.append({
                            "role": "tool",
                            "tool_call_id": tool_call_id,
                            "name": tool_name,
                            "content": json.dumps({"error": "Tool temporarily unavailable. Please try again."})
                        })

                # Add all tool results to the conversation
                messages.extend(tool_results_for_next_call)

                # Next LLM call with the tool results
                yield {"type": "status", "message": "Processing tool results..."}
                response = self.llm_engine.generate_completion_with_tools(
                    messages=messages,
                    tools=available_tools,
                    tool_choice="auto",
                    log_prefix=f"MCP-{self.server_name}",
                    max_tokens=1500
                )
                
                message = response.choices[0].message
                logger.info(f"LLM response after tool calls on {self.server_name}: content='{message.content}', has_tool_calls={hasattr(message, 'tool_calls') and message.tool_calls is not None}")

                # Stream the response
                if message.content:
                    yield {"type": "llm_response", "content": message.content}
                    messages.append({"role": "assistant", "content": message.content})

            # Final message check
            last_msg = messages[-1] if messages else {}
            if message.content and not (last_msg.get("role") == "assistant" and last_msg.get("content") == message.content):
                # Send the final message to the client
                yield {"type": "llm_response", "content": message.content, "is_final": True}
                
                # Also update the conversation history with this final message
                messages.append({"role": "assistant", "content": message.content})
                logger.info(f"Added final assistant message to conversation history: {message.content[:50]}...")

            # Complete
            yield {"type": "status", "message": "Processing complete."}
            
            # Clean up connection after request (per-request pattern)
            await self._cleanup_after_request()

        except Exception as e:
            logger.exception(f"Error processing query on server {self.server_name}")
            # Clean up on error as well
            await self._cleanup_after_request()
            yield {"type": "error", "message": f"An error occurred: {str(e)}"}

    async def cleanup(self):
        """Clean up resources (close session and exit stack) - Public method."""
        await self._safe_cleanup()

    async def _safe_cleanup(self):
        """Safe cleanup that handles event loop issues gracefully."""
        # Use connection lock if available
        lock = self._ensure_connection_lock()
        if lock:
            async with lock:
                await self._perform_cleanup()
        else:
            # No event loop available, do synchronous cleanup
            await self._perform_cleanup()
    
    async def _perform_cleanup(self):
        """Perform the actual cleanup operations."""
        # Skip if we're already cleaned up
        if not self.exit_stack and not self.session and not self._is_connected:
            logger.debug(f"Cleanup for {self.server_name} skipped - already cleaned up")
            return
            
        logger.info(f"Cleaning up MCP client resources for server {self.server_name}...")
        
        # Check event loop state
        event_loop_available = True
        try:
            loop = asyncio.get_running_loop()
            if loop.is_closed():
                event_loop_available = False
                logger.warning(f"Event loop is closed during cleanup of {self.server_name}")
        except RuntimeError:
            event_loop_available = False
            logger.warning(f"No running event loop for cleanup of {self.server_name}")
        
        # If no event loop, just reset state
        if not event_loop_available:
            logger.info(f"Event loop unavailable - performing synchronous cleanup for {self.server_name}")
            self._reset_state()
            return
        
        # Try to close the exit stack if it exists
        if self.exit_stack is not None:
            try:
                await self.exit_stack.aclose()
                logger.debug(f"Exit stack closed successfully for {self.server_name}")
            except Exception as e:
                logger.warning(f"Error during exit stack cleanup for {self.server_name}: {e}")
                # Continue with state reset even if exit stack cleanup fails
        
        # Reset all state variables
        self._reset_state()
        logger.info(f"MCP client resources cleaned up for server {self.server_name}.")
    
    def _reset_state(self):
        """Reset all connection state variables."""
        # Reset connection state
        self.session = None
        self._is_connected = False
        self._available_tools_cache = None
        
        # Clear context references
        if hasattr(self, '_session_context'):
            self._session_context = None
        if hasattr(self, '_streams_context'):
            self._streams_context = None
        
        # Reset exit stack - create new one only when needed
        self.exit_stack = None
            
        logger.debug(f"Reset state for MCP client {self.server_name}")

    def _validate_connection(self) -> bool:
        """Validate that the connection is ready for tool calls.
        
        Returns:
            bool: True if connection is valid, False otherwise
        """
        # Check basic connection state
        if not self._is_connected or not self.session:
            logger.warning(f"Connection validation failed: not connected to {self.server_name}")
            return False
            
        # Check event loop state
        try:
            loop = asyncio.get_running_loop()
            if loop.is_closed():
                logger.error(f"Connection validation failed: event loop is closed for {self.server_name}")
                self._is_connected = False
                self.session = None
                return False
        except RuntimeError:
            logger.error(f"Connection validation failed: no running event loop for {self.server_name}")
            self._is_connected = False
            self.session = None
            return False
            
        return True

    def _is_event_loop_available(self) -> bool:
        """Check if there's a running event loop available.
        
        Returns:
            bool: True if event loop is available and running, False otherwise
        """
        try:
            loop = asyncio.get_running_loop()
            return not loop.is_closed()
        except RuntimeError:
            return False

    async def _ensure_fresh_connection(self) -> bool:
        """Ensure we have a fresh, working connection for per-request pattern.
        
        Returns:
            bool: True if connection is ready, False otherwise
        """
        try:
            # Always clean up existing connection for fresh start
            if self._is_connected or self.session:
                logger.info(f"Cleaning up existing connection for fresh start on {self.server_name}")
                await self._safe_cleanup()
            
            # Establish new connection
            if not self.server_config:
                logger.error(f"No server config available for {self.server_name}")
                return False
                
            success = False
            if self.server_type == "stdio":
                success = await self.connect_to_stdio_server(
                    self.server_config.get("command"),
                    self.server_config.get("args"),
                    self.server_config.get("env")
                )
            elif self.server_type == "http":
                success = await self.connect_to_http_server(
                    self.server_config.get("base_url"),
                    self.server_config.get("headers")
                )
            else:
                logger.error(f"Unknown server type: {self.server_type}")
                return False
                
            if success:
                logger.info(f"Fresh connection established successfully for {self.server_name}")
            else:
                logger.error(f"Failed to establish fresh connection for {self.server_name}")
                
            return success
            
        except Exception as e:
            logger.exception(f"Error ensuring fresh connection for {self.server_name}")
            return False

    async def _execute_tool_with_recovery(self, tool_name: str, tool_args: dict, tool_call_id: str) -> dict:
        """Execute a tool call with robust error handling and recovery.
        
        Args:
            tool_name: Name of the tool to call
            tool_args: Arguments for the tool
            tool_call_id: ID of the tool call for response tracking
            
        Returns:
            dict: Tool result in OpenAI API format
        """
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                # Check connection before attempting tool call
                if not self.session or not self._is_connected:
                    logger.warning(f"No active session for tool '{tool_name}' on {self.server_name}, attempting reconnection")
                    
                    # Try to re-establish connection
                    if not await self._ensure_fresh_connection():
                        raise Exception(f"Failed to establish connection for tool '{tool_name}'")
                
                logger.info(f"TOOL CALL ATTEMPT {retry_count + 1}: Calling {tool_name} via MCP session")
                result = await self.session.call_tool(tool_name, tool_args)
                logger.info(f"TOOL CALL SUCCESS: {tool_name} completed successfully")
                
                # Format result for OpenAI API
                result_content = self._format_tool_result(result)
                
                return {
                    "role": "tool",
                    "tool_call_id": tool_call_id,
                    "name": tool_name,
                    "content": result_content
                }
                
            except Exception as call_exc:
                retry_count += 1
                error_msg = str(call_exc).lower()
                
                logger.warning(f"Tool call attempt {retry_count} failed for '{tool_name}' on {self.server_name}: {call_exc}")
                
                # Check for unrecoverable errors
                if any(term in error_msg for term in ["event loop is closed", "runtime error", "no running loop"]):
                    logger.error(f"Unrecoverable runtime error during tool call '{tool_name}' - stopping retries")
                    break
                
                # If we have retries left, try to recover
                if retry_count < max_retries:
                    logger.info(f"Attempting recovery for tool '{tool_name}' (attempt {retry_count}/{max_retries})")
                    
                    # Reset connection state
                    self._reset_state()
                    
                    # Wait a bit before retry
                    await asyncio.sleep(0.5 * retry_count)  # Progressive backoff
                    
                    # Try to re-establish connection
                    if not await self._ensure_fresh_connection():
                        logger.error(f"Failed to re-establish connection during recovery for tool '{tool_name}'")
                        continue  # Try again or fail if max retries reached
                else:
                    logger.error(f"Max retries ({max_retries}) reached for tool '{tool_name}' on {self.server_name}")
                    break
        
        # If we get here, all retries failed
        logger.error(f"Tool '{tool_name}' execution failed after {max_retries} attempts on {self.server_name}")
        
        # Return a graceful error response that doesn't expose internal issues
        return {
            "role": "tool",
            "tool_call_id": tool_call_id,
            "name": tool_name,
            "content": json.dumps({
                "error": f"The {tool_name} tool is temporarily unavailable. Please try your request again or rephrase it."
            })
        }

    def _format_tool_result(self, result) -> str:
        """Format tool result for consistent output.
        
        Args:
            result: Raw tool result from MCP session
            
        Returns:
            str: Formatted result content
        """
        try:
            result_content = str(result.content)
            
            # Handle different result content formats
            if hasattr(result.content, '__getitem__'):
                try:
                    # Try to access as sequence
                    if hasattr(result.content[0], 'text'):
                        result_content = str(result.content[0].text)
                    else:
                        result_content = str(result.content[0])
                except (IndexError, AttributeError):
                    # Fallback to string representation
                    result_content = str(result.content)
            
            return result_content
            
        except Exception as e:
            logger.warning(f"Error formatting tool result: {e}")
            return json.dumps({"error": "Unable to format tool result"})

    async def _cleanup_after_request(self):
        """Clean up connection resources after request completion (for per-request pattern)."""
        try:
            if self.session or self._is_connected:
                logger.debug(f"Cleaning up connection resources after request for {self.server_name}")
                await self._safe_cleanup()
        except Exception as e:
            logger.warning(f"Error during post-request cleanup for {self.server_name}: {e}")

class MCPClientManager:
    """Manager class for handling multiple MCP clients."""
    
    @staticmethod
    async def get_client(server_id, connect=True) -> Optional[MCPClient]:
        """Get a client for a specific server ID.
        
        Args:
            server_id: The ID of the MCP server to get a client for
            connect: Whether to connect the client if it's not connected
            
        Returns:
            An MCPClient instance or None if not found/failed
        """
        global _mcp_clients
        lock = _get_or_create_lock()
        
        # Handle case where no lock is available (no event loop)
        if lock is None:
            logger.warning("No event loop available for client management - operating without lock")
            # Import here to avoid circular imports
            from src.models.mcp_server import MCPServer
            
            # Check if client already exists and is connected
            client = _mcp_clients.get(server_id)
            if client and client.is_connected():
                return client
            
            # Get server config
            server = MCPServer.get_by_id(server_id)
            if not server:
                logger.error(f"Server with ID {server_id} not found")
                return None
            
            # Create new client with per-request connection mode enabled for better reliability
            client = MCPClient(
                server_id=server.id, 
                server_name=server.name, 
                server_type=server.server_type,
                per_request_connection=True
            )
            client.server_config = server.config
            return client
        
        async with lock:
            # Import here to avoid circular imports
            from src.models.mcp_server import MCPServer
            
            # Check if client already exists and is connected
            client = _mcp_clients.get(server_id)
            if client and client.is_connected():
                return client
            
            # Get server config
            server = MCPServer.get_by_id(server_id)
            if not server:
                logger.error(f"Server with ID {server_id} not found")
                return None
            
            # Create new client with per-request connection mode enabled for better reliability
            client = MCPClient(
                server_id=server.id, 
                server_name=server.name, 
                server_type=server.server_type,
                per_request_connection=True
            )
            client.server_config = server.config
            
            # Connect if requested
            if connect and server.status == 'running':
                success = False
                try:
                    if server.server_type == 'stdio':
                        success = await client.connect_to_stdio_server(
                            server.config.get('command'),
                            server.config.get('args'),
                            server.config.get('env')
                        )
                    elif server.server_type == 'http':
                        success = await client.connect_to_http_server(
                            server.config.get('base_url'),
                            server.config.get('headers')
                        )
                        
                    if success:
                        _mcp_clients[server_id] = client
                    else:
                        logger.error(f"Failed to connect to server {server.name}")
                        server.update_status('error')
                        return None
                        
                except Exception as e:
                    logger.exception(f"Failed to connect to MCP server {server.name}")
                    server.update_status('error')
                    return None
                
                server.update_status('running')
            
            return client
    
    @staticmethod
    async def start_server(server_id) -> Tuple[bool, str]:
        """Start a specific MCP server.
        
        Args:
            server_id: The ID of the MCP server to start
            
        Returns:
            A tuple (success, message)
        """
        # Import here to avoid circular imports
        from src.models.mcp_server import MCPServer, MCPServerStatus
        
        server = MCPServer.get_by_id(server_id)
        if not server:
            return False, f"Server with ID {server_id} not found"
        
        if server.status == MCPServerStatus.RUNNING.value:
            return True, f"Server {server.name} is already running"
            
        # Check if MCP is available
        if not MCP_AVAILABLE:
            return False, "MCP library is not available. Please check your installation."
        
        client = await MCPClientManager.get_client(server_id, connect=False)
        if not client:
            return False, f"Failed to create client for server {server.name}"
            
        try:
            success = False
            if server.server_type == 'stdio':
                # Get command
                command = server.config.get('command')
                if not command:
                    return False, "No command specified for stdio server"
                
                # Get args
                args = server.config.get('args')
                
                # Get env
                env = server.config.get('env')
                
                logger.info(f"Starting stdio server {server.name} with command={command}, args={args}")
                success = await client.connect_to_stdio_server(command, args, env)
                
            elif server.server_type == 'http':
                base_url = server.config.get('base_url')
                if not base_url:
                    return False, "No base URL specified for HTTP server"
                    
                headers = server.config.get('headers')
                logger.info(f"Starting HTTP server {server.name} at {base_url}")
                success = await client.connect_to_http_server(base_url, headers)
                
            else:
                return False, f"Unknown server type: {server.server_type}"
            
            if success:
                _mcp_clients[server_id] = client
                server.update_status(MCPServerStatus.RUNNING.value)
                return True, f"Server {server.name} started successfully"
            else:
                server.update_status(MCPServerStatus.ERROR.value)
                return False, f"Failed to connect to server {server.name}"
                
        except Exception as e:
            logger.exception(f"Failed to start MCP server {server.name}")
            server.update_status(MCPServerStatus.ERROR.value)
            return False, f"Failed to start server: {str(e)}"
    
    @staticmethod
    async def stop_server(server_id) -> Tuple[bool, str]:
        """Stop a specific MCP server.
        
        Args:
            server_id: The ID of the MCP server to stop
            
        Returns:
            A tuple (success, message)
        """
        global _mcp_clients
        
        # Import here to avoid circular imports
        from src.models.mcp_server import MCPServer, MCPServerStatus
        
        server = MCPServer.get_by_id(server_id)
        if not server:
            return False, f"Server with ID {server_id} not found"
        
        if server.status == MCPServerStatus.STOPPED.value:
            return True, f"Server {server.name} is already stopped"
        
        client = _mcp_clients.get(server_id)
        if client:
            try:
                await client.cleanup()
                _mcp_clients.pop(server_id, None)
            except Exception as e:
                logger.exception(f"Error stopping MCP server {server.name}")
                return False, f"Error stopping server: {str(e)}"
        
        server.update_status(MCPServerStatus.STOPPED.value)
        return True, f"Server {server.name} stopped successfully"
    
    @staticmethod
    async def restart_server(server_id) -> Tuple[bool, str]:
        """Restart a specific MCP server.
        
        Args:
            server_id: The ID of the MCP server to restart
            
        Returns:
            A tuple (success, message)
        """
        # Import here to avoid circular imports
        from src.models.mcp_server import MCPServer
        
        # Get server info before stopping
        server = MCPServer.get_by_id(server_id)
        if not server:
            return False, f"Server with ID {server_id} not found"
            
        # Store server type for special handling
        server_type = server.server_type
            
        stop_success, stop_message = await MCPClientManager.stop_server(server_id)
        if not stop_success:
            return stop_success, stop_message
        
        # Use a longer delay for HTTP/SSE servers to ensure connections are fully closed
        if server_type == 'http':
            logger.info(f"Using longer delay for HTTP/SSE server restart: {server.name}")
            await asyncio.sleep(1.0)
        else:
            # Small delay for stdio servers
            await asyncio.sleep(0.5)
        
        return await MCPClientManager.start_server(server_id)
    
    @staticmethod
    async def start_all_running_servers() -> List[Dict[str, Any]]:
        """Start all servers that are marked as running in the database.
        
        Returns:
            List of results for each server
        """
        from src.models.mcp_server import MCPServer, MCPServerStatus
        
        servers = MCPServer.get_all()
        results = []
        
        for server in servers:
            if server.status == MCPServerStatus.RUNNING.value:
                success, message = await MCPClientManager.start_server(server.id)
                results.append({
                    "server_id": server.id,
                    "server_name": server.name,
                    "success": success,
                    "message": message
                })
        
        return results
    
    @staticmethod
    async def cleanup_all() -> None:
        """Clean up all MCP clients."""
        global _mcp_clients
        
        lock = _get_or_create_lock()
        
        # Handle case where no lock is available
        if lock is None:
            logger.warning("No event loop available for cleanup_all - performing without lock")
            clients_to_cleanup = list(_mcp_clients.values())
            _mcp_clients.clear()
            
            # Attempt cleanup without async coordination
            for client in clients_to_cleanup:
                if client:
                    try:
                        client._reset_state()
                    except Exception as e:
                        logger.warning(f"Error resetting client state during cleanup_all: {e}")
            return
        
        async with lock:
            cleanup_tasks = []
            for server_id, client in _mcp_clients.items():
                if client:
                    cleanup_tasks.append(client._safe_cleanup())
            
            if cleanup_tasks:
                try:
                    await asyncio.gather(*cleanup_tasks, return_exceptions=True)
                except Exception as e:
                    logger.warning(f"Error during gather in cleanup_all: {e}")
            
            _mcp_clients.clear()
    
    @staticmethod
    async def select_server_for_query(query: str) -> Optional[int]:
        """Select the most appropriate server for a given query.
        
        Args:
            query: The user's query string
            
        Returns:
            The ID of the selected server, or None if no suitable server was found
        """
        from src.models.mcp_server import MCPServer, MCPServerStatus
        
        # Get running servers
        servers = MCPServer.get_all()
        running_servers = [s for s in servers if s.status == MCPServerStatus.RUNNING.value]
        
        if not running_servers:
            logger.warning("No running MCP servers available")
            return None
        
        # If there's only one server, use that
        if len(running_servers) == 1:
            return running_servers[0].id
        
        # Use LLM to select the best server based on the query and server descriptions
        try:
            # Get detailed information about each server
            server_descriptions = []
            for server in running_servers:
                client = _mcp_clients.get(server.id)
                
                tools_description = ""
                if client and client.is_connected():
                    tools = await client.get_available_tools()
                    if tools:
                        tool_names = [tool['function']['name'] for tool in tools]
                        tools_description = f"Available tools: {', '.join(tool_names)}"
                
                server_descriptions.append({
                    "id": server.id,
                    "name": server.name,
                    "description": server.description,
                    "tools": tools_description
                })
            
            # Use LLM engine for server selection
            llm_engine = get_llm_engine()
            if llm_engine:
                response = llm_engine.generate_completion(
                    messages=[
                        {
                            "role": "system",
                            "content": "You are a server selection assistant. Respond ONLY with the ID of the best server for the user's query."
                        },
                        {
                            "role": "user",
                            "content": f"Select the most appropriate MCP server for this query: \n\nQuery: {query}\n\nAvailable servers:\n{json.dumps(server_descriptions, indent=2)}\n\nRespond ONLY with the server ID number."
                        }
                    ],
                    log_prefix="MCP-ServerSelection"
                )
                
                server_id_str = response.strip()
                try:
                    server_id = int(server_id_str)
                    # Verify this is an actual server ID
                    if any(s['id'] == server_id for s in server_descriptions):
                        return server_id
                except ValueError:
                    pass
            
            # Default to first server if LLM selection fails
            logger.warning("Could not select best server via LLM, using first available")
            return running_servers[0].id
            
        except Exception as e:
            logger.exception("Error selecting MCP server for query")
            return running_servers[0].id if running_servers else None

async def get_mcp_client_for_query(query: str) -> Optional[MCPClient]:
    """Get the appropriate MCP client for a given query.
    
    Args:
        query: The user's query
        
    Returns:
        An MCPClient instance, or None if no suitable client was found
    """
    try:
        # Select the appropriate server
        server_id = await MCPClientManager.select_server_for_query(query)
        if not server_id:
            logger.error("No suitable MCP server found for the query")
            return None
        
        # Get client for selected server
        client = await MCPClientManager.get_client(server_id, connect=True)
        return client
        
    except Exception as e:
        logger.exception("Error getting MCP client for query")
        return None
