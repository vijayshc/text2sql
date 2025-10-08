"""
Project Mapping Routes
API endpoints for managing mapping projects and documents
"""
from flask import Blueprint, request, jsonify, send_file, render_template
from werkzeug.utils import secure_filename
import logging
import os
import uuid
from datetime import datetime

from src.utils.auth_utils import login_required
from src.models.mapping_project import MappingProject
from src.models.mapping_document import MappingDocument

logger = logging.getLogger('text2sql')

project_mapping_bp = Blueprint('project_mapping', __name__)

# Allowed file extensions for mapping documents
ALLOWED_EXTENSIONS = {'xlsx', 'xls'}

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_project_upload_dir(project_name):
    """Get the upload directory for a project"""
    base_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'uploads', 'projects', project_name)
    os.makedirs(base_dir, exist_ok=True)
    return base_dir

@project_mapping_bp.route('/admin/mapping-projects')
@project_mapping_bp.route('/admin/mapping-projects/')
@login_required
def mapping_projects_page():
    """Render the mapping projects management page"""
    logger.debug("Mapping projects page requested")
    return render_template('admin/mapping_projects.html')

# ==================== Project Management Routes ====================

@project_mapping_bp.route('/api/mapping-projects', methods=['GET'])
@login_required
def list_projects():
    """Get all mapping projects"""
    try:
        MappingProject.create_table()
        projects = MappingProject.get_all()
        return jsonify({
            'success': True,
            'projects': [p.to_dict() for p in projects]
        })
    except Exception as e:
        logger.error(f"Error listing projects: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@project_mapping_bp.route('/api/mapping-projects', methods=['POST'])
@login_required
def create_project():
    """Create a new mapping project"""
    try:
        data = request.get_json() or {}
        name = data.get('name', '').strip()
        description = data.get('description', '').strip()
        
        if not name:
            return jsonify({'success': False, 'error': 'Project name is required'}), 400
        
        # Check if project with this name already exists
        existing = MappingProject.get_by_name(name)
        if existing:
            return jsonify({'success': False, 'error': 'Project with this name already exists'}), 400
        
        # Create the project
        project = MappingProject(name=name, description=description)
        project.save()
        
        # Create the project's upload directory
        get_project_upload_dir(name)
        
        logger.info(f"Created mapping project: {name}")
        return jsonify({
            'success': True,
            'project': project.to_dict()
        })
    except Exception as e:
        logger.error(f"Error creating project: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@project_mapping_bp.route('/api/mapping-projects/<int:project_id>', methods=['GET'])
@login_required
def get_project(project_id):
    """Get a specific project"""
    try:
        project = MappingProject.get_by_id(project_id)
        if not project:
            return jsonify({'success': False, 'error': 'Project not found'}), 404
        
        return jsonify({
            'success': True,
            'project': project.to_dict()
        })
    except Exception as e:
        logger.error(f"Error getting project: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@project_mapping_bp.route('/api/mapping-projects/<int:project_id>', methods=['PUT'])
@login_required
def update_project(project_id):
    """Update a project"""
    try:
        project = MappingProject.get_by_id(project_id)
        if not project:
            return jsonify({'success': False, 'error': 'Project not found'}), 404
        
        data = request.get_json() or {}
        old_name = project.name
        new_name = data.get('name', '').strip()
        description = data.get('description', '').strip()
        
        if not new_name:
            return jsonify({'success': False, 'error': 'Project name is required'}), 400
        
        # If name is changing, check if new name already exists
        if new_name != old_name:
            existing = MappingProject.get_by_name(new_name)
            if existing:
                return jsonify({'success': False, 'error': 'Project with this name already exists'}), 400
            
            # Rename the project directory
            old_dir = get_project_upload_dir(old_name)
            new_dir = get_project_upload_dir(new_name)
            if os.path.exists(old_dir) and old_dir != new_dir:
                os.rename(old_dir, new_dir)
                
                # Update file paths for all documents
                documents = MappingDocument.get_by_project(project_id)
                for doc in documents:
                    old_path = doc.file_path
                    new_path = old_path.replace(old_dir, new_dir)
                    doc.file_path = new_path
                    doc.save()
        
        project.name = new_name
        project.description = description
        project.save()
        
        logger.info(f"Updated project: {project_id}")
        return jsonify({
            'success': True,
            'project': project.to_dict()
        })
    except Exception as e:
        logger.error(f"Error updating project: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@project_mapping_bp.route('/api/mapping-projects/<int:project_id>', methods=['DELETE'])
@login_required
def delete_project(project_id):
    """Delete a project and all its documents"""
    try:
        project = MappingProject.get_by_id(project_id)
        if not project:
            return jsonify({'success': False, 'error': 'Project not found'}), 404
        
        project_name = project.name
        project.delete()
        
        # Remove the project directory
        project_dir = get_project_upload_dir(project_name)
        if os.path.exists(project_dir):
            import shutil
            shutil.rmtree(project_dir)
        
        logger.info(f"Deleted project: {project_name}")
        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"Error deleting project: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# ==================== Mapping Document Management Routes ====================

@project_mapping_bp.route('/api/mapping-projects/<int:project_id>/documents', methods=['GET'])
@login_required
def list_documents(project_id):
    """Get all mapping documents for a project"""
    try:
        project = MappingProject.get_by_id(project_id)
        if not project:
            return jsonify({'success': False, 'error': 'Project not found'}), 404
        
        MappingDocument.create_table()
        documents = MappingDocument.get_by_project(project_id)
        
        return jsonify({
            'success': True,
            'documents': [d.to_dict() for d in documents]
        })
    except Exception as e:
        logger.error(f"Error listing documents: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@project_mapping_bp.route('/api/mapping-projects/<int:project_id>/documents/upload', methods=['POST'])
@login_required
def upload_document(project_id):
    """Upload a mapping document to a project"""
    try:
        project = MappingProject.get_by_id(project_id)
        if not project:
            return jsonify({'success': False, 'error': 'Project not found'}), 404
        
        if 'file' not in request.files:
            return jsonify({'success': False, 'error': 'No file provided'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'success': False, 'error': 'No file selected'}), 400
        
        if not allowed_file(file.filename):
            return jsonify({'success': False, 'error': 'Invalid file type. Only .xlsx and .xls files are allowed'}), 400
        
        # Use secure filename
        filename = secure_filename(file.filename)
        
        # Generate unique filename if file already exists
        base_name, ext = os.path.splitext(filename)
        upload_dir = get_project_upload_dir(project.name)
        file_path = os.path.join(upload_dir, filename)
        counter = 1
        while os.path.exists(file_path):
            filename = f"{base_name}_{counter}{ext}"
            file_path = os.path.join(upload_dir, filename)
            counter += 1
        
        # Save the file
        file.save(file_path)
        
        # Get current user from session
        from flask import session
        user_id = session.get('user_id')
        
        # Create document record
        document = MappingDocument(
            project_id=project_id,
            filename=filename,
            file_path=file_path,
            uploaded_by=user_id
        )
        document.save()
        
        logger.info(f"Uploaded document {filename} to project {project.name}")
        return jsonify({
            'success': True,
            'document': document.to_dict()
        })
    except Exception as e:
        logger.error(f"Error uploading document: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@project_mapping_bp.route('/api/mapping-projects/<int:project_id>/documents/<int:doc_id>', methods=['GET'])
@login_required
def get_document(project_id, doc_id):
    """Get a specific document"""
    try:
        document = MappingDocument.get_by_id(doc_id)
        if not document or document.project_id != project_id:
            return jsonify({'success': False, 'error': 'Document not found'}), 404
        
        return jsonify({
            'success': True,
            'document': document.to_dict()
        })
    except Exception as e:
        logger.error(f"Error getting document: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@project_mapping_bp.route('/api/mapping-projects/<int:project_id>/documents/<int:doc_id>/download', methods=['GET'])
@login_required
def download_document(project_id, doc_id):
    """Download a mapping document"""
    try:
        document = MappingDocument.get_by_id(doc_id)
        if not document or document.project_id != project_id:
            return jsonify({'success': False, 'error': 'Document not found'}), 404
        
        if not os.path.exists(document.file_path):
            return jsonify({'success': False, 'error': 'File not found on disk'}), 404
        
        return send_file(
            document.file_path,
            as_attachment=True,
            download_name=document.filename
        )
    except Exception as e:
        logger.error(f"Error downloading document: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@project_mapping_bp.route('/api/mapping-projects/<int:project_id>/documents/<int:doc_id>', methods=['DELETE'])
@login_required
def delete_document(project_id, doc_id):
    """Delete a mapping document"""
    try:
        document = MappingDocument.get_by_id(doc_id)
        if not document or document.project_id != project_id:
            return jsonify({'success': False, 'error': 'Document not found'}), 404
        
        filename = document.filename
        document.delete()
        
        logger.info(f"Deleted document: {filename}")
        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"Error deleting document: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
