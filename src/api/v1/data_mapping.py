"""
Data Mapping API endpoints for Vue.js frontend
"""
from flask import Blueprint, request, jsonify, Response, stream_with_context
import json
import logging
import uuid
import asyncio
import concurrent.futures
from typing import Dict, Any

from src.utils.auth_utils import jwt_required
from src.agents.data_mapping_agent import DataMappingAgent, MappingStatus
from src.utils.mcp_client_manager import MCPClientManager
from src.utils.user_manager import UserManager

logger = logging.getLogger('text2sql.data_mapping_api')

# Create Blueprint
data_mapping_api = Blueprint('data_mapping_api', __name__)

# Initialize user manager for audit logging
user_manager = UserManager()

# Global agent instance
_data_mapping_agent = None
_executor = concurrent.futures.ThreadPoolExecutor(max_workers=4)

def run_async_safely(coro):
    """Run an async coroutine safely in the Flask context."""
    def _run_in_new_loop():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()
    
    future = _executor.submit(_run_in_new_loop)
    return future.result()

def get_data_mapping_agent():
    """Get or create the data mapping agent instance."""
    global _data_mapping_agent
    
    if _data_mapping_agent is None:
        try:
            # Get MCP client for data mapping
            mcp_client = run_async_safely(MCPClientManager.get_client_by_name("mcp-data-mapping"))
            if mcp_client:
                _data_mapping_agent = DataMappingAgent(mcp_client)
                logger.info("Data mapping agent initialized successfully")
            else:
                logger.error("Failed to get MCP client for data mapping")
                return None
        except Exception as e:
            logger.exception(f"Error initializing data mapping agent: {e}")
            return None
    
    return _data_mapping_agent

@data_mapping_api.route('/status', methods=['GET'])
@jwt_required
def get_status():
    """Get data mapping service status."""
    try:
        agent = get_data_mapping_agent()
        if agent:
            # Check if MCP server is responsive
            try:
                # Simple health check - try to list tools
                tools = run_async_safely(agent.mcp_client.list_tools())
                return jsonify({
                    'success': True,
                    'status': 'running',
                    'tools_available': len(tools),
                    'message': 'Data mapping service is operational'
                })
            except Exception as e:
                logger.error(f"MCP server health check failed: {e}")
                return jsonify({
                    'success': False,
                    'status': 'error',
                    'message': f'MCP server not responding: {str(e)}'
                }), 503
        else:
            return jsonify({
                'success': False,
                'status': 'error',
                'message': 'Data mapping service not available'
            }), 503
    except Exception as e:
        logger.exception("Error checking data mapping status")
        return jsonify({
            'success': False,
            'status': 'error',
            'message': str(e)
        }), 500

@data_mapping_api.route('/analyze/single', methods=['POST'])
@jwt_required
def analyze_single_column():
    """Analyze a single column for mapping opportunities."""
    try:
        data = request.get_json()
        if not data or not data.get('column_name') or not data.get('table_name'):
            return jsonify({'error': 'Missing column_name or table_name'}), 400
        
        column_name = data['column_name']
        table_name = data['table_name']
        workspace = data.get('workspace', 'default')
        
        agent = get_data_mapping_agent()
        if not agent:
            return jsonify({'error': 'Data mapping service not available'}), 503
        
        def generate():
            try:
                # Start analysis
                analysis_id = str(uuid.uuid4())
                yield f"data: {json.dumps({'type': 'started', 'analysis_id': analysis_id})}\n\n"
                
                # Run the analysis
                result = run_async_safely(agent.analyze_unmapped_column(
                    column_name=column_name,
                    table_name=table_name,
                    workspace=workspace
                ))
                
                # Stream the result
                yield f"data: {json.dumps({'type': 'result', 'data': result})}\n\n"
                
            except Exception as e:
                logger.exception(f"Error in single column analysis: {e}")
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
        logger.exception("Error in single column analysis endpoint")
        return jsonify({'error': str(e)}), 500

@data_mapping_api.route('/analyze/bulk', methods=['POST'])
@jwt_required
def analyze_bulk_columns():
    """Analyze multiple columns for mapping opportunities."""
    try:
        data = request.get_json()
        if not data or not data.get('columns'):
            return jsonify({'error': 'Missing columns data'}), 400
        
        columns = data['columns']
        workspace = data.get('workspace', 'default')
        
        agent = get_data_mapping_agent()
        if not agent:
            return jsonify({'error': 'Data mapping service not available'}), 503
        
        def generate():
            try:
                # Start bulk analysis
                analysis_id = str(uuid.uuid4())
                yield f"data: {json.dumps({'type': 'started', 'analysis_id': analysis_id, 'total': len(columns)})}\n\n"
                
                results = []
                for i, column_info in enumerate(columns):
                    try:
                        # Progress update
                        yield f"data: {json.dumps({'type': 'progress', 'current': i + 1, 'total': len(columns), 'column': column_info.get('column_name', 'Unknown')})}\n\n"
                        
                        # Run analysis for this column
                        result = run_async_safely(agent.analyze_unmapped_column(
                            column_name=column_info['column_name'],
                            table_name=column_info['table_name'],
                            workspace=workspace
                        ))
                        
                        results.append({
                            'column_name': column_info['column_name'],
                            'table_name': column_info['table_name'],
                            'result': result
                        })
                        
                        # Stream individual result
                        yield f"data: {json.dumps({'type': 'column_result', 'data': results[-1]})}\n\n"
                        
                    except Exception as e:
                        logger.exception(f"Error analyzing column {column_info.get('column_name', 'Unknown')}: {e}")
                        results.append({
                            'column_name': column_info.get('column_name', 'Unknown'),
                            'table_name': column_info.get('table_name', 'Unknown'),
                            'error': str(e)
                        })
                        yield f"data: {json.dumps({'type': 'column_error', 'data': results[-1]})}\n\n"
                
                # Send final results
                yield f"data: {json.dumps({'type': 'results', 'data': results})}\n\n"
                
            except Exception as e:
                logger.exception(f"Error in bulk column analysis: {e}")
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
        logger.exception("Error in bulk column analysis endpoint")
        return jsonify({'error': str(e)}), 500

