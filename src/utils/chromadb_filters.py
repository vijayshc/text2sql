"""
ChromaDB Filter Helper Utility

This module provides essential filter functions for ChromaDB compatibility.
"""

from typing import Dict, Any, Union
import logging

logger = logging.getLogger('text2sql.chromadb_filters')


def create_rating_filter(rating: int) -> Dict[str, Any]:
    """Create a feedback rating filter
    
    Args:
        rating: The rating to filter by (e.g., 1 for positive feedback)
        
    Returns:
        Dict: ChromaDB where clause for rating filtering
    """
    return {"feedback_rating": rating}


def create_chunk_id_filter(chunk_id: Union[str, int]) -> Dict[str, Any]:
    """Create a chunk ID filter for knowledge base chunks
    
    Args:
        chunk_id: The chunk ID to filter by
        
    Returns:
        Dict: ChromaDB where clause for chunk ID filtering
    """
    return {"chunk_id": chunk_id}
