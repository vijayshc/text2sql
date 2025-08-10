"""
Security enhancement routes for the Text2SQL application.
Implements advanced security features including:
- CSRF protection
- Rate limiting
- Secure session management
- Password policy enforcement
"""

from flask import Blueprint, request, session, redirect, url_for, jsonify, abort
import functools
import time
import re
import uuid
from datetime import datetime, timedelta
import secrets
from src.utils.user_manager import UserManager
import logging

# Initialize blueprint
security_bp = Blueprint('security', __name__)

# Initialize user manager
user_manager = UserManager()

# Logger
logger = logging.getLogger('text2sql')

# Store for rate limiting (in production, use Redis or another distributed cache)
rate_limit_store = {}
failed_login_attempts = {}
ip_login_attempts = {}

# Session configurations
SESSION_TIMEOUT = 30 * 60  # 30 minutes in seconds
SESSION_ABSOLUTE_TIMEOUT = 24 * 60 * 60  # 24 hours in seconds


# Custom CSRF token functions
def generate_csrf_token():
    """Generate a new CSRF token and store in session"""
    if '_csrf_token' not in session:
        session['_csrf_token'] = secrets.token_hex(16)
    return session['_csrf_token']


def validate_csrf_token(token):
    """Validate CSRF token against the one in session"""
    session_token = session.get('_csrf_token')
    if not session_token:
        return False
    return session_token == token


# CSRF protection decorator
def csrf_protect(f):
    """Decorator to check for CSRF token in POST/PUT/DELETE requests"""
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        if request.method in ['POST', 'PUT', 'DELETE']:
            token = request.form.get('_csrf_token') or request.headers.get('X-CSRF-Token')
            if not token or not validate_csrf_token(token):
                logger.warning(f"CSRF validation failed for {request.path}")
                abort(403, description="CSRF validation failed")
        return f(*args, **kwargs)
    return decorated_function


def validate_password_strength(password):
    """
    Validate password strength based on security best practices
    Returns (is_valid, message) tuple
    """
    if len(password) < 12:
        return False, "Password must be at least 12 characters long"
    
    if not re.search(r'[A-Z]', password):
        return False, "Password must contain at least one uppercase letter"
        
    if not re.search(r'[a-z]', password):
        return False, "Password must contain at least one lowercase letter"
        
    if not re.search(r'[0-9]', password):
        return False, "Password must contain at least one number"
        
    if not re.search(r'[^A-Za-z0-9]', password):
        return False, "Password must contain at least one special character"
        
    # Check for common passwords (in production, use a more comprehensive list)
    common_passwords = ['Password123!', 'Admin123!', 'Welcome123!']
    if password in common_passwords:
        return False, "Password is too common"
        
    return True, "Password is strong"


def requires_fresh_login(f):
    """
    Decorator to require a fresh login for sensitive operations
    """
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('user_id'):
            return redirect(url_for('auth.login'))
            
        # Check if the login is fresh (less than 10 minutes old)
        if not session.get('login_fresh') or \
           datetime.utcnow().timestamp() - session.get('login_time', 0) > 600:
            # Store the original URL for redirect after re-authentication
            session['next_url'] = request.url
            return redirect(url_for('security.reauthenticate'))
            
        return f(*args, **kwargs)
    return decorated_function


