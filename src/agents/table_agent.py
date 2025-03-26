from src.utils.schema_manager import SchemaManager
from src.utils.llm_engine import LLMEngine
from azure.ai.inference.models import SystemMessage, UserMessage
import logging
import time
import json

class TableAgent:
    """Agent for identifying relevant tables for a user's query"""
    
    def __init__(self):
        """Initialize the table agent"""
        self.llm_engine = LLMEngine()
        self.schema_manager = SchemaManager()
        self.logger = logging.getLogger('text2sql.agents.table')
        
    def get_relevant_tables(self, query, workspace_name=None):
        """Identify tables that are relevant to the user's query
        
        Args:
            query (str): The natural language query from the user
            workspace_name (str, optional): Name of workspace to search in
            
        Returns:
            list: List of relevant table names
        """
        start_time = time.time()
        self.logger.info(f"Table selection started for query: '{query}'")
        
        # Get tables with their descriptions from schema manager
        all_tables = self.schema_manager.get_tables(workspace_name)
        table_names = [t["name"] for t in all_tables]
        
        self.logger.info(f"Available tables ({len(table_names)}): {', '.join(table_names)}")
        
        if not table_names:
            self.logger.warning("No tables available for selection")
            return []
            
        # If only a few tables, return all of them
        if len(table_names) <= 3:
            self.logger.info(f"Less than or equal to 3 tables available, returning all: {', '.join(table_names)}")
            return table_names
            
        # Format tables with descriptions for better context
        tables_info = []
        for table in all_tables:
            table_info = f"{table['name']}: {table.get('description', 'No description available')}"
            tables_info.append(table_info)
            
        tables_list = "\n".join(tables_info)
            
        messages = [
            SystemMessage("""You are a table selection agent for a Text-to-SQL system.
Your job is to identify which database tables are most relevant to a user query.
You will be provided with table names and their descriptions.
Return ONLY the names of relevant tables, separated by commas. Be selective and choose
only the tables that are directly needed to answer the query. If you're unsure,
include tables that might be related. Return only table names in your response."""),
            UserMessage(f"Available tables:\n{tables_list}\n\nUser query: {query}")
        ]
        
        try:
            self.logger.info("Sending request to AI model for table selection")
            
            # Use LLMEngine for centralized LLM interaction
            raw_response = self.llm_engine.generate_completion(messages, log_prefix="TABLE")
            raw_response = raw_response.strip()
            self.logger.info(f"Raw model response: '{raw_response}'")
            
            table_names = raw_response.split(",")
            table_names = [t.strip() for t in table_names]
            
            # Validate the table names
            original_count = len(table_names)
            valid_names = set([t["name"] for t in all_tables])
            table_names = [t for t in table_names if t in valid_names]
            filtered_count = len(table_names)
            
            if original_count != filtered_count:
                self.logger.warning(f"Model suggested {original_count - filtered_count} invalid tables that were filtered out")
            
            if not table_names:
                self.logger.warning("No valid tables selected by the model, defaulting to first table")
                result = [all_tables[0]["name"]]
            else:
                result = table_names
                
            processing_time = time.time() - start_time
            self.logger.info(f"Table selection completed in {processing_time:.2f}s. Selected: {', '.join(result)}")
            return result
            
        except Exception as e:
            processing_time = time.time() - start_time
            self.logger.error(f"Table selection error after {processing_time:.2f}s: {str(e)}", exc_info=True)
            # Default to first few tables on error
            result = [t["name"] for t in all_tables[:3]]
            self.logger.warning(f"Defaulting to first 3 tables due to error: {', '.join(result)}")
            return result
    
    def get_table_details(self, tables, workspace_name=None):
        """Get detailed information about selected tables
        
        Args:
            tables (list): List of selected table names
            workspace_name (str, optional): Name of workspace to search in
            
        Returns:
            str: Focused schema information for selected tables
        """
        self.logger.info(f"Getting schema details for tables: {', '.join(tables)}")
        
        if not tables:
            self.logger.warning("No tables provided, returning full schema")
            return self.schema_manager.format_schema_for_display(workspace_name)
        
        return self.schema_manager.format_schema_for_display(workspace_name, tables)
            
    def close(self):
        """Close the LLM engine connection"""
        self.logger.info("Closing table agent's LLM engine connection")
        self.llm_engine.close()