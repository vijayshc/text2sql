"""
Modern Flask API-only application serving Vue.js frontend
All backward compatibility with HTML templates removed
"""
from flask import Flask, request, jsonify, send_from_directory, current_app
from src.models.sql_generator import SQLGenerationManager
from src.utils.feedback_manager import FeedbackManager
from src.utils.schema_manager import SchemaManager
from src.utils.user_manager import UserManager
from src.utils.background_tasks import BackgroundTaskManager
from src.routes.security_routes import security_bp, generate_csrf_token
from src.routes.admin_api_routes import admin_api_bp
from src.models.user import Permissions
from config.config import SECRET_KEY, DEBUG, MCP_SERVER_SCRIPT_PATH

# API imports
from src.api import api_v1
from src.middleware import configure_cors, configure_error_handlers, handle_api_exception
import logging
import os
import sys
import time
import uuid
from datetime import datetime
from threading import Thread
import signal
import asyncio

# Get the logger configured in config.py
logger = logging.getLogger('text2sql')

# Import new MCP client manager
from src.utils.mcp_client_manager import MCPClientManager
# Import MCP server model
from src.models.mcp_server import MCPServer
# Import skill model
from src.models.skill import Skill

# Function to initialize MCP servers
def initialize_mcp_servers():
    """Initialize the MCP servers that are marked as running in the database."""
    try:
        servers = MCPServer.get_all()
        running_servers = [s for s in servers if s.status == 'running']
        
        if running_servers:
            logger.info(f"Found {len(running_servers)} running MCP servers to initialize")
            
            async def start_servers():
                for server in running_servers:
                    try:
                        client = await MCPClientManager.get_client(server.id, connect=True)
                        if client:
                            logger.info(f"Successfully initialized MCP server: {server.name}")
                        else:
                            logger.warning(f"Failed to initialize MCP server: {server.name}")
                    except Exception as e:
                        logger.error(f"Error initializing MCP server {server.name}: {str(e)}")
            
            # Run in a separate thread to avoid blocking
            def run_async():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    loop.run_until_complete(start_servers())
                finally:
                    loop.close()
            
            thread = Thread(target=run_async, daemon=True)
            thread.start()
        else:
            logger.info("No running MCP servers found to initialize")
            
    except Exception as e:
        logger.error(f"Error during MCP server initialization: {str(e)}")

# Global MCP client and event loop
mcp_client = None
mcp_event_loop = None

async def shutdown_mcp_client():
    """Shutdown the global MCP client."""
    global mcp_client
    if mcp_client is not None:
        try:
            await mcp_client.shutdown()
        except Exception as e:
            logger.error(f"Error shutting down MCP client: {str(e)}")

def cleanup_mcp_client():
    """Clean up the global MCP client and event loop."""
    global mcp_event_loop, mcp_client
    
    if mcp_client is not None:
        logger.info("Cleaning up global MCP client")
        try:
            if mcp_event_loop and not mcp_event_loop.is_closed():
                mcp_event_loop.run_until_complete(shutdown_mcp_client())
        except Exception as e:
            logger.error(f"Error shutting down MCP client: {str(e)}")
    
    if mcp_event_loop is not None and not mcp_event_loop.is_closed():
        try:
            mcp_event_loop.close()
        except Exception as e:
            logger.error(f"Error closing MCP event loop: {str(e)}")
    
    mcp_client = None
    mcp_event_loop = None

# Initialize Flask app
app = Flask(__name__, static_folder='frontend/dist', static_url_path='/')
app.config['SECRET_KEY'] = SECRET_KEY
app.config['DEBUG'] = DEBUG
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0 if DEBUG else 31536000  # 1 year in production
app.config['MCP_SERVER_SCRIPT_PATH'] = MCP_SERVER_SCRIPT_PATH

# Configure API middleware
configure_cors(app)
configure_error_handlers(app)
handle_api_exception(app)

# Set secure cookie settings
app.config['SESSION_COOKIE_SECURE'] = not DEBUG  # Secure in production
app.config['SESSION_COOKIE_HTTPONLY'] = True  # HttpOnly flag
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'  # SameSite attribute
app.config['PERMANENT_SESSION_LIFETIME'] = 86400  # 24 hours in seconds

# Initialize managers
sql_manager = SQLGenerationManager()
user_manager = UserManager()
background_task_mgr = BackgroundTaskManager(sql_manager, user_manager)

# Set up knowledge base permissions
from src.utils.setup_knowledge_permissions import setup_knowledge_permissions
setup_knowledge_permissions()

# Configure uploads folder for knowledge base documents
from config.config import UPLOADS_DIR
app.config['UPLOAD_FOLDER'] = UPLOADS_DIR

# Register API blueprints only
app.register_blueprint(api_v1)
app.register_blueprint(admin_api_bp)

# Register security blueprint for CSRF (API compatibility)
app.register_blueprint(security_bp)

# Vue.js Frontend Routes
@app.route('/')
def serve_vue_app():
    """Serve the Vue.js application"""
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/<path:path>')
def serve_vue_assets(path):
    """Serve Vue.js static assets and handle client-side routing"""
    # Check if file exists in static folder
    static_file_path = os.path.join(app.static_folder, path)
    if os.path.isfile(static_file_path):
        return send_from_directory(app.static_folder, path)
    else:
        # For client-side routing, serve index.html
        return send_from_directory(app.static_folder, 'index.html')

# Health check endpoint
@app.route('/api/health')
def health_check():
    """Health check endpoint for monitoring"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'version': '2.0.0-vue'
    })

# API endpoint for getting CSRF token (for API compatibility)
@app.route('/api/csrf-token')
def get_csrf_token():
    """Get CSRF token for API requests"""
    return jsonify({'csrf_token': generate_csrf_token()})

# Error handlers for API responses
@app.errorhandler(404)
def not_found_api(error):
    """Handle 404 errors with JSON response"""
    return jsonify({'error': 'Not found'}), 404

@app.errorhandler(500)
def internal_error_api(error):
    """Handle 500 errors with JSON response"""
    logger.exception("Internal server error")
    return jsonify({'error': 'Internal server error'}), 500

# Graceful shutdown handler
def signal_handler(sig, frame):
    """Handle graceful shutdown signals."""
    logger.info("Received shutdown signal, cleaning up...")
    cleanup_mcp_client()
    logger.info("Cleanup complete, exiting...")
    sys.exit(0)

# Register signal handlers
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

if __name__ == '__main__':
    logger.info("Starting Text2SQL API server with Vue.js frontend")
    logger.info(f"Debug mode: {DEBUG}")
    logger.info(f"Static folder: {app.static_folder}")
    
    # Initialize MCP servers
    initialize_mcp_servers()
    
    try:
        app.run(
            host='0.0.0.0',
            port=5000,
            debug=DEBUG,
            threaded=True
        )
    except KeyboardInterrupt:
        logger.info("Received KeyboardInterrupt, shutting down...")
    finally:
        cleanup_mcp_client()
        logger.info("Server shutdown complete")