"""
Admin API endpoints for v1 API
Consolidated admin functionality for user management, roles, MCP servers, and audit logs
"""

from flask import Blueprint, request, jsonify, session, Response
import datetime
import csv
import io
import json
import asyncio
import traceback
import logging

from src.utils.user_manager import UserManager
from src.utils.feedback_manager import FeedbackManager
from src.middleware.auth import api_admin_required as admin_required, api_permission_required as permission_required
from src.models.user import Permissions
from src.models.mcp_server import MCPServer, MCPServerType, MCPServerStatus
from src.utils.mcp_client_manager import MCPClientManager

admin_api = Blueprint('admin_api', __name__)
user_manager = UserManager()
feedback_manager = FeedbackManager()
logger = logging.getLogger('text2sql')

# ============================================================================
# Dashboard and Statistics
# ============================================================================

@admin_api.route('/dashboard', methods=['GET'])
@admin_required
def get_dashboard_stats():
    """Get admin dashboard statistics"""
    try:
        # Get user statistics
        users = user_manager.get_all_users()
        total_users = len(users)
        active_users = len([u for u in users if u.get('status') != 'inactive'])
        
        # Get MCP server statistics
        mcp_servers = MCPServer.get_all()
        total_servers = len(mcp_servers)
        running_servers = len([s for s in mcp_servers if s.status == 'running'])
        
        # Get recent audit logs
        recent_logs = user_manager.get_audit_logs(limit=10)
        
        # Get system info
        from src.models.sql_generator import SQLGenerationManager
        sql_manager = SQLGenerationManager()
        
        return jsonify({
            'success': True,
            'stats': {
                'users': {
                    'total': total_users,
                    'active': active_users,
                    'inactive': total_users - active_users
                },
                'mcp_servers': {
                    'total': total_servers,
                    'running': running_servers,
                    'stopped': total_servers - running_servers
                },
                'recent_activity': len(recent_logs)
            },
            'recent_logs': recent_logs
        })
    except Exception as e:
        logger.exception("Error fetching dashboard stats")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ============================================================================
# User Management
# ============================================================================

@admin_api.route('/users', methods=['GET'])
@admin_required
@permission_required(Permissions.MANAGE_USERS)
def list_users():
    """Get all users"""
    try:
        users = user_manager.get_all_users()
        return jsonify({
            'success': True,
            'users': users
        })
    except Exception as e:
        logger.exception("Error fetching users")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@admin_api.route('/users', methods=['POST'])
@admin_required
@permission_required(Permissions.MANAGE_USERS)
def create_user():
    """Create a new user"""
    try:
        data = request.json
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400
        
        username = data.get('username')
        email = data.get('email')
        password = data.get('password')
        role_ids = data.get('roles', [])
        
        if not username or not email or not password:
            return jsonify({
                'success': False,
                'error': 'Username, email, and password are required'
            }), 400
        
        # Check if user already exists
        existing_user = user_manager.get_user_by_username(username)
        if existing_user:
            return jsonify({
                'success': False,
                'error': 'Username already exists'
            }), 400
        
        existing_email = user_manager.get_user_by_email(email)
        if existing_email:
            return jsonify({
                'success': False,
                'error': 'Email already exists'
            }), 400
        
        # Create user
        user_id = user_manager.create_user(username, email, password)
        
        # Assign roles if provided
        if role_ids:
            for role_id in role_ids:
                user_manager.assign_role_to_user(user_id, role_id)
        
        # Log user creation
        user_manager.log_audit_event(
            user_id=session.get('user_id'),
            action='create_user',
            details=f"Created user: {username}",
            ip_address=request.remote_addr
        )
        
        return jsonify({
            'success': True,
            'message': f'User {username} created successfully',
            'user_id': user_id
        }), 201
        
    except Exception as e:
        logger.exception("Error creating user")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@admin_api.route('/users/<int:user_id>', methods=['PUT'])
