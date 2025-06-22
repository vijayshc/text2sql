"""
ChromaDB service for additional vector database operations.
This service provides helper functions for ChromaDB operations.
"""

import logging
from typing import List, Dict, Any, Optional
from src.utils.vector_store import VectorStore

logger = logging.getLogger('text2sql.chroma')

class ChromaService:
    """Service class for ChromaDB operations"""
    
    def __init__(self):
        """Initialize the ChromaDB service"""
        self.logger = logging.getLogger('text2sql.chroma')
        self.vector_store = VectorStore()
        
    def get_collections_info(self) -> List[Dict[str, Any]]:
        """Get information about all collections
        
        Returns:
            List[Dict]: List of collection information
        """
        try:
            if not self.vector_store.client and not self.vector_store.connect():
                return []
            
            collections_info = []
            collection_list = self.vector_store.client.list_collections()
            
            for collection in collection_list:
                try:
                    col_obj = self.vector_store.client.get_collection(name=collection.name)
                    info = {
                        'name': collection.name,
                        'count': col_obj.count(),
                        'metadata': getattr(collection, 'metadata', {})
                    }
                    collections_info.append(info)
                except Exception as e:
                    self.logger.warning(f"Could not get info for collection {collection.name}: {e}")
                    collections_info.append({
                        'name': collection.name,
                        'count': 0,
                        'error': str(e)
                    })
            
            return collections_info
        except Exception as e:
            self.logger.error(f"Error getting collections info: {e}")
            return []
    
    def collection_exists(self, collection_name: str) -> bool:
        """Check if a collection exists
        
        Args:
            collection_name: Name of the collection to check
            
        Returns:
            bool: True if collection exists, False otherwise
        """
        try:
            if not self.vector_store.client and not self.vector_store.connect():
                return False
                
            collection_list = self.vector_store.client.list_collections()
            collection_names = [col.name for col in collection_list]
            return collection_name in collection_names
        except Exception as e:
            self.logger.error(f"Error checking collection existence: {e}")
            return False
    
    def get_collection_stats(self, collection_name: str) -> Dict[str, Any]:
        """Get statistics for a specific collection
        
        Args:
            collection_name: Name of the collection
            
        Returns:
            Dict: Collection statistics
        """
        try:
            if not self.vector_store.client and not self.vector_store.connect():
                return {'error': 'Not connected to ChromaDB'}
            
            if not self.collection_exists(collection_name):
                return {'error': 'Collection does not exist'}
            
            collection = self.vector_store.client.get_collection(name=collection_name)
            
            return {
                'name': collection_name,
                'count': collection.count(),
                'metadata': getattr(collection, 'metadata', {})
            }
        except Exception as e:
            self.logger.error(f"Error getting collection stats for {collection_name}: {e}")
            return {'error': str(e)}
    
    def create_collection_with_metadata(self, collection_name: str, metadata: Dict[str, Any] = None) -> bool:
        """Create a collection with metadata
        
        Args:
            collection_name: Name of the collection to create
            metadata: Optional metadata for the collection
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            if not self.vector_store.client and not self.vector_store.connect():
                return False
            
            if self.collection_exists(collection_name):
                self.logger.info(f"Collection {collection_name} already exists")
                return True
            
            # Create collection with metadata if provided
            if metadata:
                collection = self.vector_store.client.create_collection(
                    name=collection_name,
                    embedding_function=self.vector_store.embedding_function,
                    metadata=metadata
                )
            else:
                collection = self.vector_store.client.create_collection(
                    name=collection_name,
                    embedding_function=self.vector_store.embedding_function
                )
            
            self.logger.info(f"Created collection {collection_name}")
            return True
        except Exception as e:
            self.logger.error(f"Error creating collection {collection_name}: {e}")
            return False
    
    def delete_collection(self, collection_name: str) -> bool:
        """Delete a collection
        
        Args:
            collection_name: Name of the collection to delete
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            if not self.vector_store.client and not self.vector_store.connect():
                return False
            
            if not self.collection_exists(collection_name):
                self.logger.info(f"Collection {collection_name} does not exist")
                return True
            
            self.vector_store.client.delete_collection(name=collection_name)
            self.logger.info(f"Deleted collection {collection_name}")
            return True
        except Exception as e:
            self.logger.error(f"Error deleting collection {collection_name}: {e}")
            return False
    
    def list_collections(self) -> List[str]:
        """List all collection names
        
        Returns:
            List[str]: List of collection names
        """
        try:
            if not self.vector_store.client and not self.vector_store.connect():
                return []
                
            return self.vector_store.list_collections()
        except Exception as e:
            self.logger.error(f"Error listing collections: {e}")
            return []
