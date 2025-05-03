# filepath: /home/vijay/text2sql_react/src/utils/mcp_client_manager.py
import asyncio
import json
import os
import sys
from typing import Optional, AsyncGenerator, Dict, Any, List, Union, Tuple
from contextlib import AsyncExitStack
from openai import OpenAI
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
    
# API settings
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY","")
OPENROUTER_BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "google/gemini-flash-1.5-8b-exp")

# Global registry of active MCP clients
_mcp_clients = {}
_mcp_client_lock = asyncio.Lock()

class MCPClient:
    """Client for interacting with an MCP server (stdio or HTTP)."""
    
    def __init__(self, server_id=None, server_name=None, server_type=None):
        """Initialize an MCP client.
        
        Args:
            server_id: Optional ID of the server (for multi-server management)
            server_name: Optional name of the server
            server_type: Either 'stdio' or 'http'
        """
        self.server_id = server_id
        self.server_name = server_name or f"server_{server_id}" if server_id else "unnamed_server"
        self.server_type = server_type
        self.server_config = None
        self.session = None
        self.exit_stack = AsyncExitStack()
        self.model = OPENROUTER_MODEL
        self.client = None
        self._is_connected = False
        self._connection_lock = asyncio.Lock()
        self._available_tools_cache = None
        
        if OPENROUTER_API_KEY:
            self.client = OpenAI(
                base_url=OPENROUTER_BASE_URL,
                api_key=OPENROUTER_API_KEY,
            )
        else:
            logger.warning(f"OPENROUTER_API_KEY not found for server {self.server_name}. OpenAI client not initialized.")

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
            
        async with self._connection_lock:
            if self._is_connected:
                logger.info(f"Already connected to MCP server {self.server_name}.")
                return True

            if not self.client:
                logger.error(f"OpenAI client not initialized for server {self.server_name}")
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
                    # Make sure we have a clean exit stack
                    if self.exit_stack is None:
                        self.exit_stack = AsyncExitStack()
                    
                    # Log before establishing stdio connection
                    logger.info(f"Establishing stdio connection with command: {command}")
                    stdio_transport = await asyncio.wait_for(
                        self.exit_stack.enter_async_context(stdio_client(server_params)),
                        timeout=10.0  # Add timeout to prevent hanging
                    )
                    logger.info("Stdio transport created successfully")
                    
                    # Unpack the transport
                    self.stdio, self.write = stdio_transport
                    logger.info("Creating ClientSession")
                    
                    # Create session
                    self.session = await asyncio.wait_for(
                        self.exit_stack.enter_async_context(ClientSession(self.stdio, self.write)),
                        timeout=5.0
                    )
                    logger.info("ClientSession created successfully")

                    # Initialize the session
                    logger.info("Initializing MCP session")
                    await asyncio.wait_for(
                        self.session.initialize(),
                        timeout=5.0
                    )
                    logger.info("MCP session initialized successfully")
                except asyncio.TimeoutError as to_err:
                    logger.error(f"Timeout establishing stdio connection: {to_err}")
                    await self.cleanup()
                    return False
                except Exception as conn_err:
                    logger.error(f"Error establishing stdio connection: {conn_err}")
                    await self.cleanup()
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
                    await self.cleanup()
                    return False
                    
            except Exception as e:
                logger.exception(f"Failed to connect to stdio MCP server {self.server_name}")
                await self.cleanup()
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
            
        async with self._connection_lock:
            if self._is_connected:
                logger.info(f"Already connected to HTTP MCP server {self.server_name}.")
                return True

            if not self.client:
                logger.error(f"OpenAI client not initialized for server {self.server_name}")
                return False
            
            logger.info(f"Connecting to HTTP MCP server: {self.server_name} at {base_url}")
            try:
                # Create a fresh event loop specifically for SSE connections
                # This is important as SSE connections are long-lived and may need their own event loop
                logger.info("Setting up fresh event loop for HTTP/SSE connection")
                try:
                    # First check if we can reuse the existing loop
                    loop = asyncio.get_event_loop()
                    if loop.is_closed():
                        logger.warning("Event loop is closed. Creating new event loop for HTTP/SSE.")
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                except RuntimeError:
                    logger.warning("No event loop found. Creating new event loop for HTTP/SSE.")
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                
                # Make sure we have a clean exit stack
                if self.exit_stack is None:
                    self.exit_stack = AsyncExitStack()
                
                # Store the SSE client context manager to maintain reference
                logger.info(f"Creating SSE client for {base_url}")
                self._streams_context = sse_client(base_url, headers=headers)
                
                # Get SSE streams with timeout to prevent hanging
                logger.info("Entering SSE client async context")
                streams = await asyncio.wait_for(
                    self.exit_stack.enter_async_context(self._streams_context),
                    timeout=10.0
                )
                
                # Create and store session explicitly
                logger.info("Creating ClientSession")
                if not streams:
                    logger.error("SSE streams not initialized properly")
                    return False
                
                # Check if we got a single stream or a tuple
                if isinstance(streams, tuple) and len(streams) >= 2:
                    logger.info("Got tuple of streams from SSE client")
                    read_stream, write_stream = streams
                    self._session_context = ClientSession(read_stream, write_stream)
                else:
                    logger.info("Got single stream from SSE client")
                    self._session_context = ClientSession(streams)
                
                # Enter session context with timeout
                logger.info("Entering ClientSession async context")
                self.session = await asyncio.wait_for(
                    self.exit_stack.enter_async_context(self._session_context),
                    timeout=5.0
                )
                
                # Initialize the session with timeout
                logger.info("Initializing MCP session")
                await asyncio.wait_for(
                    self.session.initialize(),
                    timeout=10.0
                )
                
                # Get and cache tools with timeout
                logger.info("Fetching available tools")
                response = await asyncio.wait_for(
                    self.session.list_tools(),
                    timeout=10.0
                )
                self._available_tools_cache = [{
                    "type": "function",
                    "function": {
                        "name": tool.name,
                        "description": tool.description,
                        "parameters": tool.inputSchema
                    }
                } for tool in response.tools]

                self._is_connected = True
                logger.info(f"Successfully connected to HTTP MCP server {self.server_name} with {len(self._available_tools_cache)} tools")
                return True
                
            except asyncio.TimeoutError as te:
                logger.error(f"Timeout connecting to HTTP MCP server {self.server_name}: {te}")
                await self.cleanup()
                return False
            except Exception as e:
                logger.exception(f"Failed to connect to HTTP MCP server {self.server_name}")
                await self.cleanup()
                return False

    def is_connected(self) -> bool:
        """Check if the client is connected to an MCP server."""
        return self._is_connected and self.session is not None

    async def get_available_tools(self) -> Optional[list]:
        """Get the list of available tools from the MCP server."""
        if not self.is_connected():
            logger.warning(f"Cannot get tools: not connected to MCP server {self.server_name}.")
            return None
            
        if self._available_tools_cache:
            return self._available_tools_cache
            
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
            return None

    async def process_query_stream(self, query: str) -> AsyncGenerator[Dict[str, Any], None]:
        """Process a query using OpenAI and the MCP server tools, streaming progress.
        
        Args:
            query: The user's query
            
        Returns:
            An async generator with streaming updates
        """
        if not self.is_connected():
            yield {"type": "error", "message": f"Not connected to MCP server {self.server_name}."}
            return
            
        if not self.client:
            yield {"type": "error", "message": "OpenAI client not configured."}
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
Follow these guidelines:
1. Plan your approach before taking action
2. Explain your reasoning and actions clearly
3. When using tools, clearly state the tool name and arguments
4. After receiving tool results, provide a brief summary
5. SQL queries should be compatible with SQLite (avoid CTEs, use subqueries if needed)
6. Retry failed steps only if it makes logical sense
7. Provide a clear final answer when complete"""
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

        # Get available tools
        available_tools = await self.get_available_tools()
        if not available_tools:
            yield {"type": "error", "message": f"Could not retrieve tools from server {self.server_name}."}
            return

        try:
            yield {"type": "status", "message": "Generating initial plan..."}
            
            # First LLM call
            response = self.client.chat.completions.create(
                model=self.model,
                max_tokens=1500,
                messages=messages,
                tools=available_tools,
                tool_choice="auto"
            )

            message = response.choices[0].message
            logger.info(f"Initial LLM response from {self.server_name}: {message}")

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
#                        yield {"type": "tool_call", "tool_name": tool_name, "arguments": tool_args}

                        # Call the tool through the MCP session
                        try:
                            # Make sure event loop is available before making the call
                            try:
                                loop = asyncio.get_event_loop()
                                if loop.is_closed():
                                    logger.warning(f"Event loop closed before tool call '{tool_name}'. Creating new event loop.")
                                    loop = asyncio.new_event_loop()
                                    asyncio.set_event_loop(loop)
                            except RuntimeError:
                                logger.warning(f"No event loop found before tool call '{tool_name}'. Creating new event loop.")
                                loop = asyncio.new_event_loop()
                                asyncio.set_event_loop(loop)
                            
                            # Special handling for HTTP/SSE connections
                            if self.server_type == 'http':
                                # For SSE connections, we need to be extra careful about event loop state
                                loop = asyncio.get_event_loop()
                                if not loop.is_running():
                                    logger.info(f"Using fresh event loop for HTTP/SSE tool call: {tool_name}")
                            
                            logger.info(f"STARTING TOOL CALL: About to call {tool_name} via MCP session")
                            result = await asyncio.wait_for(
                                self.session.call_tool(tool_name, tool_args),
                                timeout=15.0  # Increased timeout for better stability
                            )
                            logger.info(f"TOOL CALL COMPLETED: {tool_name} call returned successfully")
                        except asyncio.TimeoutError:
                            logger.error(f"TIMEOUT: Tool call to {tool_name} timed out after 15 seconds")
                            # Don't raise exception, try to reconnect instead
                            await self.cleanup()
                            success = False
                            
                            # Reconnect with new event loop
                            asyncio.set_event_loop(asyncio.new_event_loop())
                            
                            if self.server_type == "stdio" and self.server_config:
                                success = await self.connect_to_stdio_server(
                                    self.server_config.get("command"),
                                    self.server_config.get("args"),
                                    self.server_config.get("env")
                                )
                            elif self.server_type == "http" and self.server_config:
                                success = await self.connect_to_http_server(
                                    self.server_config.get("base_url"),
                                    self.server_config.get("headers")
                                )
                            
                            if success:
                                logger.info(f"RETRY TOOL CALL: Retrying {tool_name} after timeout reconnection")
                                result = await asyncio.wait_for(
                                    self.session.call_tool(tool_name, tool_args),
                                    timeout=15.0
                                )
                            else:
                                raise Exception(f"Tool call timeout: {tool_name} did not respond within 15 seconds and reconnection failed")
                        except RuntimeError as rt_err:
                            # Handle "Event loop is closed" error specifically
                            logger.warning(f"Runtime error calling tool '{tool_name}' on {self.server_name}: {rt_err}")
                            
                            # Special handling for HTTP/SSE connections which are more sensitive to event loop issues
                            if self.server_type == "http":
                                logger.info(f"Using special handling for HTTP/SSE event loop issues with tool '{tool_name}'")
                                # Force cleanup but don't wait for it to complete to avoid further event loop errors
                                asyncio.create_task(self.cleanup())
                                
                                # Create fresh event loop for HTTP connections
                                loop = asyncio.new_event_loop()
                                asyncio.set_event_loop(loop)
                                
                                # Allow a moment for things to stabilize
                                await asyncio.sleep(0.5)
                                
                                logger.info(f"Reconnecting HTTP server with fresh event loop after error")
                                success = await self.connect_to_http_server(
                                    self.server_config.get("base_url"),
                                    self.server_config.get("headers")
                                )
                            else:
                                # For stdio connections, use the standard approach
                                # Force cleanup
                                await self.cleanup()
                                
                                # Create a completely new event loop
                                loop = asyncio.new_event_loop()
                                asyncio.set_event_loop(loop)
                                
                                # Reconnect with fresh event loop
                                success = False
                                logger.info(f"Reconnecting stdio server after event loop error")
                                success = await self.connect_to_stdio_server(
                                    self.server_config.get("command"),
                                    self.server_config.get("args"),
                                    self.server_config.get("env")
                                )
                            
                            if not success:
                                logger.error(f"Failed to reconnect after event loop error for tool '{tool_name}'")
                                raise Exception(f"Failed to recover from event loop error when calling tool '{tool_name}'")
                            
                            # Retry the call after reconnection
                            logger.info(f"RETRY TOOL CALL: Retrying {tool_name} after event loop reconnection")
                            result = await asyncio.wait_for(
                                self.session.call_tool(tool_name, tool_args),
                                timeout=15.0  # Add timeout to prevent hanging on retry
                            )
                        except Exception as call_exc:
                            logger.warning(f"Error calling tool '{tool_name}' on {self.server_name}: {call_exc}. Attempting to reconnect.")
                            # Try to reconnect based on server type
                            await self.cleanup()  # Ensure clean disconnection before reconnecting
                            
                            # Create a new event loop for reconnection
                            try:
                                if asyncio.get_event_loop().is_closed():
                                    asyncio.set_event_loop(asyncio.new_event_loop())
                            except Exception:
                                asyncio.set_event_loop(asyncio.new_event_loop())
                            
                            success = False
                            if self.server_type == "stdio" and self.server_config:
                                success = await self.connect_to_stdio_server(
                                    self.server_config.get("command"),
                                    self.server_config.get("args"),
                                    self.server_config.get("env")
                                )
                            elif self.server_type == "http" and self.server_config:
                                success = await self.connect_to_http_server(
                                    self.server_config.get("base_url"),
                                    self.server_config.get("headers")
                                )
                                
                            if not success:
                                raise Exception(f"Failed to reconnect for tool '{tool_name}' call")
                                
                            # Retry the call after reconnection
                            logger.info(f"RETRY TOOL CALL: Retrying {tool_name} after reconnection")
                            result = await asyncio.wait_for(
                                self.session.call_tool(tool_name, tool_args),
                                timeout=15.0  # Add timeout to prevent hanging on retry
                            )
                        
                        # Process result
                        logger.info(f"Tool '{tool_name}' result on {self.server_name}: {result}")
                        
                        # Format result for OpenAI API
                        result_content = str(result.content)
                        if hasattr(result.content, '__getitem__'):
                            try:
                                # Try to access as sequence
                                result_content = str(result.content[0].text)
                            except (IndexError, AttributeError):
                                # Fallback to string representation
                                result_content = str(result.content)
                                
                        tool_results_for_next_call.append({
                            "role": "tool",
                            "tool_call_id": tool_call_id,
                            "name": tool_name,
                            "content": result_content
                        })

                    except json.JSONDecodeError:
                        logger.error(f"Failed to decode arguments for tool {tool_name}: {tool_args_str}")
                        yield {"type": "error", "message": f"Invalid arguments format for tool {tool_name}"}
                        tool_results_for_next_call.append({
                            "role": "tool",
                            "tool_call_id": tool_call_id,
                            "name": tool_name,
                            "content": json.dumps({"error": "Invalid arguments format provided by LLM."})
                        })
                    except Exception as tool_exc:
                        logger.exception(f"Error executing tool {tool_name} on {self.server_name}")
                        yield {"type": "error", "message": f"Error calling tool {tool_name}: {str(tool_exc)}"}
                        tool_results_for_next_call.append({
                            "role": "tool",
                            "tool_call_id": tool_call_id,
                            "name": tool_name,
                            "content": json.dumps({"error": f"Tool execution failed: {str(tool_exc)}"})
                        })

                # Add all tool results to the conversation
                messages.extend(tool_results_for_next_call)

                # Next LLM call with the tool results
                yield {"type": "status", "message": "Processing tool results..."}
                response = self.client.chat.completions.create(
                    model=self.model,
                    max_tokens=1500,
                    messages=messages,
                    tools=available_tools,
                    tool_choice="auto"
                )
                
                message = response.choices[0].message
                logger.info(f"LLM response after tool calls on {self.server_name}: {message}")

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

        except Exception as e:
            logger.exception(f"Error processing query on server {self.server_name}")
            yield {"type": "error", "message": f"An error occurred: {str(e)}"}

    async def cleanup(self):
        """Clean up resources (close session and exit stack)."""
        async with self._connection_lock:
            # Skip if we're already cleaned up
            if not self.exit_stack and not self.session and not self._is_connected:
                logger.debug(f"Cleanup for {self.server_name} skipped - already cleaned up")
                return
                
            logger.info(f"Cleaning up MCP client resources for server {self.server_name}...")
            
            # Create a working event loop if needed
            need_new_loop = False
            try:
                loop = asyncio.get_event_loop()
                if loop.is_closed():
                    logger.warning(f"Event loop closed during cleanup for {self.server_name}. Creating new loop.")
                    need_new_loop = True
            except RuntimeError:
                logger.warning(f"No event loop found during cleanup for {self.server_name}. Creating new loop.")
                need_new_loop = True
                
            if need_new_loop:
                asyncio.set_event_loop(asyncio.new_event_loop())
            
            # Clean up session separately first
            if hasattr(self, '_session_context') and self._session_context:
                try:
                    # For SSE connections, we need to check the event loop state before cleanup
                    if self.server_type == 'http':
                        # Try to ensure we have a valid event loop
                        try:
                            loop = asyncio.get_event_loop()
                            if loop.is_closed():
                                loop = asyncio.new_event_loop()
                                asyncio.set_event_loop(loop)
                        except RuntimeError:
                            loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(loop)
                            
                    await asyncio.wait_for(
                        self._session_context.__aexit__(None, None, None),
                        timeout=3.0
                    )
                except Exception as e:
                    logger.warning(f"Error closing session context for {self.server_name}: {e}")
                finally:
                    self._session_context = None
                    
            # Clean up streams separately
            if hasattr(self, '_streams_context') and self._streams_context:
                try:
                    # Make sure we have a working event loop before cleaning up SSE streams
                    if self.server_type == 'http':
                        try:
                            loop = asyncio.get_event_loop()
                            if loop.is_closed():
                                loop = asyncio.new_event_loop()
                                asyncio.set_event_loop(loop)
                        except RuntimeError:
                            loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(loop)
                            
                    await asyncio.wait_for(
                        self._streams_context.__aexit__(None, None, None),
                        timeout=3.0
                    )
                except Exception as e:
                    logger.warning(f"Error closing streams context for {self.server_name}: {e}")
                finally:
                    self._streams_context = None                # Now clean up the exit stack
            if self.exit_stack:
                try:
                    # Use a timeout to prevent hanging during cleanup
                    # For HTTP/SSE connections, we need special handling for event loop issues
                    if self.server_type == 'http':
                        try:
                            # Create a fresh event loop for cleanup if needed
                            loop = asyncio.get_event_loop()
                            if loop.is_closed():
                                logger.info(f"Creating fresh event loop for HTTP/SSE cleanup")
                                loop = asyncio.new_event_loop()
                                asyncio.set_event_loop(loop)
                            
                            # For HTTP/SSE connections, use a shorter timeout to avoid blocking
                            await asyncio.wait_for(
                                self.exit_stack.aclose(),
                                timeout=3.0
                            )
                        except (RuntimeError, asyncio.TimeoutError):
                            logger.warning(f"Forcing exit stack cleanup for HTTP/SSE server {self.server_name}")
                            # Just reset the exit stack without waiting for it to close properly
                            self.exit_stack = None
                    else:
                        # For stdio connections, use normal approach
                        await asyncio.wait_for(
                            self.exit_stack.aclose(),
                            timeout=5.0
                        )
                except asyncio.TimeoutError:
                    logger.warning(f"Timeout during exit stack cleanup for {self.server_name}")
                except Exception as e:
                    logger.warning(f"Ignored error during exit stack cleanup for {self.server_name}: {e}")
            
            # Reset all state variables
            self.exit_stack = None
            self.session = None
            self._is_connected = False
            self._available_tools_cache = None
            logger.info(f"MCP client resources cleaned up for server {self.server_name}.")


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
        async with _mcp_client_lock:
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
            
            # Create new client
            client = MCPClient(server_id=server.id, server_name=server.name, server_type=server.server_type)
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
            
            # Create fresh event loop for HTTP restarts
            try:
                loop = asyncio.get_event_loop()
                if loop.is_closed():
                    logger.info("Creating fresh event loop for HTTP server restart")
                    asyncio.set_event_loop(asyncio.new_event_loop())
            except RuntimeError:
                logger.info("No event loop found, creating new one for HTTP server restart")
                asyncio.set_event_loop(asyncio.new_event_loop())
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
        
        cleanup_tasks = []
        async with _mcp_client_lock:
            for server_id, client in _mcp_clients.items():
                if client:
                    cleanup_tasks.append(client.cleanup())
            
            if cleanup_tasks:
                await asyncio.gather(*cleanup_tasks, return_exceptions=True)
            
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
            
            # Use OpenRouter LLM for server selection
            if OPENROUTER_API_KEY:
                client = OpenAI(
                    base_url=OPENROUTER_BASE_URL,
                    api_key=OPENROUTER_API_KEY,
                )
                
                response = client.chat.completions.create(
                    model=OPENROUTER_MODEL,
                    messages=[
                        {
                            "role": "system",
                            "content": "You are a server selection assistant. Respond ONLY with the ID of the best server for the user's query."
                        },
                        {
                            "role": "user",
                            "content": f"Select the most appropriate MCP server for this query: \n\nQuery: {query}\n\nAvailable servers:\n{json.dumps(server_descriptions, indent=2)}\n\nRespond ONLY with the server ID number."
                        }
                    ]
                )
                
                server_id_str = response.choices[0].message.content.strip()
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
