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
app.config['DEBUG'] = DEBUG

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
        
    query = data.get('query')
    workspace_name = data.get('workspace', 'Default')
    
    # Generate unique ID for this query
    query_id = str(uuid.uuid4())
    query_progress[query_id] = {
        'status': 'processing',
        'current_step': 0,
        'steps': [],
        'result': None,
        'error': None
    }
    
    selected_workspaces = [w for w in workspaces if w['name'] == workspace_name]
    
    # Start processing in background
    def process_in_background():
        try:
            result = sql_manager.process_query(query, selected_workspaces, 
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

if __name__ == '__main__':
    try:
        if 'GITHUB_TOKEN' not in os.environ:
            print("Error: GITHUB_TOKEN environment variable is not set.")
            print("Please set your GitHub token as an environment variable:")
            print("export GITHUB_TOKEN=your_token_here")
            sys.exit(1)
            
        app.run(host='0.0.0.0', port=5000, debug=DEBUG, use_reloader=True)
    finally:
        sql_manager.close()