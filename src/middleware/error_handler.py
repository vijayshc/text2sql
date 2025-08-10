"""
Error handling middleware for API responses
"""
import logging
from flask import jsonify, request
from werkzeug.exceptions import HTTPException

logger = logging.getLogger(__name__)

def configure_error_handlers(app):
    """Configure error handlers for the Flask application"""
    
    @app.errorhandler(400)
    def bad_request(error):
        """Handle 400 Bad Request errors"""
        logger.warning(f"Bad request: {request.url} - {str(error)}")
        return jsonify({
            'error': 'Bad Request',
            'message': str(error.description) if hasattr(error, 'description') else 'Invalid request',
            'status_code': 400
        }), 400
    
    @app.errorhandler(401)
    def unauthorized(error):
        """Handle 401 Unauthorized errors"""
        logger.warning(f"Unauthorized access: {request.url}")
        return jsonify({
            'error': 'Unauthorized',
            'message': 'Authentication required',
            'status_code': 401
        }), 401
    
    @app.errorhandler(403)
    def forbidden(error):
        """Handle 403 Forbidden errors"""
        logger.warning(f"Forbidden access: {request.url}")
        return jsonify({
            'error': 'Forbidden',
            'message': 'Insufficient permissions',
            'status_code': 403
        }), 403
    
    @app.errorhandler(404)
    def not_found(error):
        """Handle 404 Not Found errors"""
        logger.info(f"Resource not found: {request.url}")
        return jsonify({
            'error': 'Not Found',
            'message': 'The requested resource was not found',
            'status_code': 404
        }), 404
    
    @app.errorhandler(405)
    def method_not_allowed(error):
        """Handle 405 Method Not Allowed errors"""
        logger.warning(f"Method not allowed: {request.method} {request.url}")
        return jsonify({
            'error': 'Method Not Allowed',
            'message': f'Method {request.method} is not allowed for this endpoint',
            'status_code': 405
        }), 405
    
    @app.errorhandler(422)
    def unprocessable_entity(error):
        """Handle 422 Unprocessable Entity errors"""
        logger.warning(f"Validation error: {request.url} - {str(error)}")
        return jsonify({
            'error': 'Unprocessable Entity',
            'message': 'Validation failed',
            'status_code': 422
        }), 422
    
    @app.errorhandler(429)
    def rate_limit_exceeded(error):
        """Handle 429 Rate Limit Exceeded errors"""
        logger.warning(f"Rate limit exceeded: {request.url}")
        return jsonify({
            'error': 'Rate Limit Exceeded',
            'message': 'Too many requests. Please try again later.',
            'status_code': 429
        }), 429
    
    @app.errorhandler(500)
    def internal_server_error(error):
        """Handle 500 Internal Server Error"""
        logger.error(f"Internal server error: {request.url} - {str(error)}")
        return jsonify({
            'error': 'Internal Server Error',
            'message': 'An unexpected error occurred',
            'status_code': 500
        }), 500
    
    @app.errorhandler(HTTPException)
    def handle_http_exception(error):
        """Handle all other HTTP exceptions"""
        logger.warning(f"HTTP exception: {error.code} - {request.url}")
        return jsonify({
            'error': error.name,
            'message': error.description,
            'status_code': error.code
        }), error.code
    
    @app.errorhandler(Exception)
    def handle_generic_exception(error):
        """Handle all other exceptions"""
        logger.exception(f"Unhandled exception: {request.url}")
        
        # Don't expose internal error details in production
        if app.debug:
            message = str(error)
        else:
            message = 'An unexpected error occurred'
        
        return jsonify({
            'error': 'Internal Server Error',
            'message': message,
            'status_code': 500
        }), 500
    
    return app

class APIException(Exception):
    """Custom exception for API-specific errors"""
    
    def __init__(self, message, status_code=400, payload=None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.payload = payload
    
    def to_dict(self):
        """Convert exception to dictionary for JSON response"""
        result = {'error': self.message}
        if self.payload:
            result.update(self.payload)
        return result

def handle_api_exception(app):
    """Register handler for custom API exceptions"""
    
    @app.errorhandler(APIException)
    def handle_api_error(error):
        """Handle custom API exceptions"""
        logger.warning(f"API exception: {error.message} - {request.url}")
        response = jsonify(error.to_dict())
        response.status_code = error.status_code
        return response
    
    return app