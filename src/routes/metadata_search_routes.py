"""
Routes for metadata search functionality.
"""

from flask import Blueprint, request, jsonify, current_app, render_template, session
import logging
import json
import time
from typing import Dict, Any, List, Optional
from src.utils.schema_vectorizer import SchemaVectorizer
from src.utils.llm_engine import LLMEngine
from src.utils.auth_utils import login_required
from src.utils.user_manager import UserManager

# Create Blueprint
metadata_search_bp = Blueprint('metadata_search', __name__)

# Logger
logger = logging.getLogger('text2sql.metadata_search')

# Initialize components with lazy loading
schema_vectorizer = None
llm_engine = None
reranking_model = None
user_manager = UserManager()

def get_metadata_components():
    """Get metadata search components with lazy initialization"""
    global schema_vectorizer, llm_engine
    
    if schema_vectorizer is None or llm_engine is None:
        logger.info("Initializing metadata search components")
        schema_vectorizer = SchemaVectorizer()
        llm_engine = LLMEngine()
    
    return schema_vectorizer, llm_engine

# _get_reranking_model function has been moved to LLMEngine class
def _get_reranking_model():
    """Get the reranking model from the centralized LLM engine
    
    Returns:
        CrossEncoder: The initialized reranking model (cross-encoder)
    """
    # Ensure components are initialized
    _, llm_engine_instance = get_metadata_components()
    try:
        return llm_engine_instance.get_reranking_model()
    except Exception as e:
        logger.error(f"Failed to get reranking model from LLMEngine: {str(e)}", exc_info=True)
        return None

@metadata_search_bp.route('/api/metadata/process', methods=['POST'])
@login_required
def process_schema_metadata():
    """API endpoint for processing schema metadata into vector store"""
    try:
        # Get initialized components
        schema_vectorizer_instance, _ = get_metadata_components()
        
        # Process schema metadata
        success = schema_vectorizer_instance.process_schema_metadata()
        
        if success:
            return jsonify({'success': True, 'message': 'Schema metadata processed successfully'})
        else:
            return jsonify({'success': False, 'error': 'Failed to process schema metadata'}), 500
            
    except Exception as e:
        logger.error(f"Error processing schema metadata: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

@metadata_search_bp.route('/admin/metadata')
@login_required
def admin_metadata():
    """Admin interface for schema metadata management"""
    return render_template('admin/metadata.html')
    
@metadata_search_bp.route('/api/metadata/stats', methods=['GET'])
@login_required
def get_metadata_stats():
    """Get statistics about the schema metadata in the vector database"""
    try:
        # Get initialized components
        schema_vectorizer_instance, _ = get_metadata_components()
        
        # Get stats from vector store
        stats = schema_vectorizer_instance.get_stats()
        
        if stats:
            return jsonify({'success': True, 'stats': stats})
        else:
            return jsonify({'success': False, 'message': 'No metadata statistics available'})
            
    except Exception as e:
        logger.error(f"Error getting metadata stats: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

def generate_metadata_response(query: str, sources: List[Dict[str, Any]], conversation_history: List[Dict[str, str]] = None, stream: bool = False):
    """Generate a response based on the metadata search results
    
    Args:
        query: User query
        sources: List of metadata search results
        conversation_history: Previous conversation messages for context
        stream: Whether to stream the response
        
    Returns:
        If stream=False: str: Generated response
        If stream=True: Generator that yields text chunks
    """
    if not sources:
        return "I couldn't find any schema information matching your query."
    
    try:
        # Create a prompt with the sources
        source_text = "\n\n".join([src.get('text', '') for src in sources[:5]])
        
        # Build conversation context if history is provided
        conversation_context = ""
        if conversation_history:
            conversation_context = "\n\nPrevious conversation context:\n"
            # Include only the last few messages to avoid token limits
            recent_history = conversation_history[-6:]  # Last 6 messages (3 exchanges)
            for msg in recent_history:
                role = msg.get('role', '')
                content = msg.get('content', '')
                if role == 'user':
                    conversation_context += f"User: {content}\n"
                elif role == 'assistant':
                    conversation_context += f"Assistant: {content}\n"
        
        # Format prompt as a list of messages for the LLM
        messages = [
            {
                "role": "system", 
                "content": f"You are a database expert that helps users understand database schema.{conversation_context}"
            },
            {
                "role": "user", 
                "content": f"""
Answer the following question about database schema:

Query: {query}

Here is the relevant schema information:

{source_text}

Create a helpful, answer in markdown format. When mentioning tables and columns, use code formatting like `tableName.columnName`.
For results that include multiple tables, present a summary in a markdown table format with columns for Database, Table, Column, Type, and Description.
"""
            }
        ]
        
        # Get initialized components
        _, llm_engine_instance = get_metadata_components()
        
        # Generate text with LLM using the correct method, with streaming if requested
        return llm_engine_instance.generate_completion(messages, log_prefix="Metadata QA", stream=stream)
        
    except Exception as e:
        logger.error(f"Error generating metadata response: {str(e)}", exc_info=True)
        if stream:
            def error_generator():
                yield f"I found some relevant schema information, but encountered an error formatting the response. Error: {str(e)}"
            return error_generator()
        return f"I found some relevant schema information, but encountered an error formatting the response. Error: {str(e)}"

@metadata_search_bp.route('/api/metadata/search/stream', methods=['POST', 'GET'])
@login_required
def search_metadata_stream():
    """Process a metadata search query and stream the results"""
    from flask import Response, stream_with_context, session
    
    # Handle POST request (initial query setup)
    if request.method == 'POST':
        data = request.get_json()
        
        if not data or 'query' not in data:
            return jsonify({'success': False, 'error': 'No query provided'}), 400
            
        query = data.get('query')
        limit = int(data.get('limit', 100))
        conversation_history = data.get('conversation_history', [])
        
        # Store the query, limit, and conversation history in session for the subsequent GET request
        session['current_metadata_query'] = query
        session['current_metadata_limit'] = limit
        session['current_metadata_conversation_history'] = conversation_history
        
        return jsonify({"success": True, "message": "Query received"})
    
    # Handle GET request (SSE streaming)
    elif request.method == 'GET':
        query = request.args.get('query') or session.get('current_metadata_query')
        limit = session.get('current_metadata_limit', 10)
        conversation_history = session.get('current_metadata_conversation_history', [])
        
        if not query:
            return jsonify({"error": "No query found"}), 400
    
    try:
        logger.info(f"Metadata search streaming request: {query}")
        
        rerank = request.args.get('rerank', session.get('current_metadata_rerank', True))
        if isinstance(rerank, str) and rerank.lower() == 'false':
            rerank = False
        
        # Get initialized components
        schema_vectorizer_instance, _ = get_metadata_components()
            
        # Filter results with LLM to extract schema entities (now always using enhanced search with BM25)
        results, filter_expr = schema_vectorizer_instance.filter_with_llm(query, limit=limit)
        
        # Simple logic: if filter was applied, skip reranking (direct hit optimization)
        skip_reranking = filter_expr and filter_expr.startswith('Filter:')
        
        # Apply reranking only if no direct hits detected and we have enough results
        if skip_reranking:
            logger.info(f"Direct hit detected (filter applied), skipping reranking for {len(results)} results")
        elif not rerank:
            logger.info("Reranking disabled by request")
        elif len(results) <= 1:
            logger.info(f"Only {len(results)} results, skipping reranking")
        
        if not skip_reranking and rerank and len(results) > 1:
            try:
                logger.info(f"Reranking {len(results)} results for streaming endpoint")
                reranker = _get_reranking_model()
                
                if reranker:
                    # Prepare candidate pairs for reranking
                    candidate_pairs = [(query, result.get('text', '')) for result in results]
                    
                    # Get reranking scores
                    try:
                        rerank_scores = reranker.predict(candidate_pairs)
                        
                        # Add rerank scores to candidates
                        for idx, score in enumerate(rerank_scores):
                            results[idx]['rerank_score'] = float(score)
                         
                        # Filter out candidates with negative scores (indicating poor relevance)
                        positive_scored_results = [r for r in results if r.get('rerank_score', 0) >= 0]
                        
                        if positive_scored_results:
                            logger.info(f"Found {len(positive_scored_results)} results with positive reranking scores")
                            # Sort by rerank score (higher is better) among positive scores
                            results = sorted(positive_scored_results, key=lambda x: x.get('rerank_score', 0), reverse=True)
                            
                            logger.info(f"Reranking successful, returning top {min(limit, len(results))} results")
                            # Keep only up to the original limit
                            results = results[:limit]
                        else:
                            logger.warning("No results with positive reranking scores, using original results")
                    except Exception as e:
                        logger.error(f"Reranking prediction failed: {str(e)}", exc_info=True)
                        logger.info("Falling back to vector search results")
                else:
                    logger.warning("Reranker not available, using original results")
            except Exception as e:
                logger.error(f"Reranking failed: {str(e)}", exc_info=True)
                logger.info("Falling back to vector search results")

        if not results:
            # Audit log for empty results
            user_manager.log_audit_event(
                user_id=session.get('user_id'),
                action='metadata_search_stream',
                details=f"Metadata search streaming query completed with no results",
                ip_address=request.remote_addr,
                query_text=query,
                response="No schema metadata found matching the query"
            )
            
            # Create a simple generator for empty results
            def empty_generator():
                yield "I couldn't find any schema metadata matching your query."
            
            # Return streaming response with empty generator
            def generate_empty():
                yield "Content-Type: text/event-stream\n"
                yield "Cache-Control: no-cache\n"
                yield "Connection: keep-alive\n\n"
                
                yield f"event: sources\ndata: []\n\n"
                
                empty_json = json.dumps({"text": "I couldn't find any schema metadata matching your query."})
                yield f"data: {empty_json}\n\n"
                
                yield "event: done\ndata: {}\n\n"
            
            response = Response(stream_with_context(generate_empty()), 
                            content_type='text/event-stream')
            response.headers['X-Accel-Buffering'] = 'no'
            response.headers['Cache-Control'] = 'no-cache'
            response.headers['Connection'] = 'keep-alive'
            return response
        
        # Format results for display
        sources = []
        for result in results:
            if 'text' in result:
                sources.append({
                    'workspace': result.get('workspace', ''),
                    'table': result.get('table', ''),
                    'column': result.get('column', ''),
                    'text': result.get('text', ''),
                    'similarity': result.get('similarity', 0.0)
                })
        
        # Get streaming answer
        # logger.info(f"input {sources}")
        stream_generator = generate_metadata_response(query, sources, conversation_history, stream=True)
        
        # Create a generator that yields server-sent events and captures response for audit
        def generate_sse():
            collected_response = []
            
            try:
                # Set the appropriate headers for SSE
                yield "Content-Type: text/event-stream\n"
                yield "Cache-Control: no-cache\n"
                yield "Connection: keep-alive\n\n"
                
                # First event with sources information
                sources_json = json.dumps(sources)
                yield f"event: sources\ndata: {sources_json}\n\n"
                
                # Stream the actual answer chunks and collect them
                for chunk in stream_generator:
                    if chunk:
                        collected_response.append(chunk)
                        chunk_json = json.dumps({"text": chunk})
                        yield f"data: {chunk_json}\n\n"
                
                # Signal completion
                yield "event: done\ndata: {}\n\n"
                
            finally:
                # Log the complete response for audit after streaming is done
                full_response = ''.join(collected_response)
                try:
                    user_manager.log_audit_event(
                        user_id=session.get('user_id'),
                        action='metadata_search_stream',
                        details=f"Metadata search streaming query completed. Sources: {len(sources)}, Response length: {len(full_response)} chars",
                        ip_address=request.remote_addr,
                        query_text=query,
                        response=full_response[:1000] if full_response else None  # Limit response to 1000 chars for audit
                    )
                except Exception as audit_error:
                    logger.error(f"Error logging audit event for streaming metadata search: {str(audit_error)}")
        
        # Return a streaming response
        response = Response(stream_with_context(generate_sse()), 
                        content_type='text/event-stream')
        response.headers['X-Accel-Buffering'] = 'no'  # Disable buffering in Nginx
        response.headers['Cache-Control'] = 'no-cache'
        response.headers['Connection'] = 'keep-alive'
        return response
        
    except Exception as e:
        import traceback
        error_traceback = traceback.format_exc()
        logger.error(f"Error in streaming metadata search: {str(e)}")
        logger.error(f"Full traceback:\n{error_traceback}")
        
        # For debugging, also print to console
        print(f"METADATA SEARCH ERROR: {str(e)}")
        print(f"FULL TRACEBACK:\n{error_traceback}")
        
        return jsonify({
            'success': False,
            'error': f"Metadata search error: {str(e)}"
        }), 500

def audit_metadata_search(query, user_id, success, message=''):
    """Audit metadata search operations"""
    try:
        # Log the metadata search operation
        logger.info(f"Metadata search audit - User: {user_id}, Query: {query}, Success: {success}, Message: {message}")
        
        # Store audit logs using UserManager
        user_manager.log_audit_event(
            user_id=user_id,
            action='metadata_search_audit',
            details=f"Metadata search - Success: {success}, Message: {message}",
            query_text=query,
            response=message if success else None
        )
        
    except Exception as e:
        logger.error(f"Error auditing metadata search: {str(e)}", exc_info=True)
