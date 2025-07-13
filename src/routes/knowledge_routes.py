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
from src.utils.user_manager import UserManager

# Blueprint for knowledge base routes
knowledge_bp = Blueprint('knowledge', __name__)

# Initialize knowledge manager with lazy loading
knowledge_manager = None
# Initialize user manager for audit logging
user_manager = UserManager()

def get_knowledge_manager():
    """Get knowledge manager instance with lazy initialization"""
    global knowledge_manager
    if knowledge_manager is None:
        knowledge_manager = KnowledgeManager()
    return knowledge_manager

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
    documents = get_knowledge_manager().list_documents()
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
        
        # Get tags from the form data (comma-separated string)
        tags = []
        if 'tags' in request.form:
            tags_string = request.form.get('tags', '')
            if tags_string:
                tags = [tag.strip() for tag in tags_string.split(',') if tag.strip()]
        
        # Process the document asynchronously
        document_id = get_knowledge_manager().process_document(file_path, original_filename, tags)
        
        # Audit log the document upload
        user_manager.log_audit_event(
            user_id=session.get('user_id'),
            action='upload_document',
            details={
                'document_id': document_id,
                'filename': original_filename,
                'tags': tags
            }
        )
        
        return jsonify({
            'success': True, 
            'message': 'Document uploaded and processing started',
            'documentId': document_id,
            'originalFilename': original_filename,
            'tags': tags
        })
    
    return jsonify({'success': False, 'error': 'Failed to upload document'}), 400

# Route to handle direct text input
@knowledge_bp.route('/api/knowledge/text', methods=['POST'])
@login_required
@admin_required
def add_text_content():
    """Handle direct text input and processing"""
    data = request.get_json()
    
    if not data:
        return jsonify({'success': False, 'error': 'No data provided'}), 400
        
    # Extract required fields
    name = data.get('name')
    content_type = data.get('content_type')
    content = data.get('content')
    tags = data.get('tags', [])
    
    # Validate required fields
    if not name or not content_type or not content:
        return jsonify({'success': False, 'error': 'Missing required fields'}), 400
    
    try:
        # Process the text content
        document_id = get_knowledge_manager().process_text_content(name, content_type, content, tags)
        
        # Audit log the text content addition
        user_manager.log_audit_event(
            user_id=session.get('user_id'),
            action='add_text_content',
            details={
                'document_id': document_id,
                'name': name,
                'tags': tags
            }
        )
        
        return jsonify({
            'success': True, 
            'message': 'Text content submitted for processing',
            'documentId': document_id,
            'name': name,
            'tags': tags
        })
    except Exception as e:
        current_app.logger.error(f"Error processing text content: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': f'Failed to process text content: {str(e)}'}), 500

# Route to check document processing status
@knowledge_bp.route('/api/knowledge/status/<document_id>', methods=['GET'])
@login_required
@admin_required
def document_status(document_id):
    """Get the processing status of a document"""
    status = get_knowledge_manager().get_document_status(document_id)
    return jsonify(status)

# Route to delete a document
@knowledge_bp.route('/api/knowledge/delete/<document_id>', methods=['DELETE'])
@login_required
@admin_required
def delete_document(document_id):
    """Delete a document and its chunks from the system"""
    success = get_knowledge_manager().delete_document(document_id)
    if success:
        # Audit log the document deletion
        user_manager.log_audit_event(
            user_id=session.get('user_id'),
            action='delete_document',
            details={
                'document_id': document_id
            }
        )
        return jsonify  ({'success': True, 'message': 'Document deleted successfully'})
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
    # Get tags for filtering if provided
    tags = data.get('tags', [])
    # Get conversation history for follow-up questions
    conversation_history = data.get('conversation_history', [])
    
    # Get the answer using the knowledge manager
    result = get_knowledge_manager().get_answer(query, user_id, stream=False, tags=tags, conversation_history=conversation_history)
    
    # Audit log the knowledge base query
    user_manager.log_audit_event(
        user_id=user_id,
        action='knowledge_query',
        details=f"Knowledge base query",
        ip_address=request.remote_addr,
        query_text=query,
        response=str(result.get('answer', ''))[:500] if isinstance(result, dict) else str(result)[:500]
    )
    
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
        tags = data.get('tags', [])
        conversation_history = data.get('conversation_history', [])
        
        # Store the query, tags, and conversation history in session for the subsequent GET request
        session['current_knowledge_query'] = query
        session['current_knowledge_tags'] = tags
        session['current_knowledge_conversation_history'] = conversation_history
        return jsonify({"success": True, "message": "Query received"})
    
    # Handle GET request (SSE streaming)
    elif request.method == 'GET':
        query = request.args.get('query') or session.get('current_knowledge_query')
        tags = session.get('current_knowledge_tags', [])
        conversation_history = session.get('current_knowledge_conversation_history', [])
        
        if not query:
            return jsonify({"error": "No query found"}), 400
    
    try:
        # Get the streaming answer using the knowledge manager
        result = get_knowledge_manager().get_answer(query, user_id, stream=True, tags=tags, conversation_history=conversation_history)
        
        # Check if result is a tuple with two values (stream_generator, sources)
        if isinstance(result, tuple) and len(result) == 2:
            stream_generator, sources = result
        else:
            import traceback
            error_msg = f"Invalid response from knowledge manager. Result type: {type(result)}, value: {str(result)}"
            current_app.logger.error(error_msg)
            current_app.logger.error(f"Full traceback:\n{traceback.format_exc()}")
            print(f"KNOWLEDGE ROUTE ERROR: {error_msg}")
            # If it's not a tuple with two values, handle the error case
            return jsonify({"error": "Invalid response from knowledge manager"}), 500
        
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
                        user_id=user_id,
                        action='knowledge_query_stream',
                        details=f"Knowledge base streaming query completed. Sources: {len(sources)}, Response length: {len(full_response)} chars",
                        ip_address=request.remote_addr,
                        query_text=query,
                        response=full_response[:1000] if full_response else None  # Limit response to 1000 chars for audit
                    )
                except Exception as audit_error:
                    current_app.logger.error(f"Error logging audit event for streaming query: {str(audit_error)}")
        
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
        current_app.logger.error(f"Error in streaming knowledge query: {str(e)}")
        current_app.logger.error(f"Full traceback:\n{error_traceback}")
        
        # For debugging, also print to console
        print(f"KNOWLEDGE QUERY ERROR: {str(e)}")
        print(f"FULL TRACEBACK:\n{error_traceback}")
        
        return jsonify({
            "success": False,
            "error": f"An error occurred while processing your question: {str(e)}"
        }), 500

