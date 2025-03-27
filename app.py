from flask import Flask, render_template, request, jsonify, session
from src.models.sql_generator import SQLGenerationManager
from src.utils.feedback_manager import FeedbackManager
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
    
    # Enable debug logging specifically for SQL generator and agents
    logging.getLogger('text2sql.sql_generator').setLevel(logging.DEBUG)
    logging.getLogger('text2sql.agents.intent').setLevel(logging.DEBUG)
    logging.getLogger('text2sql.agents.table').setLevel(logging.DEBUG)
    logging.getLogger('text2sql.agents.column').setLevel(logging.DEBUG)
    
    # Log that debug mode is enabled for these components
    app_logger.info("Debug logging enabled for SQL generator and agents")
    
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

@app.route('/api/feedback', methods=['POST'])
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
        
        if success:
            return jsonify({"success": True, "message": "Feedback saved successfully"})
        else:
            logger.error("Failed to save feedback")
            return jsonify({"error": "Failed to save feedback"}), 500
            
    except Exception as e:
        logger.exception(f"Error saving feedback: {str(e)}")
        return jsonify({"error": f"Error saving feedback: {str(e)}"}), 500

@app.route('/api/samples', methods=['GET', 'POST'])
def manage_samples():
    """Get or create sample entries"""
    if request.method == 'POST':
        # Create a new sample
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
            
            if success:
                return jsonify({"success": True, "message": "Sample saved successfully"})
            else:
                logger.error("Failed to save sample")
                return jsonify({"error": "Failed to save sample"}), 500
                
        except Exception as e:
            logger.exception(f"Error saving sample: {str(e)}")
            return jsonify({"error": f"Error saving sample: {str(e)}"}), 500
    else:
        # GET method - retrieve samples
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
def manage_sample(sample_id):
    """Get, update or delete a specific sample entry"""
    feedback_mgr = FeedbackManager()
    
    if request.method == 'GET':
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
        # Update an existing sample
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "No update data provided"}), 400
            
        required_fields = ['query_text', 'sql_query']
        missing_fields = [field for field in required_fields if field not in data]
        if missing_fields:
            return jsonify({"error": f"Missing required fields: {', '.join(missing_fields)}"}), 400
        
        try:
            success = feedback_mgr.update_sample(sample_id, data)
            
            if success:
                return jsonify({"success": True, "message": "Sample updated successfully"})
            else:
                return jsonify({"error": "Failed to update sample"}), 500
                
        except Exception as e:
            logger.exception(f"Error updating sample {sample_id}: {str(e)}")
            return jsonify({"error": f"Error updating sample: {str(e)}"}), 500
            
    elif request.method == 'DELETE':
        # Delete a sample
        try:
            success = feedback_mgr.delete_sample(sample_id)
            
            if success:
                return jsonify({"success": True, "message": "Sample deleted successfully"})
            else:
                return jsonify({"error": "Failed to delete sample"}), 500
                
        except Exception as e:
            logger.exception(f"Error deleting sample {sample_id}: {str(e)}")
            return jsonify({"error": f"Error deleting sample: {str(e)}"}), 500

@app.route('/api/feedback/stats', methods=['GET'])
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
def samples_page():
    """Render the samples management page"""
    logger.debug("Samples management page requested")
    return render_template('samples.html', workspaces=workspaces)

@app.route('/api/workspaces', methods=['GET'])
def get_workspaces():
    """Get the list of available workspaces"""
    logger.debug("Workspaces list requested")
    return jsonify({"workspaces": workspaces})

@app.route('/api/tables', methods=['GET'])
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