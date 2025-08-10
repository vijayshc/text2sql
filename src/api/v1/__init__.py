"""
API v1 package initialization
"""
from flask import Blueprint
from .auth import auth_api
from .query import query_api
from .feedback import feedback_api

# Create main API v1 blueprint
api_v1 = Blueprint('api_v1', __name__, url_prefix='/api/v1')

# Register sub-blueprints
api_v1.register_blueprint(auth_api, url_prefix='/auth')
api_v1.register_blueprint(query_api, url_prefix='/query')
api_v1.register_blueprint(feedback_api, url_prefix='/feedback')

__all__ = ['api_v1']