from flask import Blueprint, render_template, request, jsonify, Response, stream_with_context, current_app
from src.utils.auth_utils import login_required  # Use custom login decorator
import asyncio
import json
from src.utils.mcp_client import get_mcp_client  # We will create this utility
import logging

logger = logging.getLogger('text2sql.routes.agent')
agent_bp = Blueprint('agent', __name__, url_prefix='/agent')

@agent_bp.route('/')
@login_required
def agent_mode():
    """Renders the Agent Mode chat page."""
    return render_template('agent_mode.html', title="Agent Mode")

@agent_bp.route('/chat', methods=['POST'])
@login_required
def agent_chat():
    """Handles chat messages for Agent Mode and streams real-time responses via Server-Sent Events."""
    data = request.json
    query = data.get('query')
    mcp_server_script = current_app.config.get('MCP_SERVER_SCRIPT_PATH')

    if not query:
        return jsonify({"error": "No query provided"}), 400
    if not mcp_server_script:
        return jsonify({"error": "MCP server script path not configured"}), 500

    logger.info(f"Agent Mode streaming query received: {query}")

    def generate():
        # Create new event loop for streaming
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        client = loop.run_until_complete(get_mcp_client())
        # Connect if needed
        if not client.is_connected():
            loop.run_until_complete(client.connect_to_server(mcp_server_script))
        # Stream updates
        agen = client.process_query_stream(query)
        try:
            while True:
                upd = loop.run_until_complete(agen.__anext__())
                yield f"data: {json.dumps(upd)}\n\n"
        except StopAsyncIteration:
            # End of stream
            pass
        finally:
            # Cleanup client in same loop
            loop.run_until_complete(client.cleanup())
            loop.close()

    return Response(stream_with_context(generate()), mimetype='text/event-stream')

