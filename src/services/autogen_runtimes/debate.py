"""
Handles the debate execution pattern using proper AutoGen integration.
"""
import logging
import traceback
from typing import Any, Dict, Optional

from src.models.agent_team import AgentTeam
from src.models.execution_method import ExecutionMethod
from src.services.run_monitor import RunMonitor

logger = logging.getLogger(__name__)

async def run_debate(team: AgentTeam, method: ExecutionMethod, task: str, monitor: Optional[RunMonitor] = None) -> Dict[str, Any]:
    """
    Run debate pattern using AutoGen agents.
    
    Debate Pattern:
    1. Multiple rounds where agents present positions
    2. Each agent can respond to previous arguments
    3. Final consensus or summary is produced
    """
    try:
        logger.info(f"Starting debate pattern execution for task: {task[:100]}...")
        
        if monitor:
            monitor.log_event('pattern_start', 'debate', {'task': task[:100]})
        
        # Use AutoGen orchestrator approach for proper MCP integration
        from src.services.autogen_orchestrator import AutoGenOrchestrator
        orchestrator = AutoGenOrchestrator()
        
        # Build agents with workbenches using orchestrator approach
        agents_with_wb, _ = await orchestrator._build_agents_team(team, monitor=monitor)
        
        if len(agents_with_wb) < 2:
            logger.warning("Debate pattern requires at least 2 agents")
            if monitor:
                monitor.log_event('error', 'debate', {'error': 'Insufficient agents', 'required': 2, 'found': len(agents_with_wb)})
            return {"success": False, "error": "Debate pattern requires at least 2 agents"}
        
        agent_names = [agent.name for agent, _ in agents_with_wb]
        max_rounds = (method.config or {}).get('max_rounds', 3)
        
        if monitor:
            monitor.log_event('status', 'debate', {
                'message': 'debate pattern configured with AutoGen', 
                'agent_count': len(agents_with_wb),
                'max_rounds': max_rounds,
                'participants': agent_names
            })
        
        # Start all workbenches
        async def execute_debate_pattern():
            for _, wb in agents_with_wb:
                await wb.__aenter__()
            
            try:
                # Debate pattern execution: Multiple rounds of structured debate
                debate_rounds = []
                
                logger.info(f"🎯 DEBATE: {len(agents_with_wb)} agents debating for {max_rounds} rounds")
                
                for round_num in range(max_rounds):
                    logger.info(f"Debate round {round_num + 1}/{max_rounds}")
                    
                    if monitor:
                        monitor.log_event('status', 'debate', {
                            'message': f'starting round {round_num + 1}', 
                            'round': round_num + 1,
                            'total_rounds': max_rounds
                        })
                    
                    round_responses = []
                    
                    # Build context for this round
                    if round_num == 0:
                        # First round: Initial positions
                        round_context = f"Debate Topic: {task}\n\nThis is Round 1. Please present your initial position or analysis on this topic."
                    else:
                        # Subsequent rounds: Respond to previous arguments
                        context_parts = [f"Debate Topic: {task}", f"\nThis is Round {round_num + 1}. Previous arguments:"]
                        for prev_round_num, prev_round in enumerate(debate_rounds):
                            context_parts.append(f"\nRound {prev_round_num + 1}:")
                            for resp in prev_round:
                                context_parts.append(f"  {resp['agent']}: {resp['response']}")
                        context_parts.append(f"\nPlease respond to previous arguments and present your updated position.")
                        round_context = "\n".join(context_parts)
                    
                    # Each agent responds in this round
                    for i, (agent, wb) in enumerate(agents_with_wb):
                        agent_name = agent.name
                        
                        try:
                            if monitor:
                                monitor.log_event('status', 'debate', {
                                    'message': f'agent speaking in round {round_num + 1}', 
                                    'agent': agent_name,
                                    'round': round_num + 1
                                })
                            
                            # Agent responds to the debate context
                            result = await agent.run(task=round_context)
                            response = orchestrator._extract_final_text(result)
                            
                            round_responses.append({
                                'agent': agent_name,
                                'response': response
                            })
                            
                            logger.info(f"Agent {agent_name} provided response in round {round_num + 1}")
                            
                            if monitor:
                                monitor.log_event('status', 'debate', {
                                    'message': 'agent completed response', 
                                    'agent': agent_name,
                                    'round': round_num + 1,
                                    'response_length': len(response)
                                })
                                
                        except Exception as e:
                            logger.error(f"Agent {agent_name} failed in round {round_num + 1}: {e}")
                            if monitor:
                                monitor.log_event('error', 'debate', {
                                    'message': 'agent failed in debate round',
                                    'agent': agent_name,
                                    'round': round_num + 1,
                                    'error': str(e)
                                })
                            round_responses.append({
                                'agent': agent_name,
                                'response': f"Error: {str(e)}"
                            })
                    
                    debate_rounds.append(round_responses)
                    
                    if monitor:
                        monitor.log_event('status', 'debate', {
                            'message': f'round {round_num + 1} completed', 
                            'round': round_num + 1,
                            'responses_count': len(round_responses)
                        })
                
                # Synthesize final consensus from debate
                if debate_rounds:
                    synthesis_task = f"""
Debate Topic: {task}

The following debate has taken place between multiple agents:

{chr(10).join([f"Round {i+1}:" + chr(10).join([f"  {resp['agent']}: {resp['response']}" for resp in round_data]) for i, round_data in enumerate(debate_rounds)])}

Please synthesize a final consensus or summary that incorporates the best arguments and insights from this debate. Provide a balanced, comprehensive response to the original topic.
"""
                    
                    # Use the first agent to synthesize (or could use a dedicated moderator)
                    moderator = agents_with_wb[0][0]
                    synthesis_result = await moderator.run(task=synthesis_task)
                    final_response = orchestrator._extract_final_text(synthesis_result)
                    
                    if monitor:
                        monitor.log_event('status', 'debate', {
                            'message': 'synthesis completed',
                            'moderator': moderator.name,
                            'total_rounds': len(debate_rounds)
                        })
                else:
                    final_response = "Debate failed to produce any responses."
                
                return {
                    "success": True,
                    "reply": final_response,
                    "pattern": "debate",
                    "agents_used": agent_names,
                    "execution_steps": [
                        f"Debate conducted over {len(debate_rounds)} rounds",
                        f"Each of {len(agents_with_wb)} agents presented positions",
                        "Final consensus synthesized from all arguments"
                    ],
                    "debate_rounds": debate_rounds
                }
                
            finally:
                # Clean up workbenches
                for _, wb in agents_with_wb:
                    try:
                        await wb.__aexit__(None, None, None)
                    except Exception:
                        pass
        
        result = await execute_debate_pattern()
        
        if monitor:
            monitor.log_event('pattern_complete', 'debate', {
                'success': result.get('success', False),
                'agents_used': result.get('agents_used', [])
            })
        
        return result
        
    except Exception as e:
        logger.error(f"Debate pattern execution failed: {e}\n{traceback.format_exc()}")
        if monitor:
            monitor.log_event('error', 'debate', {'error': str(e), 'trace': traceback.format_exc()})
        return {
            "success": False,
            "error": str(e),
            "pattern": "debate",
            "trace": traceback.format_exc()
        }
