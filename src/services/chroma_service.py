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
            if not self.vector_store.connect():
                return []
            
            collections_info = []
            collection_names = self.vector_store.list_collections()
            
            for collection_name in collection_names:
                try:
                    metadata = self.vector_store.get_collection_metadata(collection_name)
                    info = {
                        'name': collection_name,
                        'count': metadata.get('count', 0),
                        'metadata': metadata.get('metadata', {})
                    }
                    collections_info.append(info)
                except Exception as e:
                    self.logger.warning(f"Could not get info for collection {collection_name}: {e}")
                    collections_info.append({
                        'name': collection_name,
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
            if not self.vector_store.connect():
                return False
                
            collection_names = self.vector_store.list_collections()
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
            if not self.vector_store.connect():
                return {'error': 'Not connected to ChromaDB'}
            
            if not self.collection_exists(collection_name):
                return {'error': 'Collection does not exist'}
            
            metadata = self.vector_store.get_collection_metadata(collection_name)
            
            return {
                'name': collection_name,
                'count': metadata.get('count', 0),
                'metadata': metadata.get('metadata', {})
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
            if not self.vector_store.connect():
                return False
            
            if self.collection_exists(collection_name):
                self.logger.info(f"Collection {collection_name} already exists")
                return True
            
            # Use the vector_store init_collection method
            success = self.vector_store.init_collection(collection_name)
            if success:
                self.logger.info(f"Created collection {collection_name}")
            return success
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
            if not self.vector_store.connect():
                return False
            
            if not self.collection_exists(collection_name):
                self.logger.info(f"Collection {collection_name} does not exist")
                return True
            
            success = self.vector_store.delete_collection(collection_name)
            if success:
                self.logger.info(f"Deleted collection {collection_name}")
            return success
        except Exception as e:
            self.logger.error(f"Error deleting collection {collection_name}: {e}")
            return False
    
    def list_collections(self) -> List[str]:
        """List all collection names
        
        Returns:
            List[str]: List of collection names
        """
        try:
            if not self.vector_store.connect():
                return []
                
            return self.vector_store.list_collections()
        except Exception as e:
            self.logger.error(f"Error listing collections: {e}")
            return []
