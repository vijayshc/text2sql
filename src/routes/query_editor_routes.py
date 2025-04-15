from flask import Blueprint, render_template, request, jsonify, session
from src.utils.database import DatabaseManager
from src.models.sql_generator import SQLGenerationManager
from src.utils.user_manager import UserManager
import logging

# Setup logger
logger = logging.getLogger('text2sql')

# Create Blueprint
query_editor_bp = Blueprint('query_editor', __name__)

# Initialize SQL generation manager
sql_manager = SQLGenerationManager()

@query_editor_bp.route('/query-editor')
def query_editor():
    """Render the query editor page"""
    user_manager = UserManager()
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
        
        if not sql_query.strip():
            return jsonify({'error': 'Query is empty'}), 400
            
        # Initialize database manager and execute query
        db_manager = DatabaseManager()
        if not db_manager.connect():
            return jsonify({'error': 'Unable to connect to database'}), 500
            
        query_result = db_manager.execute_query(sql_query)
        
        if query_result['success']:
            # Convert DataFrame to list of dictionaries for JSON serialization
            results = query_result['data'].to_dict(orient='records') if query_result['data'] is not None else []
            
            # Ensure columns are converted to a list for proper JSON serialization
            columns = list(query_result['columns']) if query_result['columns'] else []
            
            return jsonify({
                'status': 'success',
                'results': results,
                'columns': columns
            })
        else:
            return jsonify({'error': query_result['error']}), 500
    except Exception as e:
        logger.error(f"Error executing query: {str(e)}")
        return jsonify({'error': str(e)}), 500

@query_editor_bp.route('/api/complete-query', methods=['POST'])
def complete_query():
    """Complete a SQL query using AI"""
    try:
        data = request.get_json()
        partial_query = data.get('query', '')
        
        if not partial_query.strip():
            return jsonify({'error': 'Query is empty'}), 400
        
        # Use the same approach as text-to-SQL flow but with different prompt
        workspace = data.get('workspace', '')
        
        # Get tables and columns for completion
        completed_query = sql_manager.complete_sql_query(partial_query, workspace)
        
        return jsonify({
            'status': 'success',
            'completed_query': completed_query
        })
    except Exception as e:
        logger.error(f"Error completing query: {str(e)}")
        return jsonify({'error': str(e)}), 500


@query_editor_bp.route('/api/save-query', methods=['POST'])
def save_query():
    """Save a SQL query"""
    try:
        data = request.get_json()
        sql_query = data.get('query', '')
        query_name = data.get('name', '')
        description = data.get('description', '')
        
        if not sql_query.strip():
            return jsonify({'error': 'Query is empty'}), 400
            
        if not query_name.strip():
            return jsonify({'error': 'Query name is required'}), 400
            
        # Save the query using SQL manager
        query_id = sql_manager.save_user_query(
            sql_query, 
            query_name,
            description,
            session.get('user_id')
        )
        
        return jsonify({
            'status': 'success',
            'message': 'Query saved successfully',
            'query_id': query_id
        })
    except Exception as e:
        logger.error(f"Error saving query: {str(e)}")
        return jsonify({'error': str(e)}), 500