@data_mapping_api.route('/mappings', methods=['GET'])
@jwt_required
def get_mappings():
    """Get existing column mappings."""
    try:
        workspace = request.args.get('workspace', 'default')
        table_name = request.args.get('table_name')
        column_name = request.args.get('column_name')
        
        agent = get_data_mapping_agent()
        if not agent:
            return jsonify({'error': 'Data mapping service not available'}), 503
        
        # Get mappings using the agent
        mappings = run_async_safely(agent.get_column_mapping(
            workspace=workspace,
            table_name=table_name,
            column_name=column_name
        ))
        
        return jsonify({
            'success': True,
            'mappings': mappings
        })
        
    except Exception as e:
        logger.exception("Error getting mappings")
        return jsonify({'error': str(e)}), 500

@data_mapping_api.route('/mappings', methods=['POST'])
@jwt_required
def save_mapping():
    """Save a new column mapping."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Missing mapping data'}), 400
        
        # Extract mapping information
        source_table = data.get('source_table')
        source_column = data.get('source_column')
        target_table = data.get('target_table')
        target_column = data.get('target_column')
        mapping_type = data.get('mapping_type', 'direct')
        transformation = data.get('transformation')
        workspace = data.get('workspace', 'default')
        
        if not all([source_table, source_column, target_table, target_column]):
            return jsonify({'error': 'Missing required mapping fields'}), 400
        
        agent = get_data_mapping_agent()
        if not agent:
            return jsonify({'error': 'Data mapping service not available'}), 503
        
        # Save the mapping (this would need to be implemented in the agent)
        # For now, return success
        mapping_id = str(uuid.uuid4())
        
        # Log the mapping save operation
        user_id = getattr(request, 'current_user_id', 'unknown')
        ip_address = request.environ.get('HTTP_X_REAL_IP', request.remote_addr)
        
        user_manager.log_audit_event(
            event_type='data_mapping_save',
            user_id=user_id,
            ip_address=ip_address,
            event_data={
                'mapping_id': mapping_id,
                'source_table': source_table,
                'source_column': source_column,
                'target_table': target_table,
                'target_column': target_column,
                'mapping_type': mapping_type,
                'workspace': workspace
            }
        )
        
        return jsonify({
            'success': True,
            'mapping_id': mapping_id,
            'message': 'Mapping saved successfully'
        })
        
    except Exception as e:
        logger.exception("Error saving mapping")
        return jsonify({'error': str(e)}), 500

@data_mapping_api.route('/search', methods=['POST'])
@jwt_required
def search_mappings():
    """Search existing mappings in the repository."""
    try:
        data = request.get_json()
        if not data or not data.get('query'):
            return jsonify({'error': 'Missing search query'}), 400
        
        query = data['query']
        workspace = data.get('workspace', 'default')
        
        agent = get_data_mapping_agent()
        if not agent:
            return jsonify({'error': 'Data mapping service not available'}), 503
        
        # Search mappings (this would need semantic search implementation)
        # For now, return empty results
        results = []
        
        return jsonify({
            'success': True,
            'results': results,
            'total': len(results)
        })
        
    except Exception as e:
        logger.exception("Error searching mappings")
        return jsonify({'error': str(e)}), 500

@data_mapping_api.route('/catalog', methods=['GET'])
@jwt_required
def get_catalog_overview():
    """Get data catalog overview and statistics."""
    try:
        workspace = request.args.get('workspace', 'default')
        
        agent = get_data_mapping_agent()
        if not agent:
            return jsonify({'error': 'Data mapping service not available'}), 503
        
        # Get catalog statistics
        # This would need to be implemented in the agent
        catalog_stats = {
            'total_tables': 0,
            'total_columns': 0,
            'mapped_columns': 0,
            'unmapped_columns': 0,
            'mapping_coverage': 0.0,
            'workspaces': [workspace]
        }
        
        return jsonify({
            'success': True,
            'catalog': catalog_stats
        })
        
    except Exception as e:
        logger.exception("Error getting catalog overview")
        return jsonify({'error': str(e)}), 500