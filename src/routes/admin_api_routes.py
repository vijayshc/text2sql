"""
Admin API routes for Text2SQL application.
Provides RESTful API endpoints for admin functionality.
"""

from flask import Blueprint, request, jsonify, session, Response
import datetime
import csv
import io
from src.utils.user_manager import UserManager
from src.utils.feedback_manager import FeedbackManager
from src.routes.auth_routes import admin_required, permission_required
from src.models.user import Permissions

admin_api_bp = Blueprint('admin_api', __name__, url_prefix='/admin/api')
user_manager = UserManager()

# Initialize feedback manager
feedback_manager = FeedbackManager()

@admin_api_bp.route('/roles', methods=['POST'])
@admin_required
@permission_required(Permissions.MANAGE_ROLES)
def create_role():
    """Create a new role"""
    data = request.json
    
    if not data or 'name' not in data:
        return jsonify({'error': 'Role name is required'}), 400
    
    name = data['name']
    description = data.get('description', '')
    
    try:
        role_id = user_manager.create_role(name, description)
        
        # Log role creation
        user_manager.log_audit_event(
            user_id=session.get('user_id'),
            action='create_role',
            details=f"Created role: {name}",
            ip_address=request.remote_addr
        )
        
        return jsonify({
            'success': True,
            'message': f'Role {name} created successfully',
            'role_id': role_id
        }), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@admin_api_bp.route('/roles/<int:role_id>', methods=['PUT'])
