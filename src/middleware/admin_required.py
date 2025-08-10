"""
Admin required middleware for Text2SQL application.
Ensures only admin users can access admin endpoints.
"""

from functools import wraps
from flask import jsonify
from flask_jwt_extended import get_jwt_identity
from src.models.user import User

def admin_required(f):
    """
    Decorator that ensures the current user has admin privileges.
    Must be used after @jwt_required()
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            user_id = get_jwt_identity()
            if not user_id:
                return jsonify({'error': 'Authentication required'}), 401
            
            user = User.get_by_id(user_id)
            if not user:
                return jsonify({'error': 'User not found'}), 401
            
            # Check if user is admin
            if not user.is_admin:
                return jsonify({'error': 'Admin privileges required'}), 403
            
            return f(*args, **kwargs)
        except Exception as e:
            return jsonify({'error': 'Authorization check failed'}), 500
    
    return decorated_function