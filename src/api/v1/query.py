"""
Query processing API endpoints
"""
import logging
import time
import uuid
from flask import Blueprint, request, jsonify
from src.middleware import token_required, api_permission_required, APIException
from src.models.sql_generator import SQLGenerationManager
from src.models.user import Permissions
from src.utils.user_manager import UserManager
from src.utils.background_tasks import BackgroundTaskManager

logger = logging.getLogger(__name__)

query_api = Blueprint('query_api', __name__)

# Initialize managers
sql_manager = SQLGenerationManager()
user_manager = UserManager()
background_task_mgr = BackgroundTaskManager(sql_manager, user_manager)

# Store query progress (in production, use Redis or similar)
query_progress = {}

@query_api.route('/submit', methods=['POST'])
@token_required
@api_permission_required(Permissions.RUN_QUERIES)
def api_submit_query():
    """Submit a natural language query for processing"""
    try:
        data = request.get_json()
        if not data:
            raise APIException('Request body is required', 400)
        
        query = data.get('query')
        if not query:
            raise APIException('Query is required', 400)
        
        workspace_name = data.get('workspace', 'Default')
        explicit_tables = data.get('tables', [])
        
        # Replace @ mentions with table
        query = query.replace("@", "table ")
        
        # Generate unique ID for this query
        query_id = str(uuid.uuid4())
        query_progress[query_id] = {
            'status': 'processing',
            'current_step': 0,
            'steps': [],
            'result': None,
            'error': None,
            'start_time': time.time()
        }
        
        # Get workspace information
        selected_workspaces = [w for w in sql_manager.schema_manager.get_workspaces() 
                             if w['name'] == workspace_name]
        
        # Get user information
        user_id = request.current_user['user_id']
        ip_address = request.remote_addr
        
        # Log if explicit tables are provided
        if explicit_tables:
            logger.info(f"User explicitly specified tables: {', '.join(explicit_tables)}")
        
        # Start processing in background
        background_task_mgr.process_query_task(
            query_id=query_id,
            query=query,
            workspace_name=workspace_name,
            selected_workspaces=selected_workspaces,
            explicit_tables=explicit_tables,
            user_id=user_id,
            query_progress=query_progress,
            update_progress_func=update_progress,
            ip_address=ip_address
        )
        
        return jsonify({
            'query_id': query_id,
            'status': 'processing',
            'message': 'Query submitted for processing'
        }), 202
        
    except APIException:
        raise
    except Exception as e:
        logger.exception(f"Error submitting query: {str(e)}")
        raise APIException('Failed to submit query', 500)

@query_api.route('/progress/<query_id>', methods=['GET'])
@token_required
def api_get_query_progress(query_id):
    """Get the progress of a query"""
    try:
        if query_id not in query_progress:
            raise APIException('Query not found', 404)
        
        progress = query_progress[query_id]
        
        # Check for timeout (2 minutes = 120 seconds)
        current_time = time.time()
        if 'start_time' in progress and (current_time - progress['start_time']) > 120:
            logger.warning(f"Query {query_id} timed out after 2 minutes")
            progress['status'] = 'error'
            progress['error'] = "Query processing timed out after 2 minutes"
            return jsonify(progress), 408  # Request Timeout
        
        # If query is complete, clean up
        if progress['status'] in ['completed', 'error']:
            result = progress.copy()
            if progress['status'] == 'completed':
                del query_progress[query_id]  # Clean up completed queries
            return jsonify(result), 200
        
        return jsonify(progress), 200
        
    except APIException:
        raise
    except Exception as e:
        logger.exception(f"Error getting query progress: {str(e)}")
        raise APIException('Failed to get query progress', 500)

