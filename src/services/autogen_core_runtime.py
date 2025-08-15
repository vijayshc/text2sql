"""
AutoGen Core Runtime implementation for various execution patterns.
Provides standardized interfaces for different AutoGen execution methods.
"""
import asyncio
import json
import logging
import os
import re
import time as _time
import traceback
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Union

from src.models.agent_team import AgentTeam
from src.models.execution_method import ExecutionMethod
from src.services.run_monitor import RunMonitor

# Import the new runtime handlers
from src.services.autogen_runtimes.reflection import run_reflection
from src.services.autogen_runtimes.sequential import run_sequential
from src.services.autogen_runtimes.debate import run_debate
from src.services.autogen_runtimes.concurrent import run_concurrent
from src.services.autogen_runtimes.group_chat import run_group_chat
from src.services.autogen_runtimes.handoffs import run_handoffs
from src.services.autogen_runtimes.mixture import run_mixture
from src.services.autogen_runtimes.code_exec_groupchat import run_code_exec_groupchat


# Set up logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class AutoGenCoreRuntime:
    """Handles AutoGen Core runtime operations for various execution patterns."""
    
    def __init__(self):
        self.session_id = None
        logger.info("AutoGenCoreRuntime initialized")
    
    async def run_reflection(self, team: AgentTeam, method: ExecutionMethod, task: str, monitor: Optional[RunMonitor] = None) -> Dict[str, Any]:
        """Run reflection pattern using AutoGen Core runtime with tool integration."""
        try:
            return await run_reflection(team, method, task, monitor)
        except Exception as e:
            logger.error(f"Reflection pattern failed: {e}\n{traceback.format_exc()}")
            return {"success": False, "error": str(e), "trace": traceback.format_exc()}
    
    async def run_sequential(self, team: AgentTeam, method: ExecutionMethod, task: str, monitor: Optional[RunMonitor] = None) -> Dict[str, Any]:
        """Run sequential workflow pattern with tool integration."""
        try:
            return await run_sequential(team, method, task, monitor)
        except Exception as e:
            logger.error(f"Sequential pattern failed: {e}\n{traceback.format_exc()}")
            return {"success": False, "error": str(e), "trace": traceback.format_exc()}
    
    async def run_debate(self, team: AgentTeam, method: ExecutionMethod, task: str, monitor: Optional[RunMonitor] = None) -> Dict[str, Any]:
        """Run multi-agent debate pattern."""
        try:
            return await run_debate(team, method, task, monitor)
        except Exception as e:
            logger.error(f"Debate pattern failed: {e}\n{traceback.format_exc()}")
            return {"success": False, "error": str(e), "trace": traceback.format_exc()}
    
    async def run_concurrent(self, team: AgentTeam, method: ExecutionMethod, task: str, monitor: Optional[RunMonitor] = None) -> Dict[str, Any]:
        """Run concurrent agents pattern."""
        try:
            return await run_concurrent(team, method, task, monitor)
        except Exception as e:
            logger.error(f"Concurrent pattern failed: {e}\n{traceback.format_exc()}")
            return {"success": False, "error": str(e), "trace": traceback.format_exc()}
    
    async def run_group_chat(self, team: AgentTeam, method: ExecutionMethod, task: str, monitor: Optional[RunMonitor] = None) -> Dict[str, Any]:
        """Run group chat pattern."""
        try:
            return await run_group_chat(team, method, task, monitor)
        except Exception as e:
            logger.error(f"Group chat pattern failed: {e}\n{traceback.format_exc()}")
            return {"success": False, "error": str(e), "trace": traceback.format_exc()}
    
    async def run_handoffs(self, team: AgentTeam, method: ExecutionMethod, task: str, monitor: Optional[RunMonitor] = None) -> Dict[str, Any]:
        """Run handoffs pattern."""
        try:
            return await run_handoffs(team, method, task, monitor)
        except Exception as e:
            logger.error(f"Handoffs pattern failed: {e}\n{traceback.format_exc()}")
            return {"success": False, "error": str(e), "trace": traceback.format_exc()}
    
    async def run_mixture(self, team: AgentTeam, method: ExecutionMethod, task: str, monitor: Optional[RunMonitor] = None) -> Dict[str, Any]:
        """Run mixture of agents pattern with tool integration."""
        try:
            return await run_mixture(team, method, task, monitor)
        except Exception as e:
            logger.error(f"Mixture pattern failed: {e}\n{traceback.format_exc()}")
            return {"success": False, "error": str(e), "trace": traceback.format_exc()}
    
    async def run_code_exec_groupchat(self, team: AgentTeam, method: ExecutionMethod, task: str, monitor: Optional[RunMonitor] = None) -> Dict[str, Any]:
        """Run code execution group chat pattern."""
        try:
            return await run_code_exec_groupchat(team, method, task, monitor)
        except Exception as e:
            logger.error(f"Code exec groupchat pattern failed: {e}\n{traceback.format_exc()}")
            return {"success": False, "error": str(e), "trace": traceback.format_exc()}
