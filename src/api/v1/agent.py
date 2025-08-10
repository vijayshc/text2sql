"""
Agent Mode API endpoints for Vue.js frontend
"""
from flask import Blueprint, request, jsonify, Response, stream_with_context
import asyncio
import json
import logging
import uuid
import time

from src.utils.auth_utils import jwt_required
from src.models.user import User
from src.models.mcp_server import MCPServer, MCPServerStatus
from src.utils.mcp_client_manager import get_mcp_client_for_query, MCPClientManager
from src.utils.user_manager import UserManager

# Get the logger
logger = logging.getLogger('text2sql')

# Create Blueprint
agent_api = Blueprint('agent_api', __name__)

# Initialize user manager for audit logging
user_manager = UserManager()

@agent_api.route('/servers', methods=['GET'])
@jwt_required
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
                    'status': server.status,
                    'server_type': server.server_type,
                    'url': server.url if server.server_type == 'http' else None
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

@agent_api.route('/chat', methods=['POST'])
@jwt_required
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
                        
                        # Collect ALL response content for audit logging
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
                        
                        # Yield the update to the client via SSE
                        yield f"data: {json.dumps(upd)}\n\n"
                        
                except StopAsyncIteration:
                    # Stream completed normally
                    pass
                    
            except Exception as e:
                error_msg = f"Error during agent processing: {str(e)}"
                logger.exception(error_msg)
                collected_responses.append(f"ERROR: {error_msg}")
                yield f"data: {json.dumps({'type': 'error', 'message': error_msg})}\n\n"
                
            finally:
                try:
                    loop.close()
                except:
                    pass
                
        except Exception as e:
            error_msg = f"Critical error in agent chat: {str(e)}"
            logger.exception(error_msg)
            yield f"data: {json.dumps({'type': 'error', 'message': error_msg})}\n\n"
        
        finally:
            # Audit log the interaction
            try:
                # Get user info for audit logging
                user_id = getattr(request, 'current_user_id', 'unknown')
                ip_address = request.environ.get('HTTP_X_REAL_IP', request.remote_addr)
                
                # Combine collected responses for audit log
                full_response = '\n'.join(collected_responses) if collected_responses else 'No response collected'
                
                # Limit response length for audit log (to prevent excessive log sizes)
                if len(full_response) > 1000:
                    full_response = full_response[:1000] + '... (truncated)'
                
                # Log the interaction
                user_manager.log_audit_event(
                    event_type='agent_chat',
                    user_id=user_id,
                    ip_address=ip_address,
                    event_data={
                        'query': query,
                        'server_id': server_id,
                        'conversation_history_length': len(conversation_history) if conversation_history else 0,
                        'response': full_response
                    }
                )
            except Exception as audit_error:
                logger.exception(f"Error logging audit event: {audit_error}")
            
            # Send completion marker
            yield f"data: {json.dumps({'type': 'complete'})}\n\n"

    # Return Server-Sent Events response
    return Response(
        stream_with_context(generate()),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'X-Accel-Buffering': 'no'  # For nginx
        }
    )

@agent_api.route('/tool-confirm', methods=['POST'])
@jwt_required
def confirm_tool_execution():
    """Handle tool execution confirmation from the frontend."""
    data = request.get_json()
    
    if not data or 'confirmation_id' not in data or 'confirmed' not in data:
        return jsonify({'error': 'Missing confirmation_id or confirmed parameter'}), 400
    
    confirmation_id = data['confirmation_id']
    confirmed = data['confirmed']
    
    try:
        # Store the confirmation result
        from src.routes.agent_routes import confirm_flags
        confirm_flags[confirmation_id] = confirmed
        
        logger.info(f"Tool confirmation received: {confirmation_id} = {confirmed}")
        
        return jsonify({
            'success': True,
            'message': 'Tool confirmation received'
        })
    except Exception as e:
        logger.exception("Error processing tool confirmation")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@agent_api.route('/conversation/clear', methods=['POST'])
@jwt_required
def clear_conversation():
    """Clear conversation history for the current user."""
    try:
        # In a full implementation, you might store conversation history per user
        # For now, this endpoint exists for API compatibility
        return jsonify({
            'success': True,
            'message': 'Conversation history cleared'
        })
    except Exception as e:
        logger.exception("Error clearing conversation")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500