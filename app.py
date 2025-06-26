from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash, current_app
from src.models.sql_generator import SQLGenerationManager
from src.utils.feedback_manager import FeedbackManager
from src.utils.schema_manager import SchemaManager
from src.utils.user_manager import UserManager
from src.utils.template_filters import register_filters
from src.utils.background_tasks import BackgroundTaskManager
from src.routes.schema_routes import schema_bp
from src.routes.auth_routes import auth_bp, admin_required, permission_required
from src.routes.admin_routes import admin_bp
from src.routes.admin_api_routes import admin_api_bp
from src.routes.admin_db_routes import admin_db_bp
from src.routes.security_routes import security_bp, generate_csrf_token
from src.routes.vector_db_routes import vector_db_bp
from src.routes.knowledge_routes import knowledge_bp
from src.routes.metadata_search_routes import metadata_search_bp
from src.routes.agent_routes import agent_bp
from src.routes.tool_confirmation_routes import tool_confirmation_bp  # new import for confirmation endpoint
from src.routes.skill_routes import skill_bp  # Import skill routes
from src.models.user import Permissions
from config.config import SECRET_KEY, DEBUG, MCP_SERVER_SCRIPT_PATH
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
    # Ensure the MCP servers table exists
    MCPServer.create_table()
    
    # Ensure the skills table exists
    Skill.create_table()

    # Start all servers marked as running in the database
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    results = loop.run_until_complete(MCPClientManager.start_all_running_servers())
    loop.close()

    # Log startup results
    for result in results:
        if result['success']:
            logger.info(f"Successfully started MCP server: {result['server_name']}")
        else:
            logger.error(f"Failed to start MCP server {result['server_name']}: {result['message']}")

# Function to clean up MCP client (no-op; old cleanup removed)
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
app = Flask(__name__)
app.config['SECRET_KEY'] = SECRET_KEY
app.config['DEBUG'] = DEBUG  # Use the value from config instead of hardcoding
app.config['TEMPLATES_AUTO_RELOAD'] = DEBUG  # Only auto-reload templates in debug mode
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0 if DEBUG else 31536000  # 1 year in production
app.jinja_env.auto_reload = DEBUG  # Only auto-reload Jinja in debug mode
# Agent mode MCP server script path
app.config['MCP_SERVER_SCRIPT_PATH'] = MCP_SERVER_SCRIPT_PATH

# Set secure cookie settings
app.config['SESSION_COOKIE_SECURE'] = not DEBUG  # Secure in production
app.config['SESSION_COOKIE_HTTPONLY'] = True  # HttpOnly flag
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'  # SameSite attribute
app.config['PERMANENT_SESSION_LIFETIME'] = 86400  # 24 hours in seconds

# Register template filters
register_filters(app)

# Initialize the SQL generation manager
sql_manager = SQLGenerationManager()

# Initialize user manager
user_manager = UserManager()

# Initialize the background task manager
background_task_mgr = BackgroundTaskManager(sql_manager, user_manager)

# Set up knowledge base permissions
from src.utils.setup_knowledge_permissions import setup_knowledge_permissions
setup_knowledge_permissions()

# Configure uploads folder for knowledge base documents
from config.config import UPLOADS_DIR
app.config['UPLOAD_FOLDER'] = UPLOADS_DIR

