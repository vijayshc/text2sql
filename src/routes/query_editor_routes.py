from flask import Blueprint, render_template, request, jsonify, session
from src.utils.database import DatabaseManager
from src.models.sql_generator import SQLGenerationManager
from src.utils.user_manager import UserManager
import logging

# Setup logger
logger = logging.getLogger('text2sql')

# Create Blueprint
query_editor_bp = Blueprint('query_editor', __name__)

# Initialize SQL generation manager and user manager
sql_manager = SQLGenerationManager()
user_manager = UserManager()

@query_editor_bp.route('/query-editor')
def query_editor():
    """Render the query editor page"""
    # Audit log the query editor page access
    user_manager.log_audit_event(
        user_id=session.get('user_id'),
        action='access_query_editor',
        details="Accessed query editor page",
        ip_address=request.remote_addr
    )
    
    # Get workspaces from schema manager instead of user manager
    workspaces = sql_manager.schema_manager.get_workspaces()
    return render_template('query_editor.html', 
                          user_manager=user_manager,
                          workspaces=workspaces)

@query_editor_bp.route('/api/execute-query', methods=['POST'])
def execute_query_api():
    """Execute a SQL query and return results"""
    try:
        data = request.get_json()
        sql_query = data.get('query', '')
        workspace = data.get('workspace', 'Default')
        
        if not sql_query.strip():
            # Audit log failed query execution
            user_manager.log_audit_event(
                user_id=session.get('user_id'),
                action='execute_query_editor_error',
                details="Query execution failed: Query is empty",
                ip_address=request.remote_addr,
                query_text=sql_query,
                sql_query=sql_query
            )
            return jsonify({'error': 'Query is empty'}), 400
            
        # Initialize database manager and execute query
        db_manager = DatabaseManager()
        if not db_manager.connect():
            # Audit log database connection failure
            user_manager.log_audit_event(
                user_id=session.get('user_id'),
                action='execute_query_editor_error',
                details="Query execution failed: Unable to connect to database",
                ip_address=request.remote_addr,
                query_text=sql_query,
                sql_query=sql_query
            )
            return jsonify({'error': 'Unable to connect to database'}), 500
            
        query_result = db_manager.execute_query(sql_query)
        
        if query_result['success']:
            # Convert DataFrame to list of dictionaries for JSON serialization
            results = query_result['data'].to_dict(orient='records') if query_result['data'] is not None else []
            
            # Ensure columns are converted to a list for proper JSON serialization
            columns = list(query_result['columns']) if query_result['columns'] else []
            
            # Audit log successful query execution
            user_manager.log_audit_event(
                user_id=session.get('user_id'),
                action='execute_query_editor',
                details=f"Query executed successfully in workspace: {workspace}. Returned {len(results)} rows",
                ip_address=request.remote_addr,
                query_text=sql_query,
                sql_query=sql_query,
                response=f"Returned {len(results)} rows with columns: {', '.join(columns)}"
            )
            
            return jsonify({
                'status': 'success',
                'results': results,
                'columns': columns
            })
        else:
            # Audit log failed query execution
            user_manager.log_audit_event(
                user_id=session.get('user_id'),
                action='execute_query_editor_error',
                details=f"Query execution failed in workspace: {workspace}. Error: {query_result['error']}",
                ip_address=request.remote_addr,
                query_text=sql_query,
                sql_query=sql_query,
                response=query_result['error']
            )
            return jsonify({'error': query_result['error']}), 500
    except Exception as e:
        logger.error(f"Error executing query: {str(e)}")
        
        # Audit log exception in query execution
        user_manager.log_audit_event(
            user_id=session.get('user_id'),
            action='execute_query_editor_error',
            details=f"Query execution exception: {str(e)}",
            ip_address=request.remote_addr,
            query_text=data.get('query', '') if 'data' in locals() else '',
            sql_query=data.get('query', '') if 'data' in locals() else ''
        )
        return jsonify({'error': str(e)}), 500