@query_api.route('/schema', methods=['GET'])
@token_required
@api_permission_required(Permissions.VIEW_SCHEMA)
def api_get_schema():
    """Get the database schema"""
    try:
        workspace_name = request.args.get('workspace', 'Default')
        
        logger.info(f"API schema requested for workspace: {workspace_name}")
        
        # Get schema data
        tables = sql_manager.schema_manager.get_tables(workspace_name)
        
        # Convert tables to API format
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
        
        return jsonify({
            'schema': schema_data,
            'workspace': workspace_name
        }), 200
        
    except Exception as e:
        logger.exception(f"Error retrieving database schema: {str(e)}")
        raise APIException('Failed to retrieve schema', 500)

@query_api.route('/workspaces', methods=['GET'])
@token_required
def api_get_workspaces():
    """Get the list of available workspaces"""
    try:
        logger.debug("API workspaces list requested")
        
        workspaces = sql_manager.schema_manager.get_workspaces()
        
        # Audit log the workspaces request
        user_manager.log_audit_event(
            user_id=request.current_user['user_id'],
            action='api_get_workspaces',
            details=f"Retrieved {len(workspaces)} workspaces via API",
            ip_address=request.remote_addr
        )
        
        return jsonify({
            'workspaces': workspaces
        }), 200
        
    except Exception as e:
        logger.exception(f"Error retrieving workspaces: {str(e)}")
        
        # Audit log the error
        user_manager.log_audit_event(
            user_id=request.current_user['user_id'],
            action='api_get_workspaces_error',
            details=f"Error retrieving workspaces via API: {str(e)}",
            ip_address=request.remote_addr
        )
        raise APIException('Failed to retrieve workspaces', 500)

@query_api.route('/tables', methods=['GET'])
@token_required
def api_get_tables():
    """Get the list of tables for a workspace"""
    try:
        workspace_name = request.args.get('workspace', 'Default')
        logger.debug(f"API tables list requested for workspace: {workspace_name}")
        
        # Get tables from schema manager
        tables = sql_manager.schema_manager.get_table_names(workspace_name)
        
        # Audit log the tables request
        user_manager.log_audit_event(
            user_id=request.current_user['user_id'],
            action='api_get_tables',
            details=f"Retrieved {len(tables)} tables for workspace: {workspace_name} via API",
            ip_address=request.remote_addr
        )
        
        return jsonify({
            'tables': tables,
            'workspace': workspace_name
        }), 200
        
    except Exception as e:
        logger.exception(f"Error retrieving tables: {str(e)}")
        
        # Audit log the error
        user_manager.log_audit_event(
            user_id=request.current_user['user_id'],
            action='api_get_tables_error',
            details=f"Error retrieving tables for workspace {workspace_name} via API: {str(e)}",
            ip_address=request.remote_addr
        )
        raise APIException('Failed to retrieve tables', 500)

@query_api.route('/suggestions', methods=['GET'])
@token_required
def api_get_table_suggestions():
    """Get table suggestions for autocomplete"""
    try:
        workspace_name = request.args.get('workspace', 'Default')
        query = request.args.get('query', '').lower()
        
        logger.debug(f"API table suggestions requested for workspace: {workspace_name}, query: '{query}'")
        
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
        
        # Audit log the table suggestions request
        user_manager.log_audit_event(
            user_id=request.current_user['user_id'],
            action='api_get_table_suggestions',
            details=f"Retrieved {len(table_info)} table suggestions for workspace: {workspace_name} via API" + (f", filtered by: '{query}'" if query else ""),
            ip_address=request.remote_addr
        )
        
        return jsonify({
            'suggestions': table_info,
            'workspace': workspace_name
        }), 200
        
    except Exception as e:
        logger.exception(f"Error retrieving table suggestions: {str(e)}")
        
        # Audit log the error
        user_manager.log_audit_event(
            user_id=request.current_user['user_id'],
            action='api_get_table_suggestions_error',
            details=f"Error retrieving table suggestions for workspace {workspace_name} via API: {str(e)}",
            ip_address=request.remote_addr
        )
        raise APIException('Failed to retrieve table suggestions', 500)

def update_progress(query_id, step_info):
    """Update the progress of a query"""
    if query_id in query_progress:
        query_progress[query_id]['current_step'] += 1
        query_progress[query_id]['steps'].append(step_info)