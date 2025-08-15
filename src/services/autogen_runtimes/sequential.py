"""
Handles the sequential execution pattern using proper AutoGen integration.
"""
import logging
import traceback
from typing import Any, Dict, Optional

from src.models.agent_team import AgentTeam
from src.models.execution_method import ExecutionMethod
from src.services.run_monitor import RunMonitor

logger = logging.getLogger(__name__)

async def run_sequential(team: AgentTeam, method: ExecutionMethod, task: str, monitor: Optional[RunMonitor] = None) -> Dict[str, Any]:
    """
    Run sequential pattern using AutoGen agents.
    
    Sequential Pattern:
    1. Agents execute one after another in sequence
    2. Output from one agent becomes input for the next
    3. Final agent produces the end result
    """
    try:
        logger.info(f"Starting sequential pattern execution for task: {task[:100]}...")
        
        if monitor:
            monitor.log_event('pattern_start', 'sequential', {'task': task[:100]})
        
        # Use AutoGen orchestrator approach for proper MCP integration
        from src.services.autogen_orchestrator import AutoGenOrchestrator
        orchestrator = AutoGenOrchestrator()
        
        # Build agents with workbenches using orchestrator approach
        agents_with_wb, _ = await orchestrator._build_agents_team(team, monitor=monitor)
        
        if len(agents_with_wb) < 2:
            logger.warning("Sequential pattern requires at least 2 agents")
            if monitor:
                monitor.log_event('error', 'sequential', {'error': 'Insufficient agents', 'required': 2, 'found': len(agents_with_wb)})
            return {"success": False, "error": "Sequential pattern requires at least 2 agents"}
        
        agent_names = [agent.name for agent, _ in agents_with_wb]
        
        if monitor:
            monitor.log_event('status', 'sequential', {
                'message': 'sequential pattern configured with AutoGen', 
                'agent_count': len(agents_with_wb),
                'sequence': agent_names
            })
        
        # Start all workbenches
        async def execute_sequential_pattern():
            for _, wb in agents_with_wb:
                await wb.__aenter__()
            
            try:
                # Sequential pattern execution: One agent after another
                current_input = task
                execution_steps = []
                agent_outputs = []
                
                logger.info(f"🎯 SEQUENTIAL: {len(agents_with_wb)} agents executing in sequence")
                
                for i, (agent, wb) in enumerate(agents_with_wb):
                    agent_name = agent.name
                    step_num = i + 1
                    
                    try:
                        logger.info(f"Executing step {step_num}/{len(agents_with_wb)} with agent: {agent_name}")
                        
                        if monitor:
                            monitor.log_event('status', 'sequential', {
                                'message': f'starting step {step_num}', 
                                'agent': agent_name,
                                'step': step_num,
                                'total_steps': len(agents_with_wb)
                            })
                        
                        # Provide context about the sequential workflow
                        if step_num == 1:
                            # First agent gets the original task
                            agent_task = current_input
                        else:
                            # Subsequent agents get context about previous work
                            agent_task = f"""This is step {step_num} of a sequential workflow.

Original task: {task}

Previous agent completed step {step_num-1} with this result:
{current_input}

Please build upon this work and continue the task. Provide your contribution to solving the original task."""
                        
                        # Agent processes the current input
                        result = await agent.run(task=agent_task)
                        response = orchestrator._extract_final_text(result)
                        
                        agent_outputs.append({
                            'step': step_num,
                            'agent': agent_name,
                            'input': current_input,
                            'output': response
                        })
                        
                        # Output becomes input for next agent
                        current_input = response
                        execution_steps.append(f"Step {step_num}: {agent_name} processed and refined the task")
                        
                        logger.info(f"Agent {agent_name} completed step {step_num}")
                        
                        if monitor:
                            monitor.log_event('status', 'sequential', {
                                'message': f'step {step_num} completed', 
                                'agent': agent_name,
                                'output_length': len(response)
                            })
                            
                    except Exception as e:
                        logger.error(f"Agent {agent_name} failed in step {step_num}: {e}")
                        if monitor:
                            monitor.log_event('error', 'sequential', {
                                'message': f'agent failed in step {step_num}',
                                'agent': agent_name,
                                'step': step_num,
                                'error': str(e)
                            })
                        # Continue with error message as input for next agent
                        error_msg = f"Error in step {step_num} with {agent_name}: {str(e)}"
                        current_input = error_msg
                        execution_steps.append(f"Step {step_num}: {agent_name} encountered an error")
                        agent_outputs.append({
                            'step': step_num,
                            'agent': agent_name,
                            'input': current_input,
                            'output': error_msg,
                            'error': True
                        })
                
                return {
                    "success": True,
                    "reply": current_input,  # Final output from last agent
                    "pattern": "sequential",
                    "agents_used": agent_names,
                    "execution_steps": execution_steps,
                    "sequential_outputs": agent_outputs
                }
                
            finally:
                # Clean up workbenches
                for _, wb in agents_with_wb:
                    try:
                        await wb.__aexit__(None, None, None)
                    except Exception:
                        pass
        
        result = await execute_sequential_pattern()
        
        if monitor:
            monitor.log_event('pattern_complete', 'sequential', {
                'success': result.get('success', False),
                'agents_used': result.get('agents_used', [])
            })
        
        return result
        
    except Exception as e:
        logger.error(f"Sequential pattern execution failed: {e}\n{traceback.format_exc()}")
        if monitor:
            monitor.log_event('error', 'sequential', {'error': str(e), 'trace': traceback.format_exc()})
        return {
            "success": False,
            "error": str(e),
            "pattern": "sequential",
            "trace": traceback.format_exc()
        }