@admin_required
@permission_required(Permissions.MANAGE_USERS)
def update_user(user_id):
    """Update user information"""
    try:
        data = request.json
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400
        
        # Get current user
        user = user_manager.get_user_by_id(user_id)
        if not user:
            return jsonify({
                'success': False,
                'error': 'User not found'
            }), 404
        
        # Update user fields
        updates = {}
        if 'email' in data:
            updates['email'] = data['email']
        if 'status' in data:
            updates['status'] = data['status']
        
        if updates:
            user_manager.update_user(user_id, **updates)
        
        # Update roles if provided
        if 'roles' in data:
            current_roles = user_manager.get_user_roles(user_id)
            current_role_ids = [role['id'] for role in current_roles]
            new_role_ids = data['roles']
            
            # Remove old roles
            for role_id in current_role_ids:
                if role_id not in new_role_ids:
                    user_manager.remove_role_from_user(user_id, role_id)
            
            # Add new roles
            for role_id in new_role_ids:
                if role_id not in current_role_ids:
                    user_manager.assign_role_to_user(user_id, role_id)
        
        # Log user update
        user_manager.log_audit_event(
            user_id=session.get('user_id'),
            action='update_user',
            details=f"Updated user: {user['username']}",
            ip_address=request.remote_addr
        )
        
        return jsonify({
            'success': True,
            'message': 'User updated successfully'
        })
        
    except Exception as e:
        logger.exception("Error updating user")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@admin_api.route('/users/<int:user_id>', methods=['DELETE'])
@admin_required
@permission_required(Permissions.MANAGE_USERS)
def delete_user(user_id):
    """Delete a user"""
    try:
        # Get user info before deletion
        user = user_manager.get_user_by_id(user_id)
        if not user:
            return jsonify({
                'success': False,
                'error': 'User not found'
            }), 404
        
        # Don't allow deletion of current user
        if user_id == session.get('user_id'):
            return jsonify({
                'success': False,
                'error': 'Cannot delete your own account'
            }), 400
        
        # Delete user
        user_manager.delete_user(user_id)
        
        # Log user deletion
        user_manager.log_audit_event(
            user_id=session.get('user_id'),
            action='delete_user',
            details=f"Deleted user: {user['username']}",
            ip_address=request.remote_addr
        )
        
        return jsonify({
            'success': True,
            'message': f'User {user["username"]} deleted successfully'
        })
        
    except Exception as e:
        logger.exception("Error deleting user")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ============================================================================
# Role Management
# ============================================================================

@admin_api.route('/roles', methods=['GET'])
@admin_required
@permission_required(Permissions.MANAGE_ROLES)
def list_roles():
    """Get all roles"""
    try:
        roles = user_manager.get_all_roles()
        return jsonify({
            'success': True,
            'roles': roles
        })
    except Exception as e:
        logger.exception("Error fetching roles")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@admin_api.route('/roles', methods=['POST'])
@admin_required
@permission_required(Permissions.MANAGE_ROLES)
def create_role():
    """Create a new role"""
    try:
        data = request.json
        if not data or 'name' not in data:
            return jsonify({'success': False, 'error': 'Role name is required'}), 400
        
        name = data['name']
        description = data.get('description', '')
        
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
        logger.exception("Error creating role")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@admin_api.route('/roles/<int:role_id>', methods=['PUT'])
@admin_required
@permission_required(Permissions.MANAGE_ROLES)
def update_role(role_id):
    """Update role information"""
    try:
        data = request.json
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400
        
        # Get current role
        role = user_manager.get_role_by_id(role_id)
        if not role:
            return jsonify({
                'success': False,
                'error': 'Role not found'
            }), 404
        
        # Update role
        updates = {}
        if 'name' in data:
            updates['name'] = data['name']
        if 'description' in data:
            updates['description'] = data['description']
        
        if updates:
            user_manager.update_role(role_id, **updates)
        
        # Log role update
        user_manager.log_audit_event(
            user_id=session.get('user_id'),
            action='update_role',
            details=f"Updated role: {role['name']}",
            ip_address=request.remote_addr
        )
        
        return jsonify({
            'success': True,
            'message': 'Role updated successfully'
        })
        
    except Exception as e:
        logger.exception("Error updating role")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@admin_api.route('/roles/<int:role_id>', methods=['DELETE'])
