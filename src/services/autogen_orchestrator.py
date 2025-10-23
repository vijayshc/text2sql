import logging
import os
import traceback
from typing import List, Dict, Any, Optional, TYPE_CHECKING
from dataclasses import dataclass

from src.models.agent_team import AgentTeam
from src.models.agent_workflow import AgentWorkflow
from src.models.mcp_server import MCPServer, MCPServerType
from src.utils.common_llm import get_llm_engine
from src.services.run_monitor import RunMonitor, _Timer

logger = logging.getLogger('text2sql.autogen')

# Try latest AutoGen AgentChat + MCP Workbench
NEW_AUTOGEN_IMPORT_ERROR = None
try:
    from autogen_agentchat.agents import AssistantAgent
    from autogen_agentchat.teams import RoundRobinGroupChat, SelectorGroupChat, Swarm
    from autogen_agentchat.conditions import TextMentionTermination, MaxMessageTermination
    from autogen_ext.models.openai import OpenAIChatCompletionClient
    from autogen_ext.tools.mcp import McpWorkbench, StdioServerParams, SseServerParams, StreamableHttpServerParams
    from autogen_core.models import ModelInfo
    # Import AutoGen logging components
    from autogen_core import EVENT_LOGGER_NAME, TRACE_LOGGER_NAME
    NEW_AUTOGEN_AVAILABLE = True
except Exception as e:
    NEW_AUTOGEN_IMPORT_ERROR = traceback.format_exc()
    logger.warning(f"New AutoGen packages not available: {e}\n{NEW_AUTOGEN_IMPORT_ERROR}")
    NEW_AUTOGEN_AVAILABLE = False

# Fallback (older API) if needed
try:
    import autogen
    from autogen import ConversableAgent
    from autogen.agentchat import GroupChat, GroupChatManager
    OLD_AUTOGEN_AVAILABLE = True
except Exception as e:
    logger.warning(f"Legacy AutoGen import failed: {e}")
    OLD_AUTOGEN_AVAILABLE = False


if TYPE_CHECKING:
    # Only for type hints; avoids import errors at runtime
    from autogen_ext.tools.mcp import McpWorkbench as _McpWorkbench

class AutoGenEventHandler(logging.Handler):
    """Custom logging handler to capture AutoGen runtime events and forward them to RunMonitor."""
    
    def __init__(self, monitor: Optional[RunMonitor] = None):
        super().__init__()
        self.monitor = monitor
        self.setLevel(logging.INFO)
    
    def emit(self, record: logging.LogRecord) -> None:
        """Capture and forward AutoGen events to our monitoring system."""
        try:
            if not self.monitor:
                return
            
            # Extract structured event data
            event_data = {}
            event_type = 'autogen_event'
            event_category = 'runtime'
            agent_name = None
            tool_name = None
            
            # Get the logger name to determine event context
            logger_name = record.name
            
            # Check if this is a structured message (dataclass/dict)
            if hasattr(record.msg, '__dataclass_fields__'):
                # Structured dataclass event
                event_data = {
                    'event_class': record.msg.__class__.__name__,
                    'logger_name': logger_name,
                    'level': record.levelname,
                    'timestamp': record.created,
                }
                
                # Extract fields from the dataclass
                for field_name, field_value in record.msg.__dict__.items():
                    event_data[field_name] = str(field_value) if not isinstance(field_value, (dict, list, str, int, float, bool)) else field_value
                
                # Determine event categorization
                event_class = record.msg.__class__.__name__.lower()
                if 'message' in event_class:
                    event_type = 'message_event'
                    event_category = 'communication'
                elif 'tool' in event_class:
                    event_type = 'tool_event'
                    event_category = 'mcp'
                    tool_name = event_data.get('tool_name') or event_data.get('name')
                elif 'agent' in event_class:
                    event_type = 'agent_event'
                    event_category = 'agent'
                    agent_name = event_data.get('agent_name') or event_data.get('source') or event_data.get('name')
                elif 'selector' in event_class:
                    event_type = 'selector_event'
                    event_category = 'orchestrator'
                elif 'runtime' in event_class or 'execution' in event_class:
                    event_type = 'runtime_event'
                    event_category = 'runtime'
                
            elif isinstance(record.msg, dict):
                # Dictionary-based event
                event_data = record.msg.copy()
                event_data.update({
                    'logger_name': logger_name,
                    'level': record.levelname,
                    'timestamp': record.created,
                })
                event_type = 'autogen_dict_event'
                
            else:
                # String message - convert to structured format
                event_data = {
                    'message': str(record.msg),
                    'logger_name': logger_name,
                    'level': record.levelname,
                    'timestamp': record.created,
                }
                event_type = 'autogen_text_event'
            
            # Add exception info if present
            if record.exc_info:
                event_data['exception'] = self.formatException(record.exc_info)
                event_category = 'error'
            
            # Log the event to our monitor system
            self.monitor.log_event(event_type, event_category, event_data, agent_name=agent_name, tool_name=tool_name)
            
        except Exception as e:
            # Don't let logging errors break the application
            self.handleError(record)

