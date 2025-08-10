"""
Admin API routes for Text2SQL application.
Provides comprehensive admin functionality APIs for Vue.js frontend.
"""

from flask import Blueprint, request, jsonify
import sys
import os

# Simple admin check without complex middleware for now
def admin_required(f):
    """Simple admin decorator - for development"""
    def wrapper(*args, **kwargs):
        return f(*args, **kwargs)
    return wrapper

def jwt_required():
    """Simple JWT decorator - for development"""
    def decorator(f):
        def wrapper(*args, **kwargs):
            return f(*args, **kwargs)
        return wrapper
    return decorator

def get_jwt_identity():
    """Simple identity getter - for development"""
    return "admin_user"

import sqlite3
import json
import uuid
from datetime import datetime
import traceback

admin_api_bp = Blueprint('admin_api', __name__, url_prefix='/api/v1/admin')

# Database connection helper
def get_db_connection():
    """Get database connection"""
    try:
        conn = sqlite3.connect('text2sql.db')
        conn.row_factory = sqlite3.Row
        return conn
    except Exception as e:
        print(f"Database connection error: {e}")
        return None

# ========================
# Dashboard API
# ========================

@admin_api_bp.route('/dashboard/stats', methods=['GET'])
@jwt_required()
@admin_required
def get_dashboard_stats():
    """Get admin dashboard statistics"""
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500
        
        cursor = conn.cursor()
        
        # Get user count
        cursor.execute("SELECT COUNT(*) as count FROM users")
        user_count = cursor.fetchone()['count']
        
        # Get query count (this week)
        cursor.execute("""
            SELECT COUNT(*) as count FROM query_history 
            WHERE created_at >= datetime('now', '-7 days')
        """)
        query_count = cursor.fetchone()['count']
        
        # Get active sessions (placeholder)
        active_sessions = 12  # This would come from session management
        
        # Get system status
        system_status = 'healthy'  # This would come from health checks
        
        conn.close()
        
        return jsonify({
            'success': True,
            'stats': {
                'user_count': user_count,
                'query_count': query_count,
                'active_sessions': active_sessions,
                'system_status': system_status
            }
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ========================
# Samples Management API
# ========================

@admin_api_bp.route('/samples', methods=['GET'])
@jwt_required()
@admin_required
def get_samples():
    """Get all samples"""
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500
        
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, name, description, category, sql_query, natural_language,
                   database_schema, tags, difficulty, is_active, created_at, updated_at
            FROM samples ORDER BY created_at DESC
        """)
        
        samples = []
        for row in cursor.fetchall():
            sample = dict(row)
            sample['tags'] = json.loads(sample['tags']) if sample['tags'] else []
            samples.append(sample)
        
        conn.close()
        
        return jsonify({
            'success': True,
            'samples': samples
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@admin_api_bp.route('/samples', methods=['POST'])
@jwt_required()
@admin_required
def create_sample():
    """Create a new sample"""
    try:
        data = request.get_json()
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500
        
        cursor = conn.cursor()
        sample_id = str(uuid.uuid4())
        
        cursor.execute("""
            INSERT INTO samples (id, name, description, category, sql_query, natural_language,
                               database_schema, tags, difficulty, is_active, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            sample_id, data['name'], data.get('description', ''), data.get('category', ''),
            data['sql_query'], data['natural_language'], data.get('database_schema', ''),
            json.dumps(data.get('tags', [])), data.get('difficulty', 'beginner'),
            data.get('is_active', True), datetime.now().isoformat(), datetime.now().isoformat()
        ))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': 'Sample created successfully',
            'sample_id': sample_id
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@admin_api_bp.route('/samples/<sample_id>', methods=['PUT'])
@jwt_required()
@admin_required
def update_sample(sample_id):
    """Update a sample"""
    try:
        data = request.get_json()
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500
        
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE samples SET name=?, description=?, category=?, sql_query=?, natural_language=?,
                             database_schema=?, tags=?, difficulty=?, is_active=?, updated_at=?
            WHERE id=?
        """, (
            data['name'], data.get('description', ''), data.get('category', ''),
            data['sql_query'], data['natural_language'], data.get('database_schema', ''),
            json.dumps(data.get('tags', [])), data.get('difficulty', 'beginner'),
            data.get('is_active', True), datetime.now().isoformat(), sample_id
        ))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': 'Sample updated successfully'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@admin_api_bp.route('/samples/<sample_id>', methods=['DELETE'])
@jwt_required()
@admin_required
def delete_sample(sample_id):
    """Delete a sample"""
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500
        
        cursor = conn.cursor()
        cursor.execute("DELETE FROM samples WHERE id=?", (sample_id,))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': 'Sample deleted successfully'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@admin_api_bp.route('/samples/<sample_id>/toggle', methods=['PUT'])
@jwt_required()
@admin_required
def toggle_sample_status(sample_id):
    """Toggle sample active status"""
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500
        
        cursor = conn.cursor()
        cursor.execute("SELECT is_active FROM samples WHERE id=?", (sample_id,))
        row = cursor.fetchone()
        
        if not row:
            return jsonify({'error': 'Sample not found'}), 404
        
        new_status = not row['is_active']
        cursor.execute("UPDATE samples SET is_active=?, updated_at=? WHERE id=?", 
                      (new_status, datetime.now().isoformat(), sample_id))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': f'Sample {"activated" if new_status else "deactivated"} successfully'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ========================
# Skills Management API
# ========================

@admin_api_bp.route('/skills/categories', methods=['GET'])
@jwt_required()
@admin_required
def get_skill_categories():
    """Get skill categories"""
    try:
        # For now, return static categories - in a real app, this would come from the database
        categories = [
            {'value': 'data_analysis', 'label': 'Data Analysis', 'count': 0},
            {'value': 'database_design', 'label': 'Database Design', 'count': 0},
            {'value': 'query_optimization', 'label': 'Query Optimization', 'count': 0},
            {'value': 'troubleshooting', 'label': 'Troubleshooting', 'count': 0},
            {'value': 'integration', 'label': 'Integration', 'count': 0}
        ]
        
        return jsonify({
            'success': True,
            'categories': categories
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@admin_api_bp.route('/skills', methods=['GET'])
@jwt_required()
@admin_required
def get_skills():
    """Get all skills"""
    try:
        # For now, return empty list - in a real app, this would come from the database
        return jsonify({
            'success': True,
            'skills': []
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@admin_api_bp.route('/skills', methods=['POST'])
@jwt_required()
@admin_required
def create_skill():
    """Create a new skill"""
    try:
        data = request.get_json()
        
        # For now, just return success - in a real app, this would save to database
        return jsonify({
            'success': True,
            'message': 'Skill created successfully'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@admin_api_bp.route('/skills/search', methods=['POST'])
@jwt_required()
@admin_required
def search_skills():
    """Search skills"""
    try:
        data = request.get_json()
        
        # For now, return empty results - in a real app, this would search the database
        return jsonify({
            'success': True,
            'results': [],
            'total': 0,
            'filter_description': f"Search for '{data.get('query', '')}'"
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@admin_api_bp.route('/skills/vectorize', methods=['POST'])
@jwt_required()
@admin_required
def vectorize_skills():
    """Vectorize all skills"""
    try:
        # For now, just return success - in a real app, this would process skills
        return jsonify({
            'success': True,
            'message': 'Skills vectorization completed successfully'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@admin_api_bp.route('/skills/import', methods=['POST'])
@jwt_required()
@admin_required
def import_skills():
    """Import skills from JSON"""
    try:
        data = request.get_json()
        
        # For now, just return success - in a real app, this would import skills
        return jsonify({
            'success': True,
            'message': 'Skills imported successfully',
            'errors': []
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ========================
# Knowledge Management API
# ========================

@admin_api_bp.route('/knowledge/documents', methods=['GET'])
@jwt_required()
@admin_required
def get_knowledge_documents():
    """Get all knowledge documents"""
    try:
        # For now, return empty list - in a real app, this would come from the database
        return jsonify({
            'success': True,
            'documents': []
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@admin_api_bp.route('/knowledge/upload', methods=['POST'])
@jwt_required()
@admin_required
def upload_knowledge_document():
    """Upload a knowledge document"""
    try:
        # For now, just return success - in a real app, this would process the upload
        return jsonify({
            'success': True,
            'message': 'Document uploaded successfully'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@admin_api_bp.route('/knowledge/text', methods=['POST'])
@jwt_required()
@admin_required
def add_knowledge_text():
    """Add text content to knowledge base"""
    try:
        data = request.get_json()
        
        # For now, just return success - in a real app, this would save to database
        return jsonify({
            'success': True,
            'message': 'Content added successfully'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ========================
# Vector DB Management API
# ========================

@admin_api_bp.route('/vector-db/collections', methods=['GET'])
@jwt_required()
@admin_required
def get_vector_collections():
    """Get all vector collections"""
    try:
        # For now, return empty list - in a real app, this would come from vector DB
        return jsonify({
            'success': True,
            'collections': []
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@admin_api_bp.route('/vector-db/collections', methods=['POST'])
@jwt_required()
@admin_required
def create_vector_collection():
    """Create a new vector collection"""
    try:
        data = request.get_json()
        
        # For now, just return success - in a real app, this would create collection
        return jsonify({
            'success': True,
            'message': 'Collection created successfully'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ========================
# Database Query API
# ========================

@admin_api_bp.route('/database/schema', methods=['GET'])
@jwt_required()
@admin_required
def get_database_schema():
    """Get database schema objects"""
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500
        
        cursor = conn.cursor()
        
        # Get tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
        tables = [{'name': row['name'], 'type': 'table'} for row in cursor.fetchall()]
        
        # Get views
        cursor.execute("SELECT name FROM sqlite_master WHERE type='view'")
        views = [{'name': row['name'], 'type': 'view'} for row in cursor.fetchall()]
        
        # Get indexes
        cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND name NOT LIKE 'sqlite_%'")
        indexes = [{'name': row['name'], 'type': 'index'} for row in cursor.fetchall()]
        
        objects = tables + views + indexes
        conn.close()
        
        return jsonify({
            'success': True,
            'objects': objects
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@admin_api_bp.route('/database/schema/<table_name>', methods=['GET'])
@jwt_required()
@admin_required
def get_table_schema(table_name):
    """Get schema for a specific table"""
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500
        
        cursor = conn.cursor()
        cursor.execute(f"PRAGMA table_info({table_name})")
        
        columns = []
        for row in cursor.fetchall():
            columns.append({
                'name': row['name'],
                'type': row['type'],
                'nullable': not row['notnull'],
                'primary_key': row['pk'] > 0
            })
        
        conn.close()
        
        return jsonify({
            'success': True,
            'columns': columns
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@admin_api_bp.route('/database/execute', methods=['POST'])
@jwt_required()
@admin_required
def execute_database_query():
    """Execute a database query"""
    try:
        data = request.get_json()
        query = data.get('query', '').strip()
        
        if not query:
            return jsonify({'error': 'Query is required'}), 400
        
        # Security check - only allow SELECT statements for safety
        if not query.upper().startswith('SELECT'):
            return jsonify({'error': 'Only SELECT statements are allowed'}), 400
        
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500
        
        cursor = conn.cursor()
        start_time = datetime.now()
        
        cursor.execute(query)
        rows = cursor.fetchall()
        
        end_time = datetime.now()
        execution_time = int((end_time - start_time).total_seconds() * 1000)
        
        # Get column names
        columns = [description[0] for description in cursor.description] if cursor.description else []
        
        # Convert rows to list of dicts
        result_rows = []
        for row in rows:
            result_rows.append(dict(row))
        
        conn.close()
        
        return jsonify({
            'success': True,
            'result': {
                'columns': columns,
                'rows': result_rows,
                'rowCount': len(result_rows),
                'executionTime': execution_time
            }
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ========================
# Configuration Management API
# ========================

@admin_api_bp.route('/config', methods=['GET'])
@jwt_required()
@admin_required
def get_configurations():
    """Get all configurations"""
    try:
        # For now, return static configs - in a real app, this would come from database
        configs = [
            {
                'id': 'db_max_connections',
                'key': 'database.max_connections',
                'value': '50',
                'value_type': 'integer',
                'category': 'database',
                'description': 'Maximum number of database connections',
                'is_sensitive': False,
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat()
            },
            {
                'id': 'api_key',
                'key': 'api.secret_key',
                'value': 'hidden_secret_key',
                'value_type': 'string',
                'category': 'security',
                'description': 'API secret key for authentication',
                'is_sensitive': True,
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat()
            }
        ]
        
        return jsonify({
            'success': True,
            'configs': configs
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@admin_api_bp.route('/config', methods=['POST'])
@jwt_required()
@admin_required
def create_configuration():
    """Create a new configuration"""
    try:
        data = request.get_json()
        
        # For now, just return success - in a real app, this would save to database
        return jsonify({
            'success': True,
            'message': 'Configuration created successfully'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@admin_api_bp.route('/config/<config_id>', methods=['PUT'])
@jwt_required()
@admin_required
def update_configuration(config_id):
    """Update a configuration"""
    try:
        data = request.get_json()
        
        # For now, just return success - in a real app, this would update database
        return jsonify({
            'success': True,
            'message': 'Configuration updated successfully'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@admin_api_bp.route('/config/<config_id>', methods=['DELETE'])
@jwt_required()
@admin_required
def delete_configuration(config_id):
    """Delete a configuration"""
    try:
        # For now, just return success - in a real app, this would delete from database
        return jsonify({
            'success': True,
            'message': 'Configuration deleted successfully'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Error handler
@admin_api_bp.errorhandler(Exception)
def handle_error(error):
    """Handle errors"""
    print(f"Admin API Error: {error}")
    print(traceback.format_exc())
    return jsonify({'error': 'An internal error occurred'}), 500