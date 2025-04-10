from src.utils.schema_manager import SchemaManager
from src.utils.llm_engine import LLMEngine
from azure.ai.inference.models import SystemMessage, UserMessage
import logging
import time
import json

class ColumnAgent:
    """Agent for pruning irrelevant columns for a user's query"""
    
    def __init__(self):
        """Initialize the column agent"""
        self.llm_engine = LLMEngine()
        self.schema_manager = SchemaManager()
        self.logger = logging.getLogger('text2sql.agents.column')
        
    def prune_columns(self, query, tables, workspace_name=None):
        """Prune irrelevant columns from the schema based on the user's query
        
        Args:
            query (str): The natural language query from the user
            tables (list): List of table names to consider
            workspace_name (str, optional): Name of workspace to search in
            
        Returns:
            str: Pruned schema with only relevant columns
        """
        start_time = time.time()
        self.logger.info(f"Column pruning started for query: '{query}'")
        self.logger.info(f"Processing tables: {', '.join(tables)}")
        
        if not tables:
            self.logger.warning("No tables provided for column pruning")
            return ""
            
        # Skip LLM call if only one table is involved - return all columns
        if len(tables) == 1:
            self.logger.info(f"Only one table involved ({tables[0]}). Skipping LLM call and including all columns.")
            return self.schema_manager.format_schema_for_display(workspace_name, tables)
        
        # Get table and column information from schema manager
        table_info = []
        for table_name in tables:
            table = self.schema_manager.get_table_by_name(table_name, workspace_name)
            if table:
                columns_info = []
                for col in table["columns"]:
                    col_info = {
                        "name": col["name"],
                        "description": col.get("description", ""),
                        "datatype": col["datatype"],
                        "is_primary_key": col.get("is_primary_key", False)
                    }
                    columns_info.append(col_info)
                
                table_info.append({
                    "name": table["name"],
                    "description": table.get("description", ""),
                    "columns": columns_info
                })
        
        if not table_info:
            self.logger.warning("No valid tables found in schema")
            return ""
            
        # Format table and column information for the prompt
        schema_text = []
        for table in table_info:
            schema_text.append(f"Table: {table['name']}")
            schema_text.append(f"Description: {table['description']}")
            schema_text.append("Columns:")
            for col in table["columns"]:
                schema_text.append(f"- {col['name']} ({col['datatype']}): {col['description']}")
            schema_text.append("")
            
        schema_formatted = "\n".join(schema_text)
        
        messages = [
            SystemMessage("""You are a column selection agent for a Text-to-SQL system.
Your job is to identify which columns from the provided tables are most relevant to a user query.
For each table, select only the columns that will be needed to answer the query.
Return your answer as a JSON object with table names as keys and arrays of column names as values.
Always include primary key columns even if not directly mentioned in the query.
Consider columns that might be needed for:
1. Selection criteria (WHERE clauses)
2. Joining tables (foreign keys)
3. Aggregations or grouping
4. Sorting or ordering
5. Final result display"""),
            UserMessage(f"Schema:\n{schema_formatted}\n\nUser query: {query}")
        ]
        
        try:
            self.logger.info("Sending request to AI model for column selection")
            
            # Use LLMEngine for centralized LLM interaction
            raw_response = self.llm_engine.generate_completion(messages, log_prefix="COLUMN")
            raw_response = raw_response.strip()
            #self.logger.info(f"Raw model response: '{raw_response}'")
            
            # Extract JSON from response
            selected_columns = self._parse_column_selection(raw_response, table_info)
            
            # Log column pruning statistics
            for table in table_info:
                table_name = table["name"]
                if table_name in selected_columns:
                    original_cols = len(table["columns"])
                    selected_cols = len(selected_columns[table_name])
                    pruned_cols = original_cols - selected_cols
                    self.logger.info(
                        f"Table '{table_name}': Pruned {pruned_cols} columns, "
                        f"kept {selected_cols}/{original_cols}"
                    )
            
            # Build pruned schema
            result = self._build_pruned_schema(table_info, selected_columns)
            
            processing_time = time.time() - start_time
            self.logger.info(f"Column pruning completed in {processing_time:.2f}s")
            return result
            
        except Exception as e:
            processing_time = time.time() - start_time
            self.logger.error(f"Column pruning error after {processing_time:.2f}s: {str(e)}", exc_info=True)
            # On error, return schema with all columns
            return self.schema_manager.format_schema_for_display(workspace_name, tables)
    
    def _parse_column_selection(self, response_text, table_info):
        """Parse the AI response to extract selected columns
        
        Args:
            response_text (str): The model's response text
            table_info (list): List of table dictionaries with column information
            
        Returns:
            dict: Dictionary mapping table names to lists of selected column names
        """
        self.logger.info("Parsing column selection from model response")
        
        try:
            # Find JSON in response
            import re
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if not json_match:
                raise ValueError("No JSON object found in response")
                
            selected_columns = json.loads(json_match.group(0))
            self.logger.info(f"Parsed column selection JSON: {json.dumps(selected_columns)}")
            
            # Create table name to columns mapping
            table_columns = {}
            for table in table_info:
                table_name = table["name"]
                if table_name in selected_columns:
                    # Get list of all column names and primary keys for this table
                    all_columns = {col["name"] for col in table["columns"]}
                    primary_keys = {col["name"] for col in table["columns"] if col["is_primary_key"]}
                    
                    # Start with selected columns that exist in the table
                    valid_columns = {
                        col for col in selected_columns[table_name]
                        if col in all_columns
                    }
                    
                    # Add primary keys if not already included
                    valid_columns.update(primary_keys)
                    
                    table_columns[table_name] = sorted(list(valid_columns))
                    
                    # Log any invalid columns that were filtered out
                    invalid_columns = set(selected_columns[table_name]) - all_columns
                    if invalid_columns:
                        self.logger.warning(
                            f"Filtered out invalid columns for table '{table_name}': "
                            f"{', '.join(invalid_columns)}"
                        )
            
            return table_columns
            
        except Exception as e:
            self.logger.error(f"Error parsing column selection: {str(e)}", exc_info=True)
            # On error, include all columns
            return {table["name"]: [col["name"] for col in table["columns"]] 
                   for table in table_info}
    
    def _build_pruned_schema(self, table_info, selected_columns):
        """Build a schema string with only selected columns
        
        Args:
            table_info (list): List of table dictionaries with column information
            selected_columns (dict): Dictionary mapping table names to selected column names
            
        Returns:
            str: Formatted schema string with only selected columns
        """
        self.logger.info("Building pruned schema")
        schema_lines = []
        
        for table in table_info:
            table_name = table["name"]
            if table_name in selected_columns:
                schema_lines.append(f"Table: {table_name}")
                if table.get("description"):
                    schema_lines.append(f"Description: {table['description']}")
                
                # Format selected columns
                column_info = []
                primary_keys = []
                
                for col in table["columns"]:
                    if col["name"] in selected_columns[table_name]:
                        # Include column description along with name and datatype
                        column_info.append(f"{col['name']} ({col['datatype']}): {col.get('description', '')}")
                        if col.get("is_primary_key"):
                            primary_keys.append(col["name"])
                
                schema_lines.append("Columns: " + ", ".join(column_info))
                
                if primary_keys:
                    schema_lines.append(f"Primary Key(s): {', '.join(primary_keys)}")
                    
                schema_lines.append("")
        
        result = "\n".join(schema_lines)
        self.logger.info(f"Built pruned schema ({len(result)} chars)")
        return result
    
    def close(self):
        """Close the LLM engine connection"""
        self.logger.info("Closing column agent's LLM engine connection")
        self.llm_engine.close()