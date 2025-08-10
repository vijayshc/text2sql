"""
JWT Authentication middleware for API access
"""
import jwt
import logging
from datetime import datetime, timedelta
from functools import wraps
from flask import request, jsonify, current_app
from config.api_config import JWT_SECRET_KEY, JWT_ACCESS_TOKEN_EXPIRES, JWT_REFRESH_TOKEN_EXPIRES, JWT_ALGORITHM
from src.utils.user_manager import UserManager

logger = logging.getLogger(__name__)

class JWTManager:
    """JWT token management for API authentication"""
    
    def __init__(self):
        self.user_manager = UserManager()
    
    def generate_tokens(self, user_id, username):
        """Generate access and refresh tokens for a user"""
        now = datetime.utcnow()
        
        # Access token payload
        access_payload = {
            'user_id': user_id,
            'username': username,
            'type': 'access',
            'iat': now,
            'exp': now + JWT_ACCESS_TOKEN_EXPIRES
        }
        
        # Refresh token payload
        refresh_payload = {
            'user_id': user_id,
            'username': username,
            'type': 'refresh',
            'iat': now,
            'exp': now + JWT_REFRESH_TOKEN_EXPIRES
        }
        
        access_token = jwt.encode(access_payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
        refresh_token = jwt.encode(refresh_payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
        
        return {
            'access_token': access_token,
            'refresh_token': refresh_token,
            'token_type': 'Bearer',
            'expires_in': int(JWT_ACCESS_TOKEN_EXPIRES.total_seconds())
        }
    
    def verify_token(self, token, token_type='access'):
        """Verify and decode a JWT token"""
        try:
            payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
            
            # Check token type
            if payload.get('type') != token_type:
                return None
            
            # Check expiration
            if datetime.fromtimestamp(payload['exp']) < datetime.utcnow():
                return None
            
            return payload
        
        except jwt.ExpiredSignatureError:
            logger.warning("Token has expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid token: {str(e)}")
            return None
    
    def refresh_access_token(self, refresh_token):
        """Generate a new access token from a valid refresh token"""
        payload = self.verify_token(refresh_token, 'refresh')
        if not payload:
            return None
        
        # Generate new access token
        user_id = payload['user_id']
        username = payload['username']
        
        # Verify user still exists and is active
        user = self.user_manager.get_user_by_id(user_id)
        if not user or not user.get('is_active', True):
            return None
        
        now = datetime.utcnow()
        access_payload = {
            'user_id': user_id,
            'username': username,
            'type': 'access',
            'iat': now,
            'exp': now + JWT_ACCESS_TOKEN_EXPIRES
        }
        
        access_token = jwt.encode(access_payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
        
        return {
            'access_token': access_token,
            'token_type': 'Bearer',
            'expires_in': int(JWT_ACCESS_TOKEN_EXPIRES.total_seconds())
        }

# Global JWT manager instance
jwt_manager = JWTManager()

def token_required(f):
    """Decorator to require valid JWT token for API access"""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        auth_header = request.headers.get('Authorization')
        
        if auth_header:
            try:
                # Bearer token format: "Bearer <token>"
                token = auth_header.split(" ")[1]
            except IndexError:
                return jsonify({'error': 'Invalid authorization header format'}), 401
        
        if not token:
            return jsonify({'error': 'Token is missing'}), 401
        
        # Verify token
        payload = jwt_manager.verify_token(token)
        if not payload:
            return jsonify({'error': 'Token is invalid or expired'}), 401
        
        # Add user info to request context
        request.current_user = {
            'user_id': payload['user_id'],
            'username': payload['username']
        }
        
        return f(*args, **kwargs)
    
    return decorated

def api_permission_required(permission):
    """Decorator to check user permissions for API access"""
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if not hasattr(request, 'current_user'):
                return jsonify({'error': 'Authentication required'}), 401
            
            user_id = request.current_user['user_id']
            user_manager = UserManager()
            
            if not user_manager.has_permission(user_id, permission):
                return jsonify({'error': 'Insufficient permissions'}), 403
            
            return f(*args, **kwargs)
        
        return decorated
    return decorator

def api_admin_required(f):
    """Decorator to require admin role for API access"""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not hasattr(request, 'current_user'):
            return jsonify({'error': 'Authentication required'}), 401
        
        user_id = request.current_user['user_id']
        user_manager = UserManager()
        
        if not user_manager.has_role(user_id, 'admin'):
            return jsonify({'error': 'Admin access required'}), 403
        
        return f(*args, **kwargs)
    
    return decorated