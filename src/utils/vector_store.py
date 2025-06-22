"""
Vector database client for Text2SQL application.
Handles storage and retrieval of vector embeddings using Milvus.
"""

import logging
import time
import os
import json
from typing import List, Dict, Any, Optional
import numpy as np

from pymilvus import MilvusClient, Collection, CollectionSchema, FieldSchema, DataType

logger = logging.getLogger('text2sql.vector')

class VectorStore:
    """Vector database client for storing and retrieving embeddings"""
    
    def __init__(self, uri=None):
        """Initialize the vector database client
        
        Args:
            uri (str, optional): Milvus server URI, defaults to local file-based storage
        """
        self.logger = logging.getLogger('text2sql.vector')
        self.uri = uri or "./vector_store.db"
        self.client = None
        # Default dimension for popular embedding models - can be overridden per collection
        self.default_vector_dim = 384
        
    def connect(self) -> bool:
        """Connect to Milvus server
        
        Returns:
            bool: True if successful, False otherwise
        """
        start_time = time.time()
        self.logger.info(f"Connecting to vector database at {self.uri}")
        
        try:
            self.client = MilvusClient(self.uri)
            self.logger.info(f"Vector database connection established in {time.time() - start_time:.2f}s")
            return True
        except Exception as e:
            self.logger.error(f"Vector database connection error: {str(e)}", exc_info=True)
            return False
    
    def count(self, collection_name: str) -> int:
        """Count documents in a collection
        
        Args:
            collection_name: Name of the collection
            
        Returns:
            int: Number of documents in the collection
        """
        try:
            if not self.client:
                self.logger.error("Vector database client not connected")
                return 0
                
            count = self.client.count(collection_name)
            return count
        except Exception as e:
            self.logger.error(f"Error counting documents in collection {collection_name}: {str(e)}")
            return 0
            
    def list_entries(self, collection_name: str, limit: int = 100) -> List[Dict[str, Any]]:
        """List entries in a collection with metadata
        
        Args:
            collection_name: Name of the collection
            limit: Maximum number of entries to return
            
        Returns:
            List[Dict]: List of entries with metadata
        """
        try:
            if not self.client:
                self.logger.error("Vector database client not connected")
                return []
                
            # Get entries with their metadata
            entries = self.client.query(
                collection_name=collection_name,
                filter="",
                output_fields=["text", "metadata"],
                limit=limit
            )
            
            return entries
        except Exception as e:
            self.logger.error(f"Error listing entries in collection {collection_name}: {str(e)}")
            return []
    
    def init_collection(self, collection_name: str, dimension: int = None) -> bool:
        """Initialize a vector collection if it doesn't exist
        
        Args:
            collection_name (str): Name of the collection to initialize
            dimension (int, optional): Vector dimension, defaults to class default
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not self.client and not self.connect():
            return False
            
        try:
            # Check if collection exists
            has_collection = collection_name in self.client.list_collections()
            
            if not has_collection:
                self.logger.info(f"Creating collection '{collection_name}'")
                
                # Use provided dimension or default
                vector_dim = dimension or self.default_vector_dim
                
                self.client.create_collection(
                    collection_name=collection_name,
                    dimension=vector_dim,
                )
                
                self.logger.info(f"Collection '{collection_name}' created successfully with dimension {vector_dim}")
            else:
                self.logger.info(f"Collection '{collection_name}' already exists")
                
            return True
        except Exception as e:
            self.logger.error(f"Error initializing collection {collection_name}: {str(e)}", exc_info=True)
            return False
    
    def insert_embedding(self, collection_name: str, feedback_id: int, vector: List[float], 
                        query_text: str, metadata: Dict[str, Any] = None) -> bool:
        """Insert a vector embedding into the database
        
        Args:
            collection_name (str): Name of the collection to insert into
            feedback_id (int): ID of the feedback entry (primary key)
            vector (List[float]): Vector embedding to store
            query_text (str): The query text associated with the embedding
            metadata (Dict): Additional metadata to store with the vector
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not self.client and not self.connect():
            return False
            
        try:
            # Prepare metadata (ensure all values are of supported types)
            clean_metadata = {}
            if metadata:
                for k, v in metadata.items():
                    # Convert any lists to strings to avoid type issues
                    if isinstance(v, list):
                        clean_metadata[k] = ','.join(str(x) for x in v)
                    else:
                        clean_metadata[k] = v
            
            # Prepare data for insertion
            data = [{
                "id": feedback_id,
                "vector": vector,
                "query_text": query_text
            }]
            
            # Add metadata fields
            if clean_metadata:
                for k, v in clean_metadata.items():
                    data[0][k] = v
            
            # Insert the data
            result = self.client.insert(
                collection_name=collection_name,
                data=data
            )
            
            self.logger.info(f"Inserted embedding for feedback_id {feedback_id} into collection {collection_name}")
            return True
        except Exception as e:
            self.logger.error(f"Error inserting embedding into collection {collection_name}: {str(e)}", exc_info=True)
            return False
    
    def search_similar(self, collection_name: str, vector: List[float], limit: int = 5, 
                       filter_expr: str = None, output_fields: List[str] = None) -> List[Dict[str, Any]]:
        """Search for similar vectors
        
        Args:
            collection_name (str): Name of the collection to search in
            vector (List[float]): Query vector to search with
            limit (int): Maximum number of results to return
            filter_expr (str, optional): Filter expression for the search
            output_fields (List[str], optional): Specific fields to return
            
        Returns:
            List[Dict]: List of search results with similarity scores
        """
        if not self.client and not self.connect():
            return []
            
        try:
            # If no specific output fields are provided, try to get all available fields
            # from collection schema or use default fields
            self.logger.info(f"output_fields: {output_fields}")
            if not output_fields:
                try:
                    # Get collection schema to identify available fields
                    collection_info = self.client.describe_collection(collection_name)
                    self.logger.info(f"Collection info: {collection_info}")
                    if 'schema' in collection_info:
                        output_fields = []
                        for field in collection_info['schema']:
                            field_name = field.get('name')
                            field_type = field.get('type')
                            
                            # Skip vector fields as they're usually large
                            if field_name and field_type and field_type != 'VECTOR':
                                output_fields.append(field_name)
                except Exception as schema_e:
                    self.logger.info(f"Couldn't get schema for {collection_name}: {schema_e}")
                    # Default fields if schema retrieval fails
                    output_fields = ["id"]
            
            # Ensure output_fields is a list and ID field is included
            if output_fields is None:
                # Use a more comprehensive default field list when schema retrieval fails
                output_fields = ["id", "query_text", "sql_query", "feedback_rating", "results_summary", 
                                "workspace", "tables_used", "is_manual_sample", "created_at","chunk_id","document_id"]
            elif "id" not in output_fields and not any(f.lower() == 'id' for f in output_fields):
                output_fields.append("id")
                
            self.logger.info(f"Searching collection {collection_name} with fields: {output_fields}")
            
            # Ensure we get all available fields by explicitly passing them
            # Note: Milvus client needs output_fields parameter to return all columns
            self.logger.info(f"Using output fields for search: {output_fields}")
            
            # Execute the search
            results = self.client.search(
                collection_name=collection_name,
                data=[vector],
                filter=filter_expr,
                limit=limit,
                output_fields=output_fields
            )
            

            # Process and format the results
            formatted_results = []
            
            if results and len(results) > 0:
                # Log the structure of the first result for debugging
                if len(results[0]) > 0:
                    self.logger.info(f"Search result structure: {list(results[0][0].keys())}")

                
                for hit in results[0]:
                    # Create a base entry with the ID
                    entry = {'id': hit['id']}
                    
                    # Extract all entity fields
                    if 'entity' in hit and isinstance(hit['entity'], dict):
                        #self.logger.info(f"Entity fields: {list(hit['entity'].keys())}")
                        for key, value in hit['entity'].items():
                            # Process special case for comma-separated values that might be lists
                            if isinstance(value, str) and ',' in value and key.endswith('_used'):
                                entry[key] = value.split(',')
                            else:
                                entry[key] = value
                    
                    # Extract metadata field if it exists
                    if 'metadata' in hit and hit['metadata']:
                        self.logger.info(f"Metadata found in hit")
                        try:
                            if isinstance(hit['metadata'], str):
                                metadata_dict = json.loads(hit['metadata'])
                                for key, value in metadata_dict.items():
                                    entry[key] = value
                            elif isinstance(hit['metadata'], dict):
                                for key, value in hit['metadata'].items():
                                    entry[key] = value
                        except Exception as metadata_e:
                            self.logger.error(f"Error parsing metadata: {metadata_e}")
                    
                    # Extract any other fields directly in the hit
                    for key, value in hit.items():
                        if key not in ['id', 'entity', 'distance', 'metadata'] and value is not None:
                            entry[key] = value
                    
                    # Extract text field
                    if 'text' in hit:
                        entry['text'] = hit['text']
                    
                    # Extract query_text field
                    if 'query_text' in hit:
                        entry['query_text'] = hit['query_text']
                    
                    # Always add similarity score
                    entry['similarity'] = hit.get('distance')
                    
                    # Add the processed entry to results
                    formatted_results.append(entry)
            
            return formatted_results
        except Exception as e:
            self.logger.error(f"Error searching similar vectors in collection {collection_name}: {str(e)}", exc_info=True)
            return []
    
    def update_embedding(self, collection_name: str, feedback_id: int, vector: List[float], 
                        query_text: str, metadata: Dict[str, Any] = None) -> bool:
        """Update an existing vector embedding
        
        Args:
            collection_name (str): Name of the collection to update in
            feedback_id (int): ID of the feedback entry to update
            vector (List[float]): New vector embedding
            query_text (str): Updated query text
            metadata (Dict): Updated metadata
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not self.client and not self.connect():
            return False
            
        try:
            # Delete the existing record
            self.delete_embedding(collection_name, feedback_id)
            
            # Insert the new record
            return self.insert_embedding(collection_name, feedback_id, vector, query_text, metadata)
        except Exception as e:
            self.logger.error(f"Error updating embedding in collection {collection_name}: {str(e)}", exc_info=True)
            return False
    
    def delete_embedding(self, collection_name: str, feedback_id: int) -> bool:
        """Delete a vector embedding from the database
        
        Args:
            collection_name (str): Name of the collection to delete from
            feedback_id (int): ID of the feedback entry to delete
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not self.client and not self.connect():
            return False
            
        try:
            # Delete by ID
            filter_expr = f"id == {feedback_id}"
            result = self.client.delete(
                collection_name=collection_name,
                filter=filter_expr
            )
            
            self.logger.info(f"Deleted embedding for feedback_id {feedback_id} from collection {collection_name}")
            return True
        except Exception as e:
            self.logger.error(f"Error deleting embedding from collection {collection_name}: {str(e)}", exc_info=True)
            return False
    
    def query_by_filter(self, collection_name: str, filter_expr: str, limit: int = 100, 
                         output_fields: List[str] = None) -> List[Dict[str, Any]]:
        """Query entries by filter expression
        
        Args:
            collection_name (str): Name of the collection to query
            filter_expr (str): Filter expression for the query
            limit (int): Maximum number of results to return
            output_fields (List[str], optional): Specific fields to return
            
        Returns:
            List[Dict]: List of query results
        """
        if not self.client and not self.connect():
            return []
            
        try:
            # If no specific output fields are provided, try to get all available fields
            if not output_fields:
                try:
                    # Get collection schema to identify available fields
                    collection_info = self.client.describe_collection(collection_name)
                    if 'schema' in collection_info:
                        output_fields = []
                        for field in collection_info['schema']:
                            field_name = field.get('name')
                            field_type = field.get('type')
                            
                            # Skip vector fields as they're usually large
                            if field_name and field_type and field_type != 'VECTOR':
                                output_fields.append(field_name)
                except Exception as schema_e:
                    self.logger.info(f"Couldn't get schema for {collection_name}: {schema_e}")
                    # Default to just ID if schema retrieval fails
                    output_fields = ["id"]
            
            # Execute the query
            results = self.client.query(
                collection_name=collection_name,
                filter=filter_expr,
                output_fields=output_fields,
                limit=limit
            )
            
            # Process and format the results generically
            formatted_results = []
            
            for hit in results:
                # Create a base entry with original data
                entry = {}
                
                # Copy all fields from result
                for key, value in hit.items():
                    # Special handling for lists stored as comma-separated strings
                    if isinstance(value, str) and ',' in value and key.endswith('_used'):
                        entry[key] = value.split(',')
                    else:
                        entry[key] = value
                
                formatted_results.append(entry)
            
            return formatted_results
        except Exception as e:
            self.logger.error(f"Error querying by filter in collection {collection_name}: {str(e)}", exc_info=True)
            return []
    
    def close(self):
        """Close the connection to the vector database"""
        self.logger.info("Closing vector database connection")
        # With Milvus client, explicit closing is not required
        self.client = None