import asyncio
import json
import os
import sys
import logging
import uuid
import aiohttp
import traceback
from typing import Optional, AsyncGenerator, Dict, Any, List, Union, Tuple, TypedDict
from contextlib import AsyncExitStack
from openai import OpenAI
from dotenv import load_dotenv

# Set up logger
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
logger = logging.getLogger('text2sql.mcp_client')
load_dotenv(os.path.join(project_root, '.env'))

# Configurable timeouts
CONNECTION_TIMEOUT = float(os.getenv("MCP_CONNECTION_TIMEOUT", 10.0))
SESSION_TIMEOUT = float(os.getenv("MCP_SESSION_TIMEOUT", 5.0))
TOOL_CALL_TIMEOUT = float(os.getenv("MCP_TOOL_CALL_TIMEOUT", 15.0))
LOCK_TIMEOUT = float(os.getenv("MCP_LOCK_TIMEOUT", 10.0))

# Check if we need to modify any paths for MCP
if os.environ.get('MCP_LIBRARY_PATH'):
    sys.path.insert(0, os.environ.get('MCP_LIBRARY_PATH'))

# Import MCP components
try:
    from mcp import ClientSession
    from mcp.client.stdio import stdio_client, StdioServerParameters
    from mcp.client.sse import sse_client
except ImportError as e:
    logger.error(f"Failed to import MCP: {e}")
    raise ImportError("MCP library is not available. Please install the required dependencies.")

# API settings
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "google/gemini-2.0-flash-exp:free")

# Global registry of active MCP clients
_mcp_clients: Dict[str, 'MCPClient'] = {}
_mcp_client_lock = asyncio.Lock()

# Type definitions for server config
class StdioServerConfig(TypedDict):
    command: str
    args: Optional[List[str]]
    env: Optional[Dict[str, str]]

class HttpServerConfig(TypedDict):
    base_url: str
    headers: Optional[Dict[str, str]]

ServerConfig = Union[StdioServerConfig, HttpServerConfig]