class CompositeWorkbench:
    """Combines multiple McpWorkbench instances and optionally restricts visible tools."""
    def __init__(self, workbenches: Dict[str, Any], allowed_tools: Optional[List[str]] = None, monitor: Optional[RunMonitor] = None):
        self._wbs = workbenches  # key: server_id str -> workbench
        self._allowed = set(allowed_tools) if allowed_tools else None
        self._allowed_list = list(allowed_tools) if allowed_tools else []
        self._monitor = monitor
        # Mapping between sanitized tool names (what the LLM sees) and namespaced originals (serverKey:tool)
        self._sanitized_to_namespaced: Dict[str, str] = {}
        self._namespaced_to_sanitized: Dict[str, str] = {}
        # Simple cache to avoid repeated list_tools calls each turn
        self._tools_cache = None
        self._tools_cache_ts = 0.0
        self._tools_cache_ttl = 30.0  # seconds
        self._cache_hit_logged = False

    def get_allowed_tools_raw(self) -> List[str]:
        """Return namespaced allowed tool names without listing from servers."""
        return list(self._allowed_list)

    @staticmethod
    def _sanitize_name(name: str) -> str:
        """Return a name compatible with OpenAI tools: [A-Za-z0-9_-], cannot start with a digit.
        We convert any other char to '_', and prefix with 't_' if it starts with a digit.
        """
        import re
        # Replace invalid characters with '_'
        cleaned = re.sub(r"[^A-Za-z0-9_-]", "_", name)
        # Names cannot start with a digit per OpenAI spec
        if cleaned and cleaned[0].isdigit():
            cleaned = f"t_{cleaned}"
        # Avoid empty
        return cleaned or "tool"

    async def __aenter__(self):
        for wb in self._wbs.values():
            await wb.start()
        return self

    async def __aexit__(self, exc_type, exc, tb):
        for wb in self._wbs.values():
            try:
                await wb.stop()
            except Exception:
                pass

    async def list_tools(self):
        import time as _time
        # serve from cache if fresh
        if self._tools_cache and (_time.time() - self._tools_cache_ts) < self._tools_cache_ttl:
            if self._monitor and not self._cache_hit_logged:
                try:
                    self._monitor.log_event('list_tools_cache_hit', 'mcp', {"count": len(self._tools_cache)})
                    self._cache_hit_logged = True
                except Exception:
                    pass
            return self._tools_cache

        tools = []
        for server_key, wb in self._wbs.items():
            try:
                tlist = await wb.list_tools()
                if self._monitor:
                    try:
                        self._monitor.log_event(
                            'list_tools', 'mcp',
                            {"server_id": server_key, "count": len(tlist), "names": [t.get('name') for t in tlist]}
                        )
                    except Exception:
                        pass
                for t in tlist:
                    namespaced = f"{server_key}:{t['name']}"
                    if self._allowed and namespaced not in self._allowed:
                        continue
                    # create or reuse a sanitized name for LLM consumption
                    sanitized = self._namespaced_to_sanitized.get(namespaced)
                    if not sanitized:
                        base = self._sanitize_name(namespaced)
                        sanitized = base
                        # ensure uniqueness across mapping
                        counter = 1
                        while sanitized in self._sanitized_to_namespaced and self._sanitized_to_namespaced[sanitized] != namespaced:
                            counter += 1
                            sanitized = f"{base}_{counter}"
                        self._sanitized_to_namespaced[sanitized] = namespaced
                        self._namespaced_to_sanitized[namespaced] = sanitized
                    # expose sanitized tool names to the model
                    tools.append({**t, 'name': sanitized})
            except Exception:
                continue
        # update cache
        self._tools_cache = tools
        self._tools_cache_ts = _time.time()
        return tools

    async def call_tool(self, name: str, arguments: Dict[str, Any] | None = None, **kwargs):
        # Accept both sanitized names (from the model) and namespaced originals
        namespaced = self._sanitized_to_namespaced.get(name, name)
        
        # Also try to match unsanitized tool names to their namespaced equivalents
        if namespaced == name and ':' not in namespaced:
            # Look for a match in the format server_id:tool_name
            for allowed_ns in self._allowed or []:
                if ':' in allowed_ns:
                    server_key, tool_name = allowed_ns.split(':', 1)
                    if tool_name == name:
                        namespaced = allowed_ns
                        break
        
        if self._allowed and namespaced not in self._allowed:
            # Provide helpful error message showing available tools
            available_tools = []
            for sanitized, ns in self._sanitized_to_namespaced.items():
                available_tools.append(f"'{sanitized}' (maps to {ns})")
            raise ValueError(f"Tool '{name}' not found in any workbench. Available tools: {', '.join(available_tools) if available_tools else 'none'}")
        
        # expected namespaced format: serverKey:tool
        if ':' not in namespaced:
            raise ValueError(f"Composite tool name must be 'server:tool', got '{namespaced}'")
        
        server_key, tool_name = namespaced.split(':', 1)
        wb = self._wbs.get(server_key)
        if not wb:
            raise ValueError(f"Workbench for server '{server_key}' not found")
        if self._monitor:
            try:
                arg_preview = None
                if arguments is not None:
                    import json as _json
                    try:
                        arg_preview = _json.dumps(arguments)
                    except Exception:
                        arg_preview = str(arguments)[:500] + '…'
                self._monitor.log_event('tool_call', 'mcp', {"server_id": server_key, "tool": tool_name, "args": arg_preview})
            except Exception:
                pass
        result = await wb.call_tool(tool_name, arguments or {}, **kwargs)
        if self._monitor:
            try:
                preview = str(getattr(result, 'content', result))
                self._monitor.log_event('tool_result', 'mcp', {"server_id": server_key, "tool": tool_name, "result_preview": preview})
            except Exception:
                pass
        return result


