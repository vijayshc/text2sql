"""
Handles the handoffs execution pattern using proper AutoGen integration.
"""
import logging
import traceback
from typing import Any, Dict, Optional, List

from src.models.agent_team import AgentTeam
from src.models.execution_method import ExecutionMethod
from src.services.run_monitor import RunMonitor

logger = logging.getLogger(__name__)

async def run_handoffs(team: AgentTeam, method: ExecutionMethod, task: str, monitor: Optional[RunMonitor] = None) -> Dict[str, Any]:
    """
    Run handoffs pattern using AutoGen agents.
    
    Handoffs Pattern:
    1. Task is passed from one agent to another in a chain
    2. Each agent adds value and refines the work
    3. Explicit handoff decisions determine the next agent
    4. Final agent produces the complete result
    """
    try:
        logger.info(f"Starting handoffs pattern execution for task: {task[:100]}...")
        
        if monitor:
            monitor.log_event('pattern_start', 'handoffs', {'task': task[:100]})
        
        # Use AutoGen orchestrator approach for proper MCP integration
        from src.services.autogen_orchestrator import AutoGenOrchestrator
        orchestrator = AutoGenOrchestrator()
        
        # Build agents with workbenches using orchestrator approach
        agents_with_wb, _ = await orchestrator._build_agents_team(team, monitor=monitor)
        
        if len(agents_with_wb) < 2:
            logger.warning("Handoffs pattern requires at least 2 agents")
            if monitor:
                monitor.log_event('error', 'handoffs', {'error': 'Insufficient agents', 'required': 2, 'found': len(agents_with_wb)})
            return {"success": False, "error": "Handoffs pattern requires at least 2 agents"}
        
        agent_names = [agent.name for agent, _ in agents_with_wb]
        
        if monitor:
            monitor.log_event('status', 'handoffs', {
                'message': 'handoffs configured with AutoGen', 
                'agent_count': len(agents_with_wb),
                'handoff_chain': agent_names
            })
        
        # Start all workbenches
        async def execute_handoffs():
            for _, wb in agents_with_wb:
                await wb.__aenter__()
            
            try:
                # Handoffs execution
                current_work = task
                handoff_history = []
                agents_used = []
                
                logger.info(f"🎯 HANDOFFS: {len(agents_with_wb)} agents in handoff chain")
                
                for i, (agent, wb) in enumerate(agents_with_wb):
                    agent_name = agent.name
                    handoff_num = i + 1
                    
                    try:
                        logger.info(f"Handoff {handoff_num}/{len(agents_with_wb)}: {agent_name} receiving work")
                        
                        if monitor:
                            monitor.log_event('status', 'handoffs', {
                                'message': f'handoff {handoff_num} starting', 
                                'agent': agent_name,
                                'handoff': handoff_num,
                                'total_handoffs': len(agents_with_wb)
                            })
                        
                        # Build handoff context for the agent
                        if handoff_num == 1:
                            # First agent receives the original task
                            agent_task = f"""You are the first agent in a handoff chain of {len(agents_with_wb)} agents.

Original task: {task}

Please work on this task and prepare your results for handoff to the next agent. Provide your contribution and indicate what aspects should be refined or completed by subsequent agents."""
                        else:
                            # Subsequent agents receive context from previous handoffs
                            previous_work = "\n\n".join([
                                f"**{entry['agent']}** (Handoff {entry['handoff']}):\n{entry['work']}" 
                                for entry in handoff_history
                            ])
                            
                            agent_task = f"""You are agent {handoff_num} of {len(agents_with_wb)} in a handoff chain.

Original task: {task}

Work received from previous agents:
{previous_work}

Current work state: {current_work}

Please review the previous work, add your expertise, and continue refining the solution. If you are the final agent, provide a complete, polished result."""
                        
                        # Agent processes the handoff
                        result = await agent.run(task=agent_task)
                        response = orchestrator._extract_final_text(result)
                        
                        # Record handoff
                        handoff_entry = {
                            'handoff': handoff_num,
                            'agent': agent_name,
                            'previous_agent': handoff_history[-1]['agent'] if handoff_history else 'User',
                            'work': response,
                            'task_state': current_work
                        }
                        handoff_history.append(handoff_entry)
                        agents_used.append(agent_name)
                        
                        # Update current work state
                        current_work = response
                        
                        logger.info(f"Handoff {handoff_num}: {agent_name} completed work")
                        
                        if monitor:
                            monitor.log_event('status', 'handoffs', {
                                'message': f'handoff {handoff_num} completed', 
                                'agent': agent_name,
                                'output_length': len(response)
                            })
                        
                        # Check if agent indicates work is complete (for early termination)
                        completion_indicators = ['task completed', 'work finished', 'final result', 'ready for delivery']
                        if any(indicator in response.lower() for indicator in completion_indicators) and handoff_num < len(agents_with_wb):
                            logger.info(f"Agent {agent_name} indicated work completion at handoff {handoff_num}")
                            if monitor:
                                monitor.log_event('status', 'handoffs', {
                                    'message': 'early completion indicated', 
                                    'agent': agent_name,
                                    'handoff': handoff_num
                                })
                            break
                            
                    except Exception as e:
                        logger.error(f"Agent {agent_name} failed in handoff {handoff_num}: {e}")
                        if monitor:
                            monitor.log_event('error', 'handoffs', {
                                'message': f'agent failed in handoff {handoff_num}',
                                'agent': agent_name,
                                'handoff': handoff_num,
                                'error': str(e)
                            })
                        # Continue handoff chain with error message
                        error_msg = f"Error in handoff {handoff_num} with {agent_name}: {str(e)}"
                        handoff_entry = {
                            'handoff': handoff_num,
                            'agent': agent_name,
                            'previous_agent': handoff_history[-1]['agent'] if handoff_history else 'User',
                            'work': error_msg,
                            'task_state': current_work,
                            'error': True
                        }
                        handoff_history.append(handoff_entry)
                        agents_used.append(agent_name)
                        current_work = error_msg
                
                return {
                    "success": True,
                    "reply": current_work,  # Final result from last successful handoff
                    "pattern": "handoffs",
                    "agents_used": agents_used,
                    "execution_steps": [f"Completed {len(handoff_history)} handoffs through agent chain"],
                    "handoff_history": handoff_history,
                    "total_handoffs": len(handoff_history)
                }
                
            finally:
                # Clean up workbenches
                for _, wb in agents_with_wb:
                    try:
                        await wb.__aexit__(None, None, None)
                    except Exception:
                        pass
        
        result = await execute_handoffs()
        
        if monitor:
            monitor.log_event('pattern_complete', 'handoffs', {
                'success': result.get('success', False),
                'agents_used': result.get('agents_used', []),
                'total_handoffs': result.get('total_handoffs', 0)
            })
        
        return result
        
    except Exception as e:
        logger.error(f"Handoffs pattern execution failed: {e}\n{traceback.format_exc()}")
        if monitor:
            monitor.log_event('error', 'handoffs', {'error': str(e), 'trace': traceback.format_exc()})
        return {
            "success": False,
            "error": str(e),
            "pattern": "handoffs",
            "trace": traceback.format_exc()
        }
