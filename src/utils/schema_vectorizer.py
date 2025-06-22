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
                filter_expr = {"workspace": filter_workspace}
            
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
        """Use LLM to create ChromaDB filters from query and search filtered results
        
        Args:
            query: User query
            limit: Maximum number of results
            
        Returns:
            Tuple[List[Dict], str]: Search results and the filter expression used
        """
        try:
            # Ask LLM to create ChromaDB filter from query
            filter_prompt = f"""
Analyze this database query and create a ChromaDB filter in JSON format for explicitly mentioned database, table, or column names:
"{query}"

EXTRACTION RULES:
1. Extract EXPLICITLY mentioned database/table/column names from the query
2. Recognize column names that are clearly stated (e.g., "first_name", "user_id", "order_date")
3. Do NOT infer or guess names from generic descriptions
4. Use $and for specific column(s) within specific table(s)
5. Use $or for multiple alternatives (different tables OR different columns)
6. Generic terms like "customer information", "user data" are NOT explicit column names
7. But explicit names like "first_name", "last_name", "email" ARE valid column names

LOGICAL OPERATORS:
- Use $and when query asks for specific column(s) IN/FROM/WITHIN specific table(s)
- Use $or when query asks for multiple alternatives (table1 OR table2, column1 OR column2)
- Single entity (just table OR just column) doesn't need logical operators

Return a JSON object that can be used as a ChromaDB "where" clause filter.
Use these field names: "workspace", "table", "column"

Valid examples (explicit names):
- "users table" → {{"table": "users"}}
- "user_id column" → {{"column": "user_id"}}
- "phone column from customers table" → {{"$and": [{{"table": "customers"}}, {{"column": "phone"}}]}}
- "what does column phone from customers table contains" → {{"$and": [{{"table": "customers"}}, {{"column": "phone"}}]}}
- "user_id column in users table" → {{"$and": [{{"table": "users"}}, {{"column": "user_id"}}]}}
- "first_name and last_name columns" → {{"$or": [{{"column": "first_name"}}, {{"column": "last_name"}}]}}
- "users table and orders table" → {{"$or": [{{"table": "users"}}, {{"table": "orders"}}]}}
- "email, phone, address columns" → {{"$or": [{{"column": "email"}}, {{"column": "phone"}}, {{"column": "address"}}]}}
- "email and phone from users table" → {{"$and": [{{"table": "users"}}, {{"$or": [{{"column": "email"}}, {{"column": "phone"}}]}}]}}
- "sales database" → {{"workspace": "sales"}}

Invalid examples (no explicit names):
- "get me customer information" → null (generic term, no explicit column name)
- "show user data" → null (generic term, no explicit table name)
- "find sales information" → null (generic term, no explicit database name)
- "column containing customer name" → null (no explicit column name mentioned)

KEY DISTINCTION:
- "column X FROM/IN table Y" = $and (specific column within specific table)
- "column X AND column Y" = $or (multiple columns as alternatives)
- "table X AND table Y" = $or (multiple tables as alternatives)

If no EXPLICIT database/table/column names are found in the query, return: null

Return only the JSON filter object, nothing else.
            """
            
            formatted_prompt = [
                {"role": "system", "content": "You are a database expert. Create ChromaDB filters from user queries for explicitly mentioned database/table/column names. Use $and for specific columns within specific tables (e.g., 'column X FROM table Y'). Use $or for multiple alternatives (e.g., 'table1 AND table2' or 'column1 AND column2'). Pay attention to prepositions like 'from', 'in', 'within' which indicate $and relationships. Return only valid JSON."},
                {"role": "user", "content": filter_prompt}
            ]
            
            filter_result = self.llm_engine.generate_completion(formatted_prompt, log_prefix="ChromaDB Filter Creation")
            self.logger.info(f"LLM filter result: {filter_result}")
            
            # Parse the filter result
            filter_expr = None
            filter_description = "No specific filter"
            
            try:
                import json
                filter_result_clean = filter_result.strip()
                
                # Extract JSON from markdown code blocks if present
                if filter_result_clean.startswith('```json'):
                    # Remove markdown code block markers
                    filter_result_clean = filter_result_clean[7:]  # Remove ```json
                    if filter_result_clean.endswith('```'):
                        filter_result_clean = filter_result_clean[:-3]  # Remove ```
                    filter_result_clean = filter_result_clean.strip()
                elif filter_result_clean.startswith('```'):
                    # Remove generic code block markers
                    filter_result_clean = filter_result_clean[3:]  # Remove ```
                    if filter_result_clean.endswith('```'):
                        filter_result_clean = filter_result_clean[:-3]  # Remove ```
                    filter_result_clean = filter_result_clean.strip()
                
                if filter_result_clean and filter_result_clean.lower() != "null":
                    filter_expr = json.loads(filter_result_clean)
                    filter_description = f"Filter: {json.dumps(filter_expr, separators=(',', ':'))}"
                    self.logger.info(f"Using ChromaDB filter: {filter_expr}")
            except json.JSONDecodeError as e:
                self.logger.warning(f"LLM didn't return valid JSON filter: {e}. Using unfiltered search.")
                filter_expr = None
            
            # Perform search based on whether we have a filter or not
            if filter_expr:
                # Direct hit detected - retrieve records by filter only, no vector search
                self.logger.info(f"Direct hit detected with filter: {filter_expr}. Retrieving records by filter only.")
                results = self.vector_store.query_by_filter(
                    'schema_metadata',
                    filter_expr=filter_expr,
                    limit=limit,
                    output_fields=["id", "text", "metadata"]
                )
                
                # If no results with filter, fall back to vector search
                if not results:
                    self.logger.info(f"No results found with filter. Falling back to vector search.")
                    results = self.vector_store.search_similar(
                        'schema_metadata',
                        self._get_embedding(query),
                        limit=limit,
                        filter_expr=None,
                        output_fields=["id", "text", "metadata"]
                    )
                    filter_description = "Filter removed (no results), using vector search"
            else:
                # No filter - use vector search
                self.logger.info("No filter detected. Using vector search.")
                results = self.vector_store.search_similar(
                    'schema_metadata',
                    self._get_embedding(query),
                    limit=limit,
                    filter_expr=None,
                    output_fields=["id", "text", "metadata"]
                )
            
            return results, filter_description
            
        except Exception as e:
            self.logger.error(f"Error in LLM filtering: {str(e)}", exc_info=True)
            # Fallback to unfiltered search
            try:
                self.logger.info("Performing fallback unfiltered search due to error.")
                results = self.vector_store.search_similar(
                    'schema_metadata',
                    self._get_embedding(query),
                    limit=limit,
                    filter_expr=None,
                    output_fields=["id", "text", "metadata"]
                )
                return results, "Error in filtering, using unfiltered search"
            except Exception as fallback_e:
                self.logger.error(f"Fallback search also failed: {str(fallback_e)}", exc_info=True)
                return [], "Search failed"
