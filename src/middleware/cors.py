"""
CORS middleware configuration for API access
"""
from flask_cors import CORS
from config.api_config import CORS_ORIGINS, CORS_METHODS, CORS_HEADERS

def configure_cors(app):
    """Configure CORS for the Flask application"""
    
    cors_config = {
        'origins': CORS_ORIGINS,
        'methods': CORS_METHODS,
        'allow_headers': CORS_HEADERS,
        'supports_credentials': True,  # Allow credentials for JWT tokens
        'max_age': 86400  # Cache preflight requests for 24 hours
    }
    
    # Configure CORS
    CORS(app, **cors_config)
    
    return app