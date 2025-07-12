"""
Data Mapping Routes

Web interface for the AI Data Mapping Analyst Agent.
Provides UI for data mapping analysis, column mapping, and data modeling operations.
"""

import json
import logging
import uuid
import asyncio
import requests
import threading
import concurrent.futures
from datetime import datetime
from flask import Blueprint, render_template, request, jsonify, session
from typing import Dict, Any

from src.agents.data_mapping_agent import DataMappingAgent, MappingStatus
from src.utils.auth_utils import login_required
from src.routes.auth_routes import admin_required
from src.utils.mcp_client_manager import MCPClientManager

logger = logging.getLogger('text2sql.data_mapping_routes')

# Create blueprint
data_mapping_bp = Blueprint('data_mapping', __name__, url_prefix='/data-mapping')

# Global agent instance (will be initialized with MCP client)
_data_mapping_agent = None

# Thread pool for async operations
_executor = concurrent.futures.ThreadPoolExecutor(max_workers=4)


def run_async_safely(coro):
    """
    Run an async coroutine safely in the Flask context.
    This avoids event loop conflicts by running in a separate thread.
    """
    def _run_in_new_loop():
        # Create a new event loop for this thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(coro)
        finally:
            # Clean up the loop
            try:
                # Cancel any remaining tasks
                pending = asyncio.all_tasks(loop)
                for task in pending:
                    task.cancel()
                
                # Wait for tasks to complete with timeout
                if pending:
                    loop.run_until_complete(asyncio.wait_for(
                        asyncio.gather(*pending, return_exceptions=True),
                        timeout=5.0
                    ))
            except (asyncio.TimeoutError, Exception) as e:
                logger.warning(f"Event loop cleanup had issues: {e}")
            finally:
                try:
                    loop.close()
                except Exception as e:
                    logger.warning(f"Error closing event loop: {e}")
    
    # Run in thread pool to avoid blocking Flask
    future = _executor.submit(_run_in_new_loop)
    return future.result(timeout=30)  # 30 second timeout


def get_data_mapping_agent():
    """Get or create the data mapping agent instance"""
    global _data_mapping_agent
    
    if _data_mapping_agent is None:
        try:
            # Get MCP client for data mapping server
            mcp_manager = MCPClientManager()
            
            # Try to get the data mapping MCP client by server name
            data_mapping_client = None
            try:
                # Look for data mapping server by name patterns
                from src.models.mcp_server import MCPServer
                available_servers = MCPServer.get_all()
                logger.info(f"Available MCP servers: {[s.name for s in available_servers]}")
                
                for server in available_servers:
                    server_name_lower = server.name.lower()
                    if ('data' in server_name_lower and 'mapping' in server_name_lower) or \
                       'data-mapping' in server_name_lower or \
                       server_name_lower == 'data mapping analyst':
                        # Use safe async runner and ensure connection
                        data_mapping_client = run_async_safely(mcp_manager.get_client(server.id, connect=True))
                        if data_mapping_client and data_mapping_client.is_connected():
                            logger.info(f"Found data mapping server: {server.name} (ID: {server.id})")
                            break
                        else:
                            logger.warning(f"Could not connect to data mapping server: {server.name}")
                            data_mapping_client = None
                        
                # If not found, try to manually register the server
                if data_mapping_client is None:
                    logger.info("Data mapping server not found in registry, attempting manual registration")
                    try:
                        # Try to manually add the server if it's running
                        test_response = requests.get("http://localhost:8003/sse", timeout=2)
                        if test_response.status_code == 200 or test_response.status_code == 404:
                            # Server is running, but not registered - user needs to register it in admin
                            logger.info("Data mapping server is running but not registered in MCP Servers admin")
                    except Exception as e:
                        logger.warning(f"Could not connect to manual data mapping server: {str(e)}")
                        
                if data_mapping_client is None:
                    logger.warning("Data mapping MCP server not found. Agent will work without MCP features.")
                    
            except Exception as e:
                logger.warning(f"Could not connect to data mapping MCP server: {str(e)}")
            
            # Create agent with or without client
            _data_mapping_agent = DataMappingAgent(mcp_client=data_mapping_client)
            
        except Exception as e:
            logger.error(f"Error creating data mapping agent: {str(e)}")
            _data_mapping_agent = DataMappingAgent(mcp_client=None)
    
    return _data_mapping_agent


@data_mapping_bp.route('/')
@login_required
def data_mapping_page():
    """Main data mapping analysis page"""
    try:
        return render_template('data_mapping/index.html',
                             page_title="AI Data Mapping Analyst",
                             active_nav="data_mapping")
    except Exception as e:
        logger.error(f"Error loading data mapping page: {str(e)}")
        return render_template('500.html'), 500


