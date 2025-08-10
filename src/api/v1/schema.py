"""
Schema Management API endpoints for Vue.js frontend
"""
from flask import Blueprint, request, jsonify
import logging
import json

from src.utils.auth_utils import jwt_required
from src.utils.schema_manager import SchemaManager
from src.utils.user_manager import UserManager

logger = logging.getLogger('text2sql.schema_api')

# Create Blueprint
schema_api = Blueprint('schema_api', __name__)

# Initialize managers
schema_manager = SchemaManager()
user_manager = UserManager()

@schema_api.route('/workspaces', methods=['GET'])
@jwt_required
def get_workspaces():
    """Get all workspaces defined in the schema."""
    try:
        workspaces = schema_manager.get_workspaces()
        
        # Audit log the workspace retrieval
        user_id = getattr(request, 'current_user_id', 'unknown')
        ip_address = request.environ.get('HTTP_X_REAL_IP', request.remote_addr)
        
        user_manager.log_audit_event(
            event_type='view_workspaces',
            user_id=user_id,
            ip_address=ip_address,
            event_data={'workspaces_count': len(workspaces)}
        )
        
        return jsonify({
            'success': True,
            'workspaces': workspaces
        })
        
    except Exception as e:
        logger.exception("Error getting workspaces")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@schema_api.route('/tables', methods=['GET'])
@jwt_required
def get_tables():
    """Get tables for a specific workspace."""
    try:
        workspace = request.args.get('workspace')
        if not workspace:
            return jsonify({'error': 'Missing workspace parameter'}), 400
        
        tables = schema_manager.get_tables(workspace)
        
        # Audit log
        user_id = getattr(request, 'current_user_id', 'unknown')
        ip_address = request.environ.get('HTTP_X_REAL_IP', request.remote_addr)
        
        user_manager.log_audit_event(
            event_type='view_tables',
            user_id=user_id,
            ip_address=ip_address,
            event_data={'workspace': workspace, 'tables_count': len(tables)}
        )
        
        return jsonify({
            'success': True,
            'tables': tables
        })
        
    except Exception as e:
        logger.exception("Error getting tables")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@schema_api.route('/table-details', methods=['GET'])
@jwt_required
def get_table_details():
    """Get detailed information about a specific table."""
    try:
        workspace = request.args.get('workspace')
        table_name = request.args.get('table_name')
        
        if not workspace or not table_name:
            return jsonify({'error': 'Missing workspace or table_name parameter'}), 400
        
        table_details = schema_manager.get_table_details(workspace, table_name)
        
        # Audit log
        user_id = getattr(request, 'current_user_id', 'unknown')
        ip_address = request.environ.get('HTTP_X_REAL_IP', request.remote_addr)
        
        user_manager.log_audit_event(
            event_type='view_table_details',
            user_id=user_id,
            ip_address=ip_address,
            event_data={'workspace': workspace, 'table_name': table_name}
        )
        
        return jsonify({
            'success': True,
            'table': table_details
        })
        
    except Exception as e:
        logger.exception("Error getting table details")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@schema_api.route('/workspace', methods=['POST'])
@jwt_required
def create_workspace():
    """Create a new workspace."""
    try:
        data = request.get_json()
        if not data or not data.get('name'):
            return jsonify({'error': 'Missing workspace name'}), 400
        
        workspace_name = data['name']
        description = data.get('description', '')
        
        result = schema_manager.create_workspace(workspace_name, description)
        
        # Audit log
        user_id = getattr(request, 'current_user_id', 'unknown')
        ip_address = request.environ.get('HTTP_X_REAL_IP', request.remote_addr)
        
        user_manager.log_audit_event(
            event_type='create_workspace',
            user_id=user_id,
            ip_address=ip_address,
            event_data={'workspace_name': workspace_name, 'description': description}
        )
        
        return jsonify({
            'success': True,
            'message': f'Workspace "{workspace_name}" created successfully',
            'workspace': result
        })
        
    except Exception as e:
        logger.exception("Error creating workspace")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@schema_api.route('/workspace/<workspace_name>', methods=['PUT'])
