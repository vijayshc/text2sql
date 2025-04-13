"""
Admin database routes for Text2SQL application.
Handles database querying and browsing functionality.
"""

from flask import Blueprint, render_template, jsonify, request
from src.utils.database import DatabaseManager, get_db_session
from src.routes.auth_routes import admin_required
from sqlalchemy import text, inspect
import sqlite3
import pandas as pd
import logging
from config.config import DATABASE_URI

admin_db_bp = Blueprint('admin_db', __name__, url_prefix='/admin/database')
logger = logging.getLogger('text2sql.admin.database')

@admin_db_bp.route('/')
@admin_required
def db_query_editor():
    """Database query editor page"""
    return render_template('admin/db_query_editor.html')

@admin_db_bp.route('/schema')
@admin_required
def get_db_schema():
    """Get database schema information"""
    try:
        # Connect to the database and get schema information
        db_manager = DatabaseManager()
        db_manager.connect()
        
        inspector = inspect(db_manager.engine)
        
        schema_info = {
            'tables': [],
            'views': []
        }
        
        # Get tables
        for table_name in inspector.get_table_names():
            table_info = {
                'name': table_name,
                'columns': []
            }
            
            # Get columns for this table
            for column in inspector.get_columns(table_name):
                table_info['columns'].append({
                    'name': column['name'],
                    'type': str(column['type']),
                    'nullable': column['nullable']
                })
                
            # Get primary keys
            primary_keys = []
            try:
                primary_keys = [pk for pk in inspector.get_pk_constraint(table_name)['constrained_columns']]
            except:
                pass
                
            table_info['primary_keys'] = primary_keys
            
            # Get foreign keys
            foreign_keys = []
            try:
                for fk in inspector.get_foreign_keys(table_name):
                    foreign_keys.append({
                        'constrained_columns': fk['constrained_columns'],
                        'referred_table': fk['referred_table'],
                        'referred_columns': fk['referred_columns']
                    })
            except:
                pass
                
            table_info['foreign_keys'] = foreign_keys
            
            schema_info['tables'].append(table_info)
            
        # For SQLite, try to get views using a direct query
        if 'sqlite' in DATABASE_URI:
            try:
                with sqlite3.connect(DATABASE_URI.replace('sqlite:///', '')) as conn:
                    cursor = conn.cursor()
                    cursor.execute("SELECT name FROM sqlite_master WHERE type='view';")
                    views = cursor.fetchall()
                    
                    for view in views:
                        view_name = view[0]
                        # Get view definition
                        cursor.execute(f"SELECT sql FROM sqlite_master WHERE name='{view_name}' AND type='view';")
                        view_def = cursor.fetchone()[0]
                        
                        view_info = {
                            'name': view_name,
                            'definition': view_def,
                            'columns': []
                        }
                        
                        # Try to get columns for this view
                        cursor.execute(f"PRAGMA table_info({view_name});")
                        columns = cursor.fetchall()
                        
                        for col in columns:
                            view_info['columns'].append({
                                'name': col[1],
                                'type': col[2],
                                'nullable': not col[3]
                            })
                        
                        schema_info['views'].append(view_info)
            except Exception as e:
                logger.error(f"Error getting view information: {str(e)}")
        
        return jsonify(schema_info)
    except Exception as e:
        logger.error(f"Error getting database schema: {str(e)}")
        return jsonify({'error': str(e)}), 500

@admin_db_bp.route('/execute', methods=['POST'])
@admin_required
def execute_query():
    """Execute SQL query and return results"""
    sql = request.json.get('sql')
    if not sql:
        return jsonify({'error': 'No SQL query provided'}), 400
    
    try:
        # Execute the query using SQLAlchemy
        db_manager = DatabaseManager()
        db_manager.connect()
        
        # Log the query
        logger.info(f"Executing SQL query: {sql}")
        
        # For SELECT queries, return the data
        sql_lower = sql.strip().lower()
        if sql_lower.startswith('select') or sql_lower.startswith('with'):
            df = pd.read_sql(text(sql), db_manager.engine)
            return jsonify({
                'success': True,
                'isSelect': True,
                'columns': df.columns.tolist(),
                'data': df.to_dict(orient='records'),
                'rowCount': len(df)
            })
        else:
            # For non-SELECT queries, execute and return success
            with db_manager.engine.connect() as connection:
                connection.execute(text(sql))
                connection.commit()
            
            return jsonify({
                'success': True,
                'isSelect': False,
                'message': 'Query executed successfully',
                'rowCount': 0
            })
    
    except Exception as e:
        logger.error(f"Error executing query: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
