"""
Admin routes for Text2SQL application.
Handles user management, role management, and audit log views.
"""

from flask import Blueprint, render_template, flash, redirect, url_for, request, session, jsonify
from src.utils.user_manager import UserManager
from src.routes.auth_routes import admin_required, permission_required
from src.models.user import Permissions
import datetime
import csv
import io

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')
user_manager = UserManager()

@admin_bp.route('/')
@admin_required
def admin_index():
    """Admin dashboard"""
    return render_template('admin/index.html', available_templates=['admin/index.html'])

@admin_bp.route('/users')
@admin_required
@permission_required(Permissions.MANAGE_USERS)
def list_users():
    """List all users"""
    users = user_manager.get_all_users()
    return render_template('admin/users.html', users=users, available_templates=['admin/users.html'])

@admin_bp.route('/users/create', methods=['GET', 'POST'])
@admin_required
@permission_required(Permissions.MANAGE_USERS)
def create_user():
    """Create a new user"""
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        role_ids = request.form.getlist('roles')
        
        # Validate input
        if not username or not email or not password:
            flash('Username, email, and password are required.', 'danger')
            roles = user_manager.get_all_roles()
            return render_template('admin/user_form.html', roles=roles, available_templates=['admin/user_form.html'])
        
        if len(password) < 6:
            flash('Password must be at least 6 characters long.', 'danger')
            roles = user_manager.get_all_roles()
            return render_template('admin/user_form.html', roles=roles, available_templates=['admin/user_form.html'])
        
        # Create user
        try:
            user_id = user_manager.create_user(username, email, password)
            
            # Assign roles
            for role_id in role_ids:
                user_manager.add_user_to_role(user_id, int(role_id))
            
            # Log user creation
            user_manager.log_audit_event(
                user_id=session.get('user_id'),
                action='create_user',
                details=f"Created user: {username}",
                ip_address=request.remote_addr
            )
            
            flash(f'User {username} created successfully.', 'success')
            return redirect(url_for('admin.list_users'))
        except Exception as e:
            flash(f'Error creating user: {str(e)}', 'danger')
            roles = user_manager.get_all_roles()
            return render_template('admin/user_form.html', roles=roles, available_templates=['admin/user_form.html'])
    
    # GET request - display form
    roles = user_manager.get_all_roles()
    return render_template('admin/user_form.html', roles=roles, available_templates=['admin/user_form.html'])

