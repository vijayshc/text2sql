from flask import Blueprint, render_template, request, jsonify
import logging
import json
import os
from src.utils.schema_manager import SchemaManager
import time

# Configure logger
logger = logging.getLogger('text2sql.routes.schema')

# Create a Blueprint for schema routes
schema_bp = Blueprint('schema', __name__, url_prefix='/admin')

# Initialize schema manager
schema_manager = SchemaManager()

@schema_bp.route('/schema')
def schema_page():
    """Render the schema management page"""
    logger.debug("Schema management page requested")
    # Get workspaces for the dropdown
    workspaces = schema_manager.get_workspaces()
    return render_template('admin/schema.html', workspaces=workspaces)

@schema_bp.route('/api/schema/workspaces', methods=['GET'])
def get_all_workspaces():
    """Get all workspaces defined in the schema"""
    try:
        workspaces = schema_manager.get_workspaces()
        return jsonify({"success": True, "workspaces": workspaces})
    except Exception as e:
        logger.exception(f"Error retrieving workspaces: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

@schema_bp.route('/api/schema/workspaces/<workspace_name>', methods=['GET'])
def get_workspace_details(workspace_name):
    """Get detailed information about a specific workspace"""
    try:
        workspace = schema_manager.get_workspace_by_name(workspace_name)
        if workspace:
            return jsonify({"success": True, "workspace": workspace})
        else:
            return jsonify({"success": False, "error": f"Workspace '{workspace_name}' not found"}), 404
    except Exception as e:
        logger.exception(f"Error retrieving workspace details: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

@schema_bp.route('/api/schema/workspaces', methods=['POST'])
def create_workspace():
    """Create a new workspace"""
    try:
        data = request.get_json()
        
        # Basic validation
        if not data or 'name' not in data:
            return jsonify({"success": False, "error": "Workspace name is required"}), 400
        
        # Check if workspace already exists
        existing = schema_manager.get_workspace_by_name(data['name'])
        if existing:
            return jsonify({"success": False, "error": f"Workspace '{data['name']}' already exists"}), 409
        
        # Add new workspace to schema data
        schema_data = schema_manager.schema_data
        
        new_workspace = {
            "name": data['name'],
            "description": data.get('description', ''),
            "tables": []
        }
        schema_data['workspaces'].append(new_workspace)
        
        # Save updated schema data
        success = schema_manager.save_schema(schema_data)
        
        if success:
            # Reload schema data
            schema_manager.load_schema()
            return jsonify({"success": True, "workspace": new_workspace})
        else:
            return jsonify({"success": False, "error": "Failed to save schema data"}), 500
            
    except Exception as e:
        logger.exception(f"Error creating workspace: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

@schema_bp.route('/api/schema/workspaces/<workspace_name>', methods=['PUT'])
def update_workspace(workspace_name):
    """Update an existing workspace"""
    try:
        data = request.get_json()
        
        # Basic validation
        if not data:
            return jsonify({"success": False, "error": "No update data provided"}), 400
        
        schema_data = schema_manager.schema_data
        
        # Find and update the workspace
        workspace_updated = False
        for i, workspace in enumerate(schema_data['workspaces']):
            if workspace['name'] == workspace_name:
                workspace['description'] = data.get('description', workspace.get('description', ''))
                
                # If name is changing, make sure it doesn't conflict
                if 'name' in data and data['name'] != workspace_name:
                    # Check if new name already exists
                    exists = any(w['name'] == data['name'] for w in schema_data['workspaces'])
                    if exists:
                        return jsonify({
                            "success": False, 
                            "error": f"Cannot rename - workspace '{data['name']}' already exists"
                        }), 409
                    
                    workspace['name'] = data['name']
                
                workspace_updated = True
                break
        
        if not workspace_updated:
            return jsonify({"success": False, "error": f"Workspace '{workspace_name}' not found"}), 404
            
        # Save updated schema data
        success = schema_manager.save_schema(schema_data)
        
        if success:
            # Reload schema data
            schema_manager.load_schema()
            return jsonify({"success": True})
        else:
            return jsonify({"success": False, "error": "Failed to save schema data"}), 500
            
    except Exception as e:
        logger.exception(f"Error updating workspace: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

@schema_bp.route('/api/schema/workspaces/<workspace_name>', methods=['DELETE'])
def delete_workspace(workspace_name):
    """Delete an existing workspace"""
    try:
        schema_data = schema_manager.schema_data
        
        # Find the workspace
        workspace_index = None
        for i, workspace in enumerate(schema_data['workspaces']):
            if workspace['name'] == workspace_name:
                workspace_index = i
                break
        
        if workspace_index is None:
            return jsonify({"success": False, "error": f"Workspace '{workspace_name}' not found"}), 404
            
        # Remove the workspace
        schema_data['workspaces'].pop(workspace_index)
        
        # Save updated schema data
        success = schema_manager.save_schema(schema_data)
        
        if success:
            # Reload schema data
            schema_manager.load_schema()
            return jsonify({"success": True})
        else:
            return jsonify({"success": False, "error": "Failed to save schema data"}), 500
            
    except Exception as e:
        logger.exception(f"Error deleting workspace: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

@schema_bp.route('/api/schema/tables', methods=['GET'])
def get_tables():
    """Get all tables or tables for a specific workspace"""
    try:
        workspace_name = request.args.get('workspace')
        tables = schema_manager.get_tables(workspace_name)
        return jsonify({"success": True, "tables": tables})
    except Exception as e:
        logger.exception(f"Error retrieving tables: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

@schema_bp.route('/api/schema/tables/<table_name>', methods=['GET'])
def get_table_details(table_name):
    """Get detailed information about a specific table"""
    try:
        workspace_name = request.args.get('workspace')
        table = schema_manager.get_table_by_name(table_name, workspace_name)
        
        if table:
            return jsonify({"success": True, "table": table})
        else:
            return jsonify({"success": False, "error": f"Table '{table_name}' not found"}), 404
            
    except Exception as e:
        logger.exception(f"Error retrieving table details: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

@schema_bp.route('/api/schema/tables', methods=['POST'])
def create_table():
    """Create a new table in a workspace"""
    try:
        data = request.get_json()
        
        # Basic validation
        if not data or 'name' not in data or 'workspace' not in data:
            return jsonify({
                "success": False, 
                "error": "Table name and workspace are required"
            }), 400
            
        workspace_name = data['workspace']
        table_name = data['name']
        
        # Check if workspace exists
        workspace = schema_manager.get_workspace_by_name(workspace_name)
        if not workspace:
            return jsonify({
                "success": False, 
                "error": f"Workspace '{workspace_name}' not found"
            }), 404
            
        # Check if table already exists in this workspace
        existing_table = schema_manager.get_table_by_name(table_name, workspace_name)
        if existing_table:
            return jsonify({
                "success": False, 
                "error": f"Table '{table_name}' already exists in workspace '{workspace_name}'"
            }), 409
        
        # Create new table
        new_table = {
            "name": table_name,
            "description": data.get('description', ''),
            "columns": data.get('columns', [])
        }
        
        # Add table to workspace
        schema_data = schema_manager.schema_data
        for ws in schema_data['workspaces']:
            if ws['name'] == workspace_name:
                if 'tables' not in ws:
                    ws['tables'] = []
                ws['tables'].append(new_table)
                break
                
        # Save updated schema data
        success = schema_manager.save_schema(schema_data)
        
        if success:
            # Reload schema data
            schema_manager.load_schema()
            return jsonify({"success": True, "table": new_table})
        else:
            return jsonify({"success": False, "error": "Failed to save schema data"}), 500
            
    except Exception as e:
        logger.exception(f"Error creating table: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

@schema_bp.route('/api/schema/tables/<table_name>', methods=['PUT'])
def update_table(table_name):
    """Update an existing table"""
    try:
        data = request.get_json()
        
        # Basic validation
        if not data:
            return jsonify({"success": False, "error": "No update data provided"}), 400
            
        workspace_name = request.args.get('workspace')
        if not workspace_name:
            return jsonify({"success": False, "error": "Workspace parameter is required"}), 400
            
        # Find workspace and table
        schema_data = schema_manager.schema_data
        workspace = None
        workspace_index = None
        
        for i, ws in enumerate(schema_data['workspaces']):
            if ws['name'] == workspace_name:
                workspace = ws
                workspace_index = i
                break
                
        if not workspace:
            return jsonify({
                "success": False, 
                "error": f"Workspace '{workspace_name}' not found"
            }), 404
        
        # Find the table
        table = None
        table_index = None
        
        if 'tables' in workspace:
            for i, t in enumerate(workspace['tables']):
                if t['name'] == table_name:
                    table = t
                    table_index = i
                    break
                    
        if table is None:
            return jsonify({
                "success": False, 
                "error": f"Table '{table_name}' not found in workspace '{workspace_name}'"
            }), 404
        
        # Update table properties
        table['description'] = data.get('description', table.get('description', ''))
        
        # If name is changing, make sure it doesn't conflict
        if 'name' in data and data['name'] != table_name:
            # Check if new name already exists in this workspace
            exists = any(t['name'] == data['name'] for t in workspace.get('tables', []))
            if exists:
                return jsonify({
                    "success": False, 
                    "error": f"Cannot rename - table '{data['name']}' already exists in workspace '{workspace_name}'"
                }), 409
                
            table['name'] = data['name']
        
        # Update columns if provided
        if 'columns' in data:
            table['columns'] = data['columns']
        
        # Save updated schema data
        success = schema_manager.save_schema(schema_data)
        
        if success:
            # Reload schema data
            schema_manager.load_schema()
            return jsonify({"success": True})
        else:
            return jsonify({"success": False, "error": "Failed to save schema data"}), 500
            
    except Exception as e:
        logger.exception(f"Error updating table: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

@schema_bp.route('/api/schema/tables/<table_name>', methods=['DELETE'])
def delete_table(table_name):
    """Delete an existing table"""
    try:
        workspace_name = request.args.get('workspace')
        if not workspace_name:
            return jsonify({"success": False, "error": "Workspace parameter is required"}), 400
            
        # Find workspace and table
        schema_data = schema_manager.schema_data
        workspace = None
        
        for ws in schema_data['workspaces']:
            if ws['name'] == workspace_name:
                workspace = ws
                break
                
        if not workspace:
            return jsonify({
                "success": False, 
                "error": f"Workspace '{workspace_name}' not found"
            }), 404
        
        # Find the table
        table_index = None
        
        if 'tables' in workspace:
            for i, t in enumerate(workspace['tables']):
                if t['name'] == table_name:
                    table_index = i
                    break
                    
        if table_index is None:
            return jsonify({
                "success": False, 
                "error": f"Table '{table_name}' not found in workspace '{workspace_name}'"
            }), 404
        
        # Remove the table
        workspace['tables'].pop(table_index)
        
        # Save updated schema data
        success = schema_manager.save_schema(schema_data)
        
        if success:
            # Reload schema data
            schema_manager.load_schema()
            return jsonify({"success": True})
        else:
            return jsonify({"success": False, "error": "Failed to save schema data"}), 500
            
    except Exception as e:
        logger.exception(f"Error deleting table: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

@schema_bp.route('/api/schema/reload', methods=['POST'])
def reload_schema_from_files():
    """Reload schema data from JSON files"""
    try:
        # Reload schema and join conditions
        schema_loaded = schema_manager.load_schema()
        joins_loaded = schema_manager.load_join_conditions()
        
        if schema_loaded and joins_loaded:
            return jsonify({
                "success": True, 
                "message": "Schema and join conditions reloaded successfully"
            })
        else:
            errors = []
            if not schema_loaded:
                errors.append("Failed to reload schema")
            if not joins_loaded:
                errors.append("Failed to reload join conditions")
                
            return jsonify({
                "success": False, 
                "error": ", ".join(errors)
            }), 500
            
    except Exception as e:
        logger.exception(f"Error reloading schema from files: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

# Routes for join conditions
@schema_bp.route('/api/schema/joins', methods=['GET'])
def get_join_conditions():
    """Get all join conditions"""
    try:
        joins = schema_manager.joins
        return jsonify({"success": True, "joins": joins})
    except Exception as e:
        logger.exception(f"Error retrieving join conditions: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

@schema_bp.route('/api/schema/joins', methods=['POST'])
def create_join_condition():
    """Create a new join condition"""
    try:
        data = request.get_json()
        
        # Basic validation
        if not data or 'left_table' not in data or 'right_table' not in data or 'condition' not in data:
            return jsonify({
                "success": False, 
                "error": "Left table, right table, and join condition are required"
            }), 400
        
        # Check if join already exists between these tables
        existing_join = schema_manager.get_specific_join(data['left_table'], data['right_table'])
        if existing_join:
            return jsonify({
                "success": False, 
                "error": f"Join condition already exists between '{data['left_table']}' and '{data['right_table']}'"
            }), 409
        
        # Create new join condition
        new_join = {
            "left_table": data['left_table'],
            "right_table": data['right_table'],
            "condition": data['condition'],
            "join_type": data.get('join_type', 'INNER'),  # Add join_type with default INNER
            "description": data.get('description', '')
        }
        
        # Add join to condition data
        condition_data = schema_manager.condition_data
        condition_data['joins'].append(new_join)
        
        # Save updated condition data
        success = schema_manager.save_join_conditions(condition_data)
        
        if success:
            # Reload join conditions
            schema_manager.load_join_conditions()
            return jsonify({"success": True, "join": new_join})
        else:
            return jsonify({"success": False, "error": "Failed to save join condition data"}), 500
            
    except Exception as e:
        logger.exception(f"Error creating join condition: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

@schema_bp.route('/api/schema/joins/<int:join_id>', methods=['PUT'])
def update_join_condition(join_id):
    """Update an existing join condition"""
    try:
        data = request.get_json()
        
        # Basic validation
        if not data:
            return jsonify({"success": False, "error": "No update data provided"}), 400
        
        # Check if join index is valid
        condition_data = schema_manager.condition_data
        if join_id < 0 or join_id >= len(condition_data['joins']):
            return jsonify({
                "success": False, 
                "error": f"Join condition with ID {join_id} not found"
            }), 404
        
        # Update join condition properties
        join = condition_data['joins'][join_id]
        
        if 'left_table' in data:
            join['left_table'] = data['left_table']
            
        if 'right_table' in data:
            join['right_table'] = data['right_table']
            
        if 'condition' in data:
            join['condition'] = data['condition']
            
        if 'join_type' in data:
            join['join_type'] = data['join_type']
            
        if 'description' in data:
            join['description'] = data['description']
        
        # Save updated condition data
        success = schema_manager.save_join_conditions(condition_data)
        
        if success:
            # Reload join conditions
            schema_manager.load_join_conditions()
            return jsonify({"success": True})
        else:
            return jsonify({"success": False, "error": "Failed to save join condition data"}), 500
            
    except Exception as e:
        logger.exception(f"Error updating join condition: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

@schema_bp.route('/api/schema/joins/<int:join_id>', methods=['DELETE'])
def delete_join_condition(join_id):
    """Delete an existing join condition"""
    try:
        # Check if join index is valid
        condition_data = schema_manager.condition_data
        if join_id < 0 or join_id >= len(condition_data['joins']):
            return jsonify({
                "success": False, 
                "error": f"Join condition with ID {join_id} not found"
            }), 404
        
        # Remove the join condition
        condition_data['joins'].pop(join_id)
        
        # Save updated condition data
        success = schema_manager.save_join_conditions(condition_data)
        
        if success:
            # Reload join conditions
            schema_manager.load_join_conditions()
            return jsonify({"success": True})
        else:
            return jsonify({"success": False, "error": "Failed to save join condition data"}), 500
            
    except Exception as e:
        logger.exception(f"Error deleting join condition: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

# Function to export schema to JSON file
@schema_bp.route('/api/schema/export', methods=['GET'])
def export_schema():
    """Export schema data to JSON file"""
    try:
        schema_data = schema_manager.schema_data
        return jsonify({"success": True, "schema": schema_data})
    except Exception as e:
        logger.exception(f"Error exporting schema: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

# Function to export join conditions to JSON file  
@schema_bp.route('/api/schema/joins/export', methods=['GET'])
def export_join_conditions():
    """Export join conditions data to JSON file"""
    try:
        condition_data = schema_manager.condition_data
        return jsonify({"success": True, "joins": condition_data})
    except Exception as e:
        logger.exception(f"Error exporting join conditions: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

# Function to import schema from JSON file
@schema_bp.route('/api/schema/import', methods=['POST'])
def import_schema():
    """Import schema data from JSON"""
    try:
        data = request.get_json()
        
        if not data or 'workspaces' not in data:
            return jsonify({
                "success": False, 
                "error": "Invalid schema data - 'workspaces' key is required"
            }), 400
        
        # Save the imported schema data
        success = schema_manager.save_schema(data)
        
        if success:
            # Reload schema data
            schema_manager.load_schema()
            return jsonify({"success": True, "message": "Schema imported successfully"})
        else:
            return jsonify({"success": False, "error": "Failed to save imported schema data"}), 500
            
    except Exception as e:
        logger.exception(f"Error importing schema: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

# Function to import join conditions from JSON file
@schema_bp.route('/api/schema/joins/import', methods=['POST'])
def import_join_conditions():
    """Import join conditions data from JSON"""
    try:
        data = request.get_json()
        
        if not data or 'joins' not in data:
            return jsonify({
                "success": False, 
                "error": "Invalid join conditions data - 'joins' key is required"
            }), 400
        
        # Save the imported join conditions data
        success = schema_manager.save_join_conditions(data)
        
        if success:
            # Reload join conditions data
            schema_manager.load_join_conditions()
            return jsonify({"success": True, "message": "Join conditions imported successfully"})
        else:
            return jsonify({"success": False, "error": "Failed to save imported join conditions data"}), 500
            
    except Exception as e:
        logger.exception(f"Error importing join conditions: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500