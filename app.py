from flask import Flask, render_template, request, jsonify, session
from src.models.sql_generator import SQLGenerationManager
from config.config import SECRET_KEY, DEBUG
import logging
import os
import sys
import time
import uuid
from datetime import datetime
from threading import Thread
import signal

# Configure logging
def setup_logging(log_level=logging.DEBUG):
    """Configure application logging"""
    log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs')
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    # Set up main application logger
    app_logger = logging.getLogger('text2sql')
    app_logger.setLevel(log_level)
    
    formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    app_logger.addHandler(console_handler)
    
    # File handlers
    handlers = {
        'text2sql.log': logging.DEBUG,
        'error.log': logging.ERROR,
        'queries.log': logging.INFO
    }
    
    for filename, level in handlers.items():
        handler = logging.FileHandler(os.path.join(log_dir, filename))
        handler.setLevel(level)
        handler.setFormatter(formatter)
        app_logger.addHandler(handler)
    
    return app_logger

# Initialize logger
logger = setup_logging(logging.DEBUG if DEBUG else logging.INFO)

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = SECRET_KEY
app.config['DEBUG'] = True  # Force debug mode on
app.config['TEMPLATES_AUTO_RELOAD'] = True
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0  # Disable caching for static files
app.jinja_env.auto_reload = True  # Force Jinja template reloading

# Initialize the SQL generation manager
sql_manager = SQLGenerationManager()

# Define workspaces
workspaces = [
    {
        "name": "Default",
        "description": "Default workspace with access to all tables"
    },
    {
        "name": "Sales",
        "description": "Sales-related data including customers, orders, and products"
    },
    {
        "name": "Analytics",
        "description": "Analytical data for business intelligence and reporting"
    }
]

# Store query progress
query_progress = {}

@app.route('/')
def index():
    """Render the main application page"""
    logger.debug("Main page requested")
    return render_template('index.html', workspaces=workspaces)

@app.route('/api/query', methods=['POST'])
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
    
    selected_workspaces = [w for w in workspaces if w['name'] == workspace_name]
    
    # Start processing in background
    def process_in_background():
        try:
            result = sql_manager.process_query(query, selected_workspaces, explicit_tables,
                                            progress_callback=lambda step: update_progress(query_id, step))
            query_progress[query_id]['result'] = result
            query_progress[query_id]['status'] = 'completed'
        except Exception as e:
            logger.exception(f"Exception while processing query: {str(e)}")
            query_progress[query_id]['error'] = str(e)
            query_progress[query_id]['status'] = 'error'
    
    Thread(target=process_in_background).start()
    
    return jsonify({
        "query_id": query_id,
        "status": "processing"
    })

@app.route('/api/tables/suggestions', methods=['GET'])
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
def reload_app():
    """Force the application to reload itself"""
    logger.info("Manual reload requested")
    os.kill(os.getpid(), signal.SIGUSR1)
    return "Reloading..."

if __name__ == '__main__':
    try:
        if 'GITHUB_TOKEN' not in os.environ:
            print("Error: GITHUB_TOKEN environment variable is not set.")
            print("Please set your GitHub token as an environment variable:")
            print("export GITHUB_TOKEN=your_token_here")
            sys.exit(1)
            
        # Print debug information to confirm settings
        print("Starting Flask app with auto-reload enabled:")
        print(f"DEBUG mode: {app.debug}")
        print(f"TEMPLATES_AUTO_RELOAD: {app.config['TEMPLATES_AUTO_RELOAD']}")
        print(f"JINJA auto_reload: {app.jinja_env.auto_reload}")
        print(f"Working directory: {os.getcwd()}")
        
        # Run the app with explicit settings to ensure reloader works
        app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=True, threaded=True)
        
    finally:
        sql_manager.close()