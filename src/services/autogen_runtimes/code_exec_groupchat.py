"""
Handles the code execution group chat pattern using proper AutoGen integration.
"""
import logging
import traceback
from typing import Any, Dict, Optional, List

from src.models.agent_team import AgentTeam
from src.models.execution_method import ExecutionMethod
from src.services.run_monitor import RunMonitor

logger = logging.getLogger(__name__)

async def run_code_exec_groupchat(team: AgentTeam, method: ExecutionMethod, task: str, monitor: Optional[RunMonitor] = None) -> Dict[str, Any]:
    """
    Run code execution group chat pattern using AutoGen agents.
    
    Code Execution Group Chat Pattern:
    1. Agents collaborate to write and execute code
    2. Code writer proposes solution
    3. Code reviewer examines for issues
    4. Code executor runs and provides feedback
    5. Iterative refinement until working solution
    """
    try:
        logger.info(f"Starting code execution group chat pattern for task: {task[:100]}...")
        
        if monitor:
            monitor.log_event('pattern_start', 'code_exec_groupchat', {'task': task[:100]})
        
        # Use AutoGen orchestrator approach for proper MCP integration
        from src.services.autogen_orchestrator import AutoGenOrchestrator
        orchestrator = AutoGenOrchestrator()
        
        # Build agents with workbenches using orchestrator approach
        agents_with_wb, _ = await orchestrator._build_agents_team(team, monitor=monitor)
        
        if len(agents_with_wb) < 2:
            logger.warning("Code execution group chat requires at least 2 agents")
            if monitor:
                monitor.log_event('error', 'code_exec_groupchat', {'error': 'Insufficient agents', 'required': 2, 'found': len(agents_with_wb)})
            return {"success": False, "error": "Code execution group chat requires at least 2 agents"}
        
        agent_names = [agent.name for agent, _ in agents_with_wb]
        max_iterations = method.config.get('max_iterations', 5) if method.config else 5
        
        if monitor:
            monitor.log_event('status', 'code_exec_groupchat', {
                'message': 'code execution group chat configured with AutoGen', 
                'agent_count': len(agents_with_wb),
                'max_iterations': max_iterations,
                'participants': agent_names
            })
        
        # Start all workbenches
        async def execute_code_group_chat():
            for _, wb in agents_with_wb:
                await wb.__aenter__()
            
            try:
                # Code execution group chat
                code_history = []
                current_code = None
                execution_results = []
                
                logger.info(f"🎯 CODE EXEC GROUP CHAT: {len(agents_with_wb)} agents collaborating on code for max {max_iterations} iterations")
                
                for iteration in range(max_iterations):
                    iteration_num = iteration + 1
                    
                    # Phase 1: Code Writer (first agent)
                    coder_agent, coder_wb = agents_with_wb[0]
                    coder_name = coder_agent.name
                    
                    try:
                        logger.info(f"Iteration {iteration_num}: {coder_name} writing/refining code")
                        
                        if monitor:
                            monitor.log_event('status', 'code_exec_groupchat', {
                                'message': f'iteration {iteration_num} - code writing', 
                                'agent': coder_name,
                                'iteration': iteration_num
                            })
                        
                        if iteration == 0:
                            # First iteration - write initial code
                            coder_task = f"""Task: {task}

Please write Python code to solve this task. Include:
1. Clear comments explaining your approach
2. Error handling where appropriate
3. Test cases if relevant
4. Proper function/variable naming

Provide complete, executable code."""
                        else:
                            # Subsequent iterations - refine based on feedback
                            previous_feedback = execution_results[-1] if execution_results else "No previous feedback"
                            coder_task = f"""Original Task: {task}

Current Code:
```python
{current_code}
```

Previous Execution Feedback: {previous_feedback}

Please refine the code based on the feedback. Fix any issues, improve efficiency, and ensure it works correctly."""
                        
                        # Coder writes/refines code
                        coder_result = await coder_agent.run(task=coder_task)
                        code_response = orchestrator._extract_final_text(coder_result)
                        
                        # Extract code from response (look for code blocks)
                        import re
                        code_blocks = re.findall(r'```python\n(.*?)\n```', code_response, re.DOTALL)
                        if code_blocks:
                            current_code = code_blocks[0].strip()
                        else:
                            # No code block found, use entire response
                            current_code = code_response
                        
                        logger.info(f"Iteration {iteration_num}: {coder_name} provided code")
                        
                        if monitor:
                            monitor.log_event('status', 'code_exec_groupchat', {
                                'message': f'iteration {iteration_num} - code completed', 
                                'agent': coder_name,
                                'code_length': len(current_code)
                            })
                        
                    except Exception as e:
                        logger.error(f"Coder {coder_name} failed in iteration {iteration_num}: {e}")
                        if monitor:
                            monitor.log_event('error', 'code_exec_groupchat', {
                                'message': f'coder failed in iteration {iteration_num}',
                                'agent': coder_name,
                                'iteration': iteration_num,
                                'error': str(e)
                            })
                        current_code = f"# Error in code generation: {str(e)}"
                    
                    # Phase 2: Code Reviewer (second agent if available)
                    reviewer_feedback = None
                    if len(agents_with_wb) > 1:
                        reviewer_agent, reviewer_wb = agents_with_wb[1]
                        reviewer_name = reviewer_agent.name
                        
                        try:
                            logger.info(f"Iteration {iteration_num}: {reviewer_name} reviewing code")
                            
                            if monitor:
                                monitor.log_event('status', 'code_exec_groupchat', {
                                    'message': f'iteration {iteration_num} - code review', 
                                    'agent': reviewer_name,
                                    'iteration': iteration_num
                                })
                            
                            reviewer_task = f"""Original Task: {task}

Code to Review:
```python
{current_code}
```

Please review this code for:
1. Correctness and logic
2. Potential bugs or errors
3. Code quality and best practices
4. Efficiency improvements
5. Security considerations

Provide constructive feedback on how to improve the code."""
                            
                            reviewer_result = await reviewer_agent.run(task=reviewer_task)
                            reviewer_feedback = orchestrator._extract_final_text(reviewer_result)
                            
                            logger.info(f"Iteration {iteration_num}: {reviewer_name} provided review")
                            
                            if monitor:
                                monitor.log_event('status', 'code_exec_groupchat', {
                                    'message': f'iteration {iteration_num} - review completed', 
                                    'agent': reviewer_name,
                                    'feedback_length': len(reviewer_feedback)
                                })
                            
                        except Exception as e:
                            logger.error(f"Reviewer {reviewer_name} failed in iteration {iteration_num}: {e}")
                            reviewer_feedback = f"Error in code review: {str(e)}"
                    
                    # Phase 3: Code Executor (third agent if available, otherwise second)
                    executor_idx = 2 if len(agents_with_wb) > 2 else -1
                    if executor_idx < len(agents_with_wb):
                        executor_agent, executor_wb = agents_with_wb[executor_idx]
                        executor_name = executor_agent.name
                        
                        try:
                            logger.info(f"Iteration {iteration_num}: {executor_name} executing code")
                            
                            if monitor:
                                monitor.log_event('status', 'code_exec_groupchat', {
                                    'message': f'iteration {iteration_num} - code execution', 
                                    'agent': executor_name,
                                    'iteration': iteration_num
                                })
                            
                            execution_context = f"""Original Task: {task}

Code to Execute:
```python
{current_code}
```

{f"Reviewer Feedback: {reviewer_feedback}" if reviewer_feedback else ""}

Please simulate executing this code and provide:
1. Expected output or results
2. Any potential runtime errors
3. Performance analysis
4. Suggestions for improvement
5. Whether the code successfully solves the original task"""
                            
                            executor_result = await executor_agent.run(task=execution_context)
                            execution_feedback = orchestrator._extract_final_text(executor_result)
                            
                            execution_results.append(execution_feedback)
                            
                            logger.info(f"Iteration {iteration_num}: {executor_name} provided execution feedback")
                            
                            if monitor:
                                monitor.log_event('status', 'code_exec_groupchat', {
                                    'message': f'iteration {iteration_num} - execution completed', 
                                    'agent': executor_name,
                                    'feedback_length': len(execution_feedback)
                                })
                            
                            # Check if executor indicates successful completion
                            success_indicators = ['successfully solves', 'code works correctly', 'task completed', 'solution is correct']
                            if any(indicator in execution_feedback.lower() for indicator in success_indicators):
                                logger.info(f"Code execution successful at iteration {iteration_num}")
                                if monitor:
                                    monitor.log_event('status', 'code_exec_groupchat', {
                                        'message': 'code execution successful', 
                                        'iteration': iteration_num
                                    })
                                break
                            
                        except Exception as e:
                            logger.error(f"Executor {executor_name} failed in iteration {iteration_num}: {e}")
                            execution_feedback = f"Error in code execution: {str(e)}"
                            execution_results.append(execution_feedback)
                    
                    # Record iteration
                    iteration_entry = {
                        'iteration': iteration_num,
                        'code': current_code,
                        'reviewer_feedback': reviewer_feedback,
                        'execution_feedback': execution_results[-1] if execution_results else None,
                        'coder': coder_name,
                        'reviewer': reviewer_name if len(agents_with_wb) > 1 else None,
                        'executor': executor_name if executor_idx < len(agents_with_wb) else None
                    }
                    code_history.append(iteration_entry)
                
                return {
                    "success": True,
                    "reply": f"Final Code Solution:\n\n```python\n{current_code}\n```\n\nExecution Result: {execution_results[-1] if execution_results else 'No execution feedback'}",
                    "pattern": "code_exec_groupchat",
                    "agents_used": agent_names,
                    "execution_steps": [f"Completed {len(code_history)} code development iterations"],
                    "code_history": code_history,
                    "final_code": current_code,
                    "total_iterations": len(code_history),
                    "max_iterations": max_iterations
                }
                
            finally:
                # Clean up workbenches
                for _, wb in agents_with_wb:
                    try:
                        await wb.__aexit__(None, None, None)
                    except Exception:
                        pass
        
        result = await execute_code_group_chat()
        
        if monitor:
            monitor.log_event('pattern_complete', 'code_exec_groupchat', {
                'success': result.get('success', False),
                'agents_used': result.get('agents_used', []),
                'total_iterations': result.get('total_iterations', 0)
            })
        
        return result
        
    except Exception as e:
        logger.error(f"Code execution group chat pattern failed: {e}\n{traceback.format_exc()}")
        if monitor:
            monitor.log_event('error', 'code_exec_groupchat', {'error': str(e), 'trace': traceback.format_exc()})
        return {
            "success": False,
            "error": str(e),
            "pattern": "code_exec_groupchat",
            "trace": traceback.format_exc()
        }