@admin_required
@permission_required(Permissions.MANAGE_ROLES)
def delete_role(role_id):
    """Delete a role"""
    try:
        # Get role info before deletion
        role = user_manager.get_role_by_id(role_id)
        if not role:
            return jsonify({
                'success': False,
                'error': 'Role not found'
            }), 404
        
        # Check if role is in use
        users_with_role = user_manager.get_users_by_role(role_id)
        if users_with_role:
            return jsonify({
                'success': False,
                'error': f'Cannot delete role. {len(users_with_role)} users are assigned to this role.'
            }), 400
        
        # Delete role
        user_manager.delete_role(role_id)
        
        # Log role deletion
        user_manager.log_audit_event(
            user_id=session.get('user_id'),
            action='delete_role',
            details=f"Deleted role: {role['name']}",
            ip_address=request.remote_addr
        )
        
        return jsonify({
            'success': True,
            'message': f'Role {role["name"]} deleted successfully'
        })
        
    except Exception as e:
        logger.exception("Error deleting role")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ============================================================================
# MCP Server Management
# ============================================================================

@admin_api.route('/mcp-servers', methods=['GET'])
@admin_required
def list_mcp_servers():
    """Get all MCP servers"""
    try:
        servers = MCPServer.get_all()
        return jsonify({
            'success': True,
            'servers': [
                {
                    'id': server.id,
                    'name': server.name,
                    'description': server.description,
                    'server_type': server.server_type,
                    'config': server.config,
                    'status': server.status,
                    'created_at': server.created_at.isoformat() if server.created_at else None,
                    'updated_at': server.updated_at.isoformat() if server.updated_at else None
                }
                for server in servers
            ]
        })
    except Exception as e:
        logger.exception("Error fetching MCP servers")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@admin_api.route('/mcp-servers', methods=['POST'])
@admin_required
def create_mcp_server():
    """Create a new MCP server"""
    try:
        data = request.json
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400
        
        name = data.get('name')
        description = data.get('description', '')
        server_type = data.get('server_type')
        config = data.get('config', {})
        
        if not name or not server_type:
            return jsonify({
                'success': False,
                'error': 'Name and server_type are required'
            }), 400
        
        # Validate server type
        try:
            server_type_enum = MCPServerType(server_type)
        except ValueError:
            return jsonify({
                'success': False,
                'error': f'Invalid server type: {server_type}'
            }), 400
        
        # Create server
        server = MCPServer.create(
            name=name,
            description=description,
            server_type=server_type_enum,
            config=config
        )
        
        return jsonify({
            'success': True,
            'message': f'MCP server {name} created successfully',
            'server': {
                'id': server.id,
                'name': server.name,
                'description': server.description,
                'server_type': server.server_type,
                'config': server.config,
                'status': server.status
            }
        }), 201
        
    except Exception as e:
        logger.exception("Error creating MCP server")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@admin_api.route('/mcp-servers/<int:server_id>/start', methods=['POST'])
@admin_required
def start_mcp_server(server_id):
    """Start an MCP server"""
    try:
        server = MCPServer.get_by_id(server_id)
        if not server:
            return jsonify({
                'success': False,
                'error': 'Server not found'
            }), 404
        
        # Start the server asynchronously
        async def start_server():
            try:
                mcp_manager = MCPClientManager()
                await mcp_manager.initialize_server(server)
                server.update_status(MCPServerStatus.RUNNING)
                return True
            except Exception as e:
                logger.exception(f"Error starting MCP server {server.name}")
                server.update_status(MCPServerStatus.ERROR)
                return False
        
        # Run the async function
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        success = loop.run_until_complete(start_server())
        loop.close()
        
        if success:
            return jsonify({
                'success': True,
                'message': f'MCP server {server.name} started successfully'
            })
        else:
            return jsonify({
                'success': False,
                'error': f'Failed to start MCP server {server.name}'
            }), 500
            
    except Exception as e:
        logger.exception("Error starting MCP server")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@admin_api.route('/mcp-servers/<int:server_id>/stop', methods=['POST'])
