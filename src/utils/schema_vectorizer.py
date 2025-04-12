"""
Schema Vectorizer for Text2SQL application.
Handles embedding database schema metadata into vector store.
"""

import logging
import os
import time
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import numpy as np

from src.utils.vector_store import VectorStore
from src.utils.schema_manager import SchemaManager
from src.utils.llm_engine import LLMEngine

logger = logging.getLogger('text2sql.schema_vectorizer')

class SchemaVectorizer:
    """Handles embedding database schema metadata into vector store"""
    
    def __init__(self):
        """Initialize the schema vectorizer"""
        self.logger = logging.getLogger('text2sql.schema_vectorizer')
        self.logger.info("Initializing Schema Vectorizer")
        
        # Initialize vector store
        self.vector_store = VectorStore()
        self.vector_store.connect()
        # Create a separate collection for schema metadata
        self.vector_store.init_collection('schema_metadata')
        
        # Initialize schema manager
        self.schema_manager = SchemaManager()
        
        # Initialize LLM engine for embeddings
        self.llm_engine = LLMEngine()
        
        # Track processed metadata
        self.processed_count = 0
    
    def process_schema_metadata(self) -> bool:
        """Process and embed all schema metadata
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            self.logger.info("Starting schema metadata processing")
            start_time = time.time()
            
            # Get all workspaces
            workspaces = self.schema_manager.get_workspaces()
            
            total_columns = 0
            processed_columns = 0
            
            # Process each workspace
            for workspace in workspaces:
                workspace_name = workspace.get("name")
                workspace_description = workspace.get("description", "")
                
                self.logger.info(f"Processing workspace: {workspace_name}")
                
                # Get all tables for workspace
                tables = self.schema_manager.get_tables(workspace_name)
                
                # Process each table
                for table in tables:
                    table_name = table.get("name")
                    table_description = table.get("description", "")
                    
                    # Get columns for the table
                    columns = table.get("columns", [])
                    total_columns += len(columns)
                    
                    # Process each column
                    for column in columns:
                        column_name = column.get("name")
                        column_datatype = column.get("datatype", "")
                        column_description = column.get("description", "")
                        is_primary = column.get("is_primary_key", False)
                        
                        # Create a document for embedding
                        metadata_text = self._format_metadata_for_embedding(
                            workspace_name, 
                            table_name, 
                            column_name, 
                            column_datatype, 
                            table_description, 
                            column_description, 
                            is_primary
                        )
                        
                        # Embed and store the metadata
                        self._embed_and_store_metadata(
                            workspace_name,
                            table_name,
                            column_name,
                            metadata_text
                        )
                        
                        processed_columns += 1
            
            elapsed_time = time.time() - start_time
            self.logger.info(f"Schema metadata processing completed: {processed_columns} columns processed in {elapsed_time:.2f} seconds")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error processing schema metadata: {str(e)}", exc_info=True)
            return False
    
    def _format_metadata_for_embedding(self, workspace: str, table: str, column: str, 
                                      datatype: str, table_description: str, 
                                      column_description: str, is_primary: bool) -> str:
        """Format schema metadata into a standardized text for embedding
        
        Args:
            workspace: Workspace/database name
            table: Table name
            column: Column name
            datatype: Column datatype
            table_description: Table description
            column_description: Column description
            is_primary: Whether the column is a primary key
            
        Returns:
            str: Formatted metadata text
        """
        primary_key_text = "primary key" if is_primary else ""
        
        # Create a text representation of the metadata that's optimized for embedding
        return f"""
