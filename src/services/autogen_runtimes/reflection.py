"""
Handles the reflection execution pattern using proper AutoGen integration.
"""
import logging
import traceback
from typing import Any, Dict, Optional

from src.models.agent_team import AgentTeam
from src.models.execution_method import ExecutionMethod
from src.services.run_monitor import RunMonitor

logger = logging.getLogger(__name__)

async def run_reflection(team: AgentTeam, method: ExecutionMethod, task: str, monitor: Optional[RunMonitor] = None) -> Dict[str, Any]:
    """
    Run reflection pattern using AutoGen agents.
    
    Reflection Pattern:
    1. Primary agent provides initial solution
    2. Reviewer agent provides constructive feedback
    3. Primary agent refines based on feedback
    4. Multiple reflection cycles until satisfactory result
    """
    try:
        logger.info(f"Starting reflection pattern execution for task: {task[:100]}...")
        
        if monitor:
            monitor.log_event('pattern_start', 'reflection', {'task': task[:100]})
        
        # Use AutoGen orchestrator approach for proper MCP integration
        from src.services.autogen_orchestrator import AutoGenOrchestrator
        orchestrator = AutoGenOrchestrator()
        
        # Build agents with workbenches using orchestrator approach
        agents_with_wb, _ = await orchestrator._build_agents_team(team, monitor=monitor)
        
        if len(agents_with_wb) < 2:
            logger.warning("Reflection pattern requires at least 2 agents")
            if monitor:
                monitor.log_event('error', 'reflection', {'error': 'Insufficient agents', 'required': 2, 'found': len(agents_with_wb)})
            return {"success": False, "error": "Reflection pattern requires at least 2 agents"}
        
        # Get primary and reviewer agents
        primary_agent, primary_wb = agents_with_wb[0]
        reviewer_agent, reviewer_wb = agents_with_wb[1]
        
        primary_name = primary_agent.name
        reviewer_name = reviewer_agent.name
        
        max_reflection_cycles = method.config.get('max_cycles', 3) if method.config else 3
        
        if monitor:
            monitor.log_event('status', 'reflection', {
                'message': 'reflection configured with AutoGen', 
                'primary': primary_name, 
                'reviewer': reviewer_name,
                'max_cycles': max_reflection_cycles
            })
        
        # Start all workbenches
        async def execute_reflection():
            for _, wb in agents_with_wb:
                await wb.__aenter__()
            
            try:
                # Reflection execution
                reflection_history = []
                current_solution = None
                
                logger.info(f"🎯 REFLECTION: {primary_name} and {reviewer_name} collaborating over max {max_reflection_cycles} cycles")
                
                for cycle in range(max_reflection_cycles):
                    cycle_num = cycle + 1
                    
                    # Phase 1: Primary agent provides solution
                    try:
                        logger.info(f"Reflection Cycle {cycle_num}: {primary_name} providing solution")
                        
                        if monitor:
                            monitor.log_event('status', 'reflection', {
                                'message': f'cycle {cycle_num} - primary solution', 
                                'agent': primary_name,
                                'cycle': cycle_num
                            })
                        
                        if cycle == 0:
                            # First cycle - original task
                            primary_task = f"""Task: {task}

Please provide your initial solution or response to this task. Be thorough and detailed."""
                        else:
                            # Subsequent cycles - refine based on feedback
                            previous_feedback = reflection_history[-1]['feedback']
                            primary_task = f"""Original Task: {task}

Your Previous Solution: {current_solution}

Reviewer Feedback: {previous_feedback}

Please refine your solution based on the feedback. Address the specific points raised and improve the overall quality."""
                        
                        # Primary agent works on the solution
                        primary_result = await primary_agent.run(task=primary_task)
                        current_solution = orchestrator._extract_final_text(primary_result)
                        
                        logger.info(f"Cycle {cycle_num}: {primary_name} provided solution")
                        
                        if monitor:
                            monitor.log_event('status', 'reflection', {
                                'message': f'cycle {cycle_num} - solution completed', 
                                'agent': primary_name,
                                'solution_length': len(current_solution)
                            })
                        
                    except Exception as e:
                        logger.error(f"Primary agent {primary_name} failed in cycle {cycle_num}: {e}")
                        if monitor:
                            monitor.log_event('error', 'reflection', {
                                'message': f'primary agent failed in cycle {cycle_num}',
                                'agent': primary_name,
                                'cycle': cycle_num,
                                'error': str(e)
                            })
                        current_solution = f"Error in solution generation: {str(e)}"
                    
                    # Phase 2: Reviewer agent provides feedback
                    try:
                        logger.info(f"Reflection Cycle {cycle_num}: {reviewer_name} providing feedback")
                        
                        if monitor:
                            monitor.log_event('status', 'reflection', {
                                'message': f'cycle {cycle_num} - reviewer feedback', 
                                'agent': reviewer_name,
                                'cycle': cycle_num
                            })
                        
                        review_task = f"""Original Task: {task}

Solution to Review: {current_solution}

Please provide constructive feedback on this solution. Consider:
1. Accuracy and correctness
2. Completeness and thoroughness  
3. Clarity and presentation
4. Areas for improvement
5. Specific suggestions for enhancement

If the solution is satisfactory, please indicate that it meets the requirements."""
                        
                        # Reviewer provides feedback
                        review_result = await reviewer_agent.run(task=review_task)
                        feedback = orchestrator._extract_final_text(review_result)
                        
                        # Record this reflection cycle
                        cycle_entry = {
                            'cycle': cycle_num,
                            'solution': current_solution,
                            'feedback': feedback,
                            'primary_agent': primary_name,
                            'reviewer_agent': reviewer_name
                        }
                        reflection_history.append(cycle_entry)
                        
                        logger.info(f"Cycle {cycle_num}: {reviewer_name} provided feedback")
                        
                        if monitor:
                            monitor.log_event('status', 'reflection', {
                                'message': f'cycle {cycle_num} - feedback completed', 
                                'agent': reviewer_name,
                                'feedback_length': len(feedback)
                            })
                        
                        # Check if reviewer indicates solution is satisfactory
                        satisfaction_indicators = ['satisfactory', 'meets requirements', 'good solution', 'well done', 'acceptable']
                        if any(indicator in feedback.lower() for indicator in satisfaction_indicators):
                            logger.info(f"Reviewer indicated satisfaction at cycle {cycle_num}")
                            if monitor:
                                monitor.log_event('status', 'reflection', {
                                    'message': 'reviewer satisfied with solution', 
                                    'cycle': cycle_num
                                })
                            break
                            
                    except Exception as e:
                        logger.error(f"Reviewer agent {reviewer_name} failed in cycle {cycle_num}: {e}")
                        if monitor:
                            monitor.log_event('error', 'reflection', {
                                'message': f'reviewer agent failed in cycle {cycle_num}',
                                'agent': reviewer_name,
                                'cycle': cycle_num,
                                'error': str(e)
                            })
                        feedback = f"Error in feedback generation: {str(e)}"
                        cycle_entry = {
                            'cycle': cycle_num,
                            'solution': current_solution,
                            'feedback': feedback,
                            'primary_agent': primary_name,
                            'reviewer_agent': reviewer_name,
                            'error': True
                        }
                        reflection_history.append(cycle_entry)
                        break
                
                return {
                    "success": True,
                    "reply": current_solution,
                    "pattern": "reflection",
                    "agents_used": [primary_name, reviewer_name],
                    "execution_steps": [f"Completed {len(reflection_history)} reflection cycles"],
                    "reflection_history": reflection_history,
                    "total_cycles": len(reflection_history),
                    "max_cycles": max_reflection_cycles
                }
                
            finally:
                # Clean up workbenches
                for _, wb in agents_with_wb:
                    try:
                        await wb.__aexit__(None, None, None)
                    except Exception:
                        pass
        
        result = await execute_reflection()
        
        if monitor:
            monitor.log_event('pattern_complete', 'reflection', {
                'success': result.get('success', False),
                'agents_used': result.get('agents_used', []),
                'total_cycles': result.get('total_cycles', 0)
            })
        
        return result
        
    except Exception as e:
        logger.error(f"Reflection pattern execution failed: {e}\n{traceback.format_exc()}")
        if monitor:
            monitor.log_event('error', 'reflection', {'error': str(e), 'trace': traceback.format_exc()})
        return {
            "success": False,
            "error": str(e),
            "pattern": "reflection",
            "trace": traceback.format_exc()
        }