@admin_required
def stop_mcp_server(server_id):
    """Stop an MCP server"""
    try:
        server = MCPServer.get_by_id(server_id)
        if not server:
            return jsonify({
                'success': False,
                'error': 'Server not found'
            }), 404
        
        # Stop the server asynchronously
        async def stop_server():
            try:
                mcp_manager = MCPClientManager()
                await mcp_manager.stop_server(server.name)
                server.update_status(MCPServerStatus.STOPPED)
                return True
            except Exception as e:
                logger.exception(f"Error stopping MCP server {server.name}")
                return False
        
        # Run the async function
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        success = loop.run_until_complete(stop_server())
        loop.close()
        
        if success:
            return jsonify({
                'success': True,
                'message': f'MCP server {server.name} stopped successfully'
            })
        else:
            return jsonify({
                'success': False,
                'error': f'Failed to stop MCP server {server.name}'
            }), 500
            
    except Exception as e:
        logger.exception("Error stopping MCP server")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@admin_api.route('/mcp-servers/<int:server_id>', methods=['DELETE'])
@admin_required
def delete_mcp_server(server_id):
    """Delete an MCP server"""
    try:
        server = MCPServer.get_by_id(server_id)
        if not server:
            return jsonify({
                'success': False,
                'error': 'Server not found'
            }), 404
        
        # Stop server if running
        if server.status == MCPServerStatus.RUNNING:
            async def stop_server():
                try:
                    mcp_manager = MCPClientManager()
                    await mcp_manager.stop_server(server.name)
                except Exception as e:
                    logger.exception(f"Error stopping MCP server {server.name} before deletion")
            
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(stop_server())
            loop.close()
        
        # Delete server
        server.delete()
        
        return jsonify({
            'success': True,
            'message': f'MCP server {server.name} deleted successfully'
        })
        
    except Exception as e:
        logger.exception("Error deleting MCP server")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ============================================================================
# Audit Logs
# ============================================================================

@admin_api.route('/audit-logs', methods=['GET'])
@admin_required
def get_audit_logs():
    """Get audit logs with pagination"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 50, type=int)
        action_filter = request.args.get('action')
        user_filter = request.args.get('user_id', type=int)
        
        # Validate per_page
        if per_page > 100:
            per_page = 100
        
        logs = user_manager.get_audit_logs(
            page=page,
            per_page=per_page,
            action_filter=action_filter,
            user_filter=user_filter
        )
        
        return jsonify({
            'success': True,
            'logs': logs,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'has_next': len(logs) == per_page
            }
        })
    except Exception as e:
        logger.exception("Error fetching audit logs")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@admin_api.route('/audit-logs/export', methods=['GET'])
@admin_required
def export_audit_logs():
    """Export audit logs as CSV"""
    try:
        logs = user_manager.get_audit_logs(limit=10000)  # Large limit for export
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow(['ID', 'User ID', 'Username', 'Action', 'Details', 'IP Address', 'Timestamp'])
        
        # Write data
        for log in logs:
            writer.writerow([
                log.get('id', ''),
                log.get('user_id', ''),
                log.get('username', ''),
                log.get('action', ''),
                log.get('details', ''),
                log.get('ip_address', ''),
                log.get('timestamp', '')
            ])
        
        output.seek(0)
        
        return Response(
            output.getvalue(),
            mimetype='text/csv',
            headers={
                'Content-Disposition': f'attachment; filename=audit_logs_{datetime.datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
            }
        )
    except Exception as e:
        logger.exception("Error exporting audit logs")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500