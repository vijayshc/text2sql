"""
Authentication utilities for the Text2SQL application.
Contains decorators and helper functions for authentication and authorization.
"""

from flask import session, redirect, url_for, request
from functools import wraps

def login_required(f):
    """
    Decorator for routes that require login.
    Redirects to login page if user is not authenticated.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('user_id'):
            return redirect(url_for('auth.login', next=request.url))
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function