class AutoGenOrchestrator:
    """Bridges our app (LLM, MCP tools) with AutoGen multi-agent teams/workflows using latest APIs."""

    def __init__(self):
        self.llm_engine = get_llm_engine()
        self._autogen_handler = None

    def _setup_autogen_logging(self, monitor: Optional[RunMonitor] = None):
        """Setup AutoGen runtime logging to capture events while teams/workflows are running."""
        if not NEW_AUTOGEN_AVAILABLE:
            return
        
        try:
            # Create our custom handler
            self._autogen_handler = AutoGenEventHandler(monitor)
            
            # Setup event logger (structured events)
            event_logger = logging.getLogger(EVENT_LOGGER_NAME)
            event_logger.setLevel(logging.INFO)
            # Remove existing handlers to avoid duplicates
            for handler in event_logger.handlers[:]:
                event_logger.removeHandler(handler)
            event_logger.addHandler(self._autogen_handler)
            event_logger.propagate = False  # Don't propagate to root logger
            
            # Setup trace logger (debugging events)
            trace_logger = logging.getLogger(TRACE_LOGGER_NAME)
            trace_logger.setLevel(logging.DEBUG)
            # Remove existing handlers to avoid duplicates
            for handler in trace_logger.handlers[:]:
                trace_logger.removeHandler(handler)
            trace_logger.addHandler(self._autogen_handler)
            trace_logger.propagate = False  # Don't propagate to root logger
            
            if monitor:
                monitor.log_event('autogen_logging_setup', 'orchestrator', {
                    'event_logger': EVENT_LOGGER_NAME,
                    'trace_logger': TRACE_LOGGER_NAME,
                    'handler_type': 'AutoGenEventHandler',
                    'status': 'enabled'
                })
                
        except Exception as e:
            logger.error(f"Failed to setup AutoGen logging: {e}")
            if monitor:
                monitor.log_event('autogen_logging_error', 'orchestrator', {
                    'error': str(e),
                    'status': 'failed'
                })

    def _cleanup_autogen_logging(self):
        """Cleanup AutoGen logging handlers."""
        try:
            if self._autogen_handler:
                # Remove our handler from AutoGen loggers
                event_logger = logging.getLogger(EVENT_LOGGER_NAME)
                if self._autogen_handler in event_logger.handlers:
                    event_logger.removeHandler(self._autogen_handler)
                
                trace_logger = logging.getLogger(TRACE_LOGGER_NAME)
                if self._autogen_handler in trace_logger.handlers:
                    trace_logger.removeHandler(self._autogen_handler)
                
                # Close the handler
                self._autogen_handler.close()
                self._autogen_handler = None
        except Exception as e:
            logger.error(f"Failed to cleanup AutoGen logging: {e}")

    def _ensure_openai_env(self):
        # Read from config and map to OpenAI-compatible environment variables
        try:
            from config.config import OPENROUTER_API_KEY, OPENROUTER_BASE_URL
            if OPENROUTER_API_KEY:
                os.environ['OPENAI_API_KEY'] = OPENROUTER_API_KEY
            if OPENROUTER_BASE_URL:
                os.environ['OPENAI_BASE_URL'] = OPENROUTER_BASE_URL
        except Exception as e:
            logger.warning(f"Failed to map OpenRouter config to OpenAI env: {e}")

    def _build_model_client(self):
        """Construct the OpenAI-compatible model client with explicit config.
    Always passes ModelInfo for compatibility with non-OpenAI model names.
    Returns None if configuration is incomplete or init fails.
        """
        self._ensure_openai_env()
        # Read config
        try:
            from config.config import OPENROUTER_API_KEY, OPENROUTER_BASE_URL, OPENROUTER_MODEL, TEMPERATURE, MAX_TOKENS
        except Exception:
            OPENROUTER_API_KEY = os.getenv('OPENAI_API_KEY') or ''
            OPENROUTER_BASE_URL = os.getenv('OPENAI_BASE_URL') or ''
            OPENROUTER_MODEL = getattr(self.llm_engine, 'model_name', None)
            TEMPERATURE = None
            MAX_TOKENS = None

        api_key = OPENROUTER_API_KEY or os.getenv('OPENAI_API_KEY') or ''
        base_url = OPENROUTER_BASE_URL or os.getenv('OPENAI_BASE_URL') or ''
        model_name = OPENROUTER_MODEL or getattr(self.llm_engine, 'model_name', None)

        def _mask(s: Optional[str]) -> str:
            if not s:
                return '<empty>'
            return s[:4] + '…' if len(s) > 8 else '****'

        if not model_name:
            logger.error("Model client init failed: Missing model name (OPENROUTER_MODEL or llm_engine.model_name)")
            return None
        if not api_key and not os.getenv('OPENAI_API_KEY'):
            logger.error("Model client init failed: Missing API key (OPENROUTER_API_KEY/OPENAI_API_KEY)")
            return None
        # base_url is optional for pure OpenAI, but required for non-OpenAI endpoints like Gemini OpenAI-compatible
        if not base_url:
            logger.info("Model client init: base_url not set; relying on OpenAI default endpoint")

        # Always construct with ModelInfo
        inferred_family = 'openrouter'
        lower_name = (model_name or '').lower()
        if 'gemini' in lower_name:
            inferred_family = 'gemini'
        elif lower_name.startswith('gpt') or 'openai' in lower_name:
            inferred_family = 'openai'
        mi = ModelInfo(
            vision=('gemini' in lower_name),
            function_calling=True,
            json_output=False,
            family=inferred_family,
            structured_output=True,
        )
        try:
            client = OpenAIChatCompletionClient(
                model=model_name,
                api_key=api_key or None,
                base_url=base_url or None,
                temperature=TEMPERATURE if isinstance(TEMPERATURE, (int, float)) else None,
                max_tokens=MAX_TOKENS if isinstance(MAX_TOKENS, int) else None,
                model_info=mi,
                # Reduce spurious calls and racey parallel tool usage
                parallel_tool_calls=False,
            )
            logger.info(
                f"OpenAIChatCompletionClient initialized (model={model_name}, family={inferred_family}, base_url={base_url or 'default'}, api_key={_mask(api_key)})"
            )
            return client
        except Exception as e:
            tb = traceback.format_exc()
            logger.error(f"Failed to init OpenAIChatCompletionClient with ModelInfo: {e}\n{tb}")
            return None

    def _server_params_from_config(self, server: MCPServer):
        cfg = server.config or {}
        if server.server_type == MCPServerType.STDIO.value or server.server_type == MCPServerType.STDIO:
            return StdioServerParams(
                command=cfg.get('command') or cfg.get('cmd') or 'python',
                args=cfg.get('args') or [],
                env=cfg.get('env') or {},
                cwd=cfg.get('cwd')
            )
        else:
            # Prefer SSE/streamable HTTP when available
            url = cfg.get('url') or cfg.get('endpoint')
            if not url:
                raise ValueError(f"Missing URL for HTTP MCP server {server.name}")
            # Follow autogen_ext.tools.mcp docs: use url, optional headers and sensible timeouts
            return StreamableHttpServerParams(
                url=url,
                headers=cfg.get('headers') or {},
                timeout=float(cfg.get('timeout', 30.0)),
                sse_read_timeout=float(cfg.get('sse_read_timeout', 300.0)),
                terminate_on_close=bool(cfg.get('terminate_on_close', True)),
            )

    async def _build_workbench_for_agent(self, agent_spec: Dict[str, Any], monitor: Optional[RunMonitor] = None) -> CompositeWorkbench:
        """Create a CompositeWorkbench for the given agent spec, restricted to its selected tools."""
        # Collect servers used by this agent's selected tools
        tool_specs = agent_spec.get('tools') or []
        by_server: Dict[int, List[str]] = {}
        for t in tool_specs:
            sid = t.get('server_id')
            name = t.get('tool_name')
            if not sid or not name:
                continue
            by_server.setdefault(int(sid), []).append(name)

        workbenches: Dict[str, McpWorkbench] = {}
        allowed_namespaced: List[str] = []
        for sid, tools in by_server.items():
            server = MCPServer.get_by_id(sid)
            if not server:
                logger.warning(f"Server {sid} not found")
                continue
            try:
                params = self._server_params_from_config(server)
                wb = McpWorkbench(server_params=params, model_client=self._build_model_client())
                key = str(sid)
                workbenches[key] = wb
                for tn in tools:
                    allowed_namespaced.append(f"{key}:{tn}")
            except Exception as e:
                logger.warning(f"Failed to init workbench for server {server.name}: {e}")
        return CompositeWorkbench(workbenches, allowed_tools=allowed_namespaced, monitor=monitor)

    async def _build_agents_team(self, team: AgentTeam, monitor: Optional[RunMonitor] = None):
        agents_cfg = team.config.get('agents', [])
        # Prefer fewer default turns to avoid post-answer empty loops; honor user setting when provided
        settings = team.config.get('settings', {}) or {}
        execution_mode = settings.get('execution_mode', 'roundrobin')  # roundrobin or selector
        if 'max_rounds' in settings and settings.get('max_rounds') is not None:
            max_rounds = int(settings.get('max_rounds'))
        else:
            # If there are no tools across all agents, only 1 round; otherwise default to 6
            has_any_tools = any((spec or {}).get('tools') for spec in agents_cfg)
            max_rounds = 6 if has_any_tools else 1
        agents = []
        # Build an AssistantAgent for each agent spec with its own composite workbench
        for spec in agents_cfg:
            name = spec.get('name') or spec.get('role') or 'Agent'
            base_prompt = spec.get('system_prompt') or f"You are {name}."
            # Nudge to avoid unnecessary tool calls and to terminate cleanly
            system_prompt = (
                base_prompt
                + "\n\nGuidelines: You have access to tools that allow you to execute commands and perform tasks. "
                  "When you use a tool, you MUST analyze the results and provide a helpful summary or explanation "
                  "to the user in your own words. Don't just execute tools - explain what the results mean. "
                  "Always provide a complete, helpful response to the user's request with your analysis. "
                  "After giving your final answer, add exactly: TERMINATE"
            )
            wb = await self._build_workbench_for_agent(spec, monitor=monitor)
            model_client = self._build_model_client()
            if not NEW_AUTOGEN_AVAILABLE:
                raise RuntimeError("AutoGen AgentChat not available")
            if not model_client:
                raise RuntimeError("Model client init failed. Check OPENROUTER_MODEL, OPENROUTER_API_KEY, OPENROUTER_BASE_URL / OPENAI_* env.")
            # manage workbench lifecycle externally via async context when running
            agent = AssistantAgent(
                name,
                model_client=model_client,
                system_message=system_prompt,
                workbench=wb,
                model_client_stream=False,
                reflect_on_tool_use=False,
                description=spec.get('description', f"An agent responsible for {name.lower()} tasks."),
            )
            agents.append((agent, wb))

        if not agents:
            raise RuntimeError("No agents defined in team")

        # In autogen-agentchat>=0.7, pass max_turns to control rounds
        try:
            if monitor:
                monitor.log_event('status', 'orchestrator', {
                    "message": "groupchat configured", 
                    "max_turns": max_rounds, 
                    "agent_count": len(agents),
                    "execution_mode": execution_mode
                })
        except Exception:
            pass
        
        # For single-agent teams, check if they have tools that need multi-turn interaction
        if len(agents) == 1:
            agent_spec = agents_cfg[0]
            has_tools = bool(agent_spec.get('tools'))
            if has_tools:
                # Single agent with tools - use RoundRobinGroupChat with limited turns to allow tool interaction
                termination = TextMentionTermination("TERMINATE")
                team_obj = RoundRobinGroupChat(
                    [a for a, _ in agents], 
                    max_turns=min(max_rounds, 3),  # Limit turns but allow tool interaction
                    termination_condition=termination
                )
                return agents, team_obj
            else:
                # Single agent without tools - use direct execution
                return agents, None  # Signal to use direct agent execution
        else:
            # Multi-agent execution based on mode
            termination = TextMentionTermination("TERMINATE")
            
            if execution_mode == 'selector':
                # Use SelectorGroupChat with configurable selector prompt
                selector_prompt = settings.get('selector_prompt', """You are an agent selector. Your ONLY job is to select which agent should speak next.

Available agents: {participants}

Current conversation context:
{history}

CRITICAL RULES:
- Respond with EXACTLY ONE agent name from the list
- Do NOT use any tools or functions
- Do NOT explain your reasoning
- Do NOT add any extra text
- Just return the agent name

Select agent:""")
                
                allow_repeated_speaker = settings.get('allow_repeated_speaker', True)
                
                # Create a model client specifically for the selector (without tools)
                # This must be completely isolated from any agent tool definitions
                try:
                    # Get basic config values
                    api_key = os.getenv('OPENAI_API_KEY') or os.getenv('OPENROUTER_API_KEY', '')
                    base_url = os.getenv('OPENAI_BASE_URL') or os.getenv('OPENROUTER_BASE_URL', '')
                    model_name = getattr(self.llm_engine, 'model_name', None) or os.getenv('OPENROUTER_MODEL', '')
                    
                    # Create minimal ModelInfo without function calling
                    minimal_model_info = ModelInfo(
                        vision=False,
                        function_calling=False,  # Explicitly disable function calling
                        json_output=False,
                        family="openai",
                        structured_output=False,
                    )
                    
                    # Create selector model client with strict no-tools configuration
                    selector_model_client = OpenAIChatCompletionClient(
                        model=model_name,
                        api_key=api_key,
                        base_url=base_url,
                        model_info=minimal_model_info,
                        parallel_tool_calls=False,
                    )
                    
                    monitor.log_event('selector_model_created', 'orchestrator', {
                        "model": model_name,
                        "function_calling": False,
                        "max_tokens": 10
                    })
                    
                except Exception as e:
                    monitor.log_event('selector_model_error', 'orchestrator', {"error": str(e)})
                    # Fallback to basic configuration
                    selector_model_client = self._build_model_client()
                
                # Remove custom selector function to use model-based selection
                
                team_obj = SelectorGroupChat(
                    [a for a, _ in agents],
                    model_client=selector_model_client,
                    termination_condition=termination,
                    selector_prompt=selector_prompt,
                    allow_repeated_speaker=allow_repeated_speaker,
                    max_turns=max_rounds,
                )
                return agents, team_obj
            elif execution_mode == 'swarm':
                # Use Swarm team with configurable participants
                team_obj = Swarm(
                    participants=[a for a, _ in agents],
                    termination_condition=termination
                )
                return agents, team_obj
            else:
                # Default: RoundRobinGroupChat
                team_obj = RoundRobinGroupChat(
                    [a for a, _ in agents], 
                    max_turns=max_rounds,
                    termination_condition=termination
                )
                return agents, team_obj

    @staticmethod
    def _extract_final_text(result: Any) -> str:
        """Extract the last meaningful assistant/model text from an AutoGen result."""
        # Try to walk messages from the end
        try:
            msgs = getattr(result, 'messages', None)
            if not msgs or not isinstance(msgs, (list, tuple)):
                return str(result)
            
            # Look for the last TextMessage from an agent (not user) and collect context
            final_agent = None
            tools_used = []
            
            # First pass: collect tool usage information
            for m in msgs:
                m_type = type(m).__name__
                if m_type == 'ToolCallRequestEvent' and hasattr(m, 'content'):
                    for tool_call in m.content:
                        if hasattr(tool_call, 'name'):
                            tool_name = tool_call.name
                            # Clean up tool name (remove prefixes like 't_1_')
                            clean_tool_name = tool_name
                            if '_' in tool_name and tool_name.startswith('t_'):
                                parts = tool_name.split('_', 2)
                                if len(parts) >= 3:
                                    clean_tool_name = parts[2]
                            tools_used.append(clean_tool_name)
            
            # Second pass: find the final meaningful response
            for m in reversed(msgs):
                m_type = type(m).__name__
                
                # Focus on TextMessage types from agents
                if m_type == 'TextMessage':
                    content = getattr(m, 'content', None)
                    src = getattr(m, 'source', '') or ''
                    
                    # Skip user messages
                    if src.lower() == 'user':
                        continue
                    
                    # Found an agent's text message
                    if isinstance(content, str) and content.strip():
                        text = content.strip()
                        
                        # Remove TERMINATE from the end if present
                        if text.endswith('TERMINATE'):
                            text = text[:-len('TERMINATE')].rstrip()
                        
                        # Return the cleaned text with context if it has meaningful content
                        if text and text not in ('TERMINATE', ''):
                            final_agent = src
                            
                            # Build response with context
                            response_parts = []
                            
                            # Add tool context if tools were used
                            if tools_used:
                                unique_tools = list(set(tools_used))  # Remove duplicates
                                if len(unique_tools) == 1:
                                    response_parts.append(f"**Used Tool:** {unique_tools[0]}")
                                else:
                                    response_parts.append(f"**Used Tools:** {', '.join(unique_tools)}")
                            
                            # Add agent context if not generic
                            if final_agent and final_agent not in ['Assistant', 'Agent', 'assistant', 'agent']:
                                response_parts.append(f"**Agent:** {final_agent}")
                            
                            # Add separator line if we have context
                            if response_parts:
                                response_parts.append("")  # Empty line
                            
                            # Add the main content
                            response_parts.append(text)
                            
                            return "\n".join(response_parts)
            
            # Fallback: collect all meaningful assistant responses
            meaningful_contents = []
            tool_results = []
            tool_call_info = []
            
            # Collect tool execution results and meaningful responses
            for m in msgs:
                content = getattr(m, 'content', None) or getattr(m, 'text', None)
                src = (getattr(m, 'source', '') or '').lower()
                m_type = type(m).__name__
                
                # Collect tool call requests for context
                if m_type == 'ToolCallRequestEvent' and hasattr(m, 'content'):
                    for tool_call in m.content:
                        if hasattr(tool_call, 'name') and hasattr(tool_call, 'arguments'):
                            tool_call_info.append({
                                'name': tool_call.name,
                                'args': tool_call.arguments
                            })
                
                # Collect tool execution results
                if m_type == 'ToolCallExecutionEvent' and hasattr(m, 'content'):
                    for tool_result in m.content:
                        if hasattr(tool_result, 'content') and tool_result.content:
                            tool_results.append({
                                'name': getattr(tool_result, 'name', 'unknown'),
                                'content': tool_result.content
                            })
                
                # Collect meaningful assistant responses (excluding tool-only agents)
                if (src in ('assistant', 'agent', 'model') or 
                    (hasattr(m, 'source') and 'agent' in str(m.source).lower())) and isinstance(content, str) and content.strip():
                    cleaned_content = content.strip()
                    # If it's just "TERMINATE", skip it but keep looking
                    if cleaned_content not in ('TERMINATE', 'TERMINATE\n'):
                        # Remove TERMINATE from the end if present
                        if cleaned_content.endswith('TERMINATE'):
                            cleaned_content = cleaned_content[:-len('TERMINATE')].rstrip()
                        if cleaned_content:  # Only add if there's actual content
                            meaningful_contents.append(cleaned_content)
            
            # If we found meaningful responses, return the last one
            if meaningful_contents:
                return meaningful_contents[-1]  # Return the last meaningful response
            
            # If no meaningful assistant response but we have tool results, create a helpful summary
            if tool_results:
                response_parts = []
                
                for i, (tool_call, tool_result) in enumerate(zip(tool_call_info, tool_results)):
                    tool_name = tool_result.get('name', 'unknown')
                    result_content = tool_result.get('content', '')
                    
                    if 'bash' in tool_name.lower() or 'shell' in tool_name.lower():
                        # For bash/shell commands, show the command and results
                        try:
                            import json
                            args = json.loads(tool_call.get('args', '{}'))
                            command = args.get('command', 'unknown command')
                            response_parts.append(f"Executed command: `{command}`")
                            
                            response_parts.append(f"Output:\n```\n{result_content}\n```")
                        except:
                            response_parts.append(f"Command executed successfully. Output:\n```\n{result_content}\n```")
                    else:
                        # For other tools, show generic result
                        response_parts.append(f"Tool '{tool_name}' executed successfully. Result: {result_content}")
                
                return "\n\n".join(response_parts) if response_parts else "Tool executed successfully."
            
            # If no assistant message found, try to extract from any non-user message
            for m in reversed(msgs):
                content = getattr(m, 'content', None) or getattr(m, 'text', None)
                src = (getattr(m, 'source', '') or '').lower()
                if src not in ('user',) and isinstance(content, str) and content.strip():
                    text = content.strip()
                    if text.endswith('TERMINATE'):
                        text = text[: -len('TERMINATE')].rstrip()
                    if text:  # Only return if there's actual content after removing TERMINATE
                        return text
                    
        except Exception:
            pass
        
        # Fallback
        fallback = str(result)
        # If the fallback is the raw result object representation, try to get a better representation
        if fallback.startswith('messages=[') and 'TextMessage' in fallback:
            return "Task completed successfully."
        return fallback

    async def run_team(self, team: AgentTeam, task: str, context: Optional[List[Dict[str, str]]] = None) -> Dict[str, Any]:
        if not NEW_AUTOGEN_AVAILABLE:
            return {"success": False, "error": "AutoGen AgentChat not installed", "trace": NEW_AUTOGEN_IMPORT_ERROR}
        monitor = RunMonitor()
        run_id = monitor.start_run('team', team.id or -1, task or '')
        
        # Setup AutoGen logging to capture runtime events
        self._setup_autogen_logging(monitor)
        
        try:
            agents_with_wb, team_obj = await self._build_agents_team(team, monitor=monitor)
            # Start all workbenches via context managers
            async def with_all_workbenches():
                # enter all workbenches
                for _, wb in agents_with_wb:
                    await wb.__aenter__()
                try:
                    # Build and log a detailed llm_input snapshot after workbenches are active
                    try:
                        # Helper to truncate large JSON safely
                        def _truncate_obj(obj, max_len=20000):
                            import json as _json
                            try:
                                s = _json.dumps(obj, ensure_ascii=False)
                            except Exception:
                                s = str(obj)
                            return (s if len(s) <= max_len else s[:max_len] + '…')

                        detailed_inputs = {
                            'task': task,
                            'context': context or [],
                            'agents': []
                        }
                        for a, wb in agents_with_wb:
                            tools = []
                            try:
                                tlist = await wb.list_tools()
                                # trim each tool schema to avoid huge payloads
                                for t in tlist or []:
                                    t_trim = {
                                        'name': t.get('name'),
                                        'description': t.get('description'),
                                        'parameters': t.get('parameters') or t.get('schema') or t.get('function', {}).get('parameters')
                                    }
                                    tools.append(t_trim)
                            except Exception:
                                pass
                            detailed_inputs['agents'].append({
                                'name': getattr(a, 'name', None),
                                'system_message': getattr(a, 'system_message', None),
                                'tools': tools
                            })
                        monitor.log_event('llm_input', 'model', {'payload': _truncate_obj(detailed_inputs)})
                        # Also log a compact llm_first_input approximation (system + user per agent)
                        compact_inputs = []
                        for a, wb in agents_with_wb:
                            try:
                                tool_names = [t.get('name') for t in (await wb.list_tools())]
                            except Exception:
                                tool_names = []
                            compact_inputs.append({
                                'agent': getattr(a, 'name', None),
                                'messages': [
                                    {'role': 'system', 'content': getattr(a, 'system_message', None)},
                                    {'role': 'user', 'content': task},
                                ],
                                'tools': tool_names
                            })
                        monitor.log_event('llm_first_input', 'model', {'payload': _truncate_obj(compact_inputs)})
                    except Exception:
                        pass
                    monitor.log_event('status', 'orchestrator', {"message": "execution start", "task": task}, agent_name=None)
                    with _Timer() as t:
                        # Handle single agent vs multi-agent execution
                        if team_obj is None:
                            # Single agent direct execution
                            agent, _ = agents_with_wb[0]
                            monitor.log_event('status', 'orchestrator', {"message": "single agent direct execution"})
                            result = await agent.run(task=task)
                        else:
                            # Multi-agent team execution
                            monitor.log_event('status', 'orchestrator', {"message": "multi-agent team execution"})
                            result = await team_obj.run(task=task)
                    # Extract first assistant/model message as llm_first_output
                    try:
                        def _msg_to_dict(m):
                            d = {
                                'type': type(m).__name__,
                                'source': getattr(m, 'source', None),
                                'content': getattr(m, 'content', None) or getattr(m, 'text', None)
                            }
                            # capture common tool call fields if present
                            for key in ('tool_calls', 'function_call', 'tool_name', 'arguments'):
                                val = getattr(m, key, None)
                                if val is not None:
                                    d[key] = val
                            return d

                        first_output = None
                        msgs = getattr(result, 'messages', None)
                        if msgs and isinstance(msgs, (list, tuple)):
                            for m in msgs:
                                md = _msg_to_dict(m)
                                src = (md.get('source') or '').lower()
                                if src in ('assistant', 'agent', 'model'):
                                    first_output = md
                                    break
                        if first_output:
                            monitor.log_event('llm_first_output', 'model', {'message': _truncate_obj(first_output, 10000)})
                    except Exception:
                        pass
                    # Emit one event per LLM/model call for observability across loops
                    try:
                        msgs = getattr(result, 'messages', None)
                        if msgs and isinstance(msgs, (list, tuple)):
                            empty_chain = 0
                            current_tool_name = None
                            
                            for idx, m in enumerate(msgs):
                                m_type = type(m).__name__
                                src = getattr(m, 'source', None)
                                src_lower = (src or '').lower()
                                mu = getattr(m, 'models_usage', None)
                                
                                # Extract tool information from ToolCallRequestEvent
                                if m_type == 'ToolCallRequestEvent' and hasattr(m, 'content'):
                                    for tool_call in m.content:
                                        if hasattr(tool_call, 'name'):
                                            tool_name = tool_call.name
                                            # Clean up tool name (remove prefixes like 't_1_')
                                            clean_tool_name = tool_name
                                            if '_' in tool_name and tool_name.startswith('t_'):
                                                parts = tool_name.split('_', 2)
                                                if len(parts) >= 3:
                                                    clean_tool_name = parts[2]
                                            
                                            current_tool_name = clean_tool_name
                                            
                                            # Log tool call event with agent and tool info
                                            tool_args = getattr(tool_call, 'arguments', '{}')
                                            monitor.log_event(
                                                'tool_call', 
                                                'mcp', 
                                                {
                                                    'tool_name': clean_tool_name,
                                                    'original_name': tool_name,
                                                    'arguments': tool_args,
                                                    'index': idx
                                                },
                                                agent_name=src,
                                                tool_name=clean_tool_name
                                            )
                                
                                # Extract tool execution results
                                elif m_type == 'ToolCallExecutionEvent' and hasattr(m, 'content'):
                                    for tool_result in m.content:
                                        if hasattr(tool_result, 'content') and tool_result.content:
                                            result_tool_name = getattr(tool_result, 'name', current_tool_name or 'unknown')
                                            # Clean up tool name
                                            clean_result_name = result_tool_name
                                            if '_' in result_tool_name and result_tool_name.startswith('t_'):
                                                parts = result_tool_name.split('_', 2)
                                                if len(parts) >= 3:
                                                    clean_result_name = parts[2]
                                            
                                            # Log tool result event
                                            monitor.log_event(
                                                'tool_result', 
                                                'mcp', 
                                                {
                                                    'tool_name': clean_result_name,
                                                    'result_preview': str(tool_result.content)[:500],
                                                    'is_error': getattr(tool_result, 'is_error', False),
                                                    'index': idx
                                                },
                                                agent_name=src,
                                                tool_name=clean_result_name
                                            )
                                
                                # Treat model-originated messages as LLM calls when usage is present
                                elif src_lower in ('assistant', 'agent', 'model') and mu is not None:
                                    pt = getattr(mu, 'prompt_tokens', None)
                                    ct = getattr(mu, 'completion_tokens', None)
                                    content = getattr(m, 'content', None) or getattr(m, 'text', None) or ''
                                    # Detect if this message is a tool call request
                                    is_tool_req = m_type.endswith('ToolCallRequestEvent') or hasattr(m, 'function_call') or hasattr(m, 'tool_calls')
                                    payload = {
                                        'index': idx,
                                        'type': m_type,
                                        'source': src,
                                        'prompt_tokens': pt,
                                        'completion_tokens': ct,
                                        'is_tool_request': bool(is_tool_req),
                                        'content_preview': (content[:300] + '…') if isinstance(content, str) and len(content) > 300 else content,
                                        'is_empty': True if (isinstance(content, str) and content.strip() == '') else False,
                                    }
                                    monitor.log_event('llm_call', 'model', payload, agent_name=src)
                                    # Track empty chains to identify unnecessary loops
                                    if isinstance(content, str) and content.strip() == '' and not is_tool_req and (ct == 0 or ct is None):
                                        empty_chain += 1
                                
                                # Log general TextMessage events from agents  
                                elif m_type == 'TextMessage' and src and src_lower != 'user':
                                    content = getattr(m, 'content', None) or ''
                                    if isinstance(content, str) and content.strip():
                                        # Don't log if it's just TERMINATE
                                        clean_content = content.strip()
                                        if clean_content not in ('TERMINATE', 'TERMINATE\n'):
                                            if clean_content.endswith('TERMINATE'):
                                                clean_content = clean_content[:-len('TERMINATE')].rstrip()
                                            
                                            if clean_content:  # Only log if there's meaningful content
                                                monitor.log_event(
                                                    'agent_response', 
                                                    'agent', 
                                                    {
                                                        'content_preview': clean_content[:500] + ('...' if len(clean_content) > 500 else ''),
                                                        'full_length': len(clean_content),
                                                        'index': idx
                                                    },
                                                    agent_name=src
                                                )
                            
                            if empty_chain:
                                monitor.log_event('llm_loop_summary', 'model', {'empty_llm_messages': empty_chain})
                    except Exception:
                        pass
                    stop_reason = getattr(result, 'stop_reason', None)
                    monitor.log_event('llm_result', 'model', {"reply": str(result), "elapsed_sec": getattr(t, 'elapsed', None), "stop_reason": stop_reason})
                finally:
                    for _, wb in agents_with_wb:
                        try:
                            await wb.__aexit__(None, None, None)
                        except Exception:
                            pass
                return result

            result = await with_all_workbenches()
            final_text = self._extract_final_text(result)
            monitor.end_run('success', final_reply=final_text)
            return {"success": True, "reply": final_text, "run_id": run_id}
        except Exception as e:
            tb = traceback.format_exc()
            logger.error(f"Team run failed: {e}\n{tb}")
            monitor.log_event('error', 'orchestrator', {"error": str(e), "trace": tb})
            monitor.end_run('error', error=str(e))
            return {"success": False, "error": str(e), "trace": tb, "run_id": run_id}
        finally:
            # Cleanup AutoGen logging
            self._cleanup_autogen_logging()

    async def run_workflow(self, workflow: AgentWorkflow, input_text: str, context: Optional[List[Dict[str, str]]] = None) -> Dict[str, Any]:
        """Run a workflow using AutoGen GraphFlow."""
        if not NEW_AUTOGEN_AVAILABLE:
            return {"success": False, "error": "AutoGen AgentChat not installed", "trace": NEW_AUTOGEN_IMPORT_ERROR}
            
        monitor = RunMonitor()
        run_id = monitor.start_run('workflow', workflow.id or -1, input_text or '')
        
        # Setup AutoGen logging to capture runtime events
        self._setup_autogen_logging(monitor)
        
        try:
            # Import GraphFlow components  
            from autogen_agentchat.teams import DiGraphBuilder, GraphFlow
            from autogen_agentchat.conditions import MaxMessageTermination, TextMentionTermination
            from autogen_agentchat.agents import MessageFilterAgent, MessageFilterConfig, PerSourceFilter
            
            # Get the team for this workflow
            team = AgentTeam.get_by_id(workflow.team_id)
            if not team:
                return {"success": False, "error": "Workflow team not found"}
            
            # Parse the workflow graph
            graph_data = workflow.graph or {}
            nodes = graph_data.get('nodes', [])
            edges = graph_data.get('edges', [])
            workflow_config = graph_data.get('config', {})
            
            if not nodes:
                return {"success": False, "error": "Workflow has no nodes defined"}
            
            monitor.log_event('graphflow_start', 'orchestrator', {
                "workflow_id": workflow.id,
                "nodes_count": len(nodes),
                "edges_count": len(edges),
                "config": workflow_config
            })
            
            # Build agents for the team
            agents_with_wb, _ = await self._build_agents_team(team, monitor=monitor)
            
            # Create a mapping from agent names to agent objects
            agent_map = {}
            for agent, wb in agents_with_wb:
                agent_name = getattr(agent, 'name', None)
                if agent_name:
                    agent_map[agent_name] = agent
            
            # Start all workbenches
            async def execute_graphflow():
                for _, wb in agents_with_wb:
                    await wb.__aenter__()
                
                try:
                    # Build the DiGraph using DiGraphBuilder
                    builder = DiGraphBuilder()
                    graph_agents = []
                    
                    # Add nodes to builder and create filtered agents if needed
                    for node in nodes:
                        agent_name = node.get('agent')
                        if not agent_name or agent_name not in agent_map:
                            monitor.log_event('graphflow_skip_node', 'orchestrator', {
                                "node_id": node.get('id'),
                                "reason": "agent_not_found",
                                "agent_name": agent_name
                            })
                            continue
                        
                        base_agent = agent_map[agent_name]
                        
                        # Check if this node needs message filtering
                        message_filter = node.get('message_filter')
                        if message_filter and message_filter.get('enabled', False):
                            # Create filtered agent
                            per_source_filters = []
                            for filter_rule in message_filter.get('filters', []):
                                per_source_filters.append(PerSourceFilter(
                                    source=filter_rule.get('source'),
                                    position=filter_rule.get('position', 'last'),
                                    count=filter_rule.get('count', 1)
                                ))
                            
                            if per_source_filters:
                                filtered_agent = MessageFilterAgent(
                                    name=agent_name,
                                    wrapped_agent=base_agent,
                                    filter=MessageFilterConfig(per_source=per_source_filters)
                                )
                                graph_agents.append(filtered_agent)
                                builder.add_node(filtered_agent)
                                monitor.log_event('graphflow_filtered_agent', 'orchestrator', {
                                    "agent_name": agent_name,
                                    "filters": len(per_source_filters)
                                })
                            else:
                                graph_agents.append(base_agent)
                                builder.add_node(base_agent)
                        else:
                            graph_agents.append(base_agent)
                            builder.add_node(base_agent)
                    
                    # Add edges to builder with conditions and activation groups
                    for edge in edges:
                        from_node_id = edge.get('from')
                        to_node_id = edge.get('to')
                        
                        # Find corresponding agents
                        from_node = next((n for n in nodes if n.get('id') == from_node_id), None)
                        to_node = next((n for n in nodes if n.get('id') == to_node_id), None)
                        
                        if not from_node or not to_node:
                            continue
                            
                        from_agent_name = from_node.get('agent')
                        to_agent_name = to_node.get('agent')
                        
                        if not from_agent_name or not to_agent_name:
                            continue
                            
                        from_agent = next((a for a in graph_agents if getattr(a, 'name', '') == from_agent_name), None)
                        to_agent = next((a for a in graph_agents if getattr(a, 'name', '') == to_agent_name), None)
                        
                        if not from_agent or not to_agent:
                            continue
                        
                        # Build edge with optional condition and activation settings
                        edge_kwargs = {}
                        
                        # Add condition if specified
                        condition = edge.get('condition')
                        if condition:
                            if isinstance(condition, str):
                                # String-based condition (check if text contains the condition)
                                edge_kwargs['condition'] = lambda msg, cond=condition: cond in msg.to_model_text()
                            elif isinstance(condition, dict):
                                condition_type = condition.get('type')
                                if condition_type == 'text_contains':
                                    text = condition.get('text', '')
                                    edge_kwargs['condition'] = lambda msg, txt=text: txt in msg.to_model_text()
                                elif condition_type == 'lambda':
                                    # For safety, only allow simple predefined conditions
                                    text = condition.get('text', '')
                                    edge_kwargs['condition'] = lambda msg, txt=text: txt in msg.to_model_text()
                        
                        # Add activation group and condition
                        activation_group = edge.get('activation_group')
                        if activation_group:
                            edge_kwargs['activation_group'] = activation_group
                            
                        activation_condition = edge.get('activation_condition', 'all')
                        if activation_condition in ['all', 'any']:
                            edge_kwargs['activation_condition'] = activation_condition
                        
                        builder.add_edge(from_agent, to_agent, **edge_kwargs)
                    
                    # Set entry point if specified
                    entry_point_agent = None
                    entry_point_config = workflow_config.get('entry_point')
                    if entry_point_config:
                        entry_agent_name = entry_point_config
                        entry_point_agent = next((a for a in graph_agents if getattr(a, 'name', '') == entry_agent_name), None)
                        if entry_point_agent:
                            builder.set_entry_point(entry_point_agent)
                    
                    # Build the graph
                    digraph = builder.build()
                    
                    # Create termination condition
                    termination_condition = None
                    termination_config = workflow_config.get('termination', {})
                    termination_type = termination_config.get('type', 'max_message')
                    
                    if termination_type == 'max_message':
                        max_messages = termination_config.get('max_messages', 20)
                        termination_condition = MaxMessageTermination(max_messages)
                    elif termination_type == 'text_mention':
                        termination_text = termination_config.get('text', 'TERMINATE')
                        termination_condition = TextMentionTermination(termination_text)
                    else:
                        # Default termination
                        termination_condition = MaxMessageTermination(20)
                    
                    # Create GraphFlow
                    flow = GraphFlow(
                        participants=graph_agents,
                        graph=digraph,
                        termination_condition=termination_condition
                    )
                    
                    monitor.log_event('graphflow_created', 'orchestrator', {
                        "participants": len(graph_agents),
                        "termination_type": termination_type
                    })
                    
                    # Run the workflow
                    monitor.log_event('graphflow_execution_start', 'orchestrator', {"task": input_text})
                    
                    with _Timer() as timer:
                        result = await flow.run(task=input_text)
                    
                    # Extract final result
                    final_text = self._extract_final_text(result)
                    
                    monitor.log_event('graphflow_execution_complete', 'orchestrator', {
                        "elapsed_sec": getattr(timer, 'elapsed', None),
                        "final_result_preview": final_text,
                        "stop_reason": getattr(result, 'stop_reason', None)
                    })
                    
                    return {
                        "success": True,
                        "reply": final_text,
                        "run_id": run_id
                    }
                    
                finally:
                    # Clean up workbenches
                    for _, wb in agents_with_wb:
                        try:
                            await wb.__aexit__(None, None, None)
                        except Exception:
                            pass
            
            result = await execute_graphflow()
            monitor.end_run('success', final_reply=result.get('reply', ''))
            return result
            
        except Exception as e:
            tb = traceback.format_exc()
            logger.error(f"GraphFlow workflow run failed: {e}\n{tb}")
            monitor.log_event('error', 'orchestrator', {"error": str(e), "trace": tb})
            monitor.end_run('error', error=str(e))
            return {"success": False, "error": str(e), "trace": tb, "run_id": run_id}
        finally:
            # Cleanup AutoGen logging
            self._cleanup_autogen_logging()