@admin_required
@permission_required(Permissions.MANAGE_ROLES)
def update_role(role_id):
    """Update an existing role"""
    data = request.json
    
    if not data or 'name' not in data:
        return jsonify({'error': 'Role name is required'}), 400
    
    name = data['name']
    description = data.get('description', '')
    
    try:
        # Check if role exists
        role = user_manager.get_role_by_id(role_id)
        if not role:
            return jsonify({'error': 'Role not found'}), 404
        
        # Prevent updating admin role name
        if role.name == 'admin' and name != 'admin':
            return jsonify({'error': 'Cannot change the admin role name'}), 403
        
        user_manager.update_role(role_id, name, description)
        
        # Log role update
        user_manager.log_audit_event(
            user_id=session.get('user_id'),
            action='update_role',
            details=f"Updated role: {name}",
            ip_address=request.remote_addr
        )
        
        return jsonify({
            'success': True,
            'message': f'Role {name} updated successfully'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@admin_api_bp.route('/roles/<int:role_id>', methods=['DELETE'])
@admin_required
@permission_required(Permissions.MANAGE_ROLES)
def delete_role(role_id):
    """Delete a role"""
    try:
        # Check if role exists
        role = user_manager.get_role_by_id(role_id)
        if not role:
            return jsonify({'error': 'Role not found'}), 404
        
        # Prevent deleting admin role
        if role.name == 'admin':
            return jsonify({'error': 'Cannot delete the admin role'}), 403
        
        role_name = role.name
        user_manager.delete_role(role_id)
        
        # Log role deletion
        user_manager.log_audit_event(
            user_id=session.get('user_id'),
            action='delete_role',
            details=f"Deleted role: {role_name}",
            ip_address=request.remote_addr
        )
        
        return jsonify({
            'success': True,
            'message': f'Role {role_name} deleted successfully'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@admin_api_bp.route('/roles/<int:role_id>/permissions', methods=['GET'])
@admin_required
@permission_required(Permissions.MANAGE_ROLES)
def get_role_permissions(role_id):
    """Get permissions for a role"""
    try:
        # Check if role exists
        role = user_manager.get_role_by_id(role_id)
        if not role:
            return jsonify({'error': 'Role not found'}), 404
        
        # Get permissions assigned to the role
        permissions = user_manager.get_role_permissions(role_id)
        
        return jsonify({
            'success': True,
            'role_id': role_id,
            'role_name': role.name,
            'permissions': [p.name for p in permissions]
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@admin_api_bp.route('/roles/<int:role_id>/permissions', methods=['PUT'])
@admin_required
@permission_required(Permissions.MANAGE_ROLES)
def update_role_permissions(role_id):
    """Update permissions for a role"""
    data = request.json
    
    if not data or 'permissions' not in data:
        return jsonify({'error': 'Permissions list is required'}), 400
    
    try:
        # Check if role exists
        role = user_manager.get_role_by_id(role_id)
        if not role:
            return jsonify({'error': 'Role not found'}), 404
        
        # Special handling for admin role
        if role.name == 'admin':
            return jsonify({'error': 'Cannot modify admin role permissions'}), 403
        
        # Update permissions
        permission_ids = data['permissions']
        user_manager.update_role_permissions(role_id, permission_ids)
        
        # Log permissions update
        user_manager.log_audit_event(
            user_id=session.get('user_id'),
            action='update_role_permissions',
            details=f"Updated permissions for role: {role.name}",
            ip_address=request.remote_addr
        )
        
        return jsonify({
            'success': True,
            'message': f'Permissions for role {role.name} updated successfully'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@admin_api_bp.route('/roles', methods=['GET'])
@admin_required
@permission_required(Permissions.MANAGE_ROLES)
def get_all_roles():
    """Get all roles"""
    try:
        roles = user_manager.get_all_roles()
        role_list = []
        
        for role in roles:
            role_data = {
                'id': role.id,
                'name': role.name,
                'description': role.description,
                'user_count': len(role.users)
            }
            role_list.append(role_data)
        
        return jsonify({
            'success': True,
            'roles': role_list
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@admin_api_bp.route('/audit-logs/<int:log_id>', methods=['GET'])
@admin_required
@permission_required(Permissions.VIEW_AUDIT_LOGS)
def get_audit_log_details(log_id):
    """Get details for a specific audit log entry"""
    try:
        # Get the audit log
        log = user_manager.get_audit_log_by_id(log_id)
        
        if not log:
            return jsonify({'error': 'Audit log not found'}), 404
        
        # Format the log for the response
        log_data = {
            'id': log.id,
            'user_id': log.user_id,
            'action': log.action,
            'details': log.details,
            'timestamp': log.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            'ip_address': log.ip_address,
            'query_text': log.query_text,
            'sql_query': log.sql_query,
            'response': log.response
        }
        
        return jsonify(log_data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@admin_api_bp.route('/audit-logs/export', methods=['GET'])
@admin_required
@permission_required(Permissions.VIEW_AUDIT_LOGS)
def export_audit_logs():
    """Export audit logs for download"""
    try:
        filter_type = request.args.get('filter', 'all')
        logs = user_manager.export_audit_logs(filter_type)
        
        # Create CSV content
        import csv
        import io
        from flask import Response
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow(['ID', 'Timestamp', 'User ID', 'IP Address', 'Action', 'Details'])
        
        # Write data rows
        for log in logs:
            writer.writerow([
                log.id,
                log.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                log.user_id,
                log.ip_address or '',
                log.action,
                log.details
            ])
        
        # Return CSV file
        output.seek(0)
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        
        return Response(
            output,
            mimetype='text/csv',
            headers={
                'Content-Disposition': f'attachment; filename=audit_logs_{timestamp}.csv'
            }
        )
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@admin_api_bp.route('/embeddings/migrate', methods=['GET', 'POST'])
@admin_required
@permission_required(Permissions.ADMIN_ACCESS)
def migrate_embeddings():
    """Migrate existing embeddings from SQLite to Milvus vector database
    
    GET: Returns status and statistics about embeddings
    POST: Executes the migration process
    """
    try:
        # Connect to the feedback manager if not already connected
        if not feedback_manager.engine:
            feedback_manager.connect()
        
        # For GET requests, just return statistics
        if request.method == 'POST':
            # Get stats from SQLite and Milvus
            stats = feedback_manager.get_feedback_stats()
            
            # Check if vector store is connected
            vector_store_connected = feedback_manager.vector_store.client is not None
            
            # Return status info
            return jsonify({
                'success': True,
                'total_feedback_entries': stats['total'],
                'positive_feedback': stats['positive'],
                'negative_feedback': stats['negative'],
                'vector_store_connected': vector_store_connected,
                'ready_for_migration': vector_store_connected and stats['total'] > 0
            })
        
        # For POST requests, execute the migration
        else:
            # Execute the migration
            result = feedback_manager.migrate_existing_embeddings()
            
            if result['success']:
                # Log successful migration
                user_manager.log_audit_event(
                    user_id=session.get('user_id'),
                    action='migrate_embeddings',
                    details=f"Migrated {result['migrated']} of {result['total']} embeddings to vector database in {result['time_seconds']:.2f}s",
                    ip_address=request.remote_addr
                )
                
                return jsonify({
                    'success': True,
                    'message': f"Successfully migrated {result['migrated']} of {result['total']} embeddings",
                    'migrated': result['migrated'],
                    'failed': result['failed'],
                    'total': result['total'],
                    'time_seconds': result['time_seconds']
                })
            else:
                # Log failed migration
                user_manager.log_audit_event(
                    user_id=session.get('user_id'),
                    action='migrate_embeddings_failed',
                    details=f"Failed to migrate embeddings to vector database",
                    ip_address=request.remote_addr
                )
                
                return jsonify({
                    'success': False,
                    'message': "Failed to migrate embeddings to vector database"
                }), 500
    except Exception as e:
        # Log error
        user_manager.log_audit_event(
            user_id=session.get('user_id'),
            action='migrate_embeddings_error',
            details=f"Error migrating embeddings: {str(e)}",
            ip_address=request.remote_addr
        )
        
        return jsonify({'error': str(e)}), 500