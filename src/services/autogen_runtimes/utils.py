"""
Utilities for AutoGen Core Runtime - Pure orchestrator-based approach.
"""
import logging
import traceback
from typing import Any, Dict, Optional

from src.models.agent_team import AgentTeam
from src.models.execution_method import ExecutionMethod
from src.services.run_monitor import RunMonitor

logger = logging.getLogger(__name__)

async def get_agent_team_response(
    team: AgentTeam, 
    task: str, 
    monitor: Optional[RunMonitor] = None,
    pattern_hint: str = None
) -> Dict[str, Any]:
    """
    Get response from agent team using proper AutoGen orchestrator.
    NO hardcoded logic - everything driven by database configuration.
    """
    try:
        # Use the proper AutoGen orchestrator approach
        from src.services.autogen_orchestrator import AutoGenOrchestrator
        orchestrator = AutoGenOrchestrator()
        
        # Let orchestrator handle everything - team building, MCP integration, etc.
        result = await orchestrator.run_team(team, task, context=None)
        
        if monitor:
            monitor.log_event('team_response_completed', 'utils', {
                "success": result.get('success', False),
                "pattern_hint": pattern_hint
            })
        
        return result
        
    except Exception as e:
        logger.error(f"Team response failed: {e}\n{traceback.format_exc()}")
        if monitor:
            monitor.log_event('error', 'utils', {'error': str(e), 'trace': traceback.format_exc()})
        return {
            "success": False,
            "error": str(e),
            "trace": traceback.format_exc()
        }

async def get_agent_method_response(
    method: ExecutionMethod,
    task: str,
    monitor: Optional[RunMonitor] = None
) -> Dict[str, Any]:
    """
    Get response using execution method (pattern) via proper AutoGen orchestrator.
    NO hardcoded logic - everything driven by database configuration.
    """
    try:
        # Use the proper AutoGen orchestrator approach
        from src.services.autogen_orchestrator import AutoGenOrchestrator
        orchestrator = AutoGenOrchestrator()
        
        # Let orchestrator handle everything - method patterns, team building, MCP integration, etc.
        result = await orchestrator.run_method(method, task, context=None)
        
        if monitor:
            monitor.log_event('method_response_completed', 'utils', {
                "success": result.get('success', False),
                "method_type": method.type if method else None
            })
        
        return result
        
    except Exception as e:
        logger.error(f"Method response failed: {e}\n{traceback.format_exc()}")
        if monitor:
            monitor.log_event('error', 'utils', {'error': str(e), 'trace': traceback.format_exc()})
        return {
            "success": False,
            "error": str(e),
            "trace": traceback.format_exc()
        }

def extract_text_response(result: Dict[str, Any]) -> str:
    """Extract text response from orchestrator result."""
    if not result:
        return "No response available."
    
    if not result.get('success', False):
        error = result.get('error', 'Unknown error')
        return f"Error: {error}"
    
    reply = result.get('reply', '')
    if isinstance(reply, str) and reply.strip():
        return reply.strip()
    
    return "No response content available."

# Legacy functions for backward compatibility - redirect to orchestrator
async def _build_agents_with_workbenches(team: AgentTeam, monitor: Optional[RunMonitor] = None):
    """Legacy function - use orchestrator instead."""
    logger.warning("_build_agents_with_workbenches is deprecated, use AutoGenOrchestrator._build_agents_team")
    from src.services.autogen_orchestrator import AutoGenOrchestrator
    orchestrator = AutoGenOrchestrator()
    return await orchestrator._build_agents_team(team, monitor)

async def _get_agent_response_with_tools(
    agent_spec: Dict[str, Any],
    workbench: Any,
    task: str,
    agent_name: str,
    monitor: Optional[RunMonitor] = None,
    conversation_history: Optional[list] = None,
) -> str:
    """Legacy function - use orchestrator instead."""
    logger.warning("_get_agent_response_with_tools is deprecated, use AutoGenOrchestrator")
    # This should not be used - patterns should use orchestrator directly
    return f"Legacy function called for {agent_name}. Use AutoGenOrchestrator instead."

async def _get_agent_response_with_mcp_tools(
    agent_spec: Dict[str, Any],
    workbench: Any,
    task: str,
    agent_name: str,
    monitor: Optional[RunMonitor] = None,
) -> str:
    """Legacy function - use orchestrator instead."""
    logger.warning("_get_agent_response_with_mcp_tools is deprecated, use AutoGenOrchestrator")
    # This should not be used - patterns should use orchestrator directly
    return f"Legacy function called for {agent_name}. Use AutoGenOrchestrator instead."
