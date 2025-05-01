from flask import Blueprint, request, jsonify, current_app, Response, stream_with_context
import asyncio
import json
import logging
import uuid
import time
import os

# Use our own login_required decorator instead of flask_login's
from src.utils.auth_utils import login_required

from src.models.user import User
from src.routes.auth_routes import admin_required
from src.models.mcp_server import MCPServer, MCPServerStatus
from src.utils.mcp_client_manager import get_mcp_client_for_query

# Get the logger
logger = logging.getLogger('text2sql')

# Create Blueprint
agent_bp = Blueprint('agent', __name__)

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
    
    def generate():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Choose appropriate MCP client based on query content
        if server_id:
            from src.utils.mcp_client_manager import MCPClientManager
            client = loop.run_until_complete(MCPClientManager.get_client(server_id, connect=True))
            if not client:
                yield f"data: {json.dumps({'type': 'error', 'message': 'Could not connect to selected server.'})}\n\n"
                return
        else:
            # Let the system choose the best server based on the query
            client = loop.run_until_complete(get_mcp_client_for_query(query))
            if not client:
                yield f"data: {json.dumps({'type': 'error', 'message': 'No suitable MCP server available for your query.'})}\n\n"
                return
            
        yield f"data: {json.dumps({'type': 'status', 'message': f'Connected to MCP server: {client.server_name}'})}\n\n"

        # Stream updates
        agen = client.process_query_stream(query)
        try:
            while True:
                # Get next update from MCP
                upd = loop.run_until_complete(agen.__anext__())
                
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
                            yield f"data: {json.dumps(timeout_data)}\n\n"
                            return
                    
                    # Check confirmation result
                    if not confirm_flags[call_id]:
                        del confirm_flags[call_id]
                        rejection_data = {
                            'type': 'error',
                            'message': "Tool call was rejected by the user."
                        }
                        yield f"data: {json.dumps(rejection_data)}\n\n"
                        return
                    
                    # Tool call was confirmed, continue
                    del confirm_flags[call_id]
                    
                # Forward update to client
                yield f"data: {json.dumps(upd)}\n\n"
                
        except StopAsyncIteration:
            # End of generator, nothing more to stream
            yield f"data: {json.dumps({'type': 'status', 'message': 'Agent processing completed.'})}\n\n"
            pass
        except Exception as e:
            logger.exception("Error in agent chat stream")
            error_msg = str(e)
            yield f"data: {json.dumps({'type': 'error', 'message': f'Error: {error_msg}'})}\n\n"
        finally:
            loop.close()

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