@data_mapping_bp.route('/server-status')
@login_required
def get_server_status():
    """Get the status of the MCP server"""
    try:
        agent = get_data_mapping_agent()
        
        if not agent.mcp_client:
            return jsonify({
                "status": "disconnected",
                "message": "Data Mapping MCP server not available",
                "server_found": False
            })
        
        # Try to test the connection
        test_result = run_async_safely(agent.test_connection())
        
        if test_result.get("status") == "success":
            return jsonify({
                "status": "connected",
                "message": "Data Mapping MCP server is running and connected",
                "server_found": True,
                "test_result": test_result
            })
        else:
            return jsonify({
                "status": "error",
                "message": f"Server connection test failed: {test_result.get('message', 'Unknown error')}",
                "server_found": True,
                "test_result": test_result
            })
        
    except Exception as e:
        logger.error(f"Error checking server status: {str(e)}")
        return jsonify({
            "status": "error",
            "message": f"Failed to check server status: {str(e)}",
            "server_found": False
        })


@data_mapping_bp.route('/test-connection')
@login_required
def test_mcp_connection():
    """Test MCP server connection"""
    try:
        agent = get_data_mapping_agent()
        
        if not agent.mcp_client:
            return jsonify({
                "status": "error",
                "message": "No MCP client available",
                "debug_info": {
                    "agent_created": agent is not None,
                    "mcp_client": None
                }
            })
        
        # Try a simple test
        test_result = run_async_safely(agent.test_connection())
        return jsonify({
            "status": "success",
            "message": "MCP server connection successful",
            "test_result": test_result
        })
        
    except Exception as e:
        logger.error(f"Error testing MCP connection: {str(e)}")
        return jsonify({
            "status": "error",
            "message": f"Connection test failed: {str(e)}",
            "debug_info": {
                "error_type": type(e).__name__,
                "traceback": str(e)
            }
        })


@data_mapping_bp.route('/catalog-overview')
@login_required
def get_catalog_overview():
    """Get overview of the data catalog"""
    try:
        agent = get_data_mapping_agent()
        
        if not agent.mcp_client:
            return jsonify({
                "status": "error",
                "message": "Data Mapping MCP server not available. Please configure the MCP server in admin settings."
            }), 503
        
        overview = run_async_safely(agent.get_catalog_overview())
        return jsonify(overview)
        
    except Exception as e:
        logger.error(f"Error getting catalog overview: {str(e)}")
        return jsonify({
            "status": "error",
            "message": f"Failed to get catalog overview: {str(e)}"
        }), 500


