"""
API v1 package initialization
"""
from flask import Blueprint
from .auth import auth_api
from .query import query_api
from .feedback import feedback_api
from .agent import agent_api
from .data_mapping import data_mapping_api
from .schema import schema_api
from .metadata_search import metadata_search_api

# Create main API v1 blueprint
api_v1 = Blueprint('api_v1', __name__, url_prefix='/api/v1')

# Register sub-blueprints
api_v1.register_blueprint(auth_api, url_prefix='/auth')
api_v1.register_blueprint(query_api, url_prefix='/query')
api_v1.register_blueprint(feedback_api, url_prefix='/feedback')
api_v1.register_blueprint(agent_api, url_prefix='/agent')
api_v1.register_blueprint(data_mapping_api, url_prefix='/data-mapping')
api_v1.register_blueprint(schema_api, url_prefix='/schema')
api_v1.register_blueprint(metadata_search_api, url_prefix='/metadata-search')

__all__ = ['api_v1']