"""
Feedback Manager for Text2SQL application.
Handles storing and retrieving user feedback on SQL queries.
"""

import sqlite3
import logging
import time
import json
import numpy as np
import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from typing import List, Dict, Any, Optional, Tuple

from config.config import DATABASE_URI
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import pickle

class FeedbackManager:
    """Manager class for handling user feedback on SQL queries"""
    
    def __init__(self, connection_string=None):
        """Initialize the feedback manager
        
        Args:
            connection_string (str, optional): SQLAlchemy connection string, defaults to config
        """
        self.logger = logging.getLogger('text2sql.feedback')
        self.connection_string = connection_string or DATABASE_URI
        self.logger.info(f"Feedback manager initialized with connection: {self.connection_string}")
        self.engine = None
        self.embedding_model = None
        
    def connect(self):
        """Establish database connection
        
        Returns:
            bool: True if successful, False otherwise
        """
        start_time = time.time()
        self.logger.info("Attempting database connection")
        
        try:
            self.engine = create_engine(self.connection_string)
            self.logger.info(f"Database connection established in {time.time() - start_time:.2f}s")
            return True
        except Exception as e:
            self.logger.error(f"Database connection error: {str(e)}", exc_info=True)
            print(f"Database connection error: {e}")
            return False
    
    def _get_embedding_model(self):
        """Get or initialize the sentence transformer model for embeddings
        
        Returns:
            SentenceTransformer: The initialized embedding model
        """
        if self.embedding_model is None:
            start_time = time.time()
            self.logger.info("Loading embedding model 'sentence-transformers/all-MiniLM-L12-v2'")
            try:
                self.embedding_model = SentenceTransformer('all-MiniLM-L12-v2')
                self.logger.info(f"Embedding model loaded in {time.time() - start_time:.2f}s")
            except Exception as e:
                self.logger.error(f"Failed to load embedding model: {str(e)}", exc_info=True)
                # Return None if failed to load model
                return None
        return self.embedding_model
    
    def _generate_embedding(self, text: str) -> Optional[bytes]:
        """Generate embedding for the given text
        
        Args:
            text (str): Text to generate embedding for
            
        Returns:
            Optional[bytes]: Serialized embedding vector or None if failed
        """
        model = self._get_embedding_model()
        if not model or not text:
            return None
            
        try:
            start_time = time.time()
            # Generate embedding vector
            embedding = model.encode(text)
            
            # Serialize the numpy array to bytes for storage
            serialized_embedding = pickle.dumps(embedding)
            
            self.logger.debug(f"Generated embedding in {time.time() - start_time:.2f}s " +
                             f"with shape {embedding.shape}")
            return serialized_embedding
            
        except Exception as e:
            self.logger.error(f"Error generating embedding: {str(e)}", exc_info=True)
            return None
            
    def _get_reranking_model(self):
        """Get or initialize a cross-encoder model for more accurate reranking
        
        Returns:
            SentenceTransformer: The initialized reranking model (cross-encoder)
        """
        if not hasattr(self, 'reranking_model') or self.reranking_model is None:
            start_time = time.time()
            self.logger.info("Loading reranking model 'cross-encoder/ms-marco-MiniLM-L-6-v2'")
            try:
                from sentence_transformers import CrossEncoder
                self.reranking_model = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')
                self.logger.info(f"Reranking model loaded in {time.time() - start_time:.2f}s")
            except Exception as e:
                self.logger.error(f"Failed to load reranking model: {str(e)}", exc_info=True)
                return None
        return self.reranking_model
    
    def save_feedback(self, query_text: str, sql_query: str, results_summary: str, 
                      workspace: str, feedback_rating: int, tables_used: List[str], 
                      is_manual_sample: bool = False) -> bool:
        """Save user feedback to database
        
        Args:
            query_text (str): The original natural language query
            sql_query (str): The generated SQL query
            results_summary (str): Summary of the query results (e.g., "10 rows returned")
            workspace (str): Name of the workspace used
            feedback_rating (int): 1 for thumbs up, 0 for thumbs down
            tables_used (List[str]): List of tables used in the query
            is_manual_sample (bool): Flag to indicate if this is a manually added sample
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not self.engine and not self.connect():
            self.logger.error("Failed to connect to database to save feedback")
            return False
            
        try:
            # Convert tables list to comma-separated string
            tables_str = ','.join(tables_used) if tables_used else None
            
            # Generate embedding for the query text
            embedding = self._generate_embedding(query_text)
            
            # Insert feedback into database
            with self.engine.connect() as conn:
                query = text("""
                INSERT INTO query_feedback 
                (query_text, sql_query, results_summary, workspace, feedback_rating, tables_used, embedding, is_manual_sample)
                VALUES (:query_text, :sql_query, :results_summary, :workspace, :feedback_rating, :tables_used, :embedding, :is_manual_sample)
                """)
                
                conn.execute(query, {
                    'query_text': query_text,
                    'sql_query': sql_query,
                    'results_summary': results_summary,
                    'workspace': workspace,
                    'feedback_rating': feedback_rating,
                    'tables_used': tables_str,
                    'embedding': embedding,
                    'is_manual_sample': is_manual_sample
                })
                conn.commit()
            
            if is_manual_sample:
                self.logger.info(f"Saved manual sample for query: '{query_text[:50]}...'")
            else:
                self.logger.info(f"Saved feedback for query: '{query_text[:50]}...' with rating {feedback_rating}")
            return True
            
        except SQLAlchemyError as e:
            self.logger.error(f"Error saving feedback: {str(e)}", exc_info=True)
            return False
    
    def find_similar_queries(self, query_text: str, limit: int = 1, positive_only: bool = True) -> List[Dict[str, Any]]:
        """Find similar previous queries based on vector similarity
        
        Args:
            query_text (str): The natural language query to find similar queries for
            limit (int): Maximum number of similar queries to return
            positive_only (bool): If True, only return queries with positive feedback (thumbs up)
            
        Returns:
            List[Dict]: List of similar queries with their SQL and other details
        """
        if not self.engine and not self.connect():
            self.logger.error("Failed to connect to database to find similar queries")
            return []
            
        try:
            # Generate embedding for the input query
            query_embedding = self._generate_embedding(query_text)
            
            # If embedding generation failed, fall back to text-based search
            if query_embedding is None:
                self.logger.warning("Embedding generation failed, falling back to text-based search")
                return self._find_similar_queries_text_based(query_text, limit, positive_only)
            
            # Deserialize query embedding for comparison
            query_embedding_vector = pickle.loads(query_embedding)
            
            # Fetch stored queries with embeddings
            feedback_filter = "AND feedback_rating = 1" if positive_only else ""
            with self.engine.connect() as conn:
                query = text(f"""
                SELECT feedback_id, query_text, sql_query, results_summary, 
                       workspace, feedback_rating, created_at, tables_used, embedding
                FROM query_feedback
                WHERE embedding IS NOT NULL {feedback_filter}
                """)
                
                result = conn.execute(query)
                candidates = []
                
                for row in result:
                    if row.embedding:
                        # Deserialize stored embedding
                        try:
                            stored_embedding = pickle.loads(row.embedding)
                            # Calculate similarity score
                            similarity = cosine_similarity([query_embedding_vector], [stored_embedding])[0][0]
                            
                            tables_list = row.tables_used.split(',') if row.tables_used else []
                            candidates.append({
                                'feedback_id': row.feedback_id,
                                'query_text': row.query_text,
                                'sql_query': row.sql_query,
                                'results_summary': row.results_summary,
                                'workspace': row.workspace,
                                'feedback_rating': row.feedback_rating,
                                'created_at': row.created_at,
                                'tables_used': tables_list,
                                'similarity': similarity
                            })
                        except Exception as e:
                            self.logger.warning(f"Failed to process embedding for feedback_id {row.feedback_id}: {str(e)}")
                
                # Sort by similarity score (descending) and take top N
                similar_queries = sorted(candidates, key=lambda x: x['similarity'], reverse=True)[:limit]
                
            self.logger.info(f"Found {len(similar_queries)} similar queries using vector similarity for '{query_text[:50]}...'")
            return similar_queries
            
        except SQLAlchemyError as e:
            self.logger.error(f"Error finding similar queries: {str(e)}", exc_info=True)
            return []
    
    def find_similar_queries_with_reranking(self, query_text: str, limit: int = 2, positive_only: bool = True) -> List[Dict[str, Any]]:
        """Find similar previous queries using a two-stage search: vector similarity + reranking
        
        Args:
            query_text (str): The natural language query to find similar queries for
            limit (int): Maximum number of final results to return after reranking
            positive_only (bool): If True, only return queries with positive feedback (thumbs up)
            
        Returns:
            List[Dict]: List of similar queries with their SQL and other details
        """
        if not self.engine and not self.connect():
            self.logger.error("Failed to connect to database to find similar queries")
            return []
            
        try:
            # Stage 1: Vector search to get initial candidates (top 10)
            self.logger.info(f"Stage 1: Vector search for '{query_text[:50]}...'")
            initial_candidates_limit = 10  # Get top 10 candidates from vector search
            
            # Generate embedding for the input query
            query_embedding = self._generate_embedding(query_text)
            
            # If embedding generation failed, fall back to text-based search
            if query_embedding is None:
                self.logger.warning("Embedding generation failed, falling back to text-based search")
                return self._find_similar_queries_text_based(query_text, limit, positive_only)
            
            # Deserialize query embedding for comparison
            query_embedding_vector = pickle.loads(query_embedding)
            
            # Fetch stored queries with embeddings
            feedback_filter = "AND feedback_rating = 1" if positive_only else ""
            with self.engine.connect() as conn:
                query = text(f"""
                SELECT feedback_id, query_text, sql_query, results_summary, 
                       workspace, feedback_rating, created_at, tables_used, embedding, is_manual_sample
                FROM query_feedback
                WHERE embedding IS NOT NULL {feedback_filter}
                """)
                
                result = conn.execute(query)
                candidates = []
                
                for row in result:
                    if row.embedding:
                        # Deserialize stored embedding
                        try:
                            stored_embedding = pickle.loads(row.embedding)
                            # Calculate similarity score
                            similarity = cosine_similarity([query_embedding_vector], [stored_embedding])[0][0]
                            
                            tables_list = row.tables_used.split(',') if row.tables_used else []
                            candidates.append({
                                'feedback_id': row.feedback_id,
                                'query_text': row.query_text,
                                'sql_query': row.sql_query,
                                'results_summary': row.results_summary,
                                'workspace': row.workspace,
                                'feedback_rating': row.feedback_rating,
                                'created_at': row.created_at,
                                'tables_used': tables_list,
                                'similarity': similarity,
                                'is_manual_sample': bool(row.is_manual_sample)
                            })
                        except Exception as e:
                            self.logger.warning(f"Failed to process embedding for feedback_id {row.feedback_id}: {str(e)}")
                
                # Sort by similarity score (descending) and take top N for reranking
                if candidates:
                    candidates = sorted(candidates, key=lambda x: x['similarity'], reverse=True)
                    top_candidates = candidates[:initial_candidates_limit]
                    self.logger.info(f"Found {len(top_candidates)} initial candidates from vector search")
                else:
                    self.logger.warning("No candidates found from vector search")
                    return []
                
                # Stage 2: Rerank the top candidates using a more powerful model
                if len(top_candidates) > limit:
                    self.logger.info(f"Stage 2: Reranking {len(top_candidates)} candidates")
                    reranker = self._get_reranking_model()
                    
                    if reranker:
                        # Prepare candidate pairs for reranking
                        candidate_pairs = [(query_text, candidate['query_text']) for candidate in top_candidates]
                        
                        # Get reranking scores
                        try:
                            rerank_scores = reranker.predict(candidate_pairs)
                            
                            # Add rerank scores to candidates
                            for idx, score in enumerate(rerank_scores):
                                top_candidates[idx]['rerank_score'] = float(score)
                                
                            # Filter out candidates with negative scores (indicating poor relevance)
                            positive_scored_candidates = [c for c in top_candidates if c['rerank_score'] >= 0]
                            
                            if positive_scored_candidates:
                                self.logger.info(f"Found {len(positive_scored_candidates)} candidates with positive reranking scores")
                                # Sort by rerank score (higher is better) among positive scores
                                reranked_candidates = sorted(positive_scored_candidates, key=lambda x: x['rerank_score'], reverse=True)
                                
                                self.logger.info(f"Reranking successful, returning top {min(limit, len(reranked_candidates))} results")
                                return reranked_candidates[:limit]
                            else:
                                self.logger.warning("No candidates with positive reranking scores, falling back to vector search results")
                                return candidates[:limit]
                            
                        except Exception as e:
                            self.logger.error(f"Reranking failed: {str(e)}", exc_info=True)
                            self.logger.info("Falling back to vector search results")
                            return top_candidates[:limit]
                    else:
                        self.logger.warning("Reranker not available, returning vector search results")
                        return top_candidates[:limit]
                else:
                    # Not enough candidates to rerank
                    self.logger.info(f"Less than {limit+1} candidates, skipping reranking")
                    return top_candidates[:limit]
                
        except SQLAlchemyError as e:
            self.logger.error(f"Error in find_similar_queries_with_reranking: {str(e)}", exc_info=True)
            return []
    
    def _find_similar_queries_text_based(self, query_text: str, limit: int = 1, positive_only: bool = True) -> List[Dict[str, Any]]:
        """Fallback method to find similar queries using text-based search
        
        Args:
            query_text (str): The natural language query to find similar queries for
            limit (int): Maximum number of similar queries to return
            positive_only (bool): If True, only return queries with positive feedback (thumbs up)
            
        Returns:
            List[Dict]: List of similar queries with their SQL and other details
        """
        try:
            # Create a simple filter condition based on text similarity
            search_terms = [term for term in query_text.lower().split() if len(term) > 3]
            
            if not search_terms:
                self.logger.warning("No valid search terms found in query")
                return []
                
            # Build a simple LIKE query for each search term
            like_conditions = []
            for term in search_terms:
                like_conditions.append(f"LOWER(query_text) LIKE '%{term}%'")
                
            # Combine conditions
            where_clause = " OR ".join(like_conditions)
            
            # Add feedback filter if positive_only is True
            if positive_only:
                where_clause = f"({where_clause}) AND feedback_rating = 1"
                
            # Execute query to find similar queries
            with self.engine.connect() as conn:
                query = text(f"""
                SELECT feedback_id, query_text, sql_query, results_summary, 
                       workspace, feedback_rating, created_at, tables_used
                FROM query_feedback
                WHERE {where_clause}
                ORDER BY created_at DESC
                LIMIT :limit
                """)
                
                result = conn.execute(query, {'limit': limit})
                similar_queries = []
                
                for row in result:
                    tables_list = row.tables_used.split(',') if row.tables_used else []
                    similar_queries.append({
                        'feedback_id': row.feedback_id,
                        'query_text': row.query_text,
                        'sql_query': row.sql_query,
                        'results_summary': row.results_summary,
                        'workspace': row.workspace,
                        'feedback_rating': row.feedback_rating,
                        'created_at': row.created_at,
                        'tables_used': tables_list
                    })
                    
            self.logger.info(f"Found {len(similar_queries)} similar queries using text-based search for '{query_text[:50]}...'")
            return similar_queries
            
        except SQLAlchemyError as e:
            self.logger.error(f"Error in text-based search: {str(e)}", exc_info=True)
            return []
            
    def get_feedback_stats(self) -> Dict[str, Any]:
        """Get feedback statistics from the database
        
        Returns:
            Dict: Statistics about stored feedback
        """
        if not self.engine and not self.connect():
            self.logger.error("Failed to connect to database to get feedback stats")
            return {'total': 0, 'positive': 0, 'negative': 0}
            
        try:
            with self.engine.connect() as conn:
                query = text("""
                SELECT COUNT(*) as total,
                       SUM(CASE WHEN feedback_rating = 1 THEN 1 ELSE 0 END) as positive,
                       SUM(CASE WHEN feedback_rating = 0 THEN 1 ELSE 0 END) as negative
                FROM query_feedback
                """)
                
                result = conn.execute(query).fetchone()
                
                stats = {
                    'total': result.total or 0,
                    'positive': result.positive or 0,
                    'negative': result.negative or 0
                }
                
            self.logger.info(f"Feedback stats: {stats['total']} total, {stats['positive']} positive, {stats['negative']} negative")
            return stats
            
        except SQLAlchemyError as e:
            self.logger.error(f"Error getting feedback stats: {str(e)}", exc_info=True)
            return {'total': 0, 'positive': 0, 'negative': 0}
            
    def get_samples(self, page: int = 1, limit: int = 10, search_query: str = None) -> Tuple[List[Dict[str, Any]], int]:
        """Get paginated list of sample entries (manual + positive feedback)
        
        Args:
            page (int): Page number (1-indexed)
            limit (int): Number of items per page
            search_query (str, optional): Filter samples by query text
            
        Returns:
            Tuple[List[Dict], int]: List of samples and total count
        """
        if not self.engine and not self.connect():
            self.logger.error("Failed to connect to database to get samples")
            return [], 0
            
        try:
            offset = (page - 1) * limit
            
            # Build where clause
            where_clause = "feedback_rating = 1"  # Only positive feedback samples
            params = {'limit': limit, 'offset': offset}
            
            if search_query:
                where_clause += " AND LOWER(query_text) LIKE :search_query"
                params['search_query'] = f"%{search_query.lower()}%"
            
            with self.engine.connect() as conn:
                # Get total count
                count_query = text(f"SELECT COUNT(*) as total FROM query_feedback WHERE {where_clause}")
                total = conn.execute(count_query, params).scalar() or 0
                
                # Get samples
                query = text(f"""
                SELECT feedback_id, query_text, sql_query, results_summary, 
                       workspace, feedback_rating, created_at, tables_used, is_manual_sample
                FROM query_feedback
                WHERE {where_clause}
                ORDER BY created_at DESC
                LIMIT :limit OFFSET :offset
                """)
                
                result = conn.execute(query, params)
                samples = []
                
                for row in result:
                    tables_list = row.tables_used.split(',') if row.tables_used else []
                    samples.append({
                        'feedback_id': row.feedback_id,
                        'query_text': row.query_text,
                        'sql_query': row.sql_query,
                        'results_summary': row.results_summary,
                        'workspace': row.workspace,
                        'feedback_rating': row.feedback_rating,
                        'created_at': row.created_at,
                        'tables_used': tables_list,
                        'is_manual_sample': bool(row.is_manual_sample)
                    })
                
            self.logger.info(f"Retrieved {len(samples)} samples (page {page}, limit {limit})")
            return samples, total
            
        except SQLAlchemyError as e:
            self.logger.error(f"Error getting samples: {str(e)}", exc_info=True)
            return [], 0
    
    def get_sample_by_id(self, sample_id: int) -> Optional[Dict[str, Any]]:
        """Get a single sample entry by ID
        
        Args:
            sample_id (int): ID of the sample to retrieve
            
        Returns:
            Optional[Dict]: Sample data or None if not found
        """
        if not self.engine and not self.connect():
            self.logger.error("Failed to connect to database to get sample")
            return None
            
        try:
            with self.engine.connect() as conn:
                query = text("""
                SELECT feedback_id, query_text, sql_query, results_summary, 
                       workspace, feedback_rating, created_at, tables_used, is_manual_sample
                FROM query_feedback
                WHERE feedback_id = :sample_id
                """)
                
                result = conn.execute(query, {'sample_id': sample_id}).fetchone()
                
                if not result:
                    return None
                    
                tables_list = result.tables_used.split(',') if result.tables_used else []
                sample = {
                    'feedback_id': result.feedback_id,
                    'query_text': result.query_text,
                    'sql_query': result.sql_query,
                    'results_summary': result.results_summary,
                    'workspace': result.workspace,
                    'feedback_rating': result.feedback_rating,
                    'created_at': result.created_at,
                    'tables_used': tables_list,
                    'is_manual_sample': bool(result.is_manual_sample)
                }
                
                return sample
                
        except SQLAlchemyError as e:
            self.logger.error(f"Error getting sample by ID: {str(e)}", exc_info=True)
            return None
    
    def update_sample(self, sample_id: int, data: Dict[str, Any]) -> bool:
        """Update an existing sample
        
        Args:
            sample_id (int): ID of the sample to update
            data (Dict): Updated sample data
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not self.engine and not self.connect():
            self.logger.error("Failed to connect to database to update sample")
            return False
            
        try:
            # Convert tables list to comma-separated string
            tables_used = data.get('tables_used', [])
            tables_str = ','.join(tables_used) if tables_used else None
            
            # Generate new embedding for the updated query text
            embedding = self._generate_embedding(data['query_text'])
            
            with self.engine.connect() as conn:
                query = text("""
                UPDATE query_feedback
                SET query_text = :query_text,
                    sql_query = :sql_query,
                    results_summary = :results_summary,
                    workspace = :workspace,
                    feedback_rating = :feedback_rating,
                    tables_used = :tables_used,
                    embedding = :embedding,
                    is_manual_sample = :is_manual_sample
                WHERE feedback_id = :sample_id
                """)
                
                conn.execute(query, {
                    'sample_id': sample_id,
                    'query_text': data['query_text'],
                    'sql_query': data['sql_query'],
                    'results_summary': data.get('results_summary', ''),
                    'workspace': data.get('workspace', 'Default'),
                    'feedback_rating': data.get('feedback_rating', 1),
                    'tables_used': tables_str,
                    'embedding': embedding,
                    'is_manual_sample': data.get('is_manual_sample', True)
                })
                conn.commit()
                
            self.logger.info(f"Updated sample ID {sample_id}")
            return True
            
        except SQLAlchemyError as e:
            self.logger.error(f"Error updating sample: {str(e)}", exc_info=True)
            return False
    
    def delete_sample(self, sample_id: int) -> bool:
        """Delete a sample
        
        Args:
            sample_id (int): ID of the sample to delete
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not self.engine and not self.connect():
            self.logger.error("Failed to connect to database to delete sample")
            return False
            
        try:
            with self.engine.connect() as conn:
                query = text("DELETE FROM query_feedback WHERE feedback_id = :sample_id")
                conn.execute(query, {'sample_id': sample_id})
                conn.commit()
                
            self.logger.info(f"Deleted sample ID {sample_id}")
            return True
            
        except SQLAlchemyError as e:
            self.logger.error(f"Error deleting sample: {str(e)}", exc_info=True)
            return False
            
    def close(self):
        """Close database connections"""
        self.logger.info("Closing database connection")
        if self.engine:
            self.engine.dispose()
            self.logger.debug("Database engine disposed")