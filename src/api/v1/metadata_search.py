"""
Metadata Search API endpoints for Vue.js frontend
"""
from flask import Blueprint, request, jsonify, Response, stream_with_context
import logging
import json
import time
from typing import Dict, Any, List, Optional

from src.utils.auth_utils import jwt_required
from src.utils.schema_vectorizer import SchemaVectorizer
from src.utils.llm_engine import LLMEngine
from src.utils.user_manager import UserManager

logger = logging.getLogger('text2sql.metadata_search_api')

# Create Blueprint
metadata_search_api = Blueprint('metadata_search_api', __name__)

# Initialize components with lazy loading
schema_vectorizer = None
llm_engine = None
user_manager = UserManager()

def get_metadata_components():
    """Get metadata search components with lazy initialization."""
    global schema_vectorizer, llm_engine
    
    if schema_vectorizer is None or llm_engine is None:
        logger.info("Initializing metadata search components")
        schema_vectorizer = SchemaVectorizer()
        llm_engine = LLMEngine()
    
    return schema_vectorizer, llm_engine

@metadata_search_api.route('/search', methods=['POST'])
@jwt_required
def search_metadata():
    """Search database metadata using AI-powered semantic search."""
    try:
        data = request.get_json()
        if not data or not data.get('query'):
            return jsonify({'error': 'Missing search query'}), 400
        
        query = data['query']
        workspace = data.get('workspace', 'default')
        conversation_history = data.get('conversation_history', [])
        streaming = data.get('streaming', False)
        
        # Get components
        vectorizer, llm = get_metadata_components()
        
        # Audit log the search
        user_id = getattr(request, 'current_user_id', 'unknown')
        ip_address = request.environ.get('HTTP_X_REAL_IP', request.remote_addr)
        
        if streaming:
            # Return streaming response
            def generate():
                try:
                    # Start search
                    search_id = f"metadata_search_{int(time.time())}"
                    yield f"data: {json.dumps({'type': 'started', 'search_id': search_id})}\n\n"
                    
                    # Perform the search
                    start_time = time.time()
                    
                    # Update status
                    yield f"data: {json.dumps({'type': 'status', 'message': 'Searching metadata...'})}\n\n"
                    
                    # Perform vector search
                    search_results = vectorizer.search_schema(
                        query=query,
                        workspace=workspace,
                        top_k=10
                    )
                    
                    yield f"data: {json.dumps({'type': 'status', 'message': 'Generating response...'})}\n\n"
                    
                    # Generate AI response with conversation history
                    if conversation_history:
                        # Include conversation context
                        context_prompt = f"""
Based on the following search results and conversation history, provide a comprehensive answer:

Search Results:
{json.dumps(search_results, indent=2)}

Conversation History:
{json.dumps(conversation_history[-6:], indent=2)}  # Last 3 exchanges

Current Question: {query}
"""
                    else:
                        context_prompt = f"""
Based on the following database metadata search results, provide a comprehensive answer to the user's question:

Search Results:
{json.dumps(search_results, indent=2)}

Question: {query}
"""
                    
                    # Stream the AI response
                    ai_response = ""
                    for chunk in llm.generate_stream(context_prompt):
                        ai_response += chunk
                        yield f"data: {json.dumps({'type': 'text', 'content': chunk})}\n\n"
                    
                    # Send final results
                    end_time = time.time()
                    search_duration = end_time - start_time
                    
                    yield f"data: {json.dumps({'type': 'results', 'data': search_results, 'duration': search_duration})}\n\n"
                    
                    # Audit log the interaction
                    user_manager.log_audit_event(
                        event_type='metadata_search_streaming',
                        user_id=user_id,
                        ip_address=ip_address,
                        event_data={
                            'query': query,
                            'workspace': workspace,
                            'results_count': len(search_results),
                            'duration': search_duration,
                            'response_length': len(ai_response),
                            'conversation_history_length': len(conversation_history)
                        }
                    )
                    
                except Exception as e:
                    logger.exception(f"Error in streaming metadata search: {e}")
                    yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
                finally:
                    yield f"data: {json.dumps({'type': 'complete'})}\n\n"
            
            return Response(
                stream_with_context(generate()),
                mimetype='text/event-stream',
                headers={
                    'Cache-Control': 'no-cache',
                    'Connection': 'keep-alive',
                    'X-Accel-Buffering': 'no'
                }
            )
        else:
            # Non-streaming response
            start_time = time.time()
            
            # Perform the search
            search_results = vectorizer.search_schema(
                query=query,
                workspace=workspace,
                top_k=10
            )
            
            # Generate AI response
            if conversation_history:
                context_prompt = f"""
Based on the following search results and conversation history, provide a comprehensive answer:

Search Results:
{json.dumps(search_results, indent=2)}

Conversation History:
{json.dumps(conversation_history[-6:], indent=2)}

Current Question: {query}
"""
            else:
                context_prompt = f"""
Based on the following database metadata search results, provide a comprehensive answer to the user's question:

Search Results:
{json.dumps(search_results, indent=2)}

Question: {query}
"""
            
            ai_response = llm.generate(context_prompt)
            
            end_time = time.time()
            search_duration = end_time - start_time
            
            # Audit log
            user_manager.log_audit_event(
                event_type='metadata_search',
                user_id=user_id,
                ip_address=ip_address,
                event_data={
                    'query': query,
                    'workspace': workspace,
                    'results_count': len(search_results),
                    'duration': search_duration,
                    'response_length': len(ai_response),
                    'conversation_history_length': len(conversation_history)
                }
            )
            
            return jsonify({
                'success': True,
                'results': search_results,
                'ai_response': ai_response,
                'duration': search_duration,
                'query': query
            })
            
    except Exception as e:
        logger.exception("Error in metadata search")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@metadata_search_api.route('/schema', methods=['GET'])
