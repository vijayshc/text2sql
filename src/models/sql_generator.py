from src.agents.intent_agent import IntentAgent
from src.agents.table_agent import TableAgent
from src.agents.column_agent import ColumnAgent
from src.utils.azure_client import AzureAIClient
from src.utils.database import DatabaseManager
from src.utils.schema_manager import SchemaManager
import logging
import time

class SQLGenerationManager:
    """Manager class for coordinating the Text-to-SQL pipeline"""
    
    def __init__(self):
        """Initialize the SQL Generation Manager"""
        self.intent_agent = IntentAgent()
        self.table_agent = TableAgent()
        self.column_agent = ColumnAgent()
        self.ai_client = AzureAIClient()
        self.db_manager = DatabaseManager()
        self.schema_manager = SchemaManager()
        self.logger = logging.getLogger('text2sql.sql_generator')
        
    def process_query(self, query, workspaces=None, progress_callback=None):
        """Process a natural language query through the full pipeline
        
        Args:
            query (str): The natural language query from the user
            workspaces (list, optional): List of workspace dictionaries
            progress_callback (callable, optional): Callback function for progress updates
            
        Returns:
            dict: Processing results including SQL, explanation, and charts
        """
        start_time = time.time()
        self.logger.info(f"Processing query: '{query}'")
        
        # Step 1: Detect user intent
        intent_result = self.intent_agent.detect_intent(query)
        intent = intent_result["intent"]
        self.logger.info(f"Detected intent: {intent}")
        
        if progress_callback:
            progress_callback({
                "step": "intent_detection",
                "description": "Analyzing query intent",
                "result": f"Detected intent: {intent}"
            })
        
        # Initialize response structure
        response = {
            "intent": intent,
            "query": query,
            "sql": "",
            "explanation": "",
            "error": None,
            "steps": [],
            "chart_data": None
        }
        
        # Step 2: Process based on intent
        if intent == "data_retrieval":
            # For data retrieval, go through full SQL generation pipeline
            sql_result = self._generate_sql(query, workspaces, progress_callback)
            response.update(sql_result)
            
        elif intent == "schema_exploration":
            # For schema exploration, return schema information
            self.logger.info("Processing schema exploration request")
            workspace_name = workspaces[0]["name"] if workspaces else None
            
            if progress_callback:
                progress_callback({
                    "step": "schema_exploration",
                    "description": "Retrieving schema information",
                    "result": None
                })
            
            schema = self.schema_manager.format_schema_for_display(workspace_name)
            response["explanation"] = f"Here's the database schema:\n\n{schema}"
                
        elif intent == "metadata_request":
            # For metadata requests, provide database metadata
            self.logger.info("Processing metadata request")
            workspace_name = workspaces[0]["name"] if workspaces else None
            
            if progress_callback:
                progress_callback({
                    "step": "metadata_retrieval",
                    "description": "Retrieving database metadata",
                    "result": None
                })
            
            # Get metadata from schema manager
            tables = self.schema_manager.get_tables(workspace_name)
            total_columns = sum(len(table.get("columns", [])) for table in tables)
            
            metadata = [
                f"Database Overview:",
                f"- Total tables: {len(tables)}",
                f"- Total columns: {total_columns}",
                "\nTables:"
            ]
            
            for table in tables:
                col_count = len(table.get("columns", []))
                pk_count = len([c for c in table.get("columns", []) if c.get("is_primary_key")])
                metadata.append(f"- {table['name']}: {col_count} columns ({pk_count} primary keys)")
                
            response["explanation"] = "\n".join(metadata)
                
        else:  # general_question
            # For general questions, provide a general response
            response["explanation"] = ("I can help you query your database. Try asking a specific question "
                                    "about your data, and I'll generate the SQL for you.")
        
        processing_time = time.time() - start_time
        self.logger.info(f"Query processing completed in {processing_time:.2f}s")
        return response
        
    def _generate_sql(self, query, workspaces=None, progress_callback=None):
        """Generate SQL for a data retrieval query
        
        Args:
            query (str): The natural language query
            workspaces (list, optional): List of workspace dictionaries
            progress_callback (callable, optional): Callback function for progress updates
            
        Returns:
            dict: SQL generation results
        """
        start_time = time.time()
        self.logger.info("Starting SQL generation process")
        
        result = {
            "sql": "",
            "explanation": "",
            "error": None,
            "steps": [],
            "chart_data": None
        }
        
        # Step 1: Connect to database for query execution
        if not self.db_manager.connect():
            result["error"] = "Could not connect to database."
            return result
            
        # Step 2: Determine relevant workspace(s)
        workspace_name = None
        if workspaces:
            if len(workspaces) > 1:
                relevant_workspace_names = self.intent_agent.determine_relevant_workspaces(query, workspaces)
                workspace_name = relevant_workspace_names[0] if relevant_workspace_names else None
                
                step_info = {
                    "step": "workspace_selection",
                    "description": "Selecting relevant workspace(s)",
                    "result": ", ".join(relevant_workspace_names)
                }
                result["steps"].append(step_info)
                if progress_callback:
                    progress_callback(step_info)
            else:
                workspace_name = workspaces[0]["name"]
        
        # Step 3: Select relevant tables using Table Agent
        relevant_tables = self.table_agent.get_relevant_tables(query, workspace_name)
        
        step_info = {
            "step": "table_selection",
            "description": "Selecting relevant tables",
            "result": ", ".join(relevant_tables)
        }
        result["steps"].append(step_info)
        if progress_callback:
            progress_callback(step_info)
        
        if not relevant_tables:
            result["error"] = "Could not identify relevant tables for the query"
            return result
        
        # Step 4: Get detailed schema for selected tables with column pruning
        pruned_schema = self.column_agent.prune_columns(query, relevant_tables, workspace_name)
        
        step_info = {
            "step": "schema_preparation",
            "description": "Selecting relevant columns",
            "result": pruned_schema
        }
        result["steps"].append(step_info)
        if progress_callback:
            progress_callback(step_info)
        
        # Step 5: Get example queries
        first_table = relevant_tables[0] if relevant_tables else None
        examples = []
        if first_table:
            table_info = self.schema_manager.get_table_by_name(first_table, workspace_name)
            if table_info:
                # Generate examples based on table structure
                examples = [
                    {
                        "question": f"How many records are in the {first_table} table?",
                        "sql": f"SELECT COUNT(*) AS record_count FROM {first_table}"
                    },
                    {
                        "question": f"Get all columns from {first_table}",
                        "sql": f"SELECT * FROM {first_table} LIMIT 5"
                    }
                ]
                
                # Add example with primary key if available
                primary_keys = [col["name"] for col in table_info["columns"] if col.get("is_primary_key")]
                if primary_keys:
                    pk = primary_keys[0]
                    examples.append({
                        "question": f"Get record from {first_table} by {pk}",
                        "sql": f"SELECT * FROM {first_table} WHERE {pk} = 1"
                    })
        
        # Step 6: Generate SQL using Azure AI
        sql_result = self.ai_client.generate_sql(query, pruned_schema, examples)
        
        result["sql"] = sql_result.get("sql", "")
        result["explanation"] = sql_result.get("explanation", "")
        
        step_info = {
            "step": "sql_generation",
            "description": "Generating SQL query",
            "result": result["sql"]
        }
        result["steps"].append(step_info)
        if progress_callback:
            progress_callback(step_info)
        
        # Step 7: Execute SQL if present and generate chart data
        if result["sql"]:
            try:
                query_result = self.db_manager.execute_query(result["sql"])
                
                if query_result["success"]:
                    if query_result["data"] is not None:
                        # Generate chart data if we have results
                        data_df = query_result["data"]
                        result["chart_data"] = {
                            "columns": query_result["columns"],
                            "data": data_df.to_dict(orient="records"),
                            "row_count": query_result["row_count"]
                        }
                        
                        step_info = {
                            "step": "query_execution",
                            "description": "Executing SQL query",
                            "result": f"Query returned {query_result['row_count']} rows"
                        }
                    else:
                        step_info = {
                            "step": "query_execution",
                            "description": "Executing SQL query",
                            "result": "Query executed successfully with no rows returned"
                        }
                else:
                    result["error"] = query_result["error"]
                    step_info = {
                        "step": "query_execution",
                        "description": "Executing SQL query",
                        "result": f"Error: {query_result['error']}"
                    }
                    
                result["steps"].append(step_info)
                if progress_callback:
                    progress_callback(step_info)
                    
            except Exception as e:
                result["error"] = f"Error executing query: {str(e)}"
                self.logger.error(f"Query execution error: {str(e)}", exc_info=True)
        
        processing_time = time.time() - start_time
        self.logger.info(f"SQL generation completed in {processing_time:.2f}s")
        return result
    
    def close(self):
        """Close all connections"""
        self.logger.debug("Closing all agent connections")
        self.intent_agent.close()
        self.table_agent.close()
        self.column_agent.close()
        self.ai_client.close()
        self.db_manager.close()