@data_mapping_bp.route('/analyze-column', methods=['POST'])
@login_required
def analyze_column():
    """Analyze a single column for mapping opportunities"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                "status": "error",
                "message": "No data provided"
            }), 400
        
        source_table = data.get('source_table', '').strip()
        source_column = data.get('source_column', '').strip()
        target_table = data.get('target_table', '').strip() or None
        target_column = data.get('target_column', '').strip() or None
        user_context = data.get('user_context', '').strip()
        
        if not source_table or not source_column:
            return jsonify({
                "status": "error",
                "message": "Source table and column are required"
            }), 400
        
        agent = get_data_mapping_agent()
        
        if not agent.mcp_client:
            return jsonify({
                "status": "error",
                "message": "Data Mapping MCP server not available. Please configure the MCP server in admin settings."
            }), 503
        
        # Perform column mapping analysis
        result = run_async_safely(agent.map_column(
            source_table=source_table,
            source_column=source_column,
            target_table=target_table,
            target_column=target_column,
            user_context=user_context
        ))
        
        # Log the analysis for audit purposes
        logger.info(f"Column mapping analysis completed for {source_table}.{source_column} by user {session.get('user_id')}")
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error analyzing column: {str(e)}")
        return jsonify({
            "status": "error",
            "message": f"Failed to analyze column: {str(e)}"
        }), 500


@data_mapping_bp.route('/bulk-analyze', methods=['POST'])
@login_required
def bulk_analyze_columns():
    """Analyze multiple columns in batch"""
    try:
        data = request.get_json()
        
        if not data or 'columns' not in data:
            return jsonify({
                "status": "error",
                "message": "Column list is required"
            }), 400
        
        columns = data.get('columns', [])
        
        if not isinstance(columns, list) or len(columns) == 0:
            return jsonify({
                "status": "error",
                "message": "Invalid or empty column list"
            }), 400
        
        # Validate column format
        column_tuples = []
        for col in columns:
            if isinstance(col, dict):
                table = col.get('table', '').strip()
                column = col.get('column', '').strip()
            elif isinstance(col, list) and len(col) >= 2:
                table = str(col[0]).strip()
                column = str(col[1]).strip()
            else:
                return jsonify({
                    "status": "error",
                    "message": "Each column must be a dict with 'table' and 'column' or a list [table, column]"
                }), 400
            
            if not table or not column:
                return jsonify({
                    "status": "error",
                    "message": f"Invalid table/column specification: {col}"
                }), 400
            
            column_tuples.append((table, column))
        
        if len(column_tuples) > 50:  # Limit bulk operations
            return jsonify({
                "status": "error",
                "message": "Bulk analysis limited to 50 columns at a time"
            }), 400
        
        agent = get_data_mapping_agent()
        
        if not agent.mcp_client:
            return jsonify({
                "status": "error",
                "message": "Data Mapping MCP server not available"
            }), 503
        
        # Perform bulk analysis
        result = run_async_safely(agent.bulk_analyze_columns(column_tuples))
        
        # Log the bulk analysis
        logger.info(f"Bulk column analysis completed for {len(column_tuples)} columns by user {session.get('user_id')}")
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error in bulk analysis: {str(e)}")
        return jsonify({
            "status": "error",
            "message": f"Failed to perform bulk analysis: {str(e)}"
        }), 500


@data_mapping_bp.route('/save-mapping', methods=['POST'])
@login_required
def save_mapping():
    """Save a mapping to the data mappings repository"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                "status": "error",
                "message": "No mapping data provided"
            }), 400
        
        # Validate required fields
        required_fields = ['target_table', 'target_column', 'transformation_logic', 'business_rule']
        for field in required_fields:
            if not data.get(field):
                return jsonify({
                    "status": "error",
                    "message": f"Missing required field: {field}"
                }), 400
        
        # Create mapping object
        mapping_data = {
            "mappingId": data.get('mapping_id') or str(uuid.uuid4()),
            "targetTable": data['target_table'],
            "targetColumn": data['target_column'],
            "status": data.get('status', 'ACTIVE'),
            "version": data.get('version', 1),
            "transformationLogic": data['transformation_logic'],
            "businessRule": data['business_rule'],
            "lineage": data.get('lineage', []),
            "createdBy": session.get('username', 'unknown'),
            "validatedBy": data.get('validated_by'),
            "createdAt": datetime.now().isoformat() + 'Z',
            "updatedAt": datetime.now().isoformat() + 'Z'
        }
        
        # Save the mapping (this would typically save to the data_mappings.json file)
        from src.utils.data_catalog_utils import save_mapping
        
        success = save_mapping(mapping_data)
        
        if success:
            logger.info(f"Mapping saved for {data['target_table']}.{data['target_column']} by user {session.get('user_id')}")
            return jsonify({
                "status": "success",
                "message": "Mapping saved successfully",
                "mapping_id": mapping_data["mappingId"]
            })
        else:
            return jsonify({
                "status": "error",
                "message": "Failed to save mapping"
            }), 500
        
    except Exception as e:
        logger.error(f"Error saving mapping: {str(e)}")
        return jsonify({
            "status": "error",
            "message": f"Failed to save mapping: {str(e)}"
        }), 500


@data_mapping_bp.route('/search-mappings')
@login_required
def search_mappings():
    """Search existing mappings"""
    try:
        search_term = request.args.get('q', '').strip()
        table_filter = request.args.get('table', '').strip()
        status_filter = request.args.get('status', 'ACTIVE').strip()
        
        from src.utils.data_catalog_utils import load_data_mappings
        mappings_data = load_data_mappings()
        
        mappings = mappings_data.get('mappings', [])
        
        # Apply filters
        if status_filter and status_filter != 'ALL':
            mappings = [m for m in mappings if m.get('status', '').upper() == status_filter.upper()]
        
        if table_filter:
            mappings = [m for m in mappings if table_filter.upper() in m.get('targetTable', '').upper()]
        
        if search_term:
            search_term_lower = search_term.lower()
            mappings = [m for m in mappings if 
                       search_term_lower in m.get('targetTable', '').lower() or
                       search_term_lower in m.get('targetColumn', '').lower() or
                       search_term_lower in m.get('businessRule', '').lower()]
        
        # Sort by target table and column
        mappings.sort(key=lambda x: (x.get('targetTable', ''), x.get('targetColumn', '')))
        
        return jsonify({
            "status": "success",
            "mappings": mappings,
            "total_count": len(mappings)
        })
        
    except Exception as e:
        logger.error(f"Error searching mappings: {str(e)}")
        return jsonify({
            "status": "error",
            "message": f"Failed to search mappings: {str(e)}"
        }), 500


@data_mapping_bp.route('/mapping-stats')
@login_required
def get_mapping_stats():
    """Get mapping statistics and overview"""
    try:
        from src.utils.data_catalog_utils import get_catalog_stats
        stats = get_catalog_stats()
        
        return jsonify({
            "status": "success",
            "stats": stats
        })
        
    except Exception as e:
        logger.error(f"Error getting mapping stats: {str(e)}")
        return jsonify({
            "status": "error",
            "message": f"Failed to get mapping stats: {str(e)}"
        }), 500


# Error handlers
@data_mapping_bp.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    return render_template('404.html'), 404


@data_mapping_bp.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    logger.error(f"Internal error in data mapping routes: {str(error)}")
    return render_template('500.html'), 500