# Route to get all available tags
@knowledge_bp.route('/api/knowledge/tags', methods=['GET'])
@login_required
@permission_required(Permissions.VIEW_KNOWLEDGE)
def get_all_tags():
    """Get a list of all available tags in the knowledge base"""
    tags = get_knowledge_manager().get_all_tags()
    return jsonify({'success': True, 'tags': tags})

# Route to add a tag to a document
@knowledge_bp.route('/api/knowledge/tag/add', methods=['POST'])
@login_required
@admin_required
def add_document_tag():
    """Add a tag to a document"""
    data = request.get_json()
    
    if not data or 'document_id' not in data or 'tag' not in data:
        return jsonify({'success': False, 'error': 'Missing document_id or tag'}), 400
        
    document_id = data.get('document_id')
    tag = data.get('tag')
    
    success = get_knowledge_manager().add_document_tag(document_id, tag)
    
    if success:
        return jsonify({'success': True, 'message': 'Tag added successfully'})
    else:
        return jsonify({'success': False, 'error': 'Failed to add tag'}), 500

# Route to remove a tag from a document
@knowledge_bp.route('/api/knowledge/tag/remove', methods=['POST'])
@login_required
@admin_required
def remove_document_tag():
    """Remove a tag from a document"""
    data = request.get_json()
    
    if not data or 'document_id' not in data or 'tag' not in data:
        return jsonify({'success': False, 'error': 'Missing document_id or tag'}), 400
        
    document_id = data.get('document_id')
    tag = data.get('tag')
    
    success = get_knowledge_manager().remove_document_tag(document_id, tag)
    
    if success:
        return jsonify({'success': True, 'message': 'Tag removed successfully'})
    else:
        return jsonify({'success': False, 'error': 'Failed to remove tag'}), 500

# Route to view original uploaded document
@knowledge_bp.route('/api/knowledge/view/original/<document_id>')
@login_required
@admin_required
def view_original_document(document_id):
    """View the original uploaded document"""
    try:
        document_info = get_knowledge_manager().get_document_info(document_id)
        if not document_info:
            return jsonify({'success': False, 'error': 'Document not found'}), 404
        
        file_path = document_info['file_path']
        original_filename = document_info['original_filename']
        content_type = document_info['content_type']
        
        # Check if file exists
        if not os.path.exists(file_path):
            return jsonify({'success': False, 'error': 'File not found on disk'}), 404
        
        # Determine the MIME type for the response
        mime_type = 'application/octet-stream'  # Default
        if content_type:
            content_type_lower = content_type.lower()
            if content_type_lower == 'pdf':
                mime_type = 'application/pdf'
            elif content_type_lower in ['doc', 'docx']:
                mime_type = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
            elif content_type_lower in ['xls', 'xlsx']:
                mime_type = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            elif content_type_lower in ['ppt', 'pptx']:
                mime_type = 'application/vnd.openxmlformats-officedocument.presentationml.presentation'
            elif content_type_lower == 'txt':
                mime_type = 'text/plain'
        
        return send_from_directory(
            os.path.dirname(file_path),
            os.path.basename(file_path),
            as_attachment=False,
            download_name=original_filename,
            mimetype=mime_type
        )
    except Exception as e:
        current_app.logger.error(f"Error viewing original document {document_id}: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': 'Failed to load document'}), 500

# Route to view markdown output of document
@knowledge_bp.route('/api/knowledge/view/markdown/<document_id>')
@login_required
@admin_required
def view_markdown_document(document_id):
    """View the markdown output of the processed document"""
    try:
        markdown_content = get_knowledge_manager().get_document_markdown(document_id)
        if not markdown_content:
            return jsonify({'success': False, 'error': 'Document not found or not processed'}), 404
        
        document_info = get_knowledge_manager().get_document_info(document_id)
        original_filename = document_info['original_filename'] if document_info else 'Unknown'
        
        return jsonify({
            'success': True,
            'markdown_content': markdown_content,
            'original_filename': original_filename
        })
    except Exception as e:
        current_app.logger.error(f"Error viewing markdown document {document_id}: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': 'Failed to load markdown content'}), 500

# Route to get document information
@knowledge_bp.route('/api/knowledge/info/<document_id>')
@login_required
@admin_required
def get_document_info(document_id):
    """Get detailed information about a document"""
    try:
        document_info = get_knowledge_manager().get_document_info(document_id)
        if not document_info:
            return jsonify({'success': False, 'error': 'Document not found'}), 404
        
        return jsonify({
            'success': True,
            'document': document_info
        })
    except Exception as e:
        current_app.logger.error(f"Error getting document info {document_id}: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': 'Failed to get document information'}), 500
