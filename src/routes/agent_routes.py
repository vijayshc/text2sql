from flask import Blueprint, request, jsonify, current_app, Response, stream_with_context, session
import asyncio
import json
import logging
import uuid
import time
import os

# Use our own login_required decorator instead of flask_login's
from src.utils.auth_utils import login_required
from src.utils.user_manager import UserManager

from src.models.user import User
from src.routes.auth_routes import admin_required
from src.models.mcp_server import MCPServer, MCPServerStatus
from src.utils.mcp_client_manager import get_mcp_client_for_query

# Get the logger
logger = logging.getLogger('text2sql')

# Create Blueprint
agent_bp = Blueprint('agent', __name__)

# Initialize user manager for audit logging
user_manager = UserManager()

# Store for pending tool confirmations
confirm_flags = {}

@agent_bp.route('/agent', methods=['GET'])
@login_required
def agent_page():
    from flask import render_template
    
    return render_template('agent_mode.html')

@agent_bp.route('/api/agent/servers', methods=['GET'])
@login_required
def get_available_servers():
    """Get a list of available MCP servers for the UI."""
    try:
        servers = MCPServer.get_all()
        return jsonify({
            'success': True,
            'servers': [
                {
                    'id': server.id,
                    'name': server.name,
                    'description': server.description,
                    'status': server.status
                }
                for server in servers if server.status == MCPServerStatus.RUNNING.value
            ]
        })
    except Exception as e:
        logger.exception("Error fetching available MCP servers")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@agent_bp.route('/api/agent/chat', methods=['POST'])