# Register blueprints
app.register_blueprint(schema_bp)
app.register_blueprint(auth_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(admin_api_bp)
app.register_blueprint(admin_db_bp)
app.register_blueprint(security_bp)
app.register_blueprint(vector_db_bp)
app.register_blueprint(knowledge_bp)
app.register_blueprint(metadata_search_bp)
app.register_blueprint(agent_bp)  # Register the agent blueprint
app.register_blueprint(tool_confirmation_bp)  # Register tool confirmation blueprint
from src.routes.config_routes import config_bp
app.register_blueprint(config_bp)
from src.routes.query_editor_routes import query_editor_bp
app.register_blueprint(query_editor_bp)
# Register MCP server management blueprint
from src.routes.mcp_admin_routes import mcp_admin_bp
app.register_blueprint(mcp_admin_bp)
# Register skill management blueprint
app.register_blueprint(skill_bp)

# Make CSRF token available in templates
@app.context_processor
def inject_csrf_token():
    return dict(csrf_token=generate_csrf_token)

# Store query progress
query_progress = {}

# Import login_required from auth_utils
from src.utils.auth_utils import login_required

@app.route('/')
@login_required
@permission_required(Permissions.VIEW_INDEX)
def index():
    """Render the main application page"""
    logger.debug("Main page requested")
    # Get workspaces from schema manager instead of hardcoded values
    workspaces = sql_manager.schema_manager.get_workspaces()
    return render_template('index.html', workspaces=workspaces)

@app.route('/api/query', methods=['POST'])
@login_required
@permission_required(Permissions.RUN_QUERIES)
def process_query():
    """Process a natural language query and return results"""
    data = request.get_json()
    
    if not data or 'query' not in data:
        logger.warning("API request received with no query")
        return jsonify({"error": "No query provided"}), 400
        
    query = data.get('query').replace("@","table ")
    workspace_name = data.get('workspace', 'Default')
    explicit_tables = data.get('tables', [])  # Get user-specified tables if provided
    
    # Log if explicit tables are provided
    if explicit_tables:
        logger.info(f"User explicitly specified tables: {', '.join(explicit_tables)}")
    
    # Generate unique ID for this query
    query_id = str(uuid.uuid4())
    query_progress[query_id] = {
        'status': 'processing',
        'current_step': 0,
        'steps': [],
        'result': None,
        'error': None,
        'start_time': time.time()  # Add timestamp when query is initiated
    }
    
    selected_workspaces = [w for w in sql_manager.schema_manager.get_workspaces() if w['name'] == workspace_name]
    
    # Capture the user_id from the session before starting the background thread
    user_id = session.get('user_id')
    
    # Capture client IP address
    ip_address = request.remote_addr
    
    # Start processing in background using the BackgroundTaskManager
    background_task_mgr.process_query_task(
        query_id=query_id,
        query=query,
        workspace_name=workspace_name,
        selected_workspaces=selected_workspaces,
        explicit_tables=explicit_tables,
        user_id=user_id,
        query_progress=query_progress,
        update_progress_func=update_progress,
        ip_address=ip_address  # Pass the IP address to the background task
    )
    
    return jsonify({
        "query_id": query_id,
        "status": "processing"
    })

@app.route('/api/tables/suggestions', methods=['GET'])
@login_required
def get_table_suggestions():
    """Get table suggestions for autocomplete feature"""
    workspace_name = request.args.get('workspace', 'Default')
    query = request.args.get('query', '').lower()  # Optional search query for filtering
    
    logger.debug(f"Table suggestions requested for workspace: {workspace_name}, query: '{query}'")
    
    try:
        # Get all tables from schema manager
        tables = sql_manager.schema_manager.get_tables(workspace_name)
        
        # Format results with name and description
        table_info = []
        for table in tables:
            table_data = {
                "name": table["name"],
                "description": table.get("description", "")
            }
            
            # If a query is provided, filter tables that match
            if query:
                if query in table_data["name"].lower() or query in table_data["description"].lower():
                    table_info.append(table_data)
            else:
                table_info.append(table_data)
        
        # Sort alphabetically by name
        table_info.sort(key=lambda x: x["name"])
        
        return jsonify({"suggestions": table_info})
    except Exception as e:
        logger.exception(f"Error retrieving table suggestions: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/query/progress/<query_id>', methods=['GET'])
@login_required
def get_query_progress(query_id):
    """Get the progress of a query"""
    if query_id not in query_progress:
        return jsonify({"error": "Query not found"}), 404
        
    progress = query_progress[query_id]
    
    # If query is complete, clean up
    if progress['status'] in ['completed', 'error']:
        result = progress.copy()
        if progress['status'] == 'completed':
            del query_progress[query_id]  # Clean up completed queries
        return jsonify(result)
    
    # Check for timeout (2 minutes = 120 seconds)
    current_time = time.time()
    if 'start_time' in progress and (current_time - progress['start_time']) > 120:
        logger.warning(f"Query {query_id} timed out after 2 minutes")
        progress['status'] = 'error'
        progress['error'] = "Query processing timed out after 2 minutes"
        result = progress.copy()
        return jsonify(result), 408  # Return 408 Request Timeout status
        
    return jsonify(progress)

def update_progress(query_id, step_info):
    """Update the progress of a query"""
    if query_id in query_progress:
        query_progress[query_id]['current_step'] += 1
        query_progress[query_id]['steps'].append(step_info)

@app.route('/api/schema', methods=['GET'])
@login_required
@permission_required(Permissions.VIEW_SCHEMA)
def get_schema():
    """Get the database schema"""
    start_time = time.time()
    workspace_name = request.args.get('workspace', 'Default')
    
    logger.info(f"Schema requested for workspace: {workspace_name}")
    
    try:
        # Get schema data
        tables = sql_manager.schema_manager.get_tables(workspace_name)
        
        # Convert tables to a simpler format for frontend
        schema_data = []
        for table in tables:
            table_info = {
                "name": table["name"],
                "description": table.get("description", ""),
                "columns": []
            }
            
            for col in table.get("columns", []):
                column_info = {
                    "name": col["name"],
                    "datatype": col["datatype"],
                    "description": col.get("description", ""),
                    "is_primary_key": col.get("is_primary_key", False)
                }
                table_info["columns"].append(column_info)
            
            schema_data.append(table_info)
        
        processing_time = time.time() - start_time
        logger.debug(f"Schema retrieval completed in {processing_time:.3f}s")
        
        return jsonify({"schema": schema_data})
    except Exception as e:
        logger.exception(f"Error retrieving database schema: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/feedback', methods=['POST'])
@login_required
def submit_feedback():
    """Save user feedback on a generated SQL query"""
    data = request.get_json()
    
    if not data:
        logger.warning("Feedback API request received with no data")
        return jsonify({"error": "No feedback data provided"}), 400
        
    required_fields = ['query_text', 'sql_query', 'feedback_rating']
    missing_fields = [field for field in required_fields if field not in data]
    if missing_fields:
        logger.warning(f"Feedback API missing required fields: {', '.join(missing_fields)}")
        return jsonify({"error": f"Missing required fields: {', '.join(missing_fields)}"}), 400
    
    # Extract data
    query_text = data.get('query_text')
    sql_query = data.get('sql_query')
    feedback_rating = int(data.get('feedback_rating'))  # 1 for thumbs up, 0 for thumbs down
    results_summary = data.get('results_summary', '')
    workspace = data.get('workspace', 'Default')
    tables_used = data.get('tables_used', [])
    
    logger.info(f"Feedback received for query: '{query_text[:50]}...' - Rating: {feedback_rating}")
    
    try:
        # Initialize feedback manager
        feedback_mgr = FeedbackManager()
        
        # Save the feedback
        success = feedback_mgr.save_feedback(
            query_text=query_text,
            sql_query=sql_query,
            results_summary=results_summary,
            workspace=workspace,
            feedback_rating=feedback_rating,
            tables_used=tables_used
        )
        
        # Log audit for feedback
        if session.get('user_id'):
            user_manager.log_audit_event(
                user_id=session.get('user_id'),
                action='submit_feedback',
                details=f"Feedback rating: {feedback_rating}",
                query_text=query_text,
                sql_query=sql_query,
                response=None
            )
        
        if success:
            return jsonify({"success": True, "message": "Feedback saved successfully"})
        else:
            logger.error("Failed to save feedback")
            return jsonify({"error": "Failed to save feedback"}), 500
            
    except Exception as e:
        logger.exception(f"Error saving feedback: {str(e)}")
        return jsonify({"error": f"Error saving feedback: {str(e)}"}), 500

@app.route('/api/samples', methods=['GET', 'POST'])
@login_required
def manage_samples():
    """Get or create sample entries"""
    if request.method == 'POST':
        # Create a new sample - requires MANAGE_SAMPLES permission
        if not user_manager.has_permission(session.get('user_id'), Permissions.MANAGE_SAMPLES):
            return jsonify({"error": "Permission denied"}), 403
            
        data = request.get_json()
        
        if not data:
            logger.warning("Samples API request received with no data")
            return jsonify({"error": "No sample data provided"}), 400
            
        required_fields = ['query_text', 'sql_query']
        missing_fields = [field for field in required_fields if field not in data]
        if missing_fields:
            logger.warning(f"Samples API missing required fields: {', '.join(missing_fields)}")
            return jsonify({"error": f"Missing required fields: {', '.join(missing_fields)}"}), 400
        
        # Extract data
        query_text = data.get('query_text')
        sql_query = data.get('sql_query')
        results_summary = data.get('results_summary', 'Manual sample entry')
        workspace = data.get('workspace', 'Default')
        tables_used = data.get('tables_used', [])
        
        try:
            # Initialize feedback manager
            feedback_mgr = FeedbackManager()
            
            # Save the sample
            success = feedback_mgr.save_feedback(
                query_text=query_text,
                sql_query=sql_query,
                results_summary=results_summary,
                workspace=workspace,
                feedback_rating=1,  # Always positive for manual samples
                tables_used=tables_used,
                is_manual_sample=True
            )
            
            # Log audit for sample creation
            if session.get('user_id'):
                user_manager.log_audit_event(
                    user_id=session.get('user_id'),
                    action='create_sample',
                    details=f"Created sample in workspace: {workspace}",
                    query_text=query_text,
                    sql_query=sql_query,
                    response=None
                )
            
            if success:
                return jsonify({"success": True, "message": "Sample saved successfully"})
            else:
                logger.error("Failed to save sample")
                return jsonify({"error": "Failed to save sample"}), 500
                
        except Exception as e:
            logger.exception(f"Error saving sample: {str(e)}")
            return jsonify({"error": f"Error saving sample: {str(e)}"}), 500
    else:
        # GET method - retrieve samples - requires VIEW_SAMPLES permission
        if not user_manager.has_permission(session.get('user_id'), Permissions.VIEW_SAMPLES):
            return jsonify({"error": "Permission denied"}), 403
            
        try:
            page = request.args.get('page', 1, type=int)
            limit = request.args.get('limit', 10, type=int)
            search_query = request.args.get('query', None)
            
            # Initialize feedback manager
            feedback_mgr = FeedbackManager()
            
            # Get samples
            samples, total = feedback_mgr.get_samples(page, limit, search_query)
            
            return jsonify({
                "success": True,
                "samples": samples,
                "total": total,
                "page": page,
                "limit": limit
            })
                
        except Exception as e:
            logger.exception(f"Error retrieving samples: {str(e)}")
            return jsonify({"error": f"Error retrieving samples: {str(e)}"}), 500

@app.route('/api/samples/<int:sample_id>', methods=['GET', 'PUT', 'DELETE'])
@login_required
def manage_sample(sample_id):
    """Get, update or delete a specific sample entry"""
    feedback_mgr = FeedbackManager()
    
    if request.method == 'GET':
        # View a specific sample - requires VIEW_SAMPLES permission
        if not user_manager.has_permission(session.get('user_id'), Permissions.VIEW_SAMPLES):
            return jsonify({"error": "Permission denied"}), 403
            
        try:
            sample = feedback_mgr.get_sample_by_id(sample_id)
            
            if sample:
                return jsonify(sample)
            else:
                return jsonify({"error": "Sample not found"}), 404
                
        except Exception as e:
            logger.exception(f"Error retrieving sample {sample_id}: {str(e)}")
            return jsonify({"error": f"Error retrieving sample: {str(e)}"}), 500
            
    elif request.method == 'PUT':
        # Update an existing sample - requires MANAGE_SAMPLES permission
        if not user_manager.has_permission(session.get('user_id'), Permissions.MANAGE_SAMPLES):
            return jsonify({"error": "Permission denied"}), 403
            
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "No update data provided"}), 400
            
        required_fields = ['query_text', 'sql_query']
        missing_fields = [field for field in required_fields if field not in data]
        if missing_fields:
            return jsonify({"error": f"Missing required fields: {', '.join(missing_fields)}"}), 400
        
        try:
            success = feedback_mgr.update_sample(sample_id, data)
            
            # Log audit for sample update
            if session.get('user_id'):
                user_manager.log_audit_event(
                    user_id=session.get('user_id'),
                    action='update_sample',
                    details=f"Updated sample ID: {sample_id}",
                    query_text=data.get('query_text'),
                    sql_query=data.get('sql_query'),
                    response=None
                )
            
            if success:
                return jsonify({"success": True, "message": "Sample updated successfully"})
            else:
                return jsonify({"error": "Failed to update sample"}), 500
                
        except Exception as e:
            logger.exception(f"Error updating sample {sample_id}: {str(e)}")
            return jsonify({"error": f"Error updating sample: {str(e)}"}), 500
            
    elif request.method == 'DELETE':
        # Delete a sample - requires MANAGE_SAMPLES permission
        if not user_manager.has_permission(session.get('user_id'), Permissions.MANAGE_SAMPLES):
            return jsonify({"error": "Permission denied"}), 403
            
        try:
            # Get sample before deletion for audit
            sample = feedback_mgr.get_sample_by_id(sample_id)
            success = feedback_mgr.delete_sample(sample_id)
            
            # Log audit for sample deletion
            if session.get('user_id') and sample:
                user_manager.log_audit_event(
                    user_id=session.get('user_id'),
                    action='delete_sample',
                    details=f"Deleted sample ID: {sample_id}",
                    query_text=sample.get('query_text'),
                    sql_query=sample.get('sql_query'),
                    response=None
                )
            
            if success:
                return jsonify({"success": True, "message": "Sample deleted successfully"})
            else:
                return jsonify({"error": "Failed to delete sample"}), 500
                
        except Exception as e:
            logger.exception(f"Error deleting sample {sample_id}: {str(e)}")
            return jsonify({"error": f"Error deleting sample: {str(e)}"}), 500

@app.route('/api/feedback/stats', methods=['GET'])
@login_required
def get_feedback_stats():
    """Get statistics about stored feedback"""
    try:
        # Initialize feedback manager
        feedback_mgr = FeedbackManager()
        
        # Get feedback statistics
        stats = feedback_mgr.get_feedback_stats()
        
        return jsonify({"success": True, "stats": stats})
    except Exception as e:
        logger.exception(f"Error retrieving feedback stats: {str(e)}")
        return jsonify({"error": f"Error retrieving feedback stats: {str(e)}"}), 500

@app.route('/samples')
@login_required
@permission_required(Permissions.VIEW_SAMPLES)
def samples_page():
    """Render the samples management page"""
    logger.debug("Samples management page requested")
    workspaces = sql_manager.schema_manager.get_workspaces()
    return render_template('samples.html', workspaces=workspaces)

@app.route('/api/workspaces', methods=['GET'])
@login_required
def get_workspaces():
    """Get the list of available workspaces"""
    logger.debug("Workspaces list requested")
    workspaces = sql_manager.schema_manager.get_workspaces()
    return jsonify({"workspaces": workspaces})

@app.route('/api/tables', methods=['GET'])
@login_required
def get_tables_for_workspace():
    """Get the list of tables for a workspace"""
    workspace_name = request.args.get('workspace', 'Default')
    logger.debug(f"Tables list requested for workspace: {workspace_name}")
    
    try:
        # Get tables from schema manager
        tables = sql_manager.schema_manager.get_table_names(workspace_name)
        return jsonify({"tables": tables})
    except Exception as e:
        logger.exception(f"Error retrieving tables: {str(e)}")
        return jsonify({"error": str(e)}), 500

# Context processor to add user information to templates
@app.context_processor
def inject_user():
    """Add user information to all templates"""
    user = None
    is_admin = False
    
    if session.get('user_id'):
        user_id = session.get('user_id')
        user = user_manager.get_user_by_id(user_id)
        is_admin = user_manager.has_role(user_id, 'admin')
    
    # Always return a dictionary, regardless of login state
    return dict(
        current_user=user,
        is_admin=is_admin,
        user_manager=user_manager,
        has_permission=lambda permission: user_manager.has_permission(session.get('user_id'), permission) if session.get('user_id') else False,
        permissions=Permissions
    )

@app.errorhandler(404)
def page_not_found(e):
    """Handle 404 errors"""
    return render_template('404.html'), 404

@app.errorhandler(500)
def server_error(e):
    """Handle 500 errors"""
    return render_template('500.html'), 500

# Add a special route to trigger reload manually if needed
@app.route('/reload')
@login_required
@admin_required
def reload_app():
    """Force the application to reload itself"""
    logger.info("Manual reload requested")
    os.kill(os.getpid(), signal.SIGUSR1)
    return "Reloading..."

# Move initialization logic to an app setup function that registers with Flask
def init_app_with_context(app):
    """Initialize application components that need the app context"""
    # Initialize immediately within app context
    with app.app_context():
        logger.info("Initializing application-wide components")
        initialize_mcp_servers()
        logger.info("Application-wide components initialization complete")

# Register initialization function with the app
init_app_with_context(app)

# Register cleanup functions for proper shutdown
def shutdown_handler(signal_received=None, frame=None):
    """Handle application shutdown gracefully"""
    print("Shutting down application...")
    
    # Clean up MCP clients
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(MCPClientManager.cleanup_all())
    except Exception as e:
        print(f"Error cleaning up MCP clients: {e}")
    finally:
        loop.close()
    
    if sql_manager:
        sql_manager.close()
    print("Application shutdown complete.")
    sys.exit(0)

# Register signal handlers for graceful shutdown
signal.signal(signal.SIGINT, shutdown_handler)   # Ctrl+C
signal.signal(signal.SIGTERM, shutdown_handler)  # kill command

# Register Flask teardown function
@app.teardown_appcontext
def teardown_app_context(exception):
    # This runs when the application context ends
    pass  # We use the signal handlers for actual cleanup

if __name__ == '__main__':
    try:
        if 'GITHUB_TOKEN' not in os.environ:
            print("Error: GITHUB_TOKEN environment variable is not set.")
            print("Please set your GitHub token as an environment variable:")
            print("export GITHUB_TOKEN=your_token_here")
            sys.exit(1)
            
        # Print debug information to confirm settings
        print("Starting Flask app:")
        print(f"DEBUG mode: {app.debug}")
        print(f"TEMPLATES_AUTO_RELOAD: {app.config['TEMPLATES_AUTO_RELOAD']}")
        print(f"JINJA auto_reload: {app.jinja_env.auto_reload}")
        print(f"Working directory: {os.getcwd()}")
        print(f"MCP server script path: {MCP_SERVER_SCRIPT_PATH}")
        
        # Check if application is in main process or reloader mode
        is_reloader_process = os.environ.get('WERKZEUG_RUN_MAIN') == 'true'
        
        if is_reloader_process:
            logger.info("Running in reloader subprocess - skipping redundant initialization logs")
        
        # Run the app with controlled reloader settings
        app.run(host='0.0.0.0', port=5000, debug=DEBUG, use_reloader=DEBUG, threaded=True)
        
    finally:
        # Ensure cleanup happens
        shutdown_handler()