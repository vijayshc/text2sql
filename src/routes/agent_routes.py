from flask import Blueprint, render_template, request, jsonify, Response, stream_with_context, current_app
from src.utils.auth_utils import login_required  # Use custom login decorator
import asyncio
import json
from src.utils.mcp_client import get_mcp_client  # We will create this utility
import logging
import sys

# We'll access MCP client through Flask's current_app instead of direct imports
# This prevents circular import issues and ensures we access the same instance

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
        # Access MCP client and event loop through Flask's current_app
        app_mcp_client = getattr(current_app, 'mcp_client', None)
        app_mcp_event_loop = getattr(current_app, 'mcp_event_loop', None)
        
        # Use the application's MCP event loop and client if available
        if app_mcp_event_loop is not None and app_mcp_client is not None and app_mcp_client.is_connected():
            logger.info("Using application-wide MCP client and event loop")
            # Set the global event loop as the current loop for this thread
            asyncio.set_event_loop(app_mcp_event_loop)
            loop = app_mcp_event_loop
            client = app_mcp_client
        else:
            # Fallback to creating a temporary loop if app-wide client isn't available
            # This should only happen if initialization failed at app startup
            logger.warning("Application-wide MCP client not available. Creating temporary connection.")
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
                # Use the loop to get the next async generator item
                # This works with both the global loop or the temporary one
                upd = loop.run_until_complete(agen.__anext__())
                yield f"data: {json.dumps(upd)}\n\n"
        except StopAsyncIteration:
            # End of stream
            pass
        finally:
            # Only close the loop if it's a temporary one we created
            # Never close the global event loop!
            if loop is not app_mcp_event_loop and loop is not None and not loop.is_closed():
                loop.close()

    return Response(stream_with_context(generate()), mimetype='text/event-stream')

