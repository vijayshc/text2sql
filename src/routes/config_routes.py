"""
Configuration routes for managing application settings
"""

from flask import Blueprint, render_template, request, jsonify, abort, current_app, flash, redirect, url_for, session
from sqlalchemy import func
from sqlalchemy.exc import SQLAlchemyError

from src.models.configuration import Configuration, ConfigType
from src.models.user import Permissions
from src.routes.auth_routes import permission_required
from src.utils.database import get_db_session
from src.utils.auth_utils import login_required

# Create the blueprint
config_bp = Blueprint('config', __name__, url_prefix='/admin/config')

@config_bp.route('/', methods=['GET'])
@login_required
@permission_required(Permissions.MANAGE_CONFIG)
def config_list():
    """Display the configuration management page"""
    return render_template('admin/config.html')

@config_bp.route('/api/list', methods=['GET'])
@login_required
@permission_required(Permissions.MANAGE_CONFIG)
def api_config_list():
    """API endpoint to list all configurations"""
    try:
        session = get_db_session()
        
        # Get optional category filter
        category = request.args.get('category')
        
        # Query configurations
        query = session.query(Configuration)
        if category:
            query = query.filter(Configuration.category == category)
            
        # Get all configurations
        configs = query.order_by(Configuration.category, Configuration.key).all()
        
        # Format the results
        result = []
        for config in configs:
            # Mask sensitive values
            display_value = "********" if config.is_sensitive else config.value
            
            result.append({
                'id': config.id,
                'key': config.key,
                'value': display_value,
                'value_type': config.value_type.value,
                'description': config.description,
                'category': config.category,
                'is_sensitive': config.is_sensitive
            })
            
        # Get distinct categories
        categories = session.query(Configuration.category).distinct().order_by(Configuration.category).all()
        categories = [c[0] for c in categories]
        
        return jsonify({
            'status': 'success',
            'data': result,
            'categories': categories
        })
    except SQLAlchemyError as e:
        current_app.logger.error(f"Database error: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'Database error occurred'
        }), 500
    finally:
        session.close()

@config_bp.route('/api/get/<int:config_id>', methods=['GET'])
@login_required
@permission_required(Permissions.MANAGE_CONFIG)
def api_get_config(config_id):
    """API endpoint to get a specific configuration"""
    try:
        session = get_db_session()
        config = session.query(Configuration).filter_by(id=config_id).first()
        
        if not config:
            return jsonify({
                'status': 'error',
                'message': 'Configuration not found'
            }), 404
            
        # Mask sensitive values
        display_value = "********" if config.is_sensitive else config.value
        
        return jsonify({
            'status': 'success',
            'data': {
                'id': config.id,
                'key': config.key,
                'value': display_value,
                'value_type': config.value_type.value,
                'description': config.description,
                'category': config.category,
                'is_sensitive': config.is_sensitive
            }
        })
    except SQLAlchemyError as e:
        current_app.logger.error(f"Database error: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'Database error occurred'
        }), 500
    finally:
        session.close()
        
@config_bp.route('/api/update/<int:config_id>', methods=['POST'])
@login_required
@permission_required(Permissions.MANAGE_CONFIG)
def api_update_config(config_id):
    """API endpoint to update a configuration"""
    try:
        session = get_db_session()
        config = session.query(Configuration).filter_by(id=config_id).first()
        
        if not config:
            return jsonify({
                'status': 'error',
                'message': 'Configuration not found'
            }), 404
        
        # Get data from request
        data = request.json
        
        # Only update the value (other properties should be changed with caution)
        if 'value' in data:
            # If it's sensitive and value is masked, don't update
            if config.is_sensitive and data['value'] == "********":
                pass  # Keep the existing value
            else:
                config.value = data['value']
        
        session.commit()
        
        return jsonify({
            'status': 'success',
            'message': 'Configuration updated successfully'
        })
    except SQLAlchemyError as e:
        session.rollback()
        current_app.logger.error(f"Database error: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'Database error occurred'
        }), 500
    finally:
        session.close()

@config_bp.route('/api/create', methods=['POST'])
@login_required
@permission_required(Permissions.MANAGE_CONFIG)
def api_create_config():
    """API endpoint to create a new configuration"""
    try:
        session = get_db_session()
        data = request.json
        
        # Check if required fields are present
        required_fields = ['key', 'value', 'value_type', 'category', 'description']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'status': 'error',
                    'message': f'Missing required field: {field}'
                }), 400
                
        # Check if key already exists
        existing = session.query(Configuration).filter_by(key=data['key']).first()
        if existing:
            return jsonify({
                'status': 'error',
                'message': f'Configuration key already exists: {data["key"]}'
            }), 400
        
        # Create new configuration
        config = Configuration(
            key=data['key'],
            value=data['value'],
            value_type=ConfigType(data['value_type']),
            description=data['description'],
            category=data['category'],
            is_sensitive=data.get('is_sensitive', False)
        )
        
        session.add(config)
        session.commit()
        
        return jsonify({
            'status': 'success',
            'message': 'Configuration created successfully',
            'id': config.id
        })
    except SQLAlchemyError as e:
        session.rollback()
        current_app.logger.error(f"Database error: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'Database error occurred'
        }), 500
    except ValueError as e:
        # This might happen if the value_type is invalid
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 400
    finally:
        session.close()
        
@config_bp.route('/api/delete/<int:config_id>', methods=['DELETE'])
@login_required
@permission_required(Permissions.MANAGE_CONFIG)
def api_delete_config(config_id):
    """API endpoint to delete a configuration"""
    try:
        session = get_db_session()
        config = session.query(Configuration).filter_by(id=config_id).first()
        
        if not config:
            return jsonify({
                'status': 'error',
                'message': 'Configuration not found'
            }), 404
        
        session.delete(config)
        session.commit()
        
        return jsonify({
            'status': 'success',
            'message': 'Configuration deleted successfully'
        })
    except SQLAlchemyError as e:
        session.rollback()
        current_app.logger.error(f"Database error: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'Database error occurred'
        }), 500
    finally:
        session.close()
        
@config_bp.route('/api/categories', methods=['GET'])
@login_required
@permission_required(Permissions.MANAGE_CONFIG)
def api_get_categories():
    """API endpoint to get distinct configuration categories"""
    try:
        session = get_db_session()
        categories = session.query(Configuration.category).distinct().order_by(Configuration.category).all()
        categories = [c[0] for c in categories]
        
        return jsonify({
            'status': 'success',
            'data': categories
        })
    except SQLAlchemyError as e:
        current_app.logger.error(f"Database error: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'Database error occurred'
        }), 500
    finally:
        session.close()