@login_required
def agent_chat():
    """Handles chat messages for Agent Mode and streams real-time responses via Server-Sent Events."""
    data = request.get_json()
    
    if not data or not data.get('query'):
        return jsonify({'error': 'Missing query parameter'}), 400
    
    query = data.get('query')
    server_id = data.get('server_id')  # Optional specific server ID
    conversation_history = data.get('conversation_history', [])  # Get history for follow-up questions
    
    def generate():
        collected_responses = []
        
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                # Choose appropriate MCP client based on query content
                if server_id:
                    from src.utils.mcp_client_manager import MCPClientManager
                    client = loop.run_until_complete(MCPClientManager.get_client(server_id, connect=True))
                    if not client:
                        error_msg = 'Could not connect to selected server.'
                        collected_responses.append(f"ERROR: {error_msg}")
                        yield f"data: {json.dumps({'type': 'error', 'message': error_msg})}\n\n"
                        return
                else:
                    # Let the system choose the best server based on the query
                    client = loop.run_until_complete(get_mcp_client_for_query(query))
                    if not client:
                        error_msg = 'No suitable MCP server available for your query.'
                        collected_responses.append(f"ERROR: {error_msg}")
                        yield f"data: {json.dumps({'type': 'error', 'message': error_msg})}\n\n"
                        return
                    
                status_msg = f'Connected to MCP server: {client.server_name}'
                collected_responses.append(f"STATUS: {status_msg}")
                yield f"data: {json.dumps({'type': 'status', 'message': status_msg})}\n\n"

                # Prepare query with conversation history if available
                if conversation_history:
                    # Create a structured query with conversation history
                    structured_query = {
                        'query': query,
                        'conversation_history': conversation_history
                    }
                    logger.info(f"Processing query with {len(conversation_history)} previous messages for context")
                    # Stream updates with history
                    agen = client.process_query_stream(structured_query)
                else:
                    # Stream updates with just the query
                    agen = client.process_query_stream(query)
                    
                try:
                    while True:
                        # Get next update from MCP
                        upd = loop.run_until_complete(agen.__anext__())
                        
                        # Log the raw update for debugging
                        logger.debug(f"Agent stream update: {upd}")
                        
                        # Collect ALL response content for audit logging - be more comprehensive
                        update_type = upd.get('type', '')
                        
                        if update_type == 'text':
                            content = upd.get('content', '')
                            if content:
                                collected_responses.append(content)
                        elif update_type == 'final_answer':
                            content = upd.get('content', '')
                            if content:
                                collected_responses.append(content)
                        elif update_type == 'tool_result':
                            tool_result = upd.get('content', upd.get('result', ''))
                            if tool_result:
                                collected_responses.append(f"TOOL_RESULT: {tool_result}")
                        elif update_type == 'tool_call':
                            tool_name = upd.get('tool_name', '')
                            tool_args = upd.get('arguments', {})
                            collected_responses.append(f"TOOL_CALL: {tool_name}({tool_args})")
                        elif update_type == 'error':
                            error_content = upd.get('message', upd.get('content', ''))
                            if error_content:
                                collected_responses.append(f"ERROR: {error_content}")
                        elif update_type == 'status':
                            status_content = upd.get('message', upd.get('content', ''))
                            if status_content:
                                collected_responses.append(f"STATUS: {status_content}")
                        elif update_type == 'response' or update_type == 'message':
                            # Handle other response types that might contain content
                            content = upd.get('content', upd.get('text', upd.get('message', '')))
                            if content:
                                collected_responses.append(content)
                        else:
                            # Capture any other type with content for comprehensive logging
                            content = upd.get('content', upd.get('text', upd.get('message', '')))
                            if content and update_type:
                                collected_responses.append(f"{update_type.upper()}: {content}")
                            elif content:
                                collected_responses.append(content)
                        
                        # Intercept sensitive tool calls for confirmation
                        if upd.get('type') == 'tool_call' and upd.get('tool_name') == 'run_bash_shell':
                            # Generate unique call ID and set pending flag
                            call_id = str(uuid.uuid4())
                            confirm_flags[call_id] = None
                            
                            # Send tool call details to client for confirmation
                            confirmation_data = {
                                'type': 'tool_confirmation_request',
                                'call_id': call_id,
                                'tool_name': upd.get('tool_name'),
                                'arguments': upd.get('arguments')
                            }
                            yield f"data: {json.dumps(confirmation_data)}\n\n"
                            
                            # Wait for confirmation (poll with timeout)
                            start_time = time.time()
                            timeout = 60  # 1 minute timeout
                            while confirm_flags[call_id] is None:
                                loop.run_until_complete(asyncio.sleep(0.5))
                                if time.time() - start_time > timeout:
                                    del confirm_flags[call_id]
                                    timeout_data = {
                                        'type': 'error',
                                        'message': f"Tool call confirmation timed out after {timeout} seconds."
                                    }
                                    collected_responses.append(f"ERROR: {timeout_data['message']}")
                                    yield f"data: {json.dumps(timeout_data)}\n\n"
                                    return
                            
                            # Check confirmation result
                            if not confirm_flags[call_id]:
                                del confirm_flags[call_id]
                                rejection_data = {
                                    'type': 'error',
                                    'message': "Tool call was rejected by the user."
                                }
                                collected_responses.append(f"ERROR: {rejection_data['message']}")
                                yield f"data: {json.dumps(rejection_data)}\n\n"
                                return
                            
                            # Tool call was confirmed, continue
                            del confirm_flags[call_id]
                            
                        # Forward update to client and capture it as fallback
                        update_json = json.dumps(upd)
                        yield f"data: {update_json}\n\n"
                        
                        # Fallback: if we haven't captured this content yet, try to extract it
                        if update_type not in ['tool_confirmation_request'] and not any(
                            part in str(collected_responses[-5:]) if collected_responses else ''
                            for part in [upd.get('content', ''), upd.get('text', ''), upd.get('message', '')]
                            if part
                        ):
                            # Try to extract any text content we might have missed
                            fallback_content = upd.get('content') or upd.get('text') or upd.get('message')
                            if fallback_content and len(str(fallback_content).strip()) > 0:
                                collected_responses.append(f"FALLBACK_{update_type}: {fallback_content}")
                    
                except StopAsyncIteration:
                    # End of generator, nothing more to stream
                    completion_msg = 'Agent processing completed.'
                    collected_responses.append(f"STATUS: {completion_msg}")
                    yield f"data: {json.dumps({'type': 'status', 'message': completion_msg})}\n\n"
                except Exception as e:
                    logger.exception("Error in agent chat stream")
                    error_msg = str(e)
                    collected_responses.append(f"ERROR: {error_msg}")
                    yield f"data: {json.dumps({'type': 'error', 'message': f'Error: {error_msg}'})}\n\n"
                finally:
                    loop.close()
            
            except Exception as outer_error:
                logger.exception("Outer error in agent chat stream")
                collected_responses.append(f"ERROR: {str(outer_error)}")
                yield f"data: {json.dumps({'type': 'error', 'message': f'Error: {str(outer_error)}'})}\n\n"
        
        finally:
            # Log audit event with collected response after streaming is complete
            try:
                full_response = ' | '.join(collected_responses) if collected_responses else "No response content captured"
                
                # Debug logging to see what we captured
                logger.info(f"Agent audit - Collected {len(collected_responses)} response parts")
                logger.debug(f"Agent audit - Full response preview: {full_response[:500]}...")
                
                user_manager.log_audit_event(
                    user_id=session.get('user_id'),
                    action='agent_chat_stream',
                    details=f"Agent mode streaming query completed. Server: {server_id or 'auto-select'}, Response parts: {len(collected_responses)}, Response length: {len(full_response)} chars",
                    ip_address=request.remote_addr,
                    query_text=query,
                    response=full_response[:1000] if full_response else None  # Limit response to 1000 chars for audit
                )
            except Exception as audit_error:
                logger.error(f"Error logging audit event for agent streaming query: {str(audit_error)}")

    return Response(stream_with_context(generate()), mimetype='text/event-stream')

@agent_bp.route('/api/agent/tool-confirmation', methods=['POST'])
@login_required
def tool_confirmation():
    """Handle tool execution confirmation from user."""
    data = request.get_json()
    
    if not data or 'call_id' not in data or 'confirmed' not in data:
        return jsonify({'error': 'Missing required parameters'}), 400
    
    call_id = data['call_id']
    confirmed = data['confirmed']
    
    if call_id not in confirm_flags:
        return jsonify({'error': 'Invalid confirmation ID or confirmation expired'}), 400
    
    confirm_flags[call_id] = confirmed
    
    return jsonify({'success': True})