Database: {workspace}
Table: {table}
Table Description: {table_description}
Column: {column}
Datatype: {datatype}
{primary_key_text}
Description: {column_description}
        """.strip()
    
    def _embed_and_store_metadata(self, workspace: str, table: str, column: str, metadata_text: str) -> bool:
        """Embed metadata text and store in vector database
        
        Args:
            workspace: Workspace/database name
            table: Table name
            column: Column name
            metadata_text: Formatted metadata text
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Get embedding for metadata text
            embedding = self._get_embedding(metadata_text)
            
            # Create identifier for this metadata
            metadata_id = self.processed_count
            self.processed_count += 1
            
            # Store metadata in vector database
            metadata = {
                "workspace": workspace,
                "table": table,
                "column": column,
                "text": metadata_text
            }
            
            result = self.vector_store.insert_embedding(
                'schema_metadata',
                metadata_id,
                embedding,
                metadata_text,
                metadata
            )
            
            if not result:
                self.logger.warning(f"Failed to insert embedding for {workspace}.{table}.{column}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error embedding schema metadata: {str(e)}", exc_info=True)
            return False
    
    # _get_embedding_model method has been moved to LLMEngine class
    
    def _get_embedding(self, text: str) -> List[float]:
        """Get embedding for text using the centralized LLM engine
        
        Args:
            text: Text to embed
            
        Returns:
            List[float]: Vector embedding
        """
        # Use the centralized LLM engine to generate embeddings
        embedding = self.llm_engine.generate_embedding(text)
        
        # Convert to list if it's a numpy array
        if isinstance(embedding, np.ndarray):
            return embedding.tolist()
        return embedding
    
    def search_schema_metadata(self, query: str, limit: int = 10, 
                              filter_workspace: Optional[str] = None) -> List[Dict[str, Any]]:
        """Search for schema metadata matching the query
        
        Args:
            query: Search query
            limit: Maximum number of results to return
            filter_workspace: Optional workspace to filter results by
            
        Returns:
            List[Dict]: List of matching schema metadata
        """
        try:
            # Get embedding for query
            query_embedding = self._get_embedding(query)
            
            # Create filter expression if workspace is specified
            filter_expr = None
            if filter_workspace:
                filter_expr = f"workspace == '{filter_workspace}'"
            
            # Search for similar vectors
            results = self.vector_store.search_similar(
                'schema_metadata',
                query_embedding,
                limit=limit,
                filter_expr=filter_expr
            )
            
            return results
            
        except Exception as e:
            self.logger.error(f"Error searching schema metadata: {str(e)}", exc_info=True)
            return []

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about schema metadata in the vector database
        
        Returns:
            Dict: Statistics including total databases, tables, columns, etc.
        """
        try:
            # Query the vector database for stats
            stats = {}
            
            # Get total count of vectors in the schema_metadata collection
            count = self.vector_store.count('schema_metadata')
            if count == 0:
                return None
            
            # Get unique workspaces (databases)
            workspaces = set()
            tables = set()
            
            # Get metadata entries (up to 1000 for stats purposes)
            entries = self.vector_store.list_entries('schema_metadata', limit=1000)
            
            for entry in entries:
                metadata = entry.get('metadata', {})
                if metadata:
                    workspace = metadata.get('workspace')
                    table = metadata.get('table')
                    if workspace:
                        workspaces.add(workspace)
                    if table:
                        tables.add(f"{workspace}.{table}")
            
            # Build stats dictionary
            stats = {
                'total_databases': len(workspaces),
                'total_tables': len(tables),
                'total_columns': count,
                'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M')
            }
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Error getting metadata stats: {str(e)}", exc_info=True)
            return None
            
    def filter_with_llm(self, query: str, limit: int = 100) -> Tuple[List[Dict[str, Any]], str]:
        """Use LLM to extract schema filters from query and search filtered results
        
        Args:
            query: User query
            limit: Maximum number of results
            
        Returns:
            Tuple[List[Dict], str]: Search results and the filter expression used
        """
        try:
            # Ask LLM to extract database/table/column names from query
            extraction_prompt = f"""
Extract any database names, table names, and column names from this query:
"{query}"

Return as JSON with these fields (leave empty if not found):
{{
  "database": "",
  "table": "",
  "column": ""
}}
            """
            
            # Converting the prompt to the format expected by generate_completion
            formatted_prompt = [
                {"role": "system", "content": "Extract database schema entities from the query and return results as JSON."},
                {"role": "user", "content": extraction_prompt}
            ]
            
            extraction_result = self.llm_engine.generate_completion(formatted_prompt, log_prefix="Schema Entity Extraction")
            self.logger.info(f"LLM extraction result: {extraction_result}")
            # Parse extraction results (assuming JSON response from LLM)
            try:
                import json
                filters = json.loads(extraction_result)
            except:
                # Fallback if LLM doesn't return valid JSON
                self.logger.warning("LLM didn't return valid JSON, using fallback extraction")
                filters = {
                    "database": "",
                    "table": "",
                    "column": ""
                }
                
            # Build filter expression based on extracted entities
            filter_parts = []
            if filters.get("database"):
                filter_parts.append(f"workspace == '{filters['database']}'")
            if filters.get("table"):
                filter_parts.append(f"table == '{filters['table']}'")
            if filters.get("column"):
                filter_parts.append(f"column == '{filters['column']}'")
                
            filter_expr = " && ".join(filter_parts) if filter_parts else None

            self.logger.info(f"Filter expression generated: {filter_expr}")
            
            # Initial search attempt (potentially filtered)
            results = self.vector_store.search_similar(
                'schema_metadata',
                self._get_embedding(query),
                limit=limit,
                filter_expr=filter_expr,
                output_fields=["id", "text", "metadata"]
            )

            # If filters were applied and no results were found, try again without filters
            if filter_expr and not results:
                self.logger.info(f"No results found with filter '{filter_expr}'. Retrying without filter.")
                results = self.vector_store.search_similar(
                    'schema_metadata',
                    self._get_embedding(query),
                    limit=limit,
                    filter_expr=None,  # Perform unfiltered search
                    output_fields=["id", "text", "metadata"]
                )
                
            
            return results, filter_expr
            
        except Exception as e:
            self.logger.error(f"Error filtering with LLM: {str(e)}", exc_info=True)
            # Attempt a basic search as a fallback on error during filtering
            try:
                self.logger.info("Performing fallback unfiltered search due to LLM filtering error.")
                results = self.vector_store.search_similar(
                    'schema_metadata',
                    self._get_embedding(query),
                    limit=limit,
                    filter_expr=None,
                    output_fields=["id", "text", "metadata"]
                )
                return results, None # Indicate no filter was successfully applied
            except Exception as fallback_e:
                self.logger.error(f"Fallback search also failed: {str(fallback_e)}", exc_info=True)
                return [], None
