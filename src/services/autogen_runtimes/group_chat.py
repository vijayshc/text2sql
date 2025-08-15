"""
Handles the group chat execution pattern using proper AutoGen integration.
"""
import logging
import traceback
from typing import Any, Dict, Optional, List

from src.models.agent_team import AgentTeam
from src.models.execution_method import ExecutionMethod
from src.services.run_monitor import RunMonitor

logger = logging.getLogger(__name__)

async def run_group_chat(team: AgentTeam, method: ExecutionMethod, task: str, monitor: Optional[RunMonitor] = None) -> Dict[str, Any]:
    """
    Run group chat pattern using AutoGen agents.
    
    Group Chat Pattern:
    1. Multiple agents participate in a conversation
    2. Each agent contributes based on their expertise
    3. Conversation continues until consensus or max turns
    4. Final synthesis of all contributions
    """
    try:
        logger.info(f"Starting group chat pattern execution for task: {task[:100]}...")
        
        if monitor:
            monitor.log_event('pattern_start', 'group_chat', {'task': task[:100]})
        
        # Use AutoGen orchestrator approach for proper MCP integration
        from src.services.autogen_orchestrator import AutoGenOrchestrator
        orchestrator = AutoGenOrchestrator()
        
        # Build agents with workbenches using orchestrator approach
        agents_with_wb, _ = await orchestrator._build_agents_team(team, monitor=monitor)
        
        if len(agents_with_wb) < 2:
            logger.warning("Group chat pattern requires at least 2 agents")
            if monitor:
                monitor.log_event('error', 'group_chat', {'error': 'Insufficient agents', 'required': 2, 'found': len(agents_with_wb)})
            return {"success": False, "error": "Group chat pattern requires at least 2 agents"}
        
        agent_names = [agent.name for agent, _ in agents_with_wb]
        max_turns = method.config.get('max_turns', 6) if method.config else 6
        
        if monitor:
            monitor.log_event('status', 'group_chat', {
                'message': 'group chat configured with AutoGen', 
                'agent_count': len(agents_with_wb),
                'max_turns': max_turns,
                'participants': agent_names
            })
        
        # Start all workbenches
        async def execute_group_chat():
            for _, wb in agents_with_wb:
                await wb.__aenter__()
            
            try:
                # Group chat execution
                conversation_history = []
                all_contributions = []
                
                logger.info(f"🎯 GROUP CHAT: {len(agents_with_wb)} agents participating for max {max_turns} turns")
                
                for turn in range(max_turns):
                    current_agent, current_wb = agents_with_wb[turn % len(agents_with_wb)]
                    agent_name = current_agent.name
                    
                    try:
                        logger.info(f"Turn {turn + 1}/{max_turns}: {agent_name} speaking")
                        
                        if monitor:
                            monitor.log_event('status', 'group_chat', {
                                'message': f'turn {turn + 1} starting', 
                                'agent': agent_name,
                                'turn': turn + 1,
                                'max_turns': max_turns
                            })
                        
                        # Build conversation context for the agent
                        if turn == 0:
                            # First turn - agent gets the original task
                            agent_task = f"""You are participating in a group chat with {len(agents_with_wb)} agents to solve this task:

{task}

This is the first turn. Please provide your initial thoughts and contributions."""
                        else:
                            # Subsequent turns - agent sees conversation history
                            context = "\n".join([f"{entry['agent']}: {entry['message']}" for entry in conversation_history])
                            agent_task = f"""You are participating in a group chat to solve this task:

{task}

Conversation so far:
{context}

Please provide your contribution to the discussion. Build on what others have said and add your unique perspective."""
                        
                        # Agent participates in the chat
                        result = await current_agent.run(task=agent_task)
                        response = orchestrator._extract_final_text(result)
                        
                        # Add to conversation history
                        conversation_entry = {
                            'turn': turn + 1,
                            'agent': agent_name,
                            'message': response
                        }
                        conversation_history.append(conversation_entry)
                        all_contributions.append(response)
                        
                        logger.info(f"Turn {turn + 1}: {agent_name} contributed")
                        
                        if monitor:
                            monitor.log_event('status', 'group_chat', {
                                'message': f'turn {turn + 1} completed', 
                                'agent': agent_name,
                                'response_length': len(response)
                            })
                        
                        # Check for conversation conclusion keywords
                        conclusion_keywords = ['concluded', 'final answer', 'complete', 'finished', 'solved']
                        if any(keyword in response.lower() for keyword in conclusion_keywords):
                            logger.info(f"Conversation concluded naturally at turn {turn + 1}")
                            if monitor:
                                monitor.log_event('status', 'group_chat', {
                                    'message': 'conversation concluded naturally', 
                                    'final_turn': turn + 1
                                })
                            break
                            
                    except Exception as e:
                        logger.error(f"Agent {agent_name} failed in turn {turn + 1}: {e}")
                        if monitor:
                            monitor.log_event('error', 'group_chat', {
                                'message': f'agent failed in turn {turn + 1}',
                                'agent': agent_name,
                                'turn': turn + 1,
                                'error': str(e)
                            })
                        # Add error to conversation
                        error_entry = {
                            'turn': turn + 1,
                            'agent': agent_name,
                            'message': f"[Error: {agent_name} encountered an issue: {str(e)}]",
                            'error': True
                        }
                        conversation_history.append(error_entry)
                
                # Generate final synthesis from the group discussion
                if conversation_history:
                    # Use the first agent to create a final synthesis
                    first_agent, first_wb = agents_with_wb[0]
                    
                    try:
                        logger.info("Generating final synthesis from group discussion")
                        
                        # Create synthesis prompt
                        discussion = "\n\n".join([
                            f"**{entry['agent']}**: {entry['message']}" 
                            for entry in conversation_history if not entry.get('error', False)
                        ])
                        
                        synthesis_task = f"""Based on the group discussion below, please provide a comprehensive final answer to the original task:

**Original Task**: {task}

**Group Discussion**:
{discussion}

Please synthesize all the contributions into a coherent, complete response that addresses the original task."""
                        
                        synthesis_result = await first_agent.run(task=synthesis_task)
                        final_response = orchestrator._extract_final_text(synthesis_result)
                        
                        logger.info("Final synthesis completed")
                        
                    except Exception as e:
                        logger.error(f"Failed to generate synthesis: {e}")
                        # Fallback to last non-error response
                        final_response = next(
                            (entry['message'] for entry in reversed(conversation_history) if not entry.get('error', False)),
                            "Unable to generate final response"
                        )
                else:
                    final_response = "No successful contributions were made"
                
                return {
                    "success": True,
                    "reply": final_response,
                    "pattern": "group_chat",
                    "agents_used": agent_names,
                    "execution_steps": [f"Group chat with {len(agents_with_wb)} agents over {len(conversation_history)} turns"],
                    "conversation_history": conversation_history,
                    "total_turns": len(conversation_history),
                    "max_turns": max_turns
                }
                
            finally:
                # Clean up workbenches
                for _, wb in agents_with_wb:
                    try:
                        await wb.__aexit__(None, None, None)
                    except Exception:
                        pass
        
        result = await execute_group_chat()
        
        if monitor:
            monitor.log_event('pattern_complete', 'group_chat', {
                'success': result.get('success', False),
                'agents_used': result.get('agents_used', []),
                'total_turns': result.get('total_turns', 0)
            })
        
        return result
        
    except Exception as e:
        logger.error(f"Group chat pattern execution failed: {e}\n{traceback.format_exc()}")
        if monitor:
            monitor.log_event('error', 'group_chat', {'error': str(e), 'trace': traceback.format_exc()})
        return {
            "success": False,
            "error": str(e),
            "pattern": "group_chat",
            "trace": traceback.format_exc()
        }
