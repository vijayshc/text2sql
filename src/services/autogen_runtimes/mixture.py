"""
Handles the mixture of agents execution pattern using proper AutoGen integration.
"""
import logging
import traceback
from typing import Any, Dict, Optional

from src.models.agent_team import AgentTeam
from src.models.execution_method import ExecutionMethod
from src.services.run_monitor import RunMonitor

logger = logging.getLogger(__name__)

async def run_mixture(team: AgentTeam, method: ExecutionMethod, task: str, monitor: Optional[RunMonitor] = None) -> Dict[str, Any]:
    """
    Run mixture of agents pattern.
    
    Mixture Pattern:
    1. All agents work independently on the task
    2. Each agent provides their unique perspective/approach  
    3. Results are combined into a final synthesized response
    """
    try:
        logger.info(f"Starting mixture pattern execution for task: {task[:100]}...")
        
        if monitor:
            monitor.log_event('pattern_start', 'mixture', {'task': task[:100]})
        
        # Use AutoGen orchestrator approach for proper MCP integration
        from src.services.autogen_orchestrator import AutoGenOrchestrator
        orchestrator = AutoGenOrchestrator()
        
        # Build agents with workbenches using orchestrator approach
        agents_with_wb, _ = await orchestrator._build_agents_team(team, monitor=monitor)
        
        if len(agents_with_wb) < 2:
            logger.warning("Mixture pattern requires at least 2 agents")
            if monitor:
                monitor.log_event('error', 'mixture', {'error': 'Insufficient agents', 'required': 2, 'found': len(agents_with_wb)})
            return {"success": False, "error": "Mixture pattern requires at least 2 agents"}
        
        agent_names = [agent.name for agent, _ in agents_with_wb]
        
        if monitor:
            monitor.log_event('status', 'mixture', {
                'message': 'mixture pattern configured with AutoGen', 
                'agent_count': len(agents_with_wb),
                'agents': agent_names
            })
        
        # Start all workbenches
        async def execute_mixture_pattern():
            for _, wb in agents_with_wb:
                await wb.__aenter__()
            
            try:
                # Mixture pattern execution: Each agent works independently
                independent_responses = []
                
                logger.info(f"🎯 MIXTURE: {len(agents_with_wb)} agents responding independently")
                
                for i, (agent, wb) in enumerate(agents_with_wb):
                    agent_name = agent.name
                    
                    try:
                        if monitor:
                            monitor.log_event('status', 'mixture', {
                                'message': 'agent starting independent response', 
                                'agent': agent_name
                            })
                        
                        # Each agent responds to the task independently
                        result = await agent.run(task=task)
                        response = orchestrator._extract_final_text(result)
                        
                        independent_responses.append({
                            'agent': agent_name,
                            'response': response
                        })
                        
                        logger.info(f"Agent {agent_name} completed independent response")
                        
                        if monitor:
                            monitor.log_event('status', 'mixture', {
                                'message': 'agent completed independent response', 
                                'agent': agent_name,
                                'response_length': len(response)
                            })
                            
                    except Exception as e:
                        logger.error(f"Agent {agent_name} failed: {e}")
                        if monitor:
                            monitor.log_event('error', 'mixture', {
                                'message': 'agent failed',
                                'agent': agent_name,
                                'error': str(e)
                            })
                        independent_responses.append({
                            'agent': agent_name,
                            'response': f"Error: {str(e)}"
                        })
                
                # Synthesize all responses into final result
                if independent_responses:
                    synthesis_task = f"""
Task: {task}

I have received the following responses from different specialist agents:

{chr(10).join([f"**{resp['agent']}:** {resp['response']}" for resp in independent_responses])}

Please synthesize these responses into a single, comprehensive answer that combines the best insights from each agent. Focus on providing a complete, accurate, and helpful response to the original task.
"""
                    
                    # Use the first agent to synthesize (or a designated synthesizer if available)
                    synthesizer = agents_with_wb[0][0]
                    synthesis_result = await synthesizer.run(task=synthesis_task)
                    final_response = orchestrator._extract_final_text(synthesis_result)
                    
                    if monitor:
                        monitor.log_event('status', 'mixture', {
                            'message': 'synthesis completed',
                            'synthesizer': synthesizer.name,
                            'input_responses': len(independent_responses)
                        })
                else:
                    final_response = "All agents failed to provide responses."
                
                return {
                    "success": True,
                    "reply": final_response,
                    "pattern": "mixture",
                    "agents_used": agent_names,
                    "execution_steps": [
                        f"All {len(agents_with_wb)} agents responded independently",
                        "Responses synthesized into final answer"
                    ],
                    "individual_responses": independent_responses
                }
                
            finally:
                # Clean up workbenches
                for _, wb in agents_with_wb:
                    try:
                        await wb.__aexit__(None, None, None)
                    except Exception:
                        pass
        
        result = await execute_mixture_pattern()
        
        if monitor:
            monitor.log_event('pattern_complete', 'mixture', {
                'success': result.get('success', False),
                'agents_used': result.get('agents_used', [])
            })
        
        return result
        
    except Exception as e:
        logger.error(f"Mixture pattern execution failed: {e}\n{traceback.format_exc()}")
        if monitor:
            monitor.log_event('error', 'mixture', {'error': str(e), 'trace': traceback.format_exc()})
        return {
            "success": False,
            "error": str(e),
            "pattern": "mixture",
            "trace": traceback.format_exc()
        }