@jwt_required
def update_workspace(workspace_name):
    """Update an existing workspace."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Missing update data'}), 400
        
        description = data.get('description', '')
        
        result = schema_manager.update_workspace(workspace_name, description)
        
        # Audit log
        user_id = getattr(request, 'current_user_id', 'unknown')
        ip_address = request.environ.get('HTTP_X_REAL_IP', request.remote_addr)
        
        user_manager.log_audit_event(
            event_type='update_workspace',
            user_id=user_id,
            ip_address=ip_address,
            event_data={'workspace_name': workspace_name, 'description': description}
        )
        
        return jsonify({
            'success': True,
            'message': f'Workspace "{workspace_name}" updated successfully',
            'workspace': result
        })
        
    except Exception as e:
        logger.exception("Error updating workspace")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@schema_api.route('/workspace/<workspace_name>', methods=['DELETE'])
@jwt_required
def delete_workspace(workspace_name):
    """Delete a workspace."""
    try:
        result = schema_manager.delete_workspace(workspace_name)
        
        # Audit log
        user_id = getattr(request, 'current_user_id', 'unknown')
        ip_address = request.environ.get('HTTP_X_REAL_IP', request.remote_addr)
        
        user_manager.log_audit_event(
            event_type='delete_workspace',
            user_id=user_id,
            ip_address=ip_address,
            event_data={'workspace_name': workspace_name}
        )
        
        return jsonify({
            'success': True,
            'message': f'Workspace "{workspace_name}" deleted successfully'
        })
        
    except Exception as e:
        logger.exception("Error deleting workspace")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@schema_api.route('/table', methods=['POST'])
@jwt_required
def create_table():
    """Create a new table in a workspace."""
    try:
        data = request.get_json()
        if not data or not data.get('workspace') or not data.get('table_name'):
            return jsonify({'error': 'Missing workspace or table_name'}), 400
        
        workspace = data['workspace']
        table_name = data['table_name']
        columns = data.get('columns', [])
        description = data.get('description', '')
        
        result = schema_manager.create_table(workspace, table_name, columns, description)
        
        # Audit log
        user_id = getattr(request, 'current_user_id', 'unknown')
        ip_address = request.environ.get('HTTP_X_REAL_IP', request.remote_addr)
        
        user_manager.log_audit_event(
            event_type='create_table',
            user_id=user_id,
            ip_address=ip_address,
            event_data={
                'workspace': workspace,
                'table_name': table_name,
                'columns_count': len(columns),
                'description': description
            }
        )
        
        return jsonify({
            'success': True,
            'message': f'Table "{table_name}" created successfully in workspace "{workspace}"',
            'table': result
        })
        
    except Exception as e:
        logger.exception("Error creating table")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@schema_api.route('/table', methods=['PUT'])
@jwt_required
def update_table():
    """Update an existing table."""
    try:
        data = request.get_json()
        if not data or not data.get('workspace') or not data.get('table_name'):
            return jsonify({'error': 'Missing workspace or table_name'}), 400
        
        workspace = data['workspace']
        table_name = data['table_name']
        columns = data.get('columns', [])
        description = data.get('description', '')
        
        result = schema_manager.update_table(workspace, table_name, columns, description)
        
        # Audit log
        user_id = getattr(request, 'current_user_id', 'unknown')
        ip_address = request.environ.get('HTTP_X_REAL_IP', request.remote_addr)
        
        user_manager.log_audit_event(
            event_type='update_table',
            user_id=user_id,
            ip_address=ip_address,
            event_data={
                'workspace': workspace,
                'table_name': table_name,
                'columns_count': len(columns),
                'description': description
            }
        )
        
        return jsonify({
            'success': True,
            'message': f'Table "{table_name}" updated successfully',
            'table': result
        })
        
    except Exception as e:
        logger.exception("Error updating table")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@schema_api.route('/table', methods=['DELETE'])
@jwt_required
def delete_table():
    """Delete a table from a workspace."""
    try:
        workspace = request.args.get('workspace')
        table_name = request.args.get('table_name')
        
        if not workspace or not table_name:
            return jsonify({'error': 'Missing workspace or table_name parameter'}), 400
        
        result = schema_manager.delete_table(workspace, table_name)
        
        # Audit log
        user_id = getattr(request, 'current_user_id', 'unknown')
        ip_address = request.environ.get('HTTP_X_REAL_IP', request.remote_addr)
        
        user_manager.log_audit_event(
            event_type='delete_table',
            user_id=user_id,
            ip_address=ip_address,
            event_data={'workspace': workspace, 'table_name': table_name}
        )
        
        return jsonify({
            'success': True,
            'message': f'Table "{table_name}" deleted successfully from workspace "{workspace}"'
        })
        
    except Exception as e:
        logger.exception("Error deleting table")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@schema_api.route('/import', methods=['POST'])
@jwt_required
def import_schema():
    """Import schema from various sources."""
    try:
        data = request.get_json()
        if not data or not data.get('source_type'):
            return jsonify({'error': 'Missing source_type'}), 400
        
        source_type = data['source_type']
        workspace = data.get('workspace', 'default')
        
        if source_type == 'json':
            schema_data = data.get('schema_data')
            if not schema_data:
                return jsonify({'error': 'Missing schema_data for JSON import'}), 400
            
            result = schema_manager.import_from_json(workspace, schema_data)
        elif source_type == 'database':
            connection_string = data.get('connection_string')
            if not connection_string:
                return jsonify({'error': 'Missing connection_string for database import'}), 400
            
            result = schema_manager.import_from_database(workspace, connection_string)
        else:
            return jsonify({'error': f'Unsupported source_type: {source_type}'}), 400
        
        # Audit log
        user_id = getattr(request, 'current_user_id', 'unknown')
        ip_address = request.environ.get('HTTP_X_REAL_IP', request.remote_addr)
        
        user_manager.log_audit_event(
            event_type='import_schema',
            user_id=user_id,
            ip_address=ip_address,
            event_data={'source_type': source_type, 'workspace': workspace}
        )
        
        return jsonify({
            'success': True,
            'message': f'Schema imported successfully to workspace "{workspace}"',
            'result': result
        })
        
    except Exception as e:
        logger.exception("Error importing schema")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@schema_api.route('/export', methods=['GET'])
@jwt_required
def export_schema():
    """Export schema for a workspace."""
    try:
        workspace = request.args.get('workspace')
        format_type = request.args.get('format', 'json')
        
        if not workspace:
            return jsonify({'error': 'Missing workspace parameter'}), 400
        
        if format_type == 'json':
            result = schema_manager.export_to_json(workspace)
        elif format_type == 'sql':
            result = schema_manager.export_to_sql(workspace)
        else:
            return jsonify({'error': f'Unsupported format: {format_type}'}), 400
        
        # Audit log
        user_id = getattr(request, 'current_user_id', 'unknown')
        ip_address = request.environ.get('HTTP_X_REAL_IP', request.remote_addr)
        
        user_manager.log_audit_event(
            event_type='export_schema',
            user_id=user_id,
            ip_address=ip_address,
            event_data={'workspace': workspace, 'format': format_type}
        )
        
        return jsonify({
            'success': True,
            'data': result,
            'format': format_type
        })
        
    except Exception as e:
        logger.exception("Error exporting schema")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500