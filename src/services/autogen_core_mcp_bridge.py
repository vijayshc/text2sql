"""
AutoGen Core MCP Tool Bridge

Provides a bridge to use MCP tools with AutoGen Core runtime by implementing
Core-compatible tool interfaces that delegate to MCP workbenches.
"""

import logging
import asyncio
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from src.models.mcp_server import MCPServer, MCPServerType, MCPServerStatus
from src.services.run_monitor import RunMonitor

logger = logging.getLogger('text2sql.autogen_core_bridge')

if TYPE_CHECKING:
    from autogen_ext.tools.mcp import McpWorkbench


class CoreMCPToolBridge:
    """Bridges MCP tools to AutoGen Core runtime by exposing them as Core-compatible tools."""
    
    def __init__(self, monitor: Optional[RunMonitor] = None):
        self.monitor = monitor
        self._workbenches: Dict[str, Any] = {}  # server_id -> McpWorkbench
        self._tools_cache: Dict[str, Any] = {}  # tool_name -> tool_definition
        self._tool_to_server: Dict[str, str] = {}  # tool_name -> server_id
        
    async def initialize_for_agent_spec(self, agent_spec: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Initialize MCP workbenches for an agent spec and return Core-compatible tool definitions.
        
        Args:
            agent_spec: Agent configuration containing 'tools' list with server_id and tool_name
            
        Returns:
            List of Core-compatible tool definitions
        """
        tool_specs = agent_spec.get('tools') or []
        
        # Group tools by server
        by_server: Dict[int, List[str]] = {}
        for t in tool_specs:
            sid = t.get('server_id')
            name = t.get('tool_name')
            if not sid or not name:
                continue
            by_server.setdefault(int(sid), []).append(name)
        
        # Initialize workbenches for each server
        for sid, tools in by_server.items():
            server = MCPServer.get_by_id(sid)
            if not server or server.status != MCPServerStatus.RUNNING.value:
                logger.warning(f"Server {sid} not found or not running")
                continue
                
            try:
                wb = await self._create_workbench(server)
                server_key = str(sid)
                self._workbenches[server_key] = wb
                await wb.start()
                
                # Cache tool definitions
                available_tools = await wb.list_tools()
                for tool_def in available_tools:
                    tool_name = tool_def.get('name')
                    if tool_name in tools:  # Only include tools selected for this agent
                        self._tools_cache[tool_name] = tool_def
                        self._tool_to_server[tool_name] = server_key
                        
            except Exception as e:
                logger.warning(f"Failed to initialize workbench for server {server.name}: {e}")
        
        # Return Core-compatible tool definitions
        core_tools = []
        for tool_name, tool_def in self._tools_cache.items():
            core_tool = self._convert_to_core_tool(tool_def)
            core_tools.append(core_tool)
            
        if self.monitor:
            try:
                self.monitor.log_event('mcp_bridge_init', 'core', {
                    "servers_initialized": len(self._workbenches),
                    "tools_available": len(core_tools),
                    "tool_names": list(self._tools_cache.keys())
                })
            except Exception:
                pass
                
        return core_tools
    
    async def execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """Execute an MCP tool via the bridge.
        
        Args:
            tool_name: Name of the tool to execute
            arguments: Tool arguments
            
        Returns:
            Tool execution result
        """
        server_key = self._tool_to_server.get(tool_name)
        if not server_key:
            raise ValueError(f"Tool '{tool_name}' not found in bridge")
            
        workbench = self._workbenches.get(server_key)
        if not workbench:
            raise ValueError(f"Workbench for server '{server_key}' not available")
            
        if self.monitor:
            try:
                self.monitor.log_event('mcp_tool_call', 'core', {
                    "tool_name": tool_name,
                    "server_key": server_key,
                    "arguments": str(arguments)[:500]
                })
            except Exception:
                pass
                
        try:
            result = await workbench.call_tool(tool_name, arguments)
            
            if self.monitor:
                try:
                    result_preview = str(getattr(result, 'content', result))[:500]
                    self.monitor.log_event('mcp_tool_result', 'core', {
                        "tool_name": tool_name,
                        "server_key": server_key,
                        "result_preview": result_preview
                    })
                except Exception:
                    pass
                    
            return result
            
        except Exception as e:
            if self.monitor:
                try:
                    self.monitor.log_event('mcp_tool_error', 'core', {
                        "tool_name": tool_name,
                        "server_key": server_key,
                        "error": str(e)
                    })
                except Exception:
                    pass
            raise
    
    async def cleanup(self):
        """Clean up all workbenches."""
        for wb in self._workbenches.values():
            try:
                await wb.stop()
            except Exception as e:
                logger.warning(f"Error stopping workbench: {e}")
        self._workbenches.clear()
        self._tools_cache.clear()
        self._tool_to_server.clear()
    
    def _convert_to_core_tool(self, mcp_tool: Dict[str, Any]) -> Dict[str, Any]:
        """Convert an MCP tool definition to Core-compatible format.
        
        Args:
            mcp_tool: MCP tool definition
            
        Returns:
            Core-compatible tool definition
        """
        # Extract function definition from MCP tool
        function_def = mcp_tool.get('function', {})
        
        return {
            "type": "function",
            "function": {
                "name": mcp_tool.get('name'),
                "description": mcp_tool.get('description', ''),
                "parameters": function_def.get('parameters', {})
            }
        }
    
    async def _create_workbench(self, server: MCPServer):
        """Create an MCP workbench for a server.
        
        Args:
            server: MCP server configuration
            
        Returns:
            McpWorkbench instance
        """
        from autogen_ext.tools.mcp import McpWorkbench, StdioServerParams, StreamableHttpServerParams
        from autogen_ext.models.openai import OpenAIChatCompletionClient
        from autogen_core.models import ModelInfo
        import os
        
        # Build model client for workbench
        try:
            from config.config import OPENROUTER_API_KEY, OPENROUTER_BASE_URL, OPENROUTER_MODEL
        except Exception:
            OPENROUTER_API_KEY = os.getenv('OPENAI_API_KEY') or ''
            OPENROUTER_BASE_URL = os.getenv('OPENAI_BASE_URL') or ''
            OPENROUTER_MODEL = os.getenv('OPENROUTER_MODEL') or 'gpt-4o'
        
        model_info = ModelInfo(
            vision=False,
            function_calling=True,
            json_output=False,
            family='openrouter',
            structured_output=True
        )
        
        model_client = OpenAIChatCompletionClient(
            model=OPENROUTER_MODEL,
            api_key=OPENROUTER_API_KEY or None,
            base_url=OPENROUTER_BASE_URL or None,
            model_info=model_info,
            parallel_tool_calls=False
        )
        
        # Create server params based on server type
        cfg = server.config or {}
        if server.server_type == MCPServerType.STDIO.value:
            params = StdioServerParams(
                command=cfg.get('command') or cfg.get('cmd') or 'python',
                args=cfg.get('args') or [],
                env=cfg.get('env') or {},
                cwd=cfg.get('cwd')
            )
        else:
            url = cfg.get('url') or cfg.get('endpoint')
            if not url:
                raise ValueError(f"Missing URL for HTTP MCP server {server.name}")
            params = StreamableHttpServerParams(
                url=url,
                headers=cfg.get('headers') or {},
                timeout=float(cfg.get('timeout', 30.0)),
                sse_read_timeout=float(cfg.get('sse_read_timeout', 300.0)),
                terminate_on_close=bool(cfg.get('terminate_on_close', True))
            )
        
        return McpWorkbench(server_params=params, model_client=model_client)


class CoreMCPAgent:
    """AutoGen Core agent wrapper that can use MCP tools via the bridge."""
    
    def __init__(self, name: str, system_message: str, model_client, agent_spec: Dict[str, Any], 
                 monitor: Optional[RunMonitor] = None):
        self.name = name
        self.system_message = system_message
        self.model_client = model_client
        self.monitor = monitor
        self._bridge = CoreMCPToolBridge(monitor)
        self._tools = []
        self._agent_spec = agent_spec
        
    async def initialize(self):
        """Initialize the MCP bridge and tools."""
        self._tools = await self._bridge.initialize_for_agent_spec(self._agent_spec)
        
    async def run(self, task: str) -> Dict[str, Any]:
        """Run the agent with a task, using MCP tools when needed.
        
        This is a simplified implementation that demonstrates the bridge pattern.
        A full implementation would integrate with AutoGen Core's message passing.
        """
        try:
            # Import Core runtime components
            import importlib
            core_mod = importlib.import_module('autogen_core')
            SingleThreadedAgentRuntime = getattr(core_mod, 'SingleThreadedAgentRuntime')
            agents_mod = importlib.import_module('autogen_core.agents')
            RoutedAgent = getattr(agents_mod, 'RoutedAgent')
            messages_mod = importlib.import_module('autogen_core.messages')
            TextMessage = getattr(messages_mod, 'TextMessage')
            
            runtime = SingleThreadedAgentRuntime()
            
            # Create Core agent with tools
            agent = RoutedAgent(
                name=self.name,
                system_message=self.system_message,
                model_client=self.model_client,
                # Note: tools would be attached here in a full implementation
            )
            
            await runtime.add_agent(agent)
            
            # Publish task
            await runtime.publish_message(TextMessage(content=task, source='user'), topic_id='default')
            
            # Run with limited turns
            max_turns = 3
            if hasattr(runtime, 'run'):
                await runtime.run(max_turns)
            else:
                for _ in range(max_turns):
                    if hasattr(runtime, 'step'):
                        done = await runtime.step()
                        if done:
                            break
            
            # Extract result
            try:
                msgs = []
                if hasattr(runtime, 'get_messages'):
                    msgs = await runtime.get_messages()
                final = "Task completed."
                for m in reversed(msgs or []):
                    content = getattr(m, 'content', None)
                    source = getattr(m, 'source', None)
                    if isinstance(content, str) and content.strip() and source != 'user':
                        final = content.strip()
                        break
            except Exception:
                final = "Task completed."
                
            return {"success": True, "reply": final}
            
        except Exception as e:
            return {"success": False, "error": str(e)}
        finally:
            await self._bridge.cleanup()
    
    async def cleanup(self):
        """Clean up the agent and bridge."""
        await self._bridge.cleanup()
