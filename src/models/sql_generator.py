from src.agents.intent_agent import IntentAgent
from src.agents.table_agent import TableAgent
from src.agents.column_agent import ColumnAgent
from src.utils.azure_client import AzureAIClient
from src.utils.database import DatabaseManager
from src.utils.schema_manager import SchemaManager
from src.utils.feedback_manager import FeedbackManager
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
        self.feedback_manager = FeedbackManager()
        self.logger = logging.getLogger('text2sql.sql_generator')
        
    def process_query(self, query, workspaces=None, explicit_tables=None, progress_callback=None):
        """Process a natural language query through the full pipeline
        
        Args:
            query (str): The natural language query from the user
            workspaces (list, optional): List of workspace dictionaries
            explicit_tables (list, optional): List of tables explicitly selected by the user
            progress_callback (callable, optional): Callback function for progress updates
            
        Returns:
            dict: Processing results including SQL, explanation, and charts
        """
        start_time = time.time()
        self.logger.info(f"Processing query: '{query}'")
        
        if explicit_tables:
            self.logger.info(f"User explicitly selected tables: {', '.join(explicit_tables)}")
            
        # Step 1: Detect user intent
        intent_result = self.intent_agent.detect_intent(query)
        intent = intent_result["intent"]
        self.logger.info(f"Detected intent: {intent}")
        
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
        
        # Add intent identification step to the steps list
        if progress_callback:
            step_info = {
                "step": "intent_identification",
                "description": "Identifying query intent",
                "result": f"Detected intent: {intent}"
            }
            response["steps"].append(step_info)
            progress_callback(step_info)
        
        # Step 2: Process based on intent
        if intent == "data_retrieval":
            # For data retrieval, go through full SQL generation pipeline
            sql_result = self._generate_sql(query, workspaces, explicit_tables, progress_callback)
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
        
    def _generate_sql(self, query, workspaces=None, explicit_tables=None, progress_callback=None):
        """Generate SQL for a data retrieval query
        
        Args:
            query (str): The natural language query
            workspaces (list, optional): List of workspace dictionaries
            explicit_tables (list, optional): List of tables explicitly selected by the user
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
        
        # Step 3: Select relevant tables - either from user selection or using Table Agent
        if explicit_tables and len(explicit_tables) > 0:
            # If user explicitly selected tables, use those
            relevant_tables = explicit_tables
            
            step_info = {
                "step": "table_selection",
                "description": "Using explicitly selected tables",
                "result": ", ".join(relevant_tables)
            }
            result["steps"].append(step_info)
            if progress_callback:
                progress_callback(step_info)
        else:
            # Otherwise use the TableAgent to determine relevant tables
            relevant_tables = self.table_agent.get_relevant_tables(query, workspace_name)
            
            step_info = {
                "step": "table_selection",
                "description": "Automatically selecting relevant tables",
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

        # Step 5: Get join conditions if multiple tables involved
        join_conditions = []
        if len(relevant_tables) > 1:
            join_conditions = self.schema_manager.get_join_conditions(relevant_tables, workspace_name)
            
            if join_conditions:
                join_info = "\n".join([
                    f"- Join between {join['left_table']} and {join['right_table']}: "
                    f"{join['join_type']} JOIN on {join['condition']}"
                    for join in join_conditions
                ])
                
                step_info = {
                    "step": "join_conditions",
                    "description": "Identifying table join conditions",
                    "result": join_info
                }
                result["steps"].append(step_info)
                if progress_callback:
                    progress_callback(step_info)
                    
                self.logger.info(f"Found {len(join_conditions)} join conditions for the relevant tables")
            else:
                self.logger.info("No pre-defined join conditions found for the selected tables")
        
        # Step 6: Get example queries
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
                    
                # Add join example if we have join conditions
                if join_conditions and len(relevant_tables) > 1:
                    join_example = self.generate_join_example(join_conditions[0], workspace_name)
                    if join_example:
                        examples.append(join_example)
                        
        # Step 6b: Find similar successful queries from feedback database using reranking
        # First get top 10 candidates with vector search, then rerank them to get top 2
        similar_queries = self.feedback_manager.find_similar_queries_with_reranking(query, limit=1)
        
        if similar_queries:
            # Add these as high-quality examples for the AI model
            self.logger.info(f"Found {len(similar_queries)} similar queries with reranking")
            
            step_info = {
                "step": "feedback_search",
                "description": "Finding similar successful queries with reranking",
                "result": f"Found {len(similar_queries)} similar queries after two-stage search"
            }
            result["steps"].append(step_info)
            if progress_callback:
                progress_callback(step_info)
                
            # Add successful queries as examples with a source tag
            for idx, similar_query in enumerate(similar_queries):
                source_type = "manual" if similar_query.get("is_manual_sample") else "feedback"
                rerank_score = similar_query.get('rerank_score', similar_query.get('similarity', 0))
                
                examples.append({
                    "question": similar_query["query_text"],
                    "sql": similar_query["sql_query"],
                    "source": source_type,  # Tag with appropriate source type
                    "score": f"{rerank_score:.4f}"  # Add the reranker score for logging
                })
                self.logger.info(f"Added similar query #{idx+1} from {source_type} (score: {rerank_score:.4f}): {similar_query['query_text'][:50]}...")
                
        # Step 7: Generate SQL using Azure AI with join conditions included
        sql_result = self.ai_client.generate_sql(query, pruned_schema, examples, join_conditions)
        
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
        
        # Step 8: Execute SQL if present and generate chart data
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
                        
                        # Create execution step info
                        step_info = {
                            "step": "query_execution",
                            "description": "Executing SQL query",
                            "result": f"Query returned {query_result['row_count']} rows"
                        }
                        
                        # Add the step info
                        result["steps"].append(step_info)
                        if progress_callback:
                            progress_callback(step_info)
                        
                        # Step 9: Analyze query results for dashboard potential as a separate step
                        if query_result["row_count"] > 0:
                            self.logger.info("Analyzing query results for dashboard potential")
                            try:
                                # Get a sample of data for analysis (up to 5 rows)
                                data_sample = result["chart_data"]["data"][:5]
                                
                                # Call AI to analyze dashboard potential
                                dashboard_analysis = self.ai_client.analyze_for_dashboard(
                                    query=query, 
                                    sql=result["sql"],
                                    columns=query_result["columns"],
                                    data_sample=data_sample
                                )
                                
                                # Add dashboard recommendations to result
                                result["chart_data"]["dashboard_recommendations"] = dashboard_analysis
                                
                                # Create dashboard analysis step info
                                dashboard_suitable = dashboard_analysis.get('is_suitable', False)
                                self.logger.info(f"Dashboard analysis completed: suitable={dashboard_suitable}")
                                
                                step_result = "Data is suitable for visualization\n" if dashboard_suitable else "Data is not suitable for visualization"
                                if dashboard_suitable:
                                    chart_type = dashboard_analysis.get('chart_type', '')
                                    step_result += f" - Recommended chart type: {chart_type}\n"
                                    step_result += f" - Recommended x axis: {dashboard_analysis.get('x_axis','').get('column', '')}\n"
                                    step_result += f" - Recommended y axis: {dashboard_analysis.get('y_axis','').get('column', '')}"
                                
                                dashboard_step_info = {
                                    "step": "dashboard_analysis",
                                    "description": "Analyzing data for dashboard potential",
                                    "result": step_result
                                }
                                
                                result["steps"].append(dashboard_step_info)
                                if progress_callback:
                                    progress_callback(dashboard_step_info)
                                
                            except Exception as e:
                                self.logger.error(f"Error during dashboard analysis: {str(e)}")
                                # Don't fail the whole query if dashboard analysis fails
                                result["chart_data"]["dashboard_recommendations"] = {
                                    "is_suitable": False,
                                    "reason": f"Error during analysis: {str(e)}"
                                }
                                
                                # Add error step for dashboard analysis
                                error_step_info = {
                                    "step": "dashboard_analysis",
                                    "description": "Analyzing data for dashboard potential",
                                    "result": f"Error: {str(e)}"
                                }
                                result["steps"].append(error_step_info)
                                if progress_callback:
                                    progress_callback(error_step_info)
                        
                    else:
                        # Create execution step info for no rows
                        step_info = {
                            "step": "query_execution",
                            "description": "Executing SQL query",
                            "result": "Query executed successfully with no rows returned"
                        }
                        
                        # Add the step info
                        result["steps"].append(step_info)
                        if progress_callback:
                            progress_callback(step_info)
                else:
                    # Create execution step info for error
                    result["error"] = query_result["error"]
                    step_info = {
                        "step": "query_execution",
                        "description": "Executing SQL query",
                        "result": f"Error: {query_result['error']}"
                    }
                    
                    # Add the step info
                    result["steps"].append(step_info)
                    if progress_callback:
                        progress_callback(step_info)
                    
            except Exception as e:
                result["error"] = f"Error executing query: {str(e)}"
                self.logger.error(f"Query execution error: {str(e)}", exc_info=True)
                
                # Add error step for exception
                error_step_info = {
                    "step": "query_execution",
                    "description": "Executing SQL query",
                    "result": f"Error: {str(e)}"
                }
                result["steps"].append(error_step_info)
                if progress_callback:
                    progress_callback(error_step_info)
        
        processing_time = time.time() - start_time
        self.logger.info(f"SQL generation completed in {processing_time:.2f}s")
        return result
    
    def generate_join_example(self, join_condition, workspace_name=None):
        """Generate an example query using the join condition
        
        Args:
            join_condition (dict): Join condition dictionary
            workspace_name (str, optional): Workspace name for context
            
        Returns:
            dict: Example query with question and SQL
        """
        try:
            left_table = join_condition.get("left_table", "")
            right_table = join_condition.get("right_table", "")
            join_type = join_condition.get("join_type", "INNER")
            condition = join_condition.get("condition", "")
            
            # Get primary key columns for representative selection
            left_cols = self.schema_manager.get_columns(left_table, workspace_name)
            right_cols = self.schema_manager.get_columns(right_table, workspace_name)
            
            # Select a few columns for a representative query
            left_col = next((col["name"] for col in left_cols if not col.get("is_primary_key")), None)
            left_col = left_col or (left_cols[0]["name"] if left_cols else "id")
            
            right_col = next((col["name"] for col in right_cols if not col.get("is_primary_key")), None)
            right_col = right_col or (right_cols[0]["name"] if right_cols else "id")
            
            # Create a simple example query using the join
            sql = f"""SELECT {left_table}.{left_col}, {right_table}.{right_col}
FROM {left_table}
{join_type} JOIN {right_table} ON {condition}
LIMIT 5"""
            
            return {
                "question": f"Show some data from {left_table} and {right_table}",
                "sql": sql
            }
        except Exception as e:
            self.logger.warning(f"Could not generate join example: {str(e)}")
            return None
    
    def close(self):
        """Close all connections"""
        self.logger.info("Closing all agent connections")
        self.intent_agent.close()
        self.table_agent.close()
        self.column_agent.close()
        self.ai_client.close()
        self.db_manager.close()
        self.feedback_manager.close()