def rate_limit(limit=5, per=60, scope='default'):
    """
    Rate limiting decorator
    - limit: maximum number of calls
    - per: time period in seconds
    - scope: unique name for the rate limit
    """
    def decorator(f):
        @functools.wraps(f)
        def decorated_function(*args, **kwargs):
            # Get client identifier (IP address or user_id if logged in)
            client_id = session.get('user_id', request.remote_addr)
            
            # Create a unique key for this client and endpoint
            key = f"{client_id}:{scope}"
            
            # Initialize or get rate limiting data
            if key not in rate_limit_store:
                rate_limit_store[key] = {'count': 0, 'reset_time': time.time() + per}
            
            # Reset count if time period has passed
            if time.time() > rate_limit_store[key]['reset_time']:
                rate_limit_store[key] = {'count': 0, 'reset_time': time.time() + per}
            
            # Check limit
            if rate_limit_store[key]['count'] >= limit:
                # Set rate limit headers
                headers = {
                    'X-RateLimit-Limit': str(limit),
                    'X-RateLimit-Remaining': '0',
                    'X-RateLimit-Reset': str(int(rate_limit_store[key]['reset_time']))
                }
                return jsonify({'error': 'Too many requests'}), 429, headers
                
            # Increment count
            rate_limit_store[key]['count'] += 1
            
            # Set rate limit headers
            headers = {
                'X-RateLimit-Limit': str(limit),
                'X-RateLimit-Remaining': str(limit - rate_limit_store[key]['count']),
                'X-RateLimit-Reset': str(int(rate_limit_store[key]['reset_time']))
            }
            
            # Execute the function
            response = f(*args, **kwargs)
            
            # Add headers to the response
            if isinstance(response, tuple) and len(response) >= 3:
                # Response with status and headers
                body, status, existing_headers = response
                existing_headers.update(headers)
                return body, status, existing_headers
            elif isinstance(response, tuple) and len(response) == 2:
                # Response with status but no headers
                body, status = response
                return body, status, headers
            else:
                # Response is just the body
                return response
                
        return decorated_function
    return decorator


@security_bp.before_app_request
def session_timeout_check():
    """
    Check and enforce session timeout before each request
    """
    # Skip for static resources
    if request.path.startswith('/static'):
        return
        
    if 'user_id' in session:
        # Check for absolute timeout (max session length)
        if 'session_start' in session and \
           datetime.utcnow().timestamp() - session['session_start'] > SESSION_ABSOLUTE_TIMEOUT:
            # Session has expired absolutely, force logout
            session.clear()
            return redirect(url_for('auth.login'))
            
        # Check for inactivity timeout
        if 'last_active' in session and \
           datetime.utcnow().timestamp() - session['last_active'] > SESSION_TIMEOUT:
            # Session has expired due to inactivity, force logout
            session.clear()
            return redirect(url_for('auth.login'))
            
        # Update last activity time
        session['last_active'] = datetime.utcnow().timestamp()


@security_bp.after_app_request
def add_security_headers(response):
    """
    Add security-related headers to all responses
    """
    # Content Security Policy - Updated to include DataTables CDN and other necessary resources
    csp_directives = [
        "default-src 'self'",
        "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com https://code.jquery.com https://cdn.datatables.net",
        "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com https://fonts.googleapis.com https://cdn.datatables.net",
        "font-src 'self' https://fonts.gstatic.com https://cdn.jsdelivr.net https://cdnjs.cloudflare.com https://cdn.datatables.net",
        "img-src 'self' data: blob: https://cdn.datatables.net",
        "connect-src 'self'",
        "frame-src 'self'"
    ]
    response.headers['Content-Security-Policy'] = "; ".join(csp_directives)
    
    # Prevent MIME type sniffing
    response.headers['X-Content-Type-Options'] = 'nosniff'
    
    # Prevent clickjacking
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    
    # Enable XSS protection in browsers
    response.headers['X-XSS-Protection'] = '1; mode=block'
    
    # Control caching of sensitive information
    if 'Cache-Control' not in response.headers:
        response.headers['Cache-Control'] = 'no-store, max-age=0'
    
    return response


@security_bp.route('/reauthenticate', methods=['GET', 'POST'])
@csrf_protect
def reauthenticate():
    """
    Require re-authentication for sensitive operations
    """
    error = None
    if request.method == 'POST':
        username = session.get('username')
        password = request.form.get('password')
        
        if not username or not password:
            error = "Username and password required"
        else:
            user_id = user_manager.authenticate(username, password)
            
            if user_id:
                # Update session with fresh login time
                session['login_fresh'] = True
                session['login_time'] = datetime.utcnow().timestamp()
                
                # Log the successful reauthentication
                log_security_event(
                    'reauthenticate_success', 
                    username,
                    request.remote_addr,
                    f"User {username} successfully reauthenticated"
                )
                
                # Redirect to original destination
                next_url = session.pop('next_url', url_for('index'))
                return redirect(next_url)
            else:
                error = "Invalid password"
                
                # Log the failed reauthentication attempt
                log_security_event(
                    'reauthenticate_failure',
                    username,
                    request.remote_addr,
                    f"Failed reauthentication attempt for user {username}"
                )
    
    # For API-only architecture, return JSON response
    return jsonify({
        'success': False,
        'error': error or 'Reauthentication required',
        'requires_reauthentication': True
    }), 401


