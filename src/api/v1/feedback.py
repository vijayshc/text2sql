"""
Feedback and samples API endpoints
"""
import logging
from flask import Blueprint, request, jsonify
from src.middleware import token_required, api_permission_required, APIException
from src.utils.feedback_manager import FeedbackManager
from src.utils.user_manager import UserManager
from src.models.user import Permissions

logger = logging.getLogger(__name__)

feedback_api = Blueprint('feedback_api', __name__)
user_manager = UserManager()

@feedback_api.route('/submit', methods=['POST'])
@token_required
def api_submit_feedback():
    """Submit user feedback on a generated SQL query"""
    try:
        data = request.get_json()
        if not data:
            raise APIException('Request body is required', 400)
        
        # Validate required fields
        required_fields = ['query_text', 'sql_query', 'feedback_rating']
        missing_fields = [field for field in required_fields if field not in data]
        if missing_fields:
            raise APIException(f"Missing required fields: {', '.join(missing_fields)}", 400)
        
        # Extract data
        query_text = data.get('query_text')
        sql_query = data.get('sql_query')
        feedback_rating = int(data.get('feedback_rating'))  # 1 for thumbs up, 0 for thumbs down
        results_summary = data.get('results_summary', '')
        workspace = data.get('workspace', 'Default')
        tables_used = data.get('tables_used', [])
        
        logger.info(f"API feedback received for query: '{query_text[:50]}...' - Rating: {feedback_rating}")
        
        # Initialize feedback manager and save feedback
        feedback_mgr = FeedbackManager()
        success = feedback_mgr.save_feedback(
            query_text=query_text,
            sql_query=sql_query,
            results_summary=results_summary,
            workspace=workspace,
            feedback_rating=feedback_rating,
            tables_used=tables_used
        )
        
        # Log audit for feedback
        user_manager.log_audit_event(
            user_id=request.current_user['user_id'],
            action='api_submit_feedback',
            details=f"Feedback rating: {feedback_rating}",
            query_text=query_text,
            sql_query=sql_query,
            response=None,
            ip_address=request.remote_addr
        )
        
        if success:
            return jsonify({
                'success': True, 
                'message': 'Feedback saved successfully'
            }), 201
        else:
            raise APIException('Failed to save feedback', 500)
            
    except APIException:
        raise
    except ValueError as e:
        raise APIException(f'Invalid data format: {str(e)}', 400)
    except Exception as e:
        logger.exception(f"Error saving feedback: {str(e)}")
        raise APIException('Failed to save feedback', 500)

@feedback_api.route('/stats', methods=['GET'])
@token_required
def api_get_feedback_stats():
    """Get statistics about stored feedback"""
    try:
        feedback_mgr = FeedbackManager()
        stats = feedback_mgr.get_feedback_stats()
        
        return jsonify({
            'success': True, 
            'stats': stats
        }), 200
        
    except Exception as e:
        logger.exception(f"Error retrieving feedback stats: {str(e)}")
        raise APIException('Failed to retrieve feedback stats', 500)

@feedback_api.route('/samples', methods=['GET', 'POST'])
@token_required
def api_manage_samples():
    """Get or create sample entries"""
    
    if request.method == 'POST':
        # Create a new sample - requires MANAGE_SAMPLES permission
        if not user_manager.has_permission(request.current_user['user_id'], Permissions.MANAGE_SAMPLES):
            raise APIException('Permission denied', 403)
        
        try:
            data = request.get_json()
            if not data:
                raise APIException('Request body is required', 400)
            
            # Validate required fields
            required_fields = ['query_text', 'sql_query']
            missing_fields = [field for field in required_fields if field not in data]
            if missing_fields:
                raise APIException(f"Missing required fields: {', '.join(missing_fields)}", 400)
            
            # Extract data
            query_text = data.get('query_text')
            sql_query = data.get('sql_query')
            results_summary = data.get('results_summary', 'Manual sample entry')
            workspace = data.get('workspace', 'Default')
            tables_used = data.get('tables_used', [])
            
            # Initialize feedback manager and save sample
            feedback_mgr = FeedbackManager()
            success = feedback_mgr.save_feedback(
                query_text=query_text,
                sql_query=sql_query,
                results_summary=results_summary,
                workspace=workspace,
                feedback_rating=1,  # Always positive for manual samples
                tables_used=tables_used,
                is_manual_sample=True
            )
            
            # Log audit for sample creation
            user_manager.log_audit_event(
                user_id=request.current_user['user_id'],
                action='api_create_sample',
                details=f"Created sample in workspace: {workspace}",
                query_text=query_text,
                sql_query=sql_query,
                response=None,
                ip_address=request.remote_addr
            )
            
            if success:
                return jsonify({
                    'success': True, 
                    'message': 'Sample saved successfully'
                }), 201
            else:
                raise APIException('Failed to save sample', 500)
                
        except APIException:
            raise
        except Exception as e:
            logger.exception(f"Error saving sample: {str(e)}")
            raise APIException('Failed to save sample', 500)
    
    else:
        # GET method - retrieve samples - requires VIEW_SAMPLES permission
        if not user_manager.has_permission(request.current_user['user_id'], Permissions.VIEW_SAMPLES):
            raise APIException('Permission denied', 403)
        
        try:
            page = request.args.get('page', 1, type=int)
            limit = request.args.get('limit', 10, type=int)
            search_query = request.args.get('query', None)
            
            # Validate pagination parameters
            if page < 1:
                raise APIException('Page must be >= 1', 400)
            if limit < 1 or limit > 100:
                raise APIException('Limit must be between 1 and 100', 400)
            
            # Initialize feedback manager and get samples
            feedback_mgr = FeedbackManager()
            samples, total = feedback_mgr.get_samples(page, limit, search_query)
            
            return jsonify({
                'success': True,
                'samples': samples,
                'total': total,
                'page': page,
                'limit': limit,
                'pages': (total + limit - 1) // limit  # Calculate total pages
            }), 200
                
        except APIException:
            raise
        except Exception as e:
            logger.exception(f"Error retrieving samples: {str(e)}")
            raise APIException('Failed to retrieve samples', 500)