@query_editor_bp.route('/api/complete-query', methods=['POST'])
def complete_query():
    """Complete a SQL query using AI"""
    try:
        data = request.get_json()
        partial_query = data.get('query', '')
        workspace = data.get('workspace', '')
        
        if not partial_query.strip():
            # Audit log failed query completion
            user_manager.log_audit_event(
                user_id=session.get('user_id'),
                action='complete_query_error',
                details="Query completion failed: Partial query is empty",
                ip_address=request.remote_addr,
                query_text=partial_query
            )
            return jsonify({'error': 'Query is empty'}), 400
        
        # Use the same approach as text-to-SQL flow but with different prompt
        
        # Get tables and columns for completion
        completed_query = sql_manager.complete_sql_query(partial_query, workspace)
        
        # Audit log successful query completion
        user_manager.log_audit_event(
            user_id=session.get('user_id'),
            action='complete_query',
            details=f"Query completion successful in workspace: {workspace}",
            ip_address=request.remote_addr,
            query_text=partial_query,
            sql_query=completed_query,
            response=f"Query completed successfully"
        )
        
        return jsonify({
            'status': 'success',
            'completed_query': completed_query
        })
    except Exception as e:
        logger.error(f"Error completing query: {str(e)}")
        
        # Audit log exception in query completion
        user_manager.log_audit_event(
            user_id=session.get('user_id'),
            action='complete_query_error',
            details=f"Query completion exception: {str(e)}",
            ip_address=request.remote_addr,
            query_text=data.get('query', '') if 'data' in locals() else ''
        )
        return jsonify({'error': str(e)}), 500


@query_editor_bp.route('/api/save-query', methods=['POST'])
def save_query():
    """Save a SQL query"""
    try:
        data = request.get_json()
        sql_query = data.get('query', '')
        query_name = data.get('name', '')
        description = data.get('description', '')
        workspace = data.get('workspace', 'Default')
        
        if not sql_query.strip():
            # Audit log failed query save
            user_manager.log_audit_event(
                user_id=session.get('user_id'),
                action='save_query_error',
                details="Query save failed: Query is empty",
                ip_address=request.remote_addr,
                query_text=sql_query,
                sql_query=sql_query
            )
            return jsonify({'error': 'Query is empty'}), 400
            
        if not query_name.strip():
            # Audit log failed query save
            user_manager.log_audit_event(
                user_id=session.get('user_id'),
                action='save_query_error',
                details="Query save failed: Query name is required",
                ip_address=request.remote_addr,
                query_text=sql_query,
                sql_query=sql_query
            )
            return jsonify({'error': 'Query name is required'}), 400
            
        # Save the query using SQL manager
        query_id = sql_manager.save_user_query(
            sql_query, 
            query_name,
            description,
            session.get('user_id')
        )
        
        # Audit log successful query save
        user_manager.log_audit_event(
            user_id=session.get('user_id'),
            action='save_query',
            details=f"Query saved successfully: '{query_name}' in workspace: {workspace}",
            ip_address=request.remote_addr,
            query_text=f"Query Name: {query_name}, Description: {description}",
            sql_query=sql_query,
            response=f"Query saved with ID: {query_id}"
        )
        
        return jsonify({
            'status': 'success',
            'message': 'Query saved successfully',
            'query_id': query_id
        })
    except Exception as e:
        logger.error(f"Error saving query: {str(e)}")
        
        # Audit log exception in query save
        user_manager.log_audit_event(
            user_id=session.get('user_id'),
            action='save_query_error',
            details=f"Query save exception: {str(e)}",
            ip_address=request.remote_addr,
            query_text=data.get('query', '') if 'data' in locals() else '',
            sql_query=data.get('query', '') if 'data' in locals() else ''
        )
        return jsonify({'error': str(e)}), 500