@security_bp.route('/rotate-session', methods=['POST'])
def rotate_session():
    """
    Rotate session ID to prevent session fixation attacks
    This should be called after login, privilege changes, etc.
    """
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
        
    # Store important session data
    user_id = session.get('user_id')
    username = session.get('username')
    
    # Generate a new session ID while preserving the data
    session.sid = secrets.token_urlsafe(32)
    
    # Restore critical data
    session['user_id'] = user_id
    session['username'] = username
    session['session_start'] = datetime.utcnow().timestamp()
    session['last_active'] = datetime.utcnow().timestamp()
    
    return jsonify({'success': True}), 200


def is_rate_limited_for_login(ip_address):
    """
    Check if an IP address is rate-limited for login attempts
    """
    now = datetime.utcnow().timestamp()
    
    # Initialize tracking for this IP if it doesn't exist
    if ip_address not in ip_login_attempts:
        ip_login_attempts[ip_address] = {
            'attempts': 0,
            'reset_time': now + 3600,  # 1 hour window
            'blocked_until': 0
        }
    
    # Check if IP is currently blocked
    if ip_login_attempts[ip_address]['blocked_until'] > now:
        return True, int(ip_login_attempts[ip_address]['blocked_until'] - now)
    
    # Reset attempts if the window has passed
    if now > ip_login_attempts[ip_address]['reset_time']:
        ip_login_attempts[ip_address] = {
            'attempts': 0,
            'reset_time': now + 3600,  # 1 hour window
            'blocked_until': 0
        }
    
    # Check if too many attempts in this window
    if ip_login_attempts[ip_address]['attempts'] >= 10:  # 10 attempts per hour
        # Block for increasing amount of time
        block_minutes = min(60, 5 * (ip_login_attempts[ip_address]['attempts'] - 9))
        ip_login_attempts[ip_address]['blocked_until'] = now + (block_minutes * 60)
        return True, block_minutes * 60
    
    return False, 0


def record_failed_login(username, ip_address):
    """
    Record a failed login attempt for both username and IP
    """
    now = datetime.utcnow().timestamp()
    
    # Track by username
    if username not in failed_login_attempts:
        failed_login_attempts[username] = {
            'attempts': 0,
            'reset_time': now + 3600  # 1 hour window
        }
    
    if now > failed_login_attempts[username]['reset_time']:
        failed_login_attempts[username] = {
            'attempts': 1,
            'reset_time': now + 3600
        }
    else:
        failed_login_attempts[username]['attempts'] += 1
    
    # Track by IP
    if ip_address not in ip_login_attempts:
        ip_login_attempts[ip_address] = {
            'attempts': 0,
            'reset_time': now + 3600,
            'blocked_until': 0
        }
    
    if now > ip_login_attempts[ip_address]['reset_time']:
        ip_login_attempts[ip_address] = {
            'attempts': 1,
            'reset_time': now + 3600,
            'blocked_until': 0
        }
    else:
        ip_login_attempts[ip_address]['attempts'] += 1


def clear_login_attempts(username, ip_address):
    """
    Clear login attempts on successful login
    """
    if username in failed_login_attempts:
        del failed_login_attempts[username]
    
    if ip_address in ip_login_attempts:
        # Keep the IP in the tracking dict but reset attempts
        ip_login_attempts[ip_address]['attempts'] = 0


def check_for_account_lockout(username):
    """
    Check if an account should be locked due to too many failed attempts
    """
    if username in failed_login_attempts:
        # Lock account after 5 consecutive failed attempts
        return failed_login_attempts[username]['attempts'] >= 5
    
    return False


def log_security_event(event_type, username, ip_address, details=None):
    """
    Log a security-related event
    """
    try:
        user_id = None
        user = user_manager.get_user_by_username(username) if username else None
        if user:
            user_id = user.id
        
        user_manager.log_audit_event(
            user_id=user_id,
            action=f"security_{event_type}",
            details=details or f"Security event: {event_type}",
            ip_address=ip_address
        )
    except Exception as e:
        # Log the error but don't fail the request
        logger.error(f"Failed to log security event: {str(e)}")