@feedback_api.route('/samples/<int:sample_id>', methods=['GET', 'PUT', 'DELETE'])
@token_required
def api_manage_sample(sample_id):
    """Get, update or delete a specific sample entry"""
    
    feedback_mgr = FeedbackManager()
    
    if request.method == 'GET':
        # View a specific sample - requires VIEW_SAMPLES permission
        if not user_manager.has_permission(request.current_user['user_id'], Permissions.VIEW_SAMPLES):
            raise APIException('Permission denied', 403)
        
        try:
            sample = feedback_mgr.get_sample_by_id(sample_id)
            
            if sample:
                return jsonify({
                    'success': True,
                    'sample': sample
                }), 200
            else:
                raise APIException('Sample not found', 404)
                
        except APIException:
            raise
        except Exception as e:
            logger.exception(f"Error retrieving sample {sample_id}: {str(e)}")
            raise APIException('Failed to retrieve sample', 500)
    
    elif request.method == 'PUT':
        # Update an existing sample - requires MANAGE_SAMPLES permission
        if not user_manager.has_permission(request.current_user['user_id'], Permissions.MANAGE_SAMPLES):
            raise APIException('Permission denied', 403)
        
        try:
            data = request.get_json()
            if not data:
                raise APIException('Request body is required', 400)
            
            # Validate required fields
            required_fields = ['query_text', 'sql_query']
            missing_fields = [field for field in required_fields if field not in data]
            if missing_fields:
                raise APIException(f"Missing required fields: {', '.join(missing_fields)}", 400)
            
            success = feedback_mgr.update_sample(sample_id, data)
            
            # Log audit for sample update
            user_manager.log_audit_event(
                user_id=request.current_user['user_id'],
                action='api_update_sample',
                details=f"Updated sample ID: {sample_id}",
                query_text=data.get('query_text'),
                sql_query=data.get('sql_query'),
                response=None,
                ip_address=request.remote_addr
            )
            
            if success:
                return jsonify({
                    'success': True, 
                    'message': 'Sample updated successfully'
                }), 200
            else:
                raise APIException('Failed to update sample', 500)
                
        except APIException:
            raise
        except Exception as e:
            logger.exception(f"Error updating sample {sample_id}: {str(e)}")
            raise APIException('Failed to update sample', 500)
    
    elif request.method == 'DELETE':
        # Delete a sample - requires MANAGE_SAMPLES permission
        if not user_manager.has_permission(request.current_user['user_id'], Permissions.MANAGE_SAMPLES):
            raise APIException('Permission denied', 403)
        
        try:
            # Get sample before deletion for audit
            sample = feedback_mgr.get_sample_by_id(sample_id)
            success = feedback_mgr.delete_sample(sample_id)
            
            # Log audit for sample deletion
            if sample:
                user_manager.log_audit_event(
                    user_id=request.current_user['user_id'],
                    action='api_delete_sample',
                    details=f"Deleted sample ID: {sample_id}",
                    query_text=sample.get('query_text'),
                    sql_query=sample.get('sql_query'),
                    response=None,
                    ip_address=request.remote_addr
                )
            
            if success:
                return jsonify({
                    'success': True, 
                    'message': 'Sample deleted successfully'
                }), 200
            else:
                raise APIException('Failed to delete sample', 500)
                
        except APIException:
            raise
        except Exception as e:
            logger.exception(f"Error deleting sample {sample_id}: {str(e)}")
            raise APIException('Failed to delete sample', 500)