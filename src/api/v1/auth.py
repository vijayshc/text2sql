"""
Authentication API endpoints
"""
import logging
from flask import Blueprint, request, jsonify
from src.middleware import jwt_manager, token_required, APIException
from src.utils.user_manager import UserManager
from src.models.user import Permissions

logger = logging.getLogger(__name__)

auth_api = Blueprint('auth_api', __name__)
user_manager = UserManager()

@auth_api.route('/login', methods=['POST'])
def api_login():
    """Authenticate user and return JWT tokens"""
    try:
        data = request.get_json()
        if not data:
            raise APIException('Request body is required', 400)
        
        username = data.get('username')
        password = data.get('password')
        
        if not username or not password:
            raise APIException('Username and password are required', 400)
        
        # Authenticate user
        user = user_manager.authenticate(username, password)
        if not user:
            logger.warning(f"Failed login attempt for username: {username}")
            raise APIException('Invalid username or password', 401)
        
        # Check if user is active
        if not user.get('is_active', True):
            raise APIException('Account is disabled', 403)
        
        # Generate JWT tokens
        tokens = jwt_manager.generate_tokens(user['id'], user['username'])
        
        # Log successful login
        user_manager.log_audit_event(
            user_id=user['id'],
            action='api_login',
            details=f"User {username} logged in via API",
            ip_address=request.remote_addr
        )
        
        # Return user info with tokens
        response_data = {
            'user': {
                'id': user['id'],
                'username': user['username'],
                'email': user.get('email'),
                'roles': user_manager.get_user_roles(user['id']),
                'permissions': user_manager.get_user_permissions(user['id'])
            },
            'tokens': tokens
        }
        
        return jsonify(response_data), 200
        
    except APIException:
        raise
    except Exception as e:
        logger.exception(f"Error during API login: {str(e)}")
        raise APIException('Login failed', 500)

@auth_api.route('/refresh', methods=['POST'])
def api_refresh_token():
    """Refresh access token using refresh token"""
    try:
        data = request.get_json()
        if not data:
            raise APIException('Request body is required', 400)
        
        refresh_token = data.get('refresh_token')
        if not refresh_token:
            raise APIException('Refresh token is required', 400)
        
        # Generate new access token
        new_tokens = jwt_manager.refresh_access_token(refresh_token)
        if not new_tokens:
            raise APIException('Invalid or expired refresh token', 401)
        
        return jsonify(new_tokens), 200
        
    except APIException:
        raise
    except Exception as e:
        logger.exception(f"Error during token refresh: {str(e)}")
        raise APIException('Token refresh failed', 500)

@auth_api.route('/logout', methods=['POST'])
@token_required
def api_logout():
    """Logout user (client should discard tokens)"""
    try:
        user_id = request.current_user['user_id']
        username = request.current_user['username']
        
        # Log logout
        user_manager.log_audit_event(
            user_id=user_id,
            action='api_logout',
            details=f"User {username} logged out via API",
            ip_address=request.remote_addr
        )
        
        return jsonify({'message': 'Logged out successfully'}), 200
        
    except Exception as e:
        logger.exception(f"Error during API logout: {str(e)}")
        raise APIException('Logout failed', 500)

@auth_api.route('/profile', methods=['GET'])
@token_required
def api_get_profile():
    """Get current user profile"""
    try:
        user_id = request.current_user['user_id']
        
        # Get user details
        user = user_manager.get_user_by_id(user_id)
        if not user:
            raise APIException('User not found', 404)
        
        profile_data = {
            'id': user['id'],
            'username': user['username'],
            'email': user.get('email'),
            'created_at': user.get('created_at'),
            'last_login': user.get('last_login'),
            'is_active': user.get('is_active', True),
            'roles': user_manager.get_user_roles(user_id),
            'permissions': user_manager.get_user_permissions(user_id)
        }
        
        return jsonify(profile_data), 200
        
    except APIException:
        raise
    except Exception as e:
        logger.exception(f"Error getting user profile: {str(e)}")
        raise APIException('Failed to get profile', 500)

@auth_api.route('/change-password', methods=['POST'])
@token_required
def api_change_password():
    """Change user password"""
    try:
        data = request.get_json()
        if not data:
            raise APIException('Request body is required', 400)
        
        current_password = data.get('current_password')
        new_password = data.get('new_password')
        
        if not current_password or not new_password:
            raise APIException('Current password and new password are required', 400)
        
        user_id = request.current_user['user_id']
        username = request.current_user['username']
        
        # Verify current password
        user = user_manager.authenticate(username, current_password)
        if not user:
            raise APIException('Current password is incorrect', 400)
        
        # Validate new password
        if len(new_password) < 6:
            raise APIException('New password must be at least 6 characters long', 400)
        
        # Change password
        success = user_manager.change_password(user_id, new_password)
        if not success:
            raise APIException('Failed to change password', 500)
        
        # Log password change
        user_manager.log_audit_event(
            user_id=user_id,
            action='api_change_password',
            details=f"User {username} changed password via API",
            ip_address=request.remote_addr
        )
        
        return jsonify({'message': 'Password changed successfully'}), 200
        
    except APIException:
        raise
    except Exception as e:
        logger.exception(f"Error changing password: {str(e)}")
        raise APIException('Password change failed', 500)

@auth_api.route('/verify', methods=['GET'])
@token_required
def api_verify_token():
    """Verify if current token is valid"""
    try:
        user_id = request.current_user['user_id']
        username = request.current_user['username']
        
        return jsonify({
            'valid': True,
            'user': {
                'id': user_id,
                'username': username
            }
        }), 200
        
    except Exception as e:
        logger.exception(f"Error verifying token: {str(e)}")
        raise APIException('Token verification failed', 500)