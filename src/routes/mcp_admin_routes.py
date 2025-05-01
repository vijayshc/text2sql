from flask import Blueprint, request, jsonify, current_app, render_template
import asyncio
import traceback
import logging
import json

from src.routes.auth_routes import admin_required
from src.models.mcp_server import MCPServer, MCPServerType, MCPServerStatus
from src.utils.mcp_client_manager import MCPClientManager

# Get the logger
logger = logging.getLogger('text2sql')

# Create Blueprint
mcp_admin_bp = Blueprint('mcp_admin', __name__)


@mcp_admin_bp.route('/api/admin/mcp-servers', methods=['GET'])
@admin_required
def get_mcp_servers():
    """Get all MCP servers."""
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


@mcp_admin_bp.route('/api/admin/mcp-servers', methods=['POST'])
@admin_required
def add_mcp_server():
    """Add a new MCP server."""
    try:
        data = request.json
        
        # Validate required fields
        required_fields = ['name', 'server_type']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'success': False,
                    'error': f'Missing required field: {field}'
                }), 400
        
        # Validate server type
        if data['server_type'] not in [t.value for t in MCPServerType]:
            return jsonify({
                'success': False,
                'error': f'Invalid server type: {data["server_type"]}'
            }), 400
        
        # Create server object
        server = MCPServer(
            name=data['name'],
            description=data.get('description', ''),
            server_type=data['server_type'],
            config=data.get('config', {}),
            status=MCPServerStatus.STOPPED.value
        )
        
        # Save server to database
        server.save()
        
        return jsonify({
            'success': True,
            'server': {
                'id': server.id,
                'name': server.name,
                'description': server.description,
                'server_type': server.server_type,
                'config': server.config,
                'status': server.status,
                'created_at': server.created_at.isoformat() if server.created_at else None,
                'updated_at': server.updated_at.isoformat() if server.updated_at else None
            }
        })
    except Exception as e:
        logger.exception("Error adding MCP server")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@mcp_admin_bp.route('/api/admin/mcp-servers/<int:server_id>', methods=['GET'])
