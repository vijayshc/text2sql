"""
Authentication routes for Text2SQL application.
Handles login, logout, password reset, and related functionality.
"""

from flask import Blueprint, render_template, flash, redirect, url_for, request, session, abort
from functools import wraps
from src.utils.user_manager import UserManager
from src.models.user import Permissions

auth_bp = Blueprint('auth', __name__)
user_manager = UserManager()

# Decorator for routes that require admin role
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('user_id'):
            return redirect(url_for('auth.login', next=request.url))
        
        if not user_manager.has_role(session.get('user_id'), 'admin'):
            flash('You do not have permission to access this page.', 'danger')
            return redirect(url_for('index'))
            
        return f(*args, **kwargs)
    return decorated_function

# Decorator for permission-based access control
def permission_required(permission):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not session.get('user_id'):
                return redirect(url_for('auth.login', next=request.url))
                
            if not user_manager.has_permission(session.get('user_id'), permission):
                flash('You do not have permission to access this resource.', 'danger')
                return redirect(url_for('index'))
                
            return f(*args, **kwargs)
        return decorated_function
    return decorator

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Handle user login"""
    # If already logged in, redirect to index
    if session.get('user_id'):
        return redirect(url_for('index'))
        
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if not username or not password:
            flash('Username and password are required.', 'danger')
            return render_template('auth/login.html', error='Username and password are required.')
        
        # Authenticate user
        print(username, password)
        user_id = user_manager.authenticate(username, password)
        print(user_id)
        if not user_id:
            # Log failed login attempt
            user_manager.log_audit_event(
                user_id=None,
                action='login_failed',
                details=f"Failed login attempt for user: {username}",
                ip_address=request.remote_addr
            )
            flash('Invalid username or password.', 'danger')
            return render_template('auth/login.html', error='Invalid username or password.')
        
        # Check if user is active
        user = user_manager.get_user_by_id(user_id)
        if not user.is_active:
            flash('Your account is inactive. Please contact an administrator.', 'warning')
            return render_template('auth/login.html', error='Account inactive.')
        
        # Set user session
        session['user_id'] = user_id
        session.permanent = True
        
        # Log successful login
        user_manager.log_audit_event(
            user_id=user_id,
            action='login',
            details=f"User logged in: {username}",
            ip_address=request.remote_addr
        )
        
        # Redirect to next page or index
        next_page = request.args.get('next')
        if next_page and next_page.startswith('/'):  # Ensure the next URL is relative
            return redirect(next_page)
        return redirect(url_for('index'))
    
    return render_template('auth/login.html')

@auth_bp.route('/logout')
def logout():
    """Handle user logout"""
    user_id = session.get('user_id')
    username = user_manager.get_user_by_id(user_id).username if user_id else None
    
    if user_id:
        # Log logout event
        user_manager.log_audit_event(
            user_id=user_id,
            action='logout',
            details=f"User logged out: {username}",
            ip_address=request.remote_addr
        )
    
    # Clear session
    session.clear()
    
    flash('You have been logged out.', 'success')
    return redirect(url_for('auth.login'))

@auth_bp.route('/reset-password-request', methods=['GET', 'POST'])
def reset_password_request():
    """Handle password reset requests"""
    if request.method == 'POST':
        username = request.form.get('username')
        
        if not username:
            flash('Username is required.', 'danger')
            return render_template('auth/reset_request.html')
        
        # Generate and send reset token
        if user_manager.generate_reset_token(username):
            # In a real application, we would send an email with the reset link
            flash('Password reset instructions have been sent to your email.', 'success')
            
            # For demonstration, show the token in the logs (NOT secure for production)
            user = user_manager.get_user_by_username(username)
            print(f"RESET TOKEN for {username}: {user.reset_token}")
            
            return redirect(url_for('auth.login'))
        else:
            flash('Username not found.', 'danger')
            return render_template('auth/reset_request.html')
    
    return render_template('auth/reset_request.html')

@auth_bp.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    """Handle password reset with token"""
    # Verify token
    user_id = user_manager.verify_reset_token(token)
    
    if not user_id:
        flash('Invalid or expired token. Please request a new password reset.', 'danger')
        return redirect(url_for('auth.reset_password_request'))
    
    if request.method == 'POST':
        password = request.form.get('password')
        password_confirm = request.form.get('password_confirm')
        
        if not password or len(password) < 6:
            flash('Password must be at least 6 characters long.', 'danger')
            return render_template('auth/reset_password.html', token=token)
        
        if password != password_confirm:
            flash('Passwords do not match.', 'danger')
            return render_template('auth/reset_password.html', token=token)
        
        # Update the password
        if user_manager.reset_password(user_id, password):
            # Log password reset
            user_manager.log_audit_event(
                user_id=user_id,
                action='password_reset',
                details="Password reset using token",
                ip_address=request.remote_addr
            )
            
            flash('Your password has been reset successfully. You can now log in with your new password.', 'success')
            return redirect(url_for('auth.login'))
        else:
            flash('Failed to reset password. Please try again.', 'danger')
            return render_template('auth/reset_password.html', token=token)
    
    return render_template('auth/reset_password.html', token=token)

@auth_bp.route('/change-password', methods=['GET', 'POST'])
def change_password():
    """Allow logged-in users to change their password"""
    if not session.get('user_id'):
        return redirect(url_for('auth.login', next=request.url))
    
    user_id = session.get('user_id')
    
    if request.method == 'POST':
        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')
        
        if not current_password or not new_password or not confirm_password:
            flash('All fields are required.', 'danger')
            return render_template('auth/change_password.html')
        
        if new_password != confirm_password:
            flash('New passwords do not match.', 'danger')
            return render_template('auth/change_password.html')
        
        if len(new_password) < 6:
            flash('New password must be at least 6 characters long.', 'danger')
            return render_template('auth/change_password.html')
        
        # Verify current password and update
        if user_manager.change_password(user_id, current_password, new_password):
            # Log password change
            user_manager.log_audit_event(
                user_id=user_id,
                action='password_changed',
                details="Password changed by user",
                ip_address=request.remote_addr
            )
            
            flash('Your password has been updated successfully.', 'success')
            return redirect(url_for('index'))
        else:
            flash('Current password is incorrect.', 'danger')
            return render_template('auth/change_password.html')
    
    return render_template('auth/change_password.html', available_templates=auth_bp.jinja_loader.list_templates())