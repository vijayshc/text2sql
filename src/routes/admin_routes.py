"""
Admin routes for Text2SQL application.
Legacy routes that redirect to Vue.js frontend - backward compatibility removed.
All admin functionality is now handled by Vue.js frontend with API calls.
"""

from flask import Blueprint, redirect

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

@admin_bp.route('/')
def admin_index():
    """Redirect to Vue.js admin dashboard"""
    return redirect('/#/admin')
    
@admin_bp.route('/mcp-servers')
def mcp_servers():
    """Redirect to Vue.js MCP servers page"""
    return redirect('/#/admin/mcp-servers')

@admin_bp.route('/users')
def list_users():
    """Redirect to Vue.js user management page"""
    return redirect('/#/admin/users')

@admin_bp.route('/users/create')
def create_user():
    """Redirect to Vue.js user management page"""
    return redirect('/#/admin/users')

@admin_bp.route('/users/<int:user_id>')
@admin_bp.route('/users/<int:user_id>/edit')
def edit_user(user_id):
    """Redirect to Vue.js user management page"""
    return redirect('/#/admin/users')

@admin_bp.route('/users/<int:user_id>/delete')
def delete_user(user_id):
    """Redirect to Vue.js user management page"""
    return redirect('/#/admin/users')

@admin_bp.route('/roles')
def list_roles():
    """Redirect to Vue.js role management page"""
    return redirect('/#/admin/roles')

@admin_bp.route('/roles/create')
def create_role():
    """Redirect to Vue.js role management page"""
    return redirect('/#/admin/roles')

@admin_bp.route('/roles/<int:role_id>')
@admin_bp.route('/roles/<int:role_id>/edit')
def edit_role(role_id):
    """Redirect to Vue.js role management page"""
    return redirect('/#/admin/roles')

@admin_bp.route('/roles/<int:role_id>/delete')
def delete_role(role_id):
    """Redirect to Vue.js role management page"""
    return redirect('/#/admin/roles')

@admin_bp.route('/audit')
@admin_bp.route('/audit-logs')
def audit_logs():
    """Redirect to Vue.js audit logs page"""
    return redirect('/#/admin/audit')

# Catch-all for any other admin routes
@admin_bp.route('/<path:path>')
def admin_catchall(path):
    """Redirect any other admin routes to Vue.js admin dashboard"""
    return redirect('/#/admin')