@admin_required
def get_mcp_server(server_id):
    """Get a specific MCP server."""
    try:
        server = MCPServer.get_by_id(server_id)
        if not server:
            return jsonify({
                'success': False,
                'error': f'Server with ID {server_id} not found'
            }), 404
        
        return jsonify({
            'success': True,
            'server': {
                'id': server.id,
                'name': server.name,
                'description': server.description,
                'server_type': server.server_type,
                'config': server.config,
                'status': server.status,
                'created_at': server.created_at.isoformat() if server.created_at else None,
                'updated_at': server.updated_at.isoformat() if server.updated_at else None
            }
        })
    except Exception as e:
        logger.exception(f"Error fetching MCP server {server_id}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@mcp_admin_bp.route('/api/admin/mcp-servers/<int:server_id>', methods=['PUT'])
@admin_required
def update_mcp_server(server_id):
    """Update a specific MCP server."""
    try:
        server = MCPServer.get_by_id(server_id)
        if not server:
            return jsonify({
                'success': False,
                'error': f'Server with ID {server_id} not found'
            }), 404
        
        data = request.json
        
        # Update fields
        if 'name' in data:
            server.name = data['name']
        if 'description' in data:
            server.description = data['description']
        if 'server_type' in data:
            if data['server_type'] not in [t.value for t in MCPServerType]:
                return jsonify({
                    'success': False,
                    'error': f'Invalid server type: {data["server_type"]}'
                }), 400
            server.server_type = data['server_type']
        if 'config' in data:
            server.config = data['config']
        
        # Save server to database
        server.save()
        
        return jsonify({
            'success': True,
            'server': {
                'id': server.id,
                'name': server.name,
                'description': server.description,
                'server_type': server.server_type,
                'config': server.config,
                'status': server.status,
                'created_at': server.created_at.isoformat() if server.created_at else None,
                'updated_at': server.updated_at.isoformat() if server.updated_at else None
            }
        })
    except Exception as e:
        logger.exception(f"Error updating MCP server {server_id}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@mcp_admin_bp.route('/api/admin/mcp-servers/<int:server_id>', methods=['DELETE'])
@admin_required
def delete_mcp_server(server_id):
    """Delete a specific MCP server."""
    try:
        server = MCPServer.get_by_id(server_id)
        if not server:
            return jsonify({
                'success': False,
                'error': f'Server with ID {server_id} not found'
            }), 404
        
        # Stop server if it's running
        if server.status == MCPServerStatus.RUNNING.value:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            success, message = loop.run_until_complete(MCPClientManager.stop_server(server_id))
            loop.close()
            
            if not success:
                return jsonify({
                    'success': False,
                    'error': f'Failed to stop server before deletion: {message}'
                }), 500
        
        # Delete server from database
        server.delete()
        
        return jsonify({
            'success': True,
            'message': f'Server {server.name} deleted successfully'
        })
    except Exception as e:
        logger.exception(f"Error deleting MCP server {server_id}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@mcp_admin_bp.route('/api/admin/mcp-servers/<int:server_id>/start', methods=['POST'])
@admin_required
def start_mcp_server(server_id):
    """Start a specific MCP server."""
    try:
        server = MCPServer.get_by_id(server_id)
        if not server:
            return jsonify({
                'success': False,
                'error': f'Server with ID {server_id} not found'
            }), 404
        
        # Start server
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        success, message = loop.run_until_complete(MCPClientManager.start_server(server_id))
        loop.close()
        
        if not success:
            return jsonify({
                'success': False,
                'error': message
            }), 500
        
        return jsonify({
            'success': True,
            'message': message,
            'server': {
                'id': server.id,
                'name': server.name,
                'status': server.status
            }
        })
    except Exception as e:
        logger.exception(f"Error starting MCP server {server_id}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@mcp_admin_bp.route('/api/admin/mcp-servers/<int:server_id>/stop', methods=['POST'])
@admin_required
def stop_mcp_server(server_id):
    """Stop a specific MCP server."""
    try:
        server = MCPServer.get_by_id(server_id)
        if not server:
            return jsonify({
                'success': False,
                'error': f'Server with ID {server_id} not found'
            }), 404
        
        # Stop server
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        success, message = loop.run_until_complete(MCPClientManager.stop_server(server_id))
        loop.close()
        
        if not success:
            return jsonify({
                'success': False,
                'error': message
            }), 500
        
        return jsonify({
            'success': True,
            'message': message,
            'server': {
                'id': server.id,
                'name': server.name,
                'status': server.status
            }
        })
    except Exception as e:
        logger.exception(f"Error stopping MCP server {server_id}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@mcp_admin_bp.route('/api/admin/mcp-servers/<int:server_id>/restart', methods=['POST'])
@admin_required
def restart_mcp_server(server_id):
    """Restart a specific MCP server."""
    try:
        server = MCPServer.get_by_id(server_id)
        if not server:
            return jsonify({
                'success': False,
                'error': f'Server with ID {server_id} not found'
            }), 404
        
        # Restart server
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        success, message = loop.run_until_complete(MCPClientManager.restart_server(server_id))
        loop.close()
        
        if not success:
            return jsonify({
                'success': False,
                'error': message
            }), 500
        
        return jsonify({
            'success': True,
            'message': message,
            'server': {
                'id': server.id,
                'name': server.name,
                'status': server.status
            }
        })
    except Exception as e:
        logger.exception(f"Error restarting MCP server {server_id}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@mcp_admin_bp.route('/api/admin/mcp-servers/<int:server_id>/tools', methods=['GET'])
@admin_required
def get_mcp_server_tools(server_id):
    """Get tools available on a specific MCP server."""
    try:
        server = MCPServer.get_by_id(server_id)
        if not server:
            return jsonify({
                'success': False,
                'error': f'Server with ID {server_id} not found'
            }), 404
        
        # Get client
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        client = loop.run_until_complete(MCPClientManager.get_client(server_id, connect=True))
        
        if not client or not client.is_connected():
            loop.close()
            return jsonify({
                'success': False,
                'error': f'Server {server.name} is not connected'
            }), 500
        
        # Get tools
        tools = loop.run_until_complete(client.get_available_tools())
        loop.close()
        
        if not tools:
            return jsonify({
                'success': False,
                'error': f'Failed to get tools from server {server.name}'
            }), 500
        
        return jsonify({
            'success': True,
            'tools': tools
        })
    except Exception as e:
        logger.exception(f"Error getting MCP server tools for server {server_id}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