def get_or_create_event_loop() -> asyncio.AbstractEventLoop:
    """Get or create a new event loop, ensuring it is not closed."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_closed():
            logger.warning("Event loop is closed. Creating new event loop.")
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        return loop
    except RuntimeError:
        logger.warning("No event loop found. Creating new event loop.")
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop

class MCPClient:
    """Client for interacting with an MCP server (stdio or HTTP)."""
    
    def __init__(self, server_id: Optional[str] = None, server_name: Optional[str] = None, 
                 server_type: Optional[str] = None):
        """Initialize an MCP client.
        
        Args:
            server_id: Optional ID of the server (for multi-server management).
            server_name: Optional name of the server.
            server_type: Either 'stdio' or 'http'.
        """
        self.server_id = server_id
        self.server_name = server_name or f"server_{server_id}" if server_id else "unnamed_server"
        self.server_type = server_type
        self.server_config: Optional[ServerConfig] = None
        self.session: Optional[ClientSession] = None
        self.exit_stack: Optional[AsyncExitStack] = AsyncExitStack()
        self.model = OPENROUTER_MODEL
        self.client: Optional[OpenAI] = None
        self._is_connected = False
        self._connection_lock = asyncio.Lock()
        self._available_tools_cache: Optional[List[Dict[str, Any]]] = None
        self._streams_context = None
        self._session_context = None
        
        if not OPENROUTER_MODEL:
            logger.error(f"No valid OPENROUTER_MODEL specified for server {self.server_name}")
            return

        if OPENROUTER_API_KEY:
            self.client = OpenAI(
                base_url=OPENROUTER_BASE_URL,
                api_key=OPENROUTER_API_KEY,
            )
        else:
            logger.warning(f"OPENROUTER_API_KEY not found for server {self.server_name}. OpenAI client not initialized.")

    async def connect_to_stdio_server(self, command: str, args: Optional[Union[str, List[str]]] = None, 
                                    env: Optional[Dict[str, str]] = None) -> bool:
        """Connect to an MCP server via stdio.
        
        Args:
            command: The command to execute (e.g., python path).
            args: List of arguments or a single string argument.
            env: Optional environment variables dict.
        
        Returns:
            True if connection is successful, False otherwise.
        """
        async with asyncio.timeout(LOCK_TIMEOUT):
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
                
                # Store configuration
                self.server_config = {
                    'command': command,
                    'args': args,
                    'env': env
                }

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

                    # Create server parameters
                    server_params = StdioServerParameters(
                        command=command,
                        args=full_args,
                        env=full_env
                    )

                    # Set up the connection
                    stdio_transport = await asyncio.wait_for(
                        self.exit_stack.enter_async_context(stdio_client(server_params)),
                        timeout=CONNECTION_TIMEOUT
                    )
                    logger.info("Stdio transport created successfully")
                    
                    self.stdio, self.stdout = stdio_transport
                    self.session = await asyncio.wait_for(
                        self.exit_stack.enter_async_context(ClientSession(self.stdio, self.stdout)),
                        timeout=SESSION_TIMEOUT
                    )
                    logger.info("ClientSession created successfully")

                    # Initialize the session
                    await asyncio.wait_for(
                        self.session.initialize(),
                        timeout=SESSION_TIMEOUT
                    )
                    logger.info("MCP session initialized successfully")

                    # Get and cache tools
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

                except asyncio.TimeoutError as to_err:
                    logger.error(f"Timeout establishing stdio connection: {to_err}")
                    await self.cleanup()
                    return False
                except ConnectionError as conn_err:
                    logger.error(f"Connection error establishing stdio connection: {conn_err}")
                    await self.cleanup()
                    return False
                except Exception as e:
                    logger.exception(f"Failed to connect to stdio MCP server {self.server_name}: {str(e)}\n{traceback.format_exc()}")
                    await self.cleanup()
                    return False

    async def connect_to_http_server(self, base_url: str, headers: Optional[Dict[str, str]] = None) -> bool:
        """Connect to an MCP server via HTTP/SSE.
        
        Args:
            base_url: The base URL of the HTTP MCP server.
            headers: Optional headers to include in requests.
        
        Returns:
            True if connection is successful, False otherwise.
        """
        async with asyncio.timeout(LOCK_TIMEOUT):
            async with self._connection_lock:
                if self._is_connected:
                    logger.info(f"Already connected to HTTP MCP server {self.server_name}.")
                    return True

                if not self.client:
                    logger.error(f"OpenAI client not initialized for server {self.server_name}")
                    return False

                logger.info(f"Connecting to HTTP MCP server: {self.server_name} at {base_url}")
                
                # Store configuration
                self.server_config = {
                    'base_url': base_url,
                    'headers': headers
                }

                try:
                    # Ensure a valid event loop
                    get_or_create_event_loop()

                    # Create SSE client
                    self._streams_context = sse_client(base_url, headers=headers)
                    streams = await asyncio.wait_for(
                        self.exit_stack.enter_async_context(self._streams_context),
                        timeout=CONNECTION_TIMEOUT
                    )

                    # Create session
                    if isinstance(streams, tuple) and len(streams) >= 2:
                        logger.info("Got tuple of streams from SSE client")
                        read_stream, write_stream = streams
                        self._session_context = ClientSession(read_stream, write_stream)
                    else:
                        logger.info("Got single stream from SSE client")
                        self._session_context = ClientSession(streams)

                    self.session = await asyncio.wait_for(
                        self.exit_stack.enter_async_context(self._session_context),
                        timeout=SESSION_TIMEOUT
                    )

                    # Initialize the session
                    await asyncio.wait_for(
                        self.session.initialize(),
                        timeout=SESSION_TIMEOUT
                    )

                    # Get and cache tools
                    response = await asyncio.wait_for(
                        self.session.list_tools(),
                        timeout=CONNECTION_TIMEOUT
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
                except ConnectionError as ce:
                    logger.error(f"Connection error connecting to HTTP MCP server {self.server_name}: {ce}")
                    await self.cleanup()
                    return False
                except Exception as e:
                    logger.exception(f"Failed to connect to HTTP MCP server {self.server_name}: {str(e)}\n{traceback.format_exc()}")
                    await self.cleanup()
                    return False

    def is_connected(self) -> bool:
        """Check if the client is connected to an MCP server."""
        return self._is_connected and self.session is not None

    async def get_available_tools(self) -> Optional[List[Dict[str, Any]]]:
        """Get the list of available tools from the MCP server."""
        if not self.is_connected():
            logger.warning(f"Cannot get tools: not connected to MCP server {self.server_name}.")
            return None

        if self._available_tools_cache:
            return self._available_tools_cache

        try:
            response = await asyncio.wait_for(self.session.list_tools(), timeout=CONNECTION_TIMEOUT)
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
            logger.exception(f"Failed to retrieve tools from MCP server {self.server_name}: {str(e)}\n{traceback.format_exc()}")
            return None

    async def process_query_stream(self, query: Union[str, Dict[str, Any]]) -> AsyncGenerator[Dict[str, Any], None]:
        """Process a query using OpenAI and MCP server tools, streaming progress.
        
        Args:
            query: The user's query (string or dict with query and conversation_history).
        
        Yields:
            Streaming updates as dictionaries.
        """
        if not self.is_connected():
            yield {"type": "error", "message": f"Not connected to MCP server {self.server_name}."}
            return

        if not self.client:
            yield {"type": "error", "message": "OpenAI client not configured."}
            return

        # Initialize messages
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

        # Handle query type
        if isinstance(query, dict) and 'query' in query:
            logger.info(f"Processing query on server {self.server_name} with conversation history: {query['query']}")
            conversation_history = query.get('conversation_history', [])
            current_query = query.get('query', '')
            messages.extend(conversation_history)
            messages.append({"role": "user", "content": current_query})
            query_text = current_query
        else:
            logger.info(f"Processing query on server {self.server_name}: {query}")
            messages.append({"role": "user", "content": query})
            query_text = query

        yield {"type": "status", "message": f"Starting query processing on {self.server_name}..."}

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

            if message.content:
                yield {"type": "llm_response", "content": message.content}
                messages.append({"role": "assistant", "content": message.content})

            # Tool calling loop
            tool_loop_counter = 0
            max_tool_loops = 5
            max_retries = 3

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

                tool_results_for_next_call = []
                for tool_call in message.tool_calls:
                    tool_name = tool_call.function.name
                    tool_args_str = tool_call.function.arguments
                    tool_call_id = tool_call.id

                    try:
                        tool_args = json.loads(tool_args_str)
                        logger.info(f"Calling tool '{tool_name}' with args: {tool_args}")

                        # Retry logic for tool calls
                        retry_count = 0
                        while retry_count < max_retries:
                            try:
                                get_or_create_event_loop()
                                result = await asyncio.wait_for(
                                    self.session.call_tool(tool_name, tool_args),
                                    timeout=TOOL_CALL_TIMEOUT
                                )
                                break
                            except asyncio.TimeoutError as te:
                                logger.error(f"Timeout calling tool '{tool_name}': {te}")
                                retry_count += 1
                                if retry_count >= max_retries:
                                    raise Exception(f"Tool {tool_name} timed out after {max_retries} retries")
                                await self.cleanup()
                                success = await self._reconnect()
                                if not success:
                                    raise Exception(f"Failed to reconnect for tool {tool_name} after timeout")
                            except RuntimeError as re:
                                logger.error(f"Runtime error calling tool '{tool_name}': {re}")
                                retry_count += 1
                                if retry_count >= max_retries:
                                    raise Exception(f"Tool {tool_name} failed after {max_retries} retries: {str(re)}")
                                await self.cleanup()
                                get_or_create_event_loop()
                                success = await self._reconnect()
                                if not success:
                                    raise Exception(f"Failed to reconnect for tool {tool_name} after runtime error")

                        # Process result
                        result_content = str(result.content)
                        if hasattr(result.content, '__getitem__'):
                            try:
                                result_content = str(result.content[0].text)
                            except (IndexError, AttributeError):
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
                        logger.exception(f"Error executing tool {tool_name} on {self.server_name}: {str(tool_exc)}\n{traceback.format_exc()}")
                        yield {"type": "error", "message": f"Error calling tool {tool_name}: {str(tool_exc)}"}
                        tool_results_for_next_call.append({
                            "role": "tool",
                            "tool_call_id": tool_call_id,
                            "name": tool_name,
                            "content": json.dumps({"error": f"Tool execution failed: {str(tool_exc)}"})
                        })

                messages.extend(tool_results_for_next_call)

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

                if message.content:
                    yield {"type": "llm_response", "content": message.content}
                    messages.append({"role": "assistant", "content": message.content})

            # Final message check
            last_msg = messages[-1] if messages else {}
            if message.content and not (last_msg.get("role") == "assistant" and last_msg.get("content") == message.content):
                yield {"type": "llm_response", "content": message.content, "is_final": True}
                messages.append({"role": "assistant", "content": message.content})

            yield {"type": "status", "message": "Processing complete."}

        except Exception as e:
            logger.exception(f"Error processing query on server {self.server_name}: {str(e)}\n{traceback.format_exc()}")
            yield {"type": "error", "message": f"An error occurred: {str(e)}"}

    async def _reconnect(self) -> bool:
        """Reconnect to the server using stored configuration.
        
        Returns:
            True if reconnection is successful, False otherwise.
        """
        if not self.server_config:
            logger.error(f"No server configuration available for reconnection on {self.server_name}")
            return False

        if self.server_type == "stdio":
            return await self.connect_to_stdio_server(
                self.server_config.get("command"),
                self.server_config.get("args"),
                self.server_config.get("env")
            )
        elif self.server_type == "http":
            return await self.connect_to_http_server(
                self.server_config.get("base_url"),
                self.server_config.get("headers")
            )
        return False

    async def cleanup(self):
        """Clean up resources (close session, exit stack, and OpenAI client)."""
        async with asyncio.timeout(LOCK_TIMEOUT):
            async with self._connection_lock:
                if not self.exit_stack and not self.session and not self._is_connected:
                    logger.debug(f"Cleanup for {self.server_name} skipped - already cleaned up")
                    return

                logger.info(f"Cleaning up MCP client resources for server {self.server_name}...")
                
                # Ensure a valid event loop
                get_or_create_event_loop()

                # Clean up session
                if self._session_context:
                    try:
                        await asyncio.wait_for(
                            self._session_context.__aexit__(None, None, None),
                            timeout=SESSION_TIMEOUT
                        )
                    except Exception as e:
                        logger.warning(f"Error closing session context for {self.server_name}: {e}")
                    finally:
                        self._session_context = None

                # Clean up streams
                if self._streams_context:
                    try:
                        await asyncio.wait_for(
                            self._streams_context.__aexit__(None, None, None),
                            timeout=SESSION_TIMEOUT
                        )
                    except Exception as e:
                        logger.warning(f"Error closing streams context for {self.server_name}: {e}")
                    finally:
                        self._streams_context = None

                # Clean up exit stack
                if self.exit_stack:
                    try:
                        await asyncio.wait_for(
                            self.exit_stack.aclose(),
                            timeout=SESSION_TIMEOUT
                        )
                    except asyncio.TimeoutError:
                        logger.warning(f"Timeout during exit stack cleanup for {self.server_name}")
                    except Exception as e:
                        logger.warning(f"Ignored error during exit stack cleanup for {self.server_name}: {e}")

                # Close OpenAI client
                if self.client:
                    try:
                        self.client.close()
                    except Exception as e:
                        logger.warning(f"Error closing OpenAI client for {self.server_name}: {e}")
                    self.client = None

                # Reset state
                self.exit_stack = None
                self.session = None
                self._is_connected = False
                self._available_tools_cache = None
                self.server_config = None
                logger.info(f"MCP client resources cleaned up for server {self.server_name}.")

class MCPClientManager:
    """Manager class for handling multiple MCP clients."""
    
    @staticmethod
    async def get_client(server_id: str, connect: bool = True) -> Optional['MCPClient']:
        """Get a client for a specific server ID.
        
        Args:
            server_id: The ID of the MCP server to get a client for.
            connect: Whether to connect the client if it's not connected.
        
        Returns:
            An MCPClient instance or None if not found/failed.
        """
        async with asyncio.timeout(LOCK_TIMEOUT):
            async with _mcp_client_lock:
                from src.models.mcp_server import MCPServer

                client = _mcp_clients.get(server_id)
                if client and client.is_connected():
                    return client

                server = MCPServer.get_by_id(server_id)
                if not server:
                    logger.error(f"Server with ID {server_id} not found")
                    return None

                client = MCPClient(server_id=server.id, server_name=server.name, server_type=server.server_type)
                client.server_config = server.config

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
                        logger.exception(f"Failed to connect to MCP server {server.name}: {str(e)}\n{traceback.format_exc()}")
                        server.update_status('error')
                        return None

                    server.update_status('running')

                return client
    
    @staticmethod
    async def start_server(server_id: str) -> Tuple[bool, str]:
        """Start a specific MCP server.
        
        Args:
            server_id: The ID of the MCP server to start.
        
        Returns:
            A tuple (success, message).
        """
        async with asyncio.timeout(LOCK_TIMEOUT):
            async with _mcp_client_lock:
                from src.models.mcp_server import MCPServer, MCPServerStatus

                server = MCPServer.get_by_id(server_id)
                if not server:
                    return False, f"Server with ID {server_id} not found"

                if server.status == MCPServerStatus.RUNNING.value:
                    return True, f"Server {server.name} is already running"

                client = await MCPClientManager.get_client(server_id, connect=False)
                if not client:
                    return False, f"Failed to create client for server {server.name}"

                try:
                    success = False
                    if server.server_type == 'stdio':
                        command = server.config.get('command')
                        if not command:
                            return False, "No command specified for stdio server"
                        args = server.config.get('args')
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
                    logger.exception(f"Failed to start MCP server {server.name}: {str(e)}\n{traceback.format_exc()}")
                    server.update_status(MCPServerStatus.ERROR.value)
                    return False, f"Failed to start server: {str(e)}"
    
    @staticmethod
    async def stop_server(server_id: str) -> Tuple[bool, str]:
        """Stop a specific MCP server.
        
        Args:
            server_id: The ID of the MCP server to stop.
        
        Returns:
            A tuple (success, message).
        """
        async with asyncio.timeout(LOCK_TIMEOUT):
            async with _mcp_client_lock:
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
                        logger.exception(f"Error stopping MCP server {server.name}: {str(e)}\n{traceback.format_exc()}")
                        return False, f"Error stopping server: {str(e)}"

                server.update_status(MCPServerStatus.STOPPED.value)
                return True, f"Server {server.name} stopped successfully"
    
    @staticmethod
    async def restart_server(server_id: str) -> Tuple[bool, str]:
        """Restart a specific MCP server.
        
        Args:
            server_id: The ID of the MCP server to restart.
        
        Returns:
            A tuple (success, message).
        """
        async with asyncio.timeout(LOCK_TIMEOUT):
            async with _mcp_client_lock:
                from src.models.mcp_server import MCPServer

                server = MCPServer.get_by_id(server_id)
                if not server:
                    return False, f"Server with ID {server_id} not found"

                server_type = server.server_type
                stop_success, stop_message = await MCPClientManager.stop_server(server_id)
                if not stop_success:
                    return stop_success, stop_message

                delay = 1.0 if server_type == 'http' else 0.5
                logger.info(f"Delaying {delay}s for {server_type} server restart: {server.name}")
                await asyncio.sleep(delay)
                
                if server_type == 'http':
                    get_or_create_event_loop()

                return await MCPClientManager.start_server(server_id)
    
    @staticmethod
    async def start_all_running_servers() -> List[Dict[str, Any]]:
        """Start all servers that are marked as running in the database.
        
        Returns:
            List of results for each server.
        """
        async with asyncio.timeout(LOCK_TIMEOUT):
            async with _mcp_client_lock:
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
        async with asyncio.timeout(LOCK_TIMEOUT):
            async with _mcp_client_lock:
                cleanup_tasks = []
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
            query: The user's query string.
        
        Returns:
            The ID of the selected server, or None if no suitable server was found.
        """
        async with asyncio.timeout(LOCK_TIMEOUT):
            async with _mcp_client_lock:
                from src.models.mcp_server import MCPServer, MCPServerStatus

                servers = MCPServer.get_all()
                running_servers = [s for s in servers if s.status == MCPServerStatus.RUNNING.value]

                if not running_servers:
                    logger.warning("No running MCP servers available")
                    return None

                if len(running_servers) == 1:
                    return running_servers[0].id

                try:
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

                    if OPENROUTER_API_KEY:
                        client = OpenAI(
                            base_url=OPENROUTER_BASE_URL,
                            api_key=OPENROUTER_API_KEY,
                        )
                        try:
                            response = client.chat.completions.create(
                                model=OPENROUTER_MODEL,
                                messages=[
                                    {
                                        "role": "system",
                                        "content": "You are a server selection assistant. Respond ONLY with the ID of the best server for the user's query."
                                    },
                                    {
                                        "role": "user",
                                        "content": f"Select the most appropriate MCP server for this query: \n\nQuery: {query}\n\nAvailable servers:\n{json.dumps(server_descriptions, indent=2)}\n\nRespond ONLY with the server ID number"
                                    }
                                ]
                            )

                            server_id_str = response.choices[0].message.content.strip()
                            try:
                                server_id = int(server_id_str)
                                if any(s['id'] == server_id for s in server_descriptions):
                                    return server_id
                            except ValueError:
                                pass
                        finally:
                            client.close()

                    logger.warning("Could not select best server via LLM, using first available")
                    return running_servers[0].id

                except Exception as e:
                    logger.exception(f"Error selecting MCP server for query: {str(e)}\n{traceback.format_exc()}")
                    return running_servers[0].id if running_servers else None

async def get_mcp_client_for_query(query: str) -> Optional[MCPClient]:
    """Get the appropriate MCP client for a given query.
    
    Args:
        query: The user's query.
    
    Returns:
        An MCPClient instance, or None if no suitable client was found.
    """
    try:
        server_id = await MCPClientManager.select_server_for_query(query)
        if not server_id:
            logger.error("No suitable MCP server found for the query")
            return None

        client = await MCPClientManager.get_client(server_id, connect=True)
        return client
    except Exception as e:
        logger.exception(f"Error getting MCP client for query: {str(e)}\n{traceback.format_exc()}")
        return None