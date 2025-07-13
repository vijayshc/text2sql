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
from src.utils.metadata_search_enhancer import MetadataSearchEnhancer

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
        
        # Initialize metadata search enhancer
        self.search_enhancer = MetadataSearchEnhancer()
        
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
                              filter_workspace: Optional[str] = None) -> Tuple[List[Dict[str, Any]], str]:
        """Search for schema metadata with enhanced accuracy using query reformatting and BM25
        
        Args:
            query: Search query
            limit: Maximum number of results to return
            filter_workspace: Optional workspace to filter results by
            
        Returns:
            Tuple[List[Dict], str]: Enhanced search results and reformatted query
        """
        try:
            # Step 1: Reformat query for better vector search accuracy
            reformatted_query = self.search_enhancer.get_reformatted_query_for_vector_search(query)
            
            # Step 2: Get embedding for reformatted query
            query_embedding = self._get_embedding(reformatted_query)
            
            # Step 3: Create filter expression if workspace is specified
            filter_expr = None
            if filter_workspace:
                filter_expr = {"workspace": filter_workspace}
            
            # Step 4: Search for similar vectors using reformatted query
            # Use higher limit for BM25 reranking to have more candidates
            search_limit = limit * 3
            
            results = self.vector_store.search_similar(
                'schema_metadata',
                query_embedding,
                limit=search_limit,
                filter_expr=filter_expr
            )
            
            # Step 5: Apply BM25 reranking (mandatory)
            if results:
                # Use original query for BM25 to match user intent, but skip query reformatting since we already did it
                enhanced_results = self.search_enhancer.apply_bm25_reranking(query, results, top_k=limit)
                results = enhanced_results
            
            self.logger.info(f"Enhanced metadata search completed: {len(results)} results")
            return results, reformatted_query
            
        except Exception as e:
            self.logger.error(f"Error in enhanced schema metadata search: {str(e)}", exc_info=True)
            return [], query

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
        """Use LLM to extract entities from query and perform multi-level search with progressive filter reduction
        
        Args:
            query: User query
            limit: Maximum number of results
            
        Returns:
            Tuple[List[Dict], str]: Search results and the filter expression used
        """
        try:
            # Ask LLM to extract specific entities from query
            extraction_prompt = f"""
Extract explicitly mentioned database, table, and column names from this query:
"{query}"

RULES:
1. Extract ONLY explicitly mentioned names (e.g., "users", "first_name", "order_date")
2. Do NOT infer from generic terms like "customer information" or "user data"
3. Return multiple values if mentioned (e.g., "first_name, last_name, email")

Return a JSON object with arrays for each type:
{{
  "workspaces": ["database1", "database2"],
  "tables": ["table1", "table2"],
  "columns": ["column1", "column2"]
}}

If no explicit names found for a category, use an empty array.
Return only the JSON object, nothing else.
            """
            
            formatted_prompt = [
                {"role": "system", "content": "You are a database expert. Extract explicitly mentioned database/table/column names from queries. Return only valid JSON with arrays."},
                {"role": "user", "content": extraction_prompt}
            ]
            
            extraction_result = self.llm_engine.generate_completion(formatted_prompt, log_prefix="Entity Extraction")
            self.logger.info(f"LLM extraction result: {extraction_result}")
            
            # Parse extracted entities
            entities = {"workspaces": [], "tables": [], "columns": []}
            try:
                import json
                result_clean = extraction_result.strip()
                
                # Clean markdown code blocks
                if result_clean.startswith('```json'):
                    result_clean = result_clean[7:-3].strip()
                elif result_clean.startswith('```'):
                    result_clean = result_clean[3:-3].strip()
                
                if result_clean and result_clean.lower() != "null":
                    entities = json.loads(result_clean)
                    self.logger.info(f"Extracted entities: {entities}")
            except json.JSONDecodeError as e:
                self.logger.warning(f"Failed to parse extraction result: {e}")
            
            # Perform multi-level search with progressive filter reduction
            results, filter_description = self._multi_level_search(entities, query, limit)
            
            return results, filter_description
            
        except Exception as e:
            self.logger.error(f"Error in LLM filtering: {str(e)}", exc_info=True)
            # Fallback to enhanced unfiltered search
            try:
                self.logger.info("Performing fallback enhanced unfiltered search due to error.")
                results, _ = self.search_schema_metadata(query, limit=limit)
                return results, "Error in filtering, using enhanced unfiltered search"
            except Exception as fallback_e:
                self.logger.error(f"Enhanced fallback search also failed: {str(fallback_e)}", exc_info=True)
                return [], "All search methods failed"
    
    def _multi_level_search(self, entities: Dict[str, List[str]], query: str, limit: int) -> Tuple[List[Dict[str, Any]], str]:
        """Simplified 3-level search with progressive filter reduction
        
        Args:
            entities: Extracted entities from query
            query: Original query
            limit: Maximum number of results
            
        Returns:
            Tuple[List[Dict], str]: Search results and filter description
        """
        workspaces = entities.get("workspaces", [])
        tables = entities.get("tables", [])
        columns = entities.get("columns", [])
        
        # If no entities found, use vector search
        if not workspaces and not tables and not columns:
            self.logger.info("No entities found. Using enhanced vector search.")
            results, _ = self.search_schema_metadata(query, limit=limit)
            return results, "No entities found, using enhanced vector search"
        
        # Level 1: Apply all filters (workspace + table + column)
        filter_parts = []
        if workspaces:
            filter_parts.append({"workspace": {"$in": workspaces}})
        if tables:
            filter_parts.append({"table": {"$in": tables}})
        if columns:
            filter_parts.append({"column": {"$in": columns}})
        
        if filter_parts:
            filter_expr = {"$and": filter_parts} if len(filter_parts) > 1 else filter_parts[0]
            filter_desc = f"All filters: workspaces={workspaces}, tables={tables}, columns={columns}"
            
            self.logger.info(f"Level 1: Trying all filters - {filter_desc}")
            try:
                results = self.vector_store.query_by_filter(
                    'schema_metadata',
                    filter_expr=filter_expr,
                    limit=limit,
                    output_fields=["id", "text", "metadata"]
                )
                
                if results:
                    self.logger.info(f"Level 1: Found {len(results)} results with all filters")
                    return results, f"Level 1: {filter_desc}"
            except Exception as e:
                self.logger.warning(f"Level 1 failed: {str(e)}")
        
        # Level 2: Remove column filter, keep workspace + table
        if workspaces or tables:
            filter_parts = []
            if workspaces:
                filter_parts.append({"workspace": {"$in": workspaces}})
            if tables:
                filter_parts.append({"table": {"$in": tables}})
            
            filter_expr = {"$and": filter_parts} if len(filter_parts) > 1 else filter_parts[0]
            filter_desc = f"Without columns: workspaces={workspaces}, tables={tables}"
            
            self.logger.info(f"Level 2: Trying without column filter - {filter_desc}")
            try:
                results = self.vector_store.query_by_filter(
                    'schema_metadata',
                    filter_expr=filter_expr,
                    limit=limit,
                    output_fields=["id", "text", "metadata"]
                )
                
                if results:
                    self.logger.info(f"Level 2: Found {len(results)} results without column filter")
                    return results, f"Level 2: {filter_desc}"
            except Exception as e:
                self.logger.warning(f"Level 2 failed: {str(e)}")
        
        # Level 3: Use embedding search with workspace filter (if workspace exists)
        if workspaces:
            self.logger.info(f"Level 3: Using embedding search with workspace filter: {workspaces}")
            try:
                results, _ = self.search_schema_metadata(
                    query, 
                    limit=limit, 
                    filter_workspace=workspaces[0] if len(workspaces) == 1 else None
                )
                
                if results:
                    return results, f"Level 3: Embedding search with workspace filter: {workspaces}"
            except Exception as e:
                self.logger.warning(f"Level 3 failed: {str(e)}")
        
        # Final fallback: Simple vector search without any filters
        self.logger.info("All levels failed. Using simple vector search without filters.")
        results, _ = self.search_schema_metadata(query, limit=limit)
        return results, "Fallback: Simple vector search without filters"