@admin_bp.route('/users/<int:user_id>/edit', methods=['GET', 'POST'])
@admin_required
@permission_required(Permissions.MANAGE_USERS)
def edit_user(user_id):
    """Edit an existing user"""
    user = user_manager.get_user_by_id(user_id)
    
    if not user:
        flash('User not found.', 'danger')
        return redirect(url_for('admin.list_users'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        role_ids = request.form.getlist('roles')
        
        # Validate input
        if not username or not email:
            flash('Username and email are required.', 'danger')
            roles = user_manager.get_all_roles()
            user_role_ids = [r.id for r in user.roles]
            return render_template('admin/user_form.html', user=user, roles=roles, 
                                  user_role_ids=user_role_ids, available_templates=['admin/user_form.html'])
        
        # Update user
        try:
            user_manager.update_user(user_id, username, email, password if password else None)
            
            # Update roles
            current_role_ids = [r.id for r in user.roles]
            role_ids = [int(r) for r in role_ids]
            
            # Remove roles that were unchecked
            for role_id in current_role_ids:
                if role_id not in role_ids:
                    user_manager.remove_user_from_role(user_id, role_id)
            
            # Add roles that were checked
            for role_id in role_ids:
                if role_id not in current_role_ids:
                    user_manager.add_user_to_role(user_id, role_id)
            
            # Log user update
            user_manager.log_audit_event(
                user_id=session.get('user_id'),
                action='update_user',
                details=f"Updated user: {username}",
                ip_address=request.remote_addr
            )
            
            flash(f'User {username} updated successfully.', 'success')
            return redirect(url_for('admin.list_users'))
        except Exception as e:
            flash(f'Error updating user: {str(e)}', 'danger')
            roles = user_manager.get_all_roles()
            user_role_ids = [r.id for r in user.roles]
            return render_template('admin/user_form.html', user=user, roles=roles, 
                                  user_role_ids=user_role_ids, available_templates=['admin/user_form.html'])
    
    # GET request - display form
    roles = user_manager.get_all_roles()
    user_role_ids = [r.id for r in user.roles]
    return render_template('admin/user_form.html', user=user, roles=roles, 
                          user_role_ids=user_role_ids, available_templates=['admin/user_form.html'])

@admin_bp.route('/api/users/<int:user_id>/delete', methods=['POST'])
@admin_required
@permission_required(Permissions.MANAGE_USERS)
def delete_user(user_id):
    """Delete a user"""
    user = user_manager.get_user_by_id(user_id)
    
    if not user:
        flash('User not found.', 'danger')
        return redirect(url_for('admin.list_users'))
    
    # Prevent deleting admin user or self
    if user.username == 'admin' or user_id == session.get('user_id'):
        flash('Cannot delete this user.', 'danger')
        return redirect(url_for('admin.list_users'))
    
    try:
        username = user.username
        user_manager.delete_user(user_id)
        
        # Log user deletion
        user_manager.log_audit_event(
            user_id=session.get('user_id'),
            action='delete_user',
            details=f"Deleted user: {username}",
            ip_address=request.remote_addr
        )
        
        flash(f'User {username} deleted successfully.', 'success')
    except Exception as e:
        flash(f'Error deleting user: {str(e)}', 'danger')
    
    return redirect(url_for('admin.list_users'))

@admin_bp.route('/roles')
@admin_required
@permission_required(Permissions.MANAGE_ROLES)
def list_roles():
    """List all roles and permissions"""
    roles = user_manager.get_all_roles()
    permissions = user_manager.get_all_permissions()
    
    return render_template('admin/roles.html', roles=roles, permissions=permissions, 
                          available_templates=['admin/roles.html'])

@admin_bp.route('/audit-logs')
@admin_required
@permission_required(Permissions.VIEW_AUDIT_LOGS)
def audit_logs():
    """View audit logs"""
    page = request.args.get('page', 1, type=int)
    limit = request.args.get('limit', 50, type=int)
    
    logs, total = user_manager.get_audit_logs(page, limit)
    total_pages = (total + limit - 1) // limit  # Ceiling division
    
    return render_template('admin/audit_logs.html', logs=logs, page=page, 
                          total_pages=total_pages, user_manager=user_manager,
                          available_templates=['admin/audit_logs.html'])

@admin_bp.route('/api/dashboard/stats')
@admin_required
def dashboard_stats():
    """API endpoint for dashboard statistics"""
    # Get counts
    user_count = user_manager.get_user_count()
    role_count = user_manager.get_role_count()
    
    # Get today's query count
    today = datetime.datetime.now().date()
    today_start = datetime.datetime.combine(today, datetime.time.min)
    query_count = user_manager.get_query_count_since(today_start)
    
    # Get recent activity count (last 24 hours)
    day_ago = datetime.datetime.now() - datetime.timedelta(days=1)
    activity_count = user_manager.get_activity_count_since(day_ago)
    
    return jsonify({
        'userCount': user_count,
        'roleCount': role_count,
        'queryCount': query_count,
        'activityCount': activity_count
    })

@admin_bp.route('/api/audit-logs')
@admin_required
@permission_required(Permissions.VIEW_AUDIT_LOGS)
def api_audit_logs():
    """API endpoint for audit logs"""
    page = request.args.get('page', 1, type=int)
    limit = request.args.get('limit', 50, type=int)
    
    logs, total = user_manager.get_audit_logs(page, limit)
    
    # Format logs for JSON response
    log_list = []
    for log in logs:
        log_data = {
            'id': log.id,
            'timestamp': log.timestamp.isoformat(),
            'user_id': log.user_id,
            'username': user_manager.get_username_by_id(log.user_id) if log.user_id else 'System',
            'action': log.action,
            'details': log.details,
            'ip_address': log.ip_address,
            'has_detail_data': bool(log.query_text or log.sql_query or log.response)
        }
        log_list.append(log_data)
    
    return jsonify({
        'logs': log_list,
        'total': total,
        'page': page,
        'limit': limit
    })

@admin_bp.route('/api/audit-logs/<int:log_id>')
@admin_required
@permission_required(Permissions.VIEW_AUDIT_LOGS)
def api_audit_log_detail(log_id):
    """API endpoint for audit log details"""
    log = user_manager.get_audit_log_by_id(log_id)
    
    if not log:
        return jsonify({'error': 'Log not found'}), 404
    
    return jsonify({
        'id': log.id,
        'query_text': log.query_text,
        'sql_query': log.sql_query,
        'response': log.response
    })

@admin_bp.route('/api/audit-logs/export')
@admin_required
@permission_required(Permissions.VIEW_AUDIT_LOGS)
def export_audit_logs():
    """Export audit logs as CSV"""
    filter_type = request.args.get('filter', 'all')
    
    # Get all logs for export
    logs = user_manager.export_audit_logs(filter_type)
    
    # Create CSV in memory
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow(['ID', 'Timestamp', 'User', 'IP Address', 'Action', 'Details'])
    
    # Write data rows
    for log in logs:
        username = user_manager.get_username_by_id(log.user_id) if log.user_id else 'System'
        writer.writerow([
            log.id,
            log.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            username,
            log.ip_address or '-',
            log.action,
            log.details
        ])
    
    # Prepare response
    output.seek(0)
    date_str = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    
    from flask import Response
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment;filename=audit_logs_{filter_type}_{date_str}.csv'}
    )