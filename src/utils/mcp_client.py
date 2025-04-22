import asyncio
import json
import os
import sys
from typing import Optional, AsyncGenerator, Dict, Any
from contextlib import AsyncExitStack
from openai import OpenAI
from dotenv import load_dotenv
import logging

# Determine the correct path for mcp library based on environment
# This might need adjustment depending on your project structure and venv
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
# Add potential locations for the mcp library if it's not installed globally
sys.path.insert(0, os.path.join(project_root, '..', 'mcp_learn')) # Adjust if needed

try:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
except ImportError:
    print("Error: MCP library not found. Ensure it's installed or path is correct.")
    # You might want to raise an exception or handle this more gracefully
    # For now, define dummy classes to avoid import errors later if MCP is missing
    class ClientSession: pass
    class StdioServerParameters: pass
    def stdio_client(*args, **kwargs): pass


logger = logging.getLogger('text2sql.mcp_client')
load_dotenv(os.path.join(project_root, '.env')) # Load .env from project root

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "google/gemini-2.0-flash-exp:free") # Using a capable model

# --- Singleton Pattern for MCPClient ---
_mcp_client_instance = None
_mcp_client_lock = asyncio.Lock()

class MCPClient:
    def __init__(self):
        self.server_script_path: Optional[str] = None  # remember path for reconnect
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        self.model = OPENROUTER_MODEL
        self.client = None
        self._is_connected = False
        self._connection_lock = asyncio.Lock()
        self._available_tools_cache = None # Cache for available tools

        if OPENROUTER_API_KEY:
            self.client = OpenAI(
                base_url=OPENROUTER_BASE_URL,
                api_key=OPENROUTER_API_KEY,
            )
        else:
            logger.warning("OPENROUTER_API_KEY not found. OpenAI client not initialized.")


    async def connect_to_server(self, server_script_path: str):
        """Connect to an MCP server if not already connected."""
        async with self._connection_lock:
            if self._is_connected:
                logger.info("Already connected to MCP server.")
                return

            if not self.client:
                 raise ConnectionError("OpenAI client not initialized. Check API key.")
            if not os.path.exists(server_script_path):
                 raise FileNotFoundError(f"MCP server script not found at: {server_script_path}")

            logger.info(f"Attempting to connect to MCP server: {server_script_path}")
            try:
                is_python = server_script_path.endswith('.py')
                is_js = server_script_path.endswith('.js')
                if not (is_python or is_js):
                    raise ValueError("Server script must be a .py or .js file")

                # Determine python executable path more reliably
                python_executable = sys.executable # Use the current python interpreter
                logger.info(f"Using Python executable: {python_executable}")

                command = python_executable if is_python else "node"
                server_params = StdioServerParameters(
                    command=command,
                    args=[server_script_path],
                    env=os.environ.copy() # Pass current environment
                )

                # Ensure the exit stack is managed correctly
                if self.exit_stack is None:
                    self.exit_stack = AsyncExitStack()

                stdio_transport = await self.exit_stack.enter_async_context(stdio_client(server_params))
                self.stdio, self.write = stdio_transport
                self.session = await self.exit_stack.enter_async_context(ClientSession(self.stdio, self.write))

                await self.session.initialize()

                # List and cache available tools
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
                self.server_script_path = server_script_path
                logger.info("Successfully connected to MCP server with tools: %s", [tool['function']['name'] for tool in self._available_tools_cache])

            except Exception as e:
                logger.exception(f"Failed to connect to MCP server at {server_script_path}")
                await self.cleanup() # Attempt cleanup on connection failure
                raise ConnectionError(f"Failed to connect to MCP server: {e}") from e

    def is_connected(self) -> bool:
        """Check if the client is connected to the server."""
        return self._is_connected and self.session is not None

    async def get_available_tools(self) -> Optional[list]:
         """Get the list of available tools, using cache if possible."""
         if not self.is_connected():
              logger.warning("Cannot get tools, not connected to MCP server.")
              return None
         if self._available_tools_cache:
              return self._available_tools_cache
         # Fetch if cache is empty (should have been populated on connect)
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
              logger.exception("Failed to retrieve tools from MCP server.")
              return None


    async def process_query_stream(self, query: str) -> AsyncGenerator[Dict[str, Any], None]:
        """Process a query using OpenAI and available tools, streaming progress."""
        if not self.is_connected():
            yield {"type": "error", "message": "Not connected to MCP server."}
            return
        if not self.client:
             yield {"type": "error", "message": "OpenAI client not configured."}
             return

        logger.info(f"Processing query stream: {query}")
        yield {"type": "status", "message": "Starting query processing..."}

        messages = [
            {
                "role": "system",
                "content": """
1. You are an AI assistant interacting with a set of tools via the Model Context Protocol (MCP).
2. Plan your steps before executing actions.
3. Explain your plan and each step you take.
4. When calling a tool, clearly state the tool name and arguments.
5. After receiving a tool result, summarize it briefly.
6. Generate SQL queries in SQLite format. Avoid CTEs; use subqueries if necessary.
7. Only retry a failed step if it makes sense (e.g., temporary network issue). Ask for clarification if unsure.
8. Provide the final answer clearly at the end.
"""
            },
            {
                "role": "user",
                "content": query
            }
        ]

        available_tools = await self.get_available_tools()
        if not available_tools:
             yield {"type": "error", "message": "Could not retrieve available tools from MCP server."}
             return

        try:
            yield {"type": "status", "message": "Generating initial plan..."}
            # Initial OpenAI API call
            response = self.client.chat.completions.create(
                model=self.model,
                max_tokens=1500, # Increased max tokens
                messages=messages,
                tools=available_tools,
                tool_choice="auto" # Let the model decide when to use tools
            )

            message = response.choices[0].message
            logger.info(f"Initial LLM response: {message}")

            # Stream initial text response from the assistant, if any
            if message.content:
                yield {"type": "llm_response", "content": message.content}
                messages.append({"role": "assistant", "content": message.content}) # Add assistant text response

            # --- Tool Calling Loop ---
            # Initialize tool loop counter to limit maximum iterations
            tool_loop_counter = 0
            max_tool_loops = 5  # Maximum number of tool calling loops allowed
            
            while hasattr(message, 'tool_calls') and message.tool_calls and tool_loop_counter < max_tool_loops:
                tool_loop_counter += 1
                logger.info(f"Tool calls detected: {len(message.tool_calls)} (Loop {tool_loop_counter}/{max_tool_loops})")
                # Append the assistant's message with tool calls (even if content was null)
                # Important: The API expects the *entire* message object including tool_calls
                assistant_message_with_calls = {
                    "role": "assistant",
                    "content": message.content, # Can be None
                    "tool_calls": [
                        {"id": tc.id, "type": tc.type, "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
                        for tc in message.tool_calls
                    ]
                }
                # Filter out None content if necessary for cleaner history, but keep tool_calls
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
                        yield {"type": "tool_call", "tool_name": tool_name, "arguments": tool_args}

                        # Execute tool call via MCP session, retry once on failure
                        try:
                            result = await self.session.call_tool(tool_name, tool_args)
                        except Exception as call_exc:
                            logger.warning(f"Error calling tool '{tool_name}': {call_exc}. Attempting to reconnect and retry.")
                            # Attempt to reconnect and retry once
                            if self.server_script_path:
                                await self.connect_to_server(self.server_script_path)
                                result = await self.session.call_tool(tool_name, tool_args)
                            else:
                                raise
                        logger.info(f"Tool '{tool_name}' result: {result}")
                        result_content_str = str(result.content) # Ensure result is JSON string

                        logger.info(f"Tool '{tool_name}' result received.")
                        # Send structured tool result as serializable string
                        #yield {"type": "tool_result", "tool_name": tool_name, "result": result_content_str}

                        # Append result for the next OpenAI call
                        # tool_results_for_next_call.append({
                        #     "role": "tool",
                        #     "tool_call_id": tool_call_id,
                        #     "name": tool_name,
                        #     "content": result_content_str # API expects string content
                        # })
                        tool_results_for_next_call.append({
                            "role": "assistant",
                            "content": "Result from calling the tool "+tool_name+"\n"+str(result.content[0].text) # API expects string content
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
                        logger.exception(f"Error executing tool {tool_name}")
                        yield {"type": "error", "message": f"Error calling tool {tool_name}: {str(tool_exc)}"}
                        # Provide error feedback to the model
                        tool_results_for_next_call.append({
                            "role": "tool",
                            "tool_call_id": tool_call_id,
                            "name": tool_name,
                            "content": json.dumps({"error": f"Tool execution failed: {str(tool_exc)}"})
                        })

                # Append all tool results before the next LLM call
                messages.extend(tool_results_for_next_call)
                logger.info(f"Tool results appended to messages: {messages}")

                yield {"type": "status", "message": "Sending tool results back to LLM..."}
                # Continue conversation with tool results
                response = self.client.chat.completions.create(
                    model=self.model,
                    max_tokens=1500,
                    messages=messages,
                    tools=available_tools,
                    tool_choice="auto"
                )
                logger.info(f"LLM response after tool calls: {response}")
                message = response.choices[0].message
                logger.info(f"LLM response after tool calls: {message}")

                # Stream subsequent text response from the assistant, if any
                if message.content:
                    yield {"type": "llm_response", "content": message.content}
                    # Add assistant text response to messages *before* checking for more tool calls
                    # This ensures the text context is available for the next potential tool decision
                    messages.append({"role": "assistant", "content": message.content})


            # --- End of Tool Calling Loop ---

            # Final message content after loop finishes (if any)
            # This handles the case where the last LLM response didn't have tool calls
            # Note: We might have already yielded this content above if it existed before the loop check
            # Check if the last message added was already this assistant message to avoid duplicates
            last_msg = messages[-1] if messages else {}
            if message.content and not (last_msg.get("role") == "assistant" and last_msg.get("content") == message.content):
                 yield {"type": "llm_response", "content": message.content}


            yield {"type": "status", "message": "Processing complete."}

        except Exception as e:
            logger.exception("Error processing query stream")
            yield {"type": "error", "message": f"An unexpected error occurred: {str(e)}"}
        finally:
             # Optional: Consider if you want to disconnect after each query
             # await self.cleanup() # Uncomment if you want to disconnect
             pass


    async def cleanup(self):
        """Clean up resources (close session and exit stack)."""
        async with self._connection_lock:
            if self.exit_stack:
                logger.info("Cleaning up MCP client resources...")
                try:
                    await self.exit_stack.aclose()
                except BaseExceptionGroup as beg:
                    logger.warning(f"Ignored BaseExceptionGroup during MCP client cleanup: {beg}")
                except Exception as cleanup_exc:
                    logger.warning(f"Ignored error during MCP client cleanup: {cleanup_exc}")
                self.exit_stack = None # Reset stack
                self.session = None
                self._is_connected = False
                self._available_tools_cache = None
                logger.info("MCP client resources cleaned up.")


async def get_mcp_client() -> MCPClient:
    """Provides a singleton instance of the MCPClient."""
    global _mcp_client_instance
    async with _mcp_client_lock:
        if _mcp_client_instance is None:
            logger.info("Creating new MCPClient instance.")
            _mcp_client_instance = MCPClient()
        return _mcp_client_instance

async def shutdown_mcp_client():
     """Explicitly shuts down the singleton MCP client."""
     global _mcp_client_instance
     async with _mcp_client_lock:
          if _mcp_client_instance:
               logger.info("Shutting down singleton MCPClient instance.")
               await _mcp_client_instance.cleanup()
               _mcp_client_instance = None


# Example usage (for testing purposes)
async def main_test():
    if len(sys.argv) < 2:
        print("Usage: python mcp_client.py <path_to_server_script>")
        sys.exit(1)

    server_path = sys.argv[1]
    client = await get_mcp_client()

    try:
        await client.connect_to_server(server_path)

        print("\nMCP Client Started for testing!")
        print("Type your queries or 'quit' to exit.")

        while True:
            try:
                query = input("\nQuery: ").strip()
                if query.lower() == 'quit':
                    break

                print("--- Response Stream ---")
                async for update in client.process_query_stream(query):
                    print(f"Update: {update}")
                print("--- End of Stream ---")

            except Exception as e:
                logger.exception("Unexpected error in test chat loop")
                print(f"\nError: {str(e)}")

    finally:
        await shutdown_mcp_client()

if __name__ == "__main__":
    # This allows running the client standalone for testing
    # Example: python src/utils/mcp_client.py ../../mcp_learn/dataengineer/dataengineer.py
    # Ensure the path to dataengineer.py is correct relative to mcp_client.py
    # And that the mcp library is accessible
    asyncio.run(main_test())