@jwt_required
def get_schema_overview():
    """Get schema overview for a workspace."""
    try:
        workspace = request.args.get('workspace', 'default')
        
        # Get components
        vectorizer, _ = get_metadata_components()
        
        # Get schema overview
        schema_overview = vectorizer.get_schema_overview(workspace)
        
        # Audit log
        user_id = getattr(request, 'current_user_id', 'unknown')
        ip_address = request.environ.get('HTTP_X_REAL_IP', request.remote_addr)
        
        user_manager.log_audit_event(
            event_type='view_schema_overview',
            user_id=user_id,
            ip_address=ip_address,
            event_data={'workspace': workspace}
        )
        
        return jsonify({
            'success': True,
            'schema': schema_overview,
            'workspace': workspace
        })
        
    except Exception as e:
        logger.exception("Error getting schema overview")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@metadata_search_api.route('/tables', methods=['GET'])
@jwt_required
def get_tables_metadata():
    """Get metadata for all tables in a workspace."""
    try:
        workspace = request.args.get('workspace', 'default')
        
        # Get components
        vectorizer, _ = get_metadata_components()
        
        # Get tables metadata
        tables_metadata = vectorizer.get_tables_metadata(workspace)
        
        # Audit log
        user_id = getattr(request, 'current_user_id', 'unknown')
        ip_address = request.environ.get('HTTP_X_REAL_IP', request.remote_addr)
        
        user_manager.log_audit_event(
            event_type='view_tables_metadata',
            user_id=user_id,
            ip_address=ip_address,
            event_data={'workspace': workspace, 'tables_count': len(tables_metadata)}
        )
        
        return jsonify({
            'success': True,
            'tables': tables_metadata,
            'workspace': workspace
        })
        
    except Exception as e:
        logger.exception("Error getting tables metadata")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@metadata_search_api.route('/table/<table_name>', methods=['GET'])
@jwt_required
def get_table_metadata(table_name):
    """Get detailed metadata for a specific table."""
    try:
        workspace = request.args.get('workspace', 'default')
        
        # Get components
        vectorizer, _ = get_metadata_components()
        
        # Get table metadata
        table_metadata = vectorizer.get_table_metadata(workspace, table_name)
        
        # Audit log
        user_id = getattr(request, 'current_user_id', 'unknown')
        ip_address = request.environ.get('HTTP_X_REAL_IP', request.remote_addr)
        
        user_manager.log_audit_event(
            event_type='view_table_metadata',
            user_id=user_id,
            ip_address=ip_address,
            event_data={'workspace': workspace, 'table_name': table_name}
        )
        
        return jsonify({
            'success': True,
            'table': table_metadata,
            'workspace': workspace
        })
        
    except Exception as e:
        logger.exception("Error getting table metadata")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@metadata_search_api.route('/suggestions', methods=['GET'])
@jwt_required
def get_search_suggestions():
    """Get search suggestions based on available metadata."""
    try:
        workspace = request.args.get('workspace', 'default')
        query_prefix = request.args.get('prefix', '')
        
        # Get components
        vectorizer, _ = get_metadata_components()
        
        # Get suggestions
        suggestions = vectorizer.get_search_suggestions(workspace, query_prefix)
        
        return jsonify({
            'success': True,
            'suggestions': suggestions,
            'workspace': workspace
        })
        
    except Exception as e:
        logger.exception("Error getting search suggestions")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@metadata_search_api.route('/conversation/clear', methods=['POST'])
@jwt_required
def clear_conversation():
    """Clear conversation history for metadata search."""
    try:
        # Audit log
        user_id = getattr(request, 'current_user_id', 'unknown')
        ip_address = request.environ.get('HTTP_X_REAL_IP', request.remote_addr)
        
        user_manager.log_audit_event(
            event_type='clear_metadata_conversation',
            user_id=user_id,
            ip_address=ip_address,
            event_data={}
        )
        
        return jsonify({
            'success': True,
            'message': 'Conversation history cleared'
        })
        
    except Exception as e:
        logger.exception("Error clearing conversation")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@metadata_search_api.route('/reindex', methods=['POST'])
@jwt_required
def reindex_metadata():
    """Reindex metadata for better search performance."""
    try:
        data = request.get_json() or {}
        workspace = data.get('workspace', 'default')
        
        # Get components
        vectorizer, _ = get_metadata_components()
        
        # Start reindexing
        def generate():
            try:
                yield f"data: {json.dumps({'type': 'started', 'workspace': workspace})}\n\n"
                
                # Perform reindexing
                yield f"data: {json.dumps({'type': 'status', 'message': 'Reindexing schema metadata...'})}\n\n"
                
                result = vectorizer.reindex_schema(workspace)
                
                yield f"data: {json.dumps({'type': 'result', 'data': result})}\n\n"
                
                # Audit log
                user_id = getattr(request, 'current_user_id', 'unknown')
                ip_address = request.environ.get('HTTP_X_REAL_IP', request.remote_addr)
                
                user_manager.log_audit_event(
                    event_type='reindex_metadata',
                    user_id=user_id,
                    ip_address=ip_address,
                    event_data={'workspace': workspace, 'result': result}
                )
                
            except Exception as e:
                logger.exception(f"Error reindexing metadata: {e}")
                yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
            finally:
                yield f"data: {json.dumps({'type': 'complete'})}\n\n"
        
        return Response(
            stream_with_context(generate()),
            mimetype='text/event-stream',
            headers={
                'Cache-Control': 'no-cache',
                'Connection': 'keep-alive',
                'X-Accel-Buffering': 'no'
            }
        )
        
    except Exception as e:
        logger.exception("Error in reindex endpoint")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500