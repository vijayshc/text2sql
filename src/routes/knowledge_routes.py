"""
Routes for the knowledge base feature.
Handles document upload, conversion, chunking, embedding, and retrieval.
"""

from flask import Blueprint, render_template, request, jsonify, session, current_app, flash, redirect, url_for, send_from_directory
import os
import uuid
import json
from datetime import datetime
from werkzeug.utils import secure_filename
from src.utils.knowledge_manager import KnowledgeManager
from src.routes.auth_routes import admin_required, permission_required
from src.utils.auth_utils import login_required
from src.models.user import Permissions

# Blueprint for knowledge base routes
knowledge_bp = Blueprint('knowledge', __name__)

# Initialize knowledge manager
knowledge_manager = None

@knowledge_bp.before_app_first_request
def setup_knowledge_manager():
    global knowledge_manager
    knowledge_manager = KnowledgeManager()

# Knowledge base homepage route
@knowledge_bp.route('/knowledge')
@login_required
@permission_required(Permissions.VIEW_KNOWLEDGE)
def knowledge_index():
    """Render the knowledge base interface"""
    return render_template('knowledgebase.html')

# Admin route for document management
@knowledge_bp.route('/admin/knowledge')
@login_required
@admin_required
def admin_knowledge():
    """Render the admin interface for knowledge base management"""
    # Get list of documents from knowledge manager
    documents = knowledge_manager.list_documents()
    return render_template('admin/knowledge.html', documents=documents)

# Route to handle document upload
@knowledge_bp.route('/api/knowledge/upload', methods=['POST'])
@login_required
@admin_required
def upload_document():
    """Handle document upload and processing"""
    if 'document' not in request.files:
        return jsonify({'success': False, 'error': 'No document part'}), 400
        
    file = request.files['document']
    if file.filename == '':
        return jsonify({'success': False, 'error': 'No selected document'}), 400
        
    if file:
        # Generate a unique filename
        original_filename = secure_filename(file.filename)
        filename = f"{uuid.uuid4()}_{original_filename}"
        
        # Save the file
        file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        
        # Process the document asynchronously
        document_id = knowledge_manager.process_document(file_path, original_filename)
        
        return jsonify({
            'success': True, 
            'message': 'Document uploaded and processing started',
            'documentId': document_id,
            'originalFilename': original_filename
        })
    
    return jsonify({'success': False, 'error': 'Failed to upload document'}), 400

# Route to check document processing status
@knowledge_bp.route('/api/knowledge/status/<document_id>', methods=['GET'])
@login_required
@admin_required
def document_status(document_id):
    """Get the processing status of a document"""
    status = knowledge_manager.get_document_status(document_id)
    return jsonify(status)

# Route to delete a document
@knowledge_bp.route('/api/knowledge/delete/<document_id>', methods=['DELETE'])
@login_required
@admin_required
def delete_document(document_id):
    """Delete a document and its chunks from the system"""
    success = knowledge_manager.delete_document(document_id)
    if success:
        return jsonify({'success': True, 'message': 'Document deleted successfully'})
    else:
        return jsonify({'success': False, 'error': 'Failed to delete document'}), 500

# Route for knowledge retrieval and QA
@knowledge_bp.route('/api/knowledge/query', methods=['POST'])
@login_required
@permission_required(Permissions.USE_KNOWLEDGE)
def query_knowledge():
    """Process a knowledge query and return results"""
    data = request.get_json()
    
    if not data or 'query' not in data:
        return jsonify({"error": "No query provided"}), 400
        
    query = data.get('query')
    user_id = session.get('user_id')
    
    # Get the answer using the knowledge manager
    result = knowledge_manager.get_answer(query, user_id)
    
    return jsonify(result)

# Route for streaming knowledge retrieval and QA
@knowledge_bp.route('/api/knowledge/query/stream', methods=['POST', 'GET'])
@login_required
@permission_required(Permissions.USE_KNOWLEDGE)
def query_knowledge_stream():
    """Process a knowledge query and stream the results"""
    from flask import Response, stream_with_context
    
    user_id = session.get('user_id')
    
    # Handle POST request (initial query setup)
    if request.method == 'POST':
        data = request.get_json()
        
        if not data or 'query' not in data:
            return jsonify({"error": "No query provided"}), 400
            
        query = data.get('query')
        
        # Store the query in session for the subsequent GET request
        session['current_knowledge_query'] = query
        return jsonify({"success": True, "message": "Query received"})
    
    # Handle GET request (SSE streaming)
    elif request.method == 'GET':
        query = request.args.get('query') or session.get('current_knowledge_query')
        
        if not query:
            return jsonify({"error": "No query found"}), 400
    
    try:
        # Get the streaming answer using the knowledge manager
        stream_generator, sources = knowledge_manager.get_answer(query, user_id, stream=True)
        
        # Create a generator that yields server-sent events
        def generate_sse():
            # Set the appropriate headers for SSE
            yield "Content-Type: text/event-stream\n"
            yield "Cache-Control: no-cache\n"
            yield "Connection: keep-alive\n\n"
            
            # First event with sources information
            sources_json = json.dumps(sources)
            yield f"event: sources\ndata: {sources_json}\n\n"
            
            # Stream the actual answer chunks
            for chunk in stream_generator:
                if chunk:
                    chunk_json = json.dumps({"text": chunk})
                    yield f"data: {chunk_json}\n\n"
            
            # Signal completion
            yield "event: done\ndata: {}\n\n"
        
        # Return a streaming response
        response = Response(stream_with_context(generate_sse()), 
                        content_type='text/event-stream')
        response.headers['X-Accel-Buffering'] = 'no'  # Disable buffering in Nginx
        response.headers['Cache-Control'] = 'no-cache'
        response.headers['Connection'] = 'keep-alive'
        return response
    
    except Exception as e:
        current_app.logger.error(f"Error in streaming knowledge query: {str(e)}", exc_info=True)
        return jsonify({
            "success": False,
            "error": "An error occurred while processing your question."
        }), 500
