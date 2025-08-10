"""
API-specific configuration for the Text2SQL application
"""
import os
from datetime import timedelta

# API Configuration
API_PREFIX = '/api/v1'
API_VERSION = 'v1'

# CORS Configuration
CORS_ORIGINS = os.getenv('CORS_ORIGINS', 'http://localhost:3000,http://localhost:5173').split(',')
CORS_METHODS = ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS']
CORS_HEADERS = [
    'Content-Type',
    'Authorization',
    'X-Requested-With',
    'Accept',
    'Origin',
    'Cache-Control',
    'X-File-Name'
]

# JWT Configuration
JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', os.getenv('SECRET_KEY', 'default-jwt-secret'))
JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=int(os.getenv('JWT_ACCESS_TOKEN_HOURS', '24')))
JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=int(os.getenv('JWT_REFRESH_TOKEN_DAYS', '30')))
JWT_ALGORITHM = 'HS256'

# API Rate Limiting
RATE_LIMIT_ENABLED = os.getenv('RATE_LIMIT_ENABLED', 'true').lower() == 'true'
RATE_LIMIT_DEFAULT = os.getenv('RATE_LIMIT_DEFAULT', '1000 per hour')

# API Response Configuration
API_RESPONSE_TIMEOUT = int(os.getenv('API_RESPONSE_TIMEOUT', '30'))
MAX_CONTENT_LENGTH = int(os.getenv('MAX_CONTENT_LENGTH', '16777216'))  # 16MB

# API Documentation
API_TITLE = 'Text2SQL API'
API_DESCRIPTION = 'RESTful API for Text2SQL Assistant'
API_VERSION_STRING = '1.0.0'

# Environment specific settings
ENVIRONMENT = os.getenv('ENVIRONMENT', 'development')
API_DEBUG = os.getenv('API_DEBUG', 'false').lower() == 'true' if ENVIRONMENT == 'development' else False