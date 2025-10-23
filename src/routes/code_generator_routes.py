"""
Code Generator Routes

API endpoints for intelligent code generation from data mappings
"""

import json
import logging
import asyncio
import threading
from datetime import datetime
from flask import Blueprint, render_template, request, jsonify, session

from src.utils.auth_utils import login_required
from src.services.code_generator_service import CodeGeneratorService
from src.utils.user_manager import UserManager
from src.models.code_generation_history import CodeGenerationHistory

logger = logging.getLogger('text2sql.code_generator_routes')

# Create blueprint
code_generator_bp = Blueprint('code_generator', __name__, url_prefix='/code-generator')

# Initialize user manager for audit logging
user_manager = UserManager()

# Global service instance
_code_generator_service = None

# Progress tracking for active generations
_active_generations = {}
_generation_lock = threading.Lock()


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
    
    # Run in a separate thread
    import concurrent.futures
    with concurrent.futures.ThreadPoolExecutor() as executor:
        future = executor.submit(_run_in_new_loop)
        return future.result(timeout=300)  # 5 minute timeout


def get_code_generator_service():
    """Get or create the code generator service instance"""
    global _code_generator_service
    
    if _code_generator_service is None:
        _code_generator_service = CodeGeneratorService()
        # Initialize asynchronously
        try:
            run_async_safely(_code_generator_service.initialize())
        except Exception as e:
            logger.error(f"Error initializing code generator service: {str(e)}")
    
    return _code_generator_service


@code_generator_bp.route('/')
@login_required
def code_generator_page():
    """Main code generator page"""
    try:
        # Audit log the code generator page access
        user_manager.log_audit_event(
            user_id=session.get('user_id'),
            action='access_code_generator',
            details="Accessed code generator page",
            ip_address=request.remote_addr
        )
        
        return render_template('code_generator.html',
                             page_title="Code Generator",
                             active_nav="code_generator")
    except Exception as e:
        logger.error(f"Error loading code generator page: {str(e)}")
        
        # Audit log the error
        user_manager.log_audit_event(
            user_id=session.get('user_id'),
            action='access_code_generator_error',
            details=f"Error loading code generator page: {str(e)}",
            ip_address=request.remote_addr
        )
        return render_template('500.html'), 500


