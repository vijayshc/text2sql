"""
Vector database client for Text2SQL application.
Handles storage and retrieval of vector embeddings using ChromaDB REST API.
"""

import logging
from typing import List, Dict, Any, Optional
from .vector_store_client import VectorStoreClient
from config.config import CHROMADB_SERVICE_URL

logger = logging.getLogger('text2sql.vector')

class VectorStore:
    """Vector database client for storing and retrieving embeddings using ChromaDB REST API"""
    
    def __init__(self, uri=None):
        """Initialize the vector database client
        
        Args:
            uri (str, optional): ChromaDB service URL, defaults to config setting
        """
        self.logger = logging.getLogger('text2sql.vector')
        service_url = uri or CHROMADB_SERVICE_URL
        self.client = VectorStoreClient(service_url=service_url)
        # Default dimension for popular embedding models - can be overridden per collection
        self.default_vector_dim = 384
        
    def connect(self) -> bool:
        """Connect to ChromaDB
        
        Returns:
            bool: True if successful, False otherwise
        """
        start_time = time.time()
        self.logger.info(f"Connecting to ChromaDB at {self.persist_directory}")
        
        try:
            # Create the data directory if it doesn't exist
            os.makedirs(self.persist_directory, exist_ok=True)
            
            # Initialize ChromaDB client with persistent storage
            self.client = chromadb.PersistentClient(path=self.persist_directory)
            
            # Initialize embedding function (using sentence transformers)
            self.embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
                model_name="all-MiniLM-L6-v2"
            )
            
            self.logger.info(f"ChromaDB connection established in {time.time() - start_time:.2f}s")
            return True
        except Exception as e:
            self.logger.error(f"ChromaDB connection error: {str(e)}", exc_info=True)
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
                self.logger.error("ChromaDB client not connected")
                return 0
                
            try:
                collection = self.client.get_collection(name=collection_name)
                count = collection.count()
                return count
            except Exception as e:
                # Collection doesn't exist
                self.logger.info(f"Collection {collection_name} doesn't exist: {str(e)}")
                return 0
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
                self.logger.error("ChromaDB client not connected")
                return []
            
            try:
                collection = self.client.get_collection(name=collection_name)
                result = collection.get(limit=limit, include=['metadatas', 'documents'])
                
                entries = []
                for i, doc_id in enumerate(result['ids']):
                    entry = {
                        'id': doc_id,
                        'text': result['documents'][i] if i < len(result['documents']) else '',
                        'metadata': result['metadatas'][i] if i < len(result['metadatas']) else {}
                    }
                    entries.append(entry)
                
                return entries
            except Exception as e:
                self.logger.info(f"Collection {collection_name} doesn't exist or is empty: {str(e)}")
                return []
        except Exception as e:
            self.logger.error(f"Error listing entries in collection {collection_name}: {str(e)}")
            return []
    
    def init_collection(self, collection_name: str, dimension: int = None) -> bool:
        """Initialize a vector collection if it doesn't exist
        
        Args:
            collection_name (str): Name of the collection to initialize
            dimension (int, optional): Vector dimension (not used in ChromaDB, kept for compatibility)
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not self.client and not self.connect():
            return False
            
        try:
            # Try to get existing collection
            try:
                collection = self.client.get_collection(name=collection_name)
                self.logger.info(f"Collection '{collection_name}' already exists")
                return True
            except Exception:
                # Collection doesn't exist, create it
                self.logger.info(f"Creating collection '{collection_name}'")
                
                collection = self.client.create_collection(
                    name=collection_name,
                    embedding_function=self.embedding_function
                )
                
                self.logger.info(f"Collection '{collection_name}' created successfully")
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
            vector (List[float]): Vector embedding to store (optional for ChromaDB with embedding function)
            query_text (str): The query text associated with the embedding
            metadata (Dict): Additional metadata to store with the vector
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not self.client and not self.connect():
            return False
            
        try:
            # Get or create collection
            try:
                collection = self.client.get_collection(name=collection_name)
            except Exception:
                if not self.init_collection(collection_name):
                    return False
                collection = self.client.get_collection(name=collection_name)
            
            # Prepare metadata (ensure all values are of supported types)
            clean_metadata = {}
            if metadata:
                for k, v in metadata.items():
                    # Convert any lists to strings to avoid type issues
                    if isinstance(v, list):
                        clean_metadata[k] = ','.join(str(x) for x in v)
                    elif v is not None:
                        clean_metadata[k] = str(v)
            
            # Add query_text to metadata for better searchability
            clean_metadata['query_text'] = query_text
            
            # Insert the data - ChromaDB will handle embedding generation if we don't provide embeddings
            if vector and len(vector) > 0:
                # Use provided vector
                collection.add(
                    ids=[str(feedback_id)],
                    documents=[query_text],
                    metadatas=[clean_metadata],
                    embeddings=[vector]
                )
            else:
                # Let ChromaDB generate embeddings
                collection.add(
                    ids=[str(feedback_id)],
                    documents=[query_text],
                    metadatas=[clean_metadata]
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
            vector (List[float]): Query vector to search with (optional for ChromaDB with embedding function)
            limit (int): Maximum number of results to return
            filter_expr (str, optional): Filter expression for the search (ChromaDB uses where clause)
            output_fields (List[str], optional): Specific fields to return (kept for compatibility)
            
        Returns:
            List[Dict]: List of search results with similarity scores
        """
        if not self.client and not self.connect():
            return []
            
        try:
            # Get collection
            try:
                collection = self.client.get_collection(name=collection_name)
            except Exception:
                self.logger.info(f"Collection {collection_name} doesn't exist")
                return []
            
            self.logger.info(f"Searching collection {collection_name} with limit: {limit}")
            
            # Prepare where clause from filter_expr if provided
            where_clause = None
            if filter_expr:
                # Convert Milvus-style filter to ChromaDB where clause
                # This is a basic conversion - might need more sophisticated parsing
                try:
                    # Simple conversions for common patterns
                    if "==" in filter_expr:
                        parts = filter_expr.split("==")
                        if len(parts) == 2:
                            key = parts[0].strip()
                            value = parts[1].strip().strip('"\'')
                            # Try to convert to appropriate type
                            try:
                                value = int(value)
                            except ValueError:
                                try:
                                    value = float(value)
                                except ValueError:
                                    pass  # Keep as string
                            where_clause = {key: value}
                except Exception as e:
                    self.logger.warning(f"Could not parse filter expression '{filter_expr}': {e}")
            
            # Execute the search
            if vector and len(vector) > 0:
                # Use provided vector for search
                results = collection.query(
                    query_embeddings=[vector],
                    n_results=limit,
                    where=where_clause,
                    include=['metadatas', 'documents', 'distances']
                )
                print(collection_name,results,where_clause)
            else:
                # This shouldn't happen in normal usage, but handle gracefully
                self.logger.warning("No vector provided for search, returning empty results")
                return []

            # Process and format the results
            formatted_results = []
            
            if results and 'ids' in results and len(results['ids']) > 0:
                # ChromaDB returns results in a different format
                ids = results['ids'][0] if results['ids'] else []
                documents = results['documents'][0] if results['documents'] else []
                metadatas = results['metadatas'][0] if results['metadatas'] else []
                distances = results['distances'][0] if results['distances'] else []
                
                self.logger.info(f"Found {len(ids)} search results")
                
                for i, doc_id in enumerate(ids):
                    # Create a base entry with the ID
                    entry = {'id': doc_id}
                    
                    # Add document text
                    if i < len(documents) and documents[i]:
                        entry['query_text'] = documents[i]
                        entry['text'] = documents[i]
                    
                    # Add metadata fields
                    if i < len(metadatas) and metadatas[i]:
                        metadata = metadatas[i]
                        for key, value in metadata.items():
                            # Process special case for comma-separated values that might be lists
                            if isinstance(value, str) and ',' in value and key.endswith('_used'):
                                entry[key] = value.split(',')
                            else:
                                entry[key] = value
                    
                    # Add similarity score (ChromaDB returns distance, convert to similarity)
                    if i < len(distances):
                        # ChromaDB typically returns L2 distance, convert to similarity score
                        # Similarity = 1 / (1 + distance) for a more intuitive score
                        distance = distances[i]
                        similarity = 1 / (1 + distance) if distance >= 0 else 0
                        entry['similarity'] = similarity
                        entry['distance'] = distance
                    
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
            # Delete the existing record first
            if self.delete_embedding(collection_name, feedback_id):
                # Insert the new record
                return self.insert_embedding(collection_name, feedback_id, vector, query_text, metadata)
            return False
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
            # Get collection
            try:
                collection = self.client.get_collection(name=collection_name)
            except Exception:
                self.logger.info(f"Collection {collection_name} doesn't exist")
                return True  # Consider it successful if collection doesn't exist
            
            # Delete by ID
            collection.delete(ids=[str(feedback_id)])
            
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
            filter_expr (str): Filter expression for the query (converted to ChromaDB where clause)
            limit (int): Maximum number of results to return
            output_fields (List[str], optional): Specific fields to return (kept for compatibility)
            
        Returns:
            List[Dict]: List of query results
        """
        if not self.client and not self.connect():
            return []
            
        try:
            # Get collection
            try:
                collection = self.client.get_collection(name=collection_name)
            except Exception:
                self.logger.info(f"Collection {collection_name} doesn't exist")
                return []
            
            # Prepare where clause from filter_expr if provided
            where_clause = None
            if filter_expr and filter_expr.strip():
                # Convert Milvus-style filter to ChromaDB where clause
                try:
                    # Simple conversions for common patterns
                    if "==" in filter_expr:
                        parts = filter_expr.split("==")
                        if len(parts) == 2:
                            key = parts[0].strip()
                            value = parts[1].strip().strip('"\'')
                            # Try to convert to appropriate type
                            try:
                                value = int(value)
                            except ValueError:
                                try:
                                    value = float(value)
                                except ValueError:
                                    pass  # Keep as string
                            where_clause = {key: value}
                except Exception as e:
                    self.logger.warning(f"Could not parse filter expression '{filter_expr}': {e}")
            
            # Execute the query
            results = collection.get(
                where=where_clause,
                limit=limit,
                include=['metadatas', 'documents']
            )
            
            # Process and format the results generically
            formatted_results = []
            
            if results and 'ids' in results:
                ids = results['ids']
                documents = results.get('documents', [])
                metadatas = results.get('metadatas', [])
                
                for i, doc_id in enumerate(ids):
                    # Create a base entry
                    entry = {'id': doc_id}
                    
                    # Add document text
                    if i < len(documents) and documents[i]:
                        entry['query_text'] = documents[i]
                        entry['text'] = documents[i]
                    
                    # Add metadata fields
                    if i < len(metadatas) and metadatas[i]:
                        metadata = metadatas[i]
                        for key, value in metadata.items():
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
        self.logger.info("Closing ChromaDB connection")
        # ChromaDB doesn't require explicit closing for persistent client
        self.client = None

    def search_by_text(self, collection_name: str, query_text: str, limit: int = 5, 
                       filter_expr: str = None) -> List[Dict[str, Any]]:
        """Search for similar vectors using text query (ChromaDB will handle embedding)
        
        Args:
            collection_name (str): Name of the collection to search in
            query_text (str): Text query to search with
            limit (int): Maximum number of results to return
            filter_expr (str, optional): Filter expression for the search
            
        Returns:
            List[Dict]: List of search results with similarity scores
        """
        if not self.client and not self.connect():
            return []
            
        try:
            # Get collection
            try:
                collection = self.client.get_collection(name=collection_name)
            except Exception:
                self.logger.info(f"Collection {collection_name} doesn't exist")
                return []
            
            self.logger.info(f"Searching collection {collection_name} with text: '{query_text[:50]}...'")
            
            # Prepare where clause from filter_expr if provided
            where_clause = None
            if filter_expr:
                try:
                    if "==" in filter_expr:
                        parts = filter_expr.split("==")
                        if len(parts) == 2:
                            key = parts[0].strip()
                            value = parts[1].strip().strip('"\'')
                            try:
                                value = int(value)
                            except ValueError:
                                try:
                                    value = float(value)
                                except ValueError:
                                    pass
                            where_clause = {key: value}
                except Exception as e:
                    self.logger.warning(f"Could not parse filter expression '{filter_expr}': {e}")
            
            # Execute the search using text query (ChromaDB will generate embeddings)
            results = collection.query(
                query_texts=[query_text],
                n_results=limit,
                where=where_clause,
                include=['metadatas', 'documents', 'distances']
            )

            # Process and format the results (same as search_similar)
            formatted_results = []
            
            if results and 'ids' in results and len(results['ids']) > 0:
                ids = results['ids'][0] if results['ids'] else []
                documents = results['documents'][0] if results['documents'] else []
                metadatas = results['metadatas'][0] if results['metadatas'] else []
                distances = results['distances'][0] if results['distances'] else []
                
                self.logger.info(f"Found {len(ids)} search results")
                
                for i, doc_id in enumerate(ids):
                    entry = {'id': doc_id}
                    
                    if i < len(documents) and documents[i]:
                        entry['query_text'] = documents[i]
                        entry['text'] = documents[i]
                    
                    if i < len(metadatas) and metadatas[i]:
                        metadata = metadatas[i]
                        for key, value in metadata.items():
                            if isinstance(value, str) and ',' in value and key.endswith('_used'):
                                entry[key] = value.split(',')
                            else:
                                entry[key] = value
                    
                    if i < len(distances):
                        distance = distances[i]
                        similarity = 1 / (1 + distance) if distance >= 0 else 0
                        entry['similarity'] = similarity
                        entry['distance'] = distance
                    
                    formatted_results.append(entry)
            
            return formatted_results
        except Exception as e:
            self.logger.error(f"Error searching by text in collection {collection_name}: {str(e)}", exc_info=True)
            return []
    
    def list_collections(self) -> List[str]:
        """List all collections
        
        Returns:
            List[str]: List of collection names
        """
        try:
            if not self.client and not self.connect():
                self.logger.error("Failed to connect for list_collections")
                return []
            
            collection_list = self.client.list_collections()
            collection_names = [col.name for col in collection_list]
            self.logger.info(f"LIST_COLLECTIONS: Found collections: {collection_names}")
            return collection_names
        except Exception as e:
            self.logger.error(f"Error listing collections: {e}")
            return []
    
    def get_collection_metadata(self, collection_name: str) -> Dict[str, Any]:
        """Get metadata for a collection
        
        Args:
            collection_name: Name of the collection
            
        Returns:
            Dict: Collection metadata
        """
        try:
            if not self.client and not self.connect():
                return {}
            
            collection = self.client.get_collection(name=collection_name)
            return {
                'name': collection_name,
                'count': collection.count(),
                'metadata': getattr(collection, 'metadata', {})
            }
        except Exception as e:
            self.logger.error(f"Error getting collection metadata for {collection_name}: {e}")
            return {}