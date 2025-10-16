"""
Background task handler for Text2SQL application.
Handles tasks that need to run asynchronously without blocking the main request.
"""

import logging
from threading import Thread

# Initialize logger
logger = logging.getLogger('text2sql')

class BackgroundTaskManager:
    """Manages background tasks for the application"""
    
    def __init__(self, sql_manager, user_manager):
        """Initialize with required managers"""
        self.sql_manager = sql_manager
        self.user_manager = user_manager
    
    def process_query_task(self, query_id, query, workspace_name, selected_workspaces, 
                         explicit_tables, user_id, query_progress, update_progress_func, query_progress_lock=None, ip_address=None):
        """
        Process a SQL query in the background
        
        Args:
            query_id (str): Unique ID for this query
            query (str): The natural language query to process
            workspace_name (str): Name of the workspace
            selected_workspaces (list): List of workspace objects
            explicit_tables (list): Tables explicitly specified by the user
            user_id (int): ID of the user who initiated the query (None if not logged in)
            query_progress (dict): Dictionary to store query progress
            update_progress_func (function): Function to update progress
            query_progress_lock (threading.Lock, optional): Lock for thread-safe access to query_progress
            ip_address (str, optional): IP address of the client making the request
        """
        # Create a new thread for processing
        def process_in_background():
            try:
                result = self.sql_manager.process_query(
                    query, 
                    selected_workspaces, 
                    explicit_tables,
                    progress_callback=lambda step: update_progress_func(query_id, step)
                )
                
                if query_progress_lock:
                    with query_progress_lock:
                        query_progress[query_id]['result'] = result
                        query_progress[query_id]['status'] = 'completed'
                else:
                    query_progress[query_id]['result'] = result
                    query_progress[query_id]['status'] = 'completed'
                
                # Log audit for the query
                if user_id:
                    self.user_manager.log_audit_event(
                        user_id=user_id,
                        action='execute_query',
                        details=f"Executed query in workspace: {workspace_name}",
                        query_text=query,
                        sql_query=result.get('sql', ''),
                        response=str(result.get('results', '')),
                        ip_address=ip_address
                    )
                    
            except Exception as e:
                logger.exception(f"Exception while processing query: {str(e)}")
                if query_progress_lock:
                    with query_progress_lock:
                        query_progress[query_id]['error'] = str(e)
                        query_progress[query_id]['status'] = 'error'
                else:
                    query_progress[query_id]['error'] = str(e)
                    query_progress[query_id]['status'] = 'error'
                
                # Log audit for failed query
                if user_id:
                    self.user_manager.log_audit_event(
                        user_id=user_id,
                        action='query_error',
                        details=f"Query error: {str(e)}",
                        query_text=query,
                        sql_query=None,
                        response=None,
                        ip_address=ip_address
                    )
        
        # Start the thread
        Thread(target=process_in_background).start()