"""
Handles the concurrent execution pattern using proper AutoGen integration.
"""
import asyncio
import logging
import traceback
from typing import Any, Dict, Optional

from src.models.agent_team import AgentTeam
from src.models.execution_method import ExecutionMethod
from src.services.run_monitor import RunMonitor

logger = logging.getLogger(__name__)

async def run_concurrent(team: AgentTeam, method: ExecutionMethod, task: str, monitor: Optional[RunMonitor] = None) -> Dict[str, Any]:
    """
    Run concurrent pattern using AutoGen agents.
    
    Concurrent Pattern:
    1. All agents work simultaneously on the same task
    2. Each agent works independently without seeing others' work
    3. Results are combined into a final synthesized response
    """
    try:
        logger.info(f"Starting concurrent pattern execution for task: {task[:100]}...")
        
        if monitor:
            monitor.log_event('pattern_start', 'concurrent', {'task': task[:100]})
        
        # Use AutoGen orchestrator approach for proper MCP integration
        from src.services.autogen_orchestrator import AutoGenOrchestrator
        orchestrator = AutoGenOrchestrator()
        
        # Build agents with workbenches using orchestrator approach
        agents_with_wb, _ = await orchestrator._build_agents_team(team, monitor=monitor)
        
        if len(agents_with_wb) < 2:
            logger.warning("Concurrent pattern requires at least 2 agents")
            if monitor:
                monitor.log_event('error', 'concurrent', {'error': 'Insufficient agents', 'required': 2, 'found': len(agents_with_wb)})
            return {"success": False, "error": "Concurrent pattern requires at least 2 agents"}
        
        agent_names = [agent.name for agent, _ in agents_with_wb]
        
        if monitor:
            monitor.log_event('status', 'concurrent', {
                'message': 'concurrent pattern configured with AutoGen', 
                'agent_count': len(agents_with_wb),
                'agents': agent_names
            })
        
        # Start all workbenches
        async def execute_concurrent_pattern():
            for _, wb in agents_with_wb:
                await wb.__aenter__()
            
            try:
                # Concurrent pattern execution: All agents work simultaneously
                logger.info(f"🎯 CONCURRENT: {len(agents_with_wb)} agents working simultaneously")
                
                async def run_single_agent(agent_wb_pair, task_input):
                    """Run a single agent and return its response."""
                    agent, wb = agent_wb_pair
                    agent_name = agent.name
                    
                    try:
                        if monitor:
                            monitor.log_event('status', 'concurrent', {
                                'message': 'agent starting concurrent execution', 
                                'agent': agent_name
                            })
                        
                        # Each agent works on the task independently
                        result = await agent.run(task=task_input)
                        response = orchestrator._extract_final_text(result)
                        
                        logger.info(f"Agent {agent_name} completed concurrent execution")
                        
                        if monitor:
                            monitor.log_event('status', 'concurrent', {
                                'message': 'agent completed concurrent execution', 
                                'agent': agent_name,
                                'response_length': len(response)
                            })
                        
                        return {
                            'agent': agent_name,
                            'response': response,
                            'success': True
                        }
                        
                    except Exception as e:
                        logger.error(f"Agent {agent_name} failed during concurrent execution: {e}")
                        if monitor:
                            monitor.log_event('error', 'concurrent', {
                                'message': 'agent failed during concurrent execution',
                                'agent': agent_name,
                                'error': str(e)
                            })
                        return {
                            'agent': agent_name,
                            'response': f"Error: {str(e)}",
                            'success': False
                        }
                
                # Execute all agents concurrently
                if monitor:
                    monitor.log_event('status', 'concurrent', {
                        'message': 'starting concurrent execution', 
                        'concurrent_agents': len(agents_with_wb)
                    })
                
                concurrent_tasks = [
                    run_single_agent(agent_wb_pair, task) 
                    for agent_wb_pair in agents_with_wb
                ]
                
                responses = await asyncio.gather(*concurrent_tasks, return_exceptions=True)
                
                if monitor:
                    monitor.log_event('status', 'concurrent', {
                        'message': 'concurrent execution completed', 
                        'responses_received': len(responses)
                    })
                
                # Process responses
                valid_responses = []
                failed_count = 0
                
                for response in responses:
                    if isinstance(response, Exception):
                        logger.error(f"Concurrent task failed: {response}")
                        failed_count += 1
                    elif isinstance(response, dict):
                        if response.get('success', False):
                            valid_responses.append(response)
                        else:
                            failed_count += 1
                    else:
                        failed_count += 1
                
                if not valid_responses:
                    if monitor:
                        monitor.log_event('error', 'concurrent', {'error': 'All agents failed', 'failed_count': failed_count})
                    return {
                        "success": False,
                        "error": "All agents failed to execute",
                        "pattern": "concurrent"
                    }
                
                # Synthesize all concurrent responses into final result
                if valid_responses:
                    synthesis_task = f"""
Task: {task}

I have received the following responses from agents working concurrently on the same task:

{chr(10).join([f"**{resp['agent']}:** {resp['response']}" for resp in valid_responses])}

Please synthesize these concurrent responses into a single, comprehensive answer that combines the best insights from each agent. Focus on providing a complete, accurate, and helpful response to the original task.
"""
                    
                    # Use the first agent to synthesize
                    synthesizer = agents_with_wb[0][0]
                    synthesis_result = await synthesizer.run(task=synthesis_task)
                    final_response = orchestrator._extract_final_text(synthesis_result)
                    
                    if monitor:
                        monitor.log_event('status', 'concurrent', {
                            'message': 'synthesis completed',
                            'synthesizer': synthesizer.name,
                            'valid_responses': len(valid_responses),
                            'failed_responses': failed_count
                        })
                else:
                    final_response = "All concurrent agents failed to provide responses."
                
                return {
                    "success": True,
                    "reply": final_response,
                    "pattern": "concurrent",
                    "agents_used": agent_names,
                    "execution_steps": [
                        f"All {len(agents_with_wb)} agents executed concurrently",
                        f"{len(valid_responses)} agents succeeded, {failed_count} failed",
                        "Responses synthesized into final answer"
                    ],
                    "concurrent_responses": valid_responses
                }
                
            finally:
                # Clean up workbenches
                for _, wb in agents_with_wb:
                    try:
                        await wb.__aexit__(None, None, None)
                    except Exception:
                        pass
        
        result = await execute_concurrent_pattern()
        
        if monitor:
            monitor.log_event('pattern_complete', 'concurrent', {
                'success': result.get('success', False),
                'agents_used': result.get('agents_used', [])
            })
        
        return result
        
    except Exception as e:
        logger.error(f"Concurrent pattern execution failed: {e}\n{traceback.format_exc()}")
        if monitor:
            monitor.log_event('error', 'concurrent', {'error': str(e), 'trace': traceback.format_exc()})
        return {
            "success": False,
            "error": str(e),
            "pattern": "concurrent",
            "trace": traceback.format_exc()
        }
