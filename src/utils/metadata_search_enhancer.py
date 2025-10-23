"""
Metadata Search Enhancer for improving vector search accuracy.
Includes query reformatting and BM25 ranking functionality.
"""

import logging
import re
import nltk
from typing import List, Dict, Any, Tuple
from rank_bm25 import BM25Okapi
from src.utils.llm_engine import LLMEngine

# Download required NLTK data
try:
    nltk.data.find('tokenizers/punkt')
    nltk.data.find('corpora/stopwords')
except LookupError:
    import ssl
    try:
        _create_unverified_https_context = ssl._create_unverified_context
    except AttributeError:
        pass
    else:
        ssl._create_default_https_context = _create_unverified_https_context
    
    nltk.download('punkt', quiet=True)
    nltk.download('stopwords', quiet=True)

from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords

logger = logging.getLogger('text2sql.metadata_enhancer')

class MetadataSearchEnhancer:
    """Enhances metadata search with query reformatting and BM25 ranking"""
    
    def __init__(self):
        """Initialize the metadata search enhancer"""
        self.logger = logging.getLogger('text2sql.metadata_enhancer')
        self.llm_engine = LLMEngine()
        
        # Initialize NLTK components
        try:
            self.stop_words = set(stopwords.words('english'))
        except Exception as e:
            self.logger.warning(f"Could not load stopwords: {e}")
            self.stop_words = set()
    
    def reformat_query_for_vector_search(self, user_query: str) -> str:
        """
        Reformat user query to match the schema vectorization format for better accuracy.
        
        Args:
            user_query: Original user query in free text format
            
        Returns:
            str: Reformatted query optimized for vector search
        """
        try:
            # Prompt to reformat user query to match schema format
            reformat_prompt = f"""
You are a database expert. The user is searching for database schema information. The schema is vectorized in this standardized format:

"Database: [database_name] Table: [table_name] Table Description: [description] Column: [column_name] Datatype: [datatype] primary key Description: [description]"

User's query: "{user_query}"

Reformat this query to match the schema format and improve vector search accuracy. Consider:

1. If asking about tables, include "Table:" prefix
2. If asking about columns, include "Column:" prefix  
3. If asking about databases, include "Database:" prefix
4. If asking about datatypes, include "Datatype:" prefix
5. If asking about primary keys, include "primary key"
6. If asking about descriptions, include "Description:" prefix
7. Convert synonyms to standard database terms:
   - "field" → "column"
   - "schema", "db" → "database"
   - "relation" → "table"
   - "type" → "datatype"
   - "key", "id" → "primary key"

Examples:
- "show me customer table" → "Table: customer"
- "what columns are in users" → "Table: users Column:"
- "find email field" → "Column: email"
- "primary key of orders" → "Table: orders primary key"
- "user information columns" → "Table: user Column: Description: information"
- "customer database schema" → "Database: customer"
- "datatypes in products table" → "Table: products Datatype:"

Return only the reformatted query, nothing else.
            """
            
            formatted_prompt = [
                {"role": "system", "content": "You are a database expert. Reformat user queries to match the schema vectorization format for better vector search accuracy. Return only the reformatted query without any explanations."},
                {"role": "user", "content": reformat_prompt}
            ]
            
            reformatted_query = self.llm_engine.generate_completion(formatted_prompt, log_prefix="Query Reformatting")
            reformatted_query = reformatted_query.strip()
            
            self.logger.info(f"Query reformatted: '{user_query}' → '{reformatted_query}'")
            
            return reformatted_query
            
        except Exception as e:
            self.logger.error(f"Error reformatting query: {str(e)}", exc_info=True)
            # Return original query if reformatting fails
            return user_query
    
    def _preprocess_text_for_bm25(self, text: str) -> List[str]:
        """
        Preprocess text for BM25 scoring by tokenizing and removing stop words.
        
        Args:
            text: Text to preprocess
            
        Returns:
            List[str]: List of processed tokens
        """
        try:
            # Convert to lowercase and tokenize
            tokens = word_tokenize(text.lower())
            
            # Remove non-alphanumeric tokens and stop words
            tokens = [token for token in tokens if token.isalnum() and token not in self.stop_words]
            
            return tokens
            
        except Exception as e:
            self.logger.warning(f"Error preprocessing text for BM25: {e}")
            # Fallback to simple split
            return text.lower().split()
    
    def apply_bm25_reranking(self, query: str, results: List[Dict[str, Any]], 
                           top_k: int = None) -> List[Dict[str, Any]]:
        """
        Apply BM25 scoring to rerank vector search results.
        
        Args:
            query: Original search query
            results: List of vector search results
            top_k: Number of top results to return (None to return all)
            
        Returns:
            List[Dict]: Reranked results with BM25 scores
        """
        if not results:
            return results
            
        try:
            self.logger.info(f"Applying BM25 reranking to {len(results)} results")
            
            # Extract text content from results for BM25
            documents = []
            for result in results:
                text = result.get('text', '')
                if not text:
                    text = f"{result.get('workspace', '')} {result.get('table', '')} {result.get('column', '')}"
                documents.append(text)
            
            # Preprocess documents and query for BM25
            processed_docs = [self._preprocess_text_for_bm25(doc) for doc in documents]
            processed_query = self._preprocess_text_for_bm25(query)
            
            # Initialize BM25
            bm25 = BM25Okapi(processed_docs)
            
            # Get BM25 scores
            bm25_scores = bm25.get_scores(processed_query)
            
            # Add BM25 scores to results
            for i, result in enumerate(results):
                result['bm25_score'] = float(bm25_scores[i])
                
                # Create a combined score (weighted average of vector similarity and BM25)
                vector_score = result.get('similarity', 0.0)
                bm25_score = result['bm25_score']
                
                # Normalize BM25 score to 0-1 range (using max score in results)
                max_bm25 = max(bm25_scores) if max(bm25_scores) > 0 else 1.0
                normalized_bm25 = bm25_score / max_bm25
                
                # Weighted combination: 60% vector similarity, 40% BM25
                result['combined_score'] = (0.6 * vector_score) + (0.4 * normalized_bm25)
            
            # Sort by combined score (higher is better)
            reranked_results = sorted(results, key=lambda x: x.get('combined_score', 0), reverse=True)
            
            # Apply top_k limit if specified
            if top_k:
                reranked_results = reranked_results[:top_k]
            
            self.logger.info(f"BM25 reranking completed. Top result combined score: {reranked_results[0].get('combined_score', 0):.4f}")
            
            return reranked_results
            
        except Exception as e:
            self.logger.error(f"Error applying BM25 reranking: {str(e)}", exc_info=True)
            # Return original results if BM25 fails
            return results
    
    def enhance_metadata_search(self, user_query: str, vector_search_results: List[Dict[str, Any]], 
                              apply_bm25: bool = True, top_k: int = None) -> Tuple[str, List[Dict[str, Any]]]:
        """
        Apply all enhancements to metadata search results.
        
        Args:
            user_query: Original user query
            vector_search_results: Results from vector search
            apply_bm25: Whether to apply BM25 reranking
            top_k: Number of top results to return
            
        Returns:
            Tuple[str, List[Dict]]: Reformatted query and enhanced results
        """
        try:
            # Step 1: Reformat query for better vector search (for logging/debugging)
            reformatted_query = self.reformat_query_for_vector_search(user_query)
            
            # Step 2: Apply BM25 reranking if requested
            enhanced_results = vector_search_results
            if apply_bm25 and vector_search_results:
                enhanced_results = self.apply_bm25_reranking(user_query, vector_search_results, top_k)
            
            self.logger.info(f"Metadata search enhancement completed. Results: {len(enhanced_results)}")
            
            return reformatted_query, enhanced_results
            
        except Exception as e:
            self.logger.error(f"Error in metadata search enhancement: {str(e)}", exc_info=True)
            return user_query, vector_search_results
    
    def get_reformatted_query_for_vector_search(self, user_query: str) -> str:
        """
        Get a reformatted version of the user query optimized for vector search.
        This method can be used before performing the vector search.
        
        Args:
            user_query: Original user query
            
        Returns:
            str: Reformatted query for vector search
        """
        return self.reformat_query_for_vector_search(user_query)