@code_generator_bp.route('/api/projects')
@login_required
def list_projects():
    """Get list of available projects"""
    try:
        service = get_code_generator_service()
        projects = run_async_safely(service.list_projects())
        
        # Audit log
        user_manager.log_audit_event(
            user_id=session.get('user_id'),
            action='list_projects_code_gen',
            details=f"Listed {len(projects)} projects for code generation",
            ip_address=request.remote_addr
        )
        
        return jsonify({
            "success": True,
            "projects": projects
        })
        
    except Exception as e:
        logger.error(f"Error listing projects: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@code_generator_bp.route('/api/mappings')
@login_required
def list_mappings():
    """Get list of available mappings"""
    try:
        project_name = request.args.get('project_name')
        
        service = get_code_generator_service()
        mappings = run_async_safely(service.list_mappings(project_name))
        
        # Audit log
        user_manager.log_audit_event(
            user_id=session.get('user_id'),
            action='list_mappings_code_gen',
            details=f"Listed {len(mappings)} mappings" + (f" for project {project_name}" if project_name else ""),
            ip_address=request.remote_addr
        )
        
        return jsonify({
            "success": True,
            "mappings": mappings
        })
        
    except Exception as e:
        logger.error(f"Error listing mappings: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@code_generator_bp.route('/api/generate', methods=['POST'])
@login_required
def generate_code():
    """Generate code for a mapping based on user prompt"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                "success": False,
                "error": "No data provided"
            }), 400
        
        user_prompt = data.get('user_prompt', '').strip()
        project_name = data.get('project_name', '').strip()
        
        if not user_prompt or not project_name:
            return jsonify({
                "success": False,
                "error": "User prompt and project name are required"
            }), 400
        
        # Generate unique operation ID
        import uuid
        operation_id = str(uuid.uuid4())
        
        # Capture session data before background thread (to avoid "Working outside of request context")
        user_id = session.get('user_id')
        # Fetch username from database instead of session (session only has user_id)
        try:
            user = user_manager.get_user_by_id(user_id) if user_id else None
            username = user.username if user else 'Unknown'
        except:
            username = 'Unknown'
        
        # Initialize progress tracking
        with _generation_lock:
            _active_generations[operation_id] = {
                "status": "started",
                "progress": 0,
                "message": "Initializing code generation...",
                "user_prompt": user_prompt,
                "project_name": project_name,
                "started_at": datetime.now().isoformat(),
                "step_details": {}  # Store details for each step
            }
        
        # Start generation in background thread
        def generate_in_background():
            try:
                logger.info(f"Starting code generation - Operation: {operation_id}, User Prompt: {user_prompt}, Project: {project_name}")
                service = get_code_generator_service()
                
                # Progress callback with step details
                def update_progress(message, progress, step_key=None, step_data=None):
                    with _generation_lock:
                        if operation_id in _active_generations:
                            _active_generations[operation_id]["message"] = message
                            _active_generations[operation_id]["progress"] = progress
                            # Store step details if provided
                            if step_key and step_data is not None:
                                _active_generations[operation_id]["step_details"][step_key] = step_data
                
                # Run generation (use captured user data from session)
                logger.info(f"Calling generate_code service method for operation {operation_id}")
                result = run_async_safely(
                    service.generate_code(
                        user_prompt=user_prompt,
                        project_name=project_name,
                        progress_callback=update_progress,
                        user_id=user_id,
                        username=username
                    )
                )
                logger.info(f"Generation result for {operation_id}: Success={result.get('success')}")
                
                # Update final status
                with _generation_lock:
                    if operation_id in _active_generations:
                        if result.get("success"):
                            _active_generations[operation_id]["status"] = "completed"
                            _active_generations[operation_id]["result"] = result
                            _active_generations[operation_id]["progress"] = 100
                            _active_generations[operation_id]["message"] = "Code generation completed!"
                        else:
                            _active_generations[operation_id]["status"] = "error"
                            _active_generations[operation_id]["error"] = result.get("error", "Unknown error")
                            _active_generations[operation_id]["progress"] = 0
                
            except Exception as e:
                import traceback
                error_traceback = traceback.format_exc()
                logger.error(f"Error in background generation for {operation_id}: {str(e)}")
                logger.error(f"Traceback:\n{error_traceback}")
                
                with _generation_lock:
                    if operation_id in _active_generations:
                        _active_generations[operation_id]["status"] = "error"
                        _active_generations[operation_id]["error"] = f"{str(e)}\n\nTraceback:\n{error_traceback}"
                        _active_generations[operation_id]["progress"] = 0
        
        # Start background thread
        thread = threading.Thread(target=generate_in_background, daemon=True)
        thread.start()
        
        # Audit log
        user_manager.log_audit_event(
            user_id=session.get('user_id'),
            action='generate_code',
            details=f"Started code generation with prompt: {user_prompt[:100]}, project: {project_name}",
            ip_address=request.remote_addr
        )
        
        return jsonify({
            "success": True,
            "operation_id": operation_id,
            "message": "Code generation started"
        })
        
    except Exception as e:
        logger.error(f"Error starting code generation: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@code_generator_bp.route('/api/progress/<operation_id>')
@login_required
def get_progress(operation_id):
    """Get progress of a code generation operation"""
    try:
        with _generation_lock:
            if operation_id not in _active_generations:
                return jsonify({
                    "success": False,
                    "error": "Operation not found"
                }), 404
            
            progress_info = _active_generations[operation_id].copy()
        
        return jsonify({
            "success": True,
            "operation_id": operation_id,
            "status": progress_info.get("status"),
            "progress": progress_info.get("progress", 0),
            "message": progress_info.get("message", ""),
            "error": progress_info.get("error"),
            "result": progress_info.get("result"),
            "step_details": progress_info.get("step_details", {})  # Include step details
        })
        
    except Exception as e:
        logger.error(f"Error getting progress: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@code_generator_bp.route('/api/cleanup/<operation_id>', methods=['DELETE'])
@login_required
def cleanup_operation(operation_id):
    """Clean up completed operation from memory"""
    try:
        with _generation_lock:
            if operation_id in _active_generations:
                del _active_generations[operation_id]
        
        return jsonify({
            "success": True
        })
        
    except Exception as e:
        logger.error(f"Error cleaning up operation: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@code_generator_bp.route('/history')
@login_required
def history_page():
    """Code generation history page"""
    try:
        # Create table if doesn't exist
        CodeGenerationHistory.create_table()
        
        # Get history records (all records for server-side rendering)
        records = CodeGenerationHistory.get_all()
        
        # Audit log
        user_manager.log_audit_event(
            user_id=session.get('user_id'),
            action='access_code_gen_history',
            details="Accessed code generation history page",
            ip_address=request.remote_addr
        )
        
        return render_template('code_generator_history.html',
                             history=records,
                             page_title="Code Generation History")
    except Exception as e:
        logger.error(f"Error loading history page: {str(e)}")
        return render_template('500.html'), 500


@code_generator_bp.route('/api/history')
@login_required
def get_history():
    """Get code generation history"""
    try:
        limit = int(request.args.get('limit', 50))
        offset = int(request.args.get('offset', 0))
        project_name = request.args.get('project_name')
        
        # Create table if doesn't exist
        CodeGenerationHistory.create_table()
        
        # Get history records
        records = CodeGenerationHistory.get_all(
            limit=limit,
            offset=offset,
            project_name=project_name
        )
        
        return jsonify({
            "success": True,
            "history": [r.to_dict() for r in records],
            "count": len(records)
        })
        
    except Exception as e:
        logger.error(f"Error getting history: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@code_generator_bp.route('/api/history/stats')
@login_required
def get_history_stats():
    """Get statistics about code generation"""
    try:
        # Create table if doesn't exist
        CodeGenerationHistory.create_table()
        
        stats = CodeGenerationHistory.get_stats()
        
        return jsonify({
            "success": True,
            "stats": stats
        })
        
    except Exception as e:
        logger.error(f"Error getting stats: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@code_generator_bp.route('/api/history/<int:history_id>')
@login_required
def get_history_detail(history_id):
    """Get detailed information about a specific generation"""
    try:
        record = CodeGenerationHistory.get_by_id(history_id)
        
        if not record:
            return jsonify({
                "success": False,
                "error": "History record not found"
            }), 404
        
        return jsonify({
            "success": True,
            "history": record.to_dict()
        })
        
    except Exception as e:
        logger.error(f"Error getting history detail: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@code_generator_bp.route('/api/read-code')
@login_required
def read_code_file():
    """Read generated code file"""
    try:
        import os
        
        file_path = request.args.get('file')
        
        if not file_path:
            return jsonify({
                "success": False,
                "error": "No file path provided"
            }), 400
        
        # Security check: ensure file is within allowed directory
        uploads_dir = os.path.abspath('uploads/projects')
        abs_file_path = os.path.abspath(file_path)
        
        if not abs_file_path.startswith(uploads_dir):
            return jsonify({
                "success": False,
                "error": "Access denied: Invalid file path"
            }), 403
        
        # Check if file exists
        if not os.path.exists(abs_file_path):
            return jsonify({
                "success": False,
                "error": "File not found"
            }), 404
        
        # Read file content
        with open(abs_file_path, 'r', encoding='utf-8') as f:
            code = f.read()
        
        # Audit log
        user_manager.log_audit_event(
            user_id=session.get('user_id'),
            action='read_generated_code',
            details=f"Viewed generated code file: {file_path}",
            ip_address=request.remote_addr
        )
        
        return jsonify({
            "success": True,
            "code": code,
            "file_path": file_path
        })
        
    except Exception as e:
        logger.error(f"Error reading code file: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@code_generator_bp.route('/api/save-code', methods=['POST'])
@login_required
def save_code_file():
    """Save generated code file"""
    try:
        import os
        
        data = request.get_json()
        
        if not data:
            return jsonify({
                "success": False,
                "error": "No data provided"
            }), 400
        
        file_path = data.get('file')
        code = data.get('code')
        
        if not file_path or code is None:
            return jsonify({
                "success": False,
                "error": "File path and code are required"
            }), 400
        
        # Security check: ensure file is within allowed directory
        uploads_dir = os.path.abspath('uploads/projects')
        abs_file_path = os.path.abspath(file_path)
        
        if not abs_file_path.startswith(uploads_dir):
            return jsonify({
                "success": False,
                "error": "Access denied: Invalid file path"
            }), 403
        
        # Check if file exists
        if not os.path.exists(abs_file_path):
            return jsonify({
                "success": False,
                "error": "File not found"
            }), 404
        
        # Save file content
        with open(abs_file_path, 'w', encoding='utf-8') as f:
            f.write(code)
        
        # Audit log
        user_manager.log_audit_event(
            user_id=session.get('user_id'),
            action='save_generated_code',
            details=f"Saved changes to generated code file: {file_path}",
            ip_address=request.remote_addr
        )
        
        return jsonify({
            "success": True,
            "message": "Code saved successfully",
            "file_path": file_path
        })
        
    except Exception as e:
        logger.error(f"Error saving code file: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


# Error handlers
@code_generator_bp.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    return render_template('404.html'), 404


@code_generator_bp.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    logger.error(f"Internal error in code generator routes: {str(error)}")
    return render_template('500.html'), 500

