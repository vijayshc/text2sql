"""
Knowledge Manager for Text2SQL project.
Handles document processing, chunking, embedding, and retrieval.
"""

import os
import logging
import uuid
import json
import tempfile
import shutil
import time
from typing import List, Dict, Any, Tuple, Optional
import threading
from datetime import datetime
import numpy as np
import sqlite3
from markitdown import MarkItDown
from src.utils.database import get_db_session
from src.utils.vector_store import VectorStore
from src.utils.llm_engine import LLMEngine
from config.config import UPLOADS_DIR, CHUNK_SIZE, CHUNK_OVERLAP

# Create logger
logger = logging.getLogger('text2sql.knowledge')

class KnowledgeManager:
    """Manages knowledge base documents, chunking, embedding, and retrieval"""
    
    def __init__(self):
        """Initialize the knowledge manager"""
        self.logger = logging.getLogger('text2sql.knowledge')
        self.logger.info("Initializing Knowledge Manager")
        
        # Ensure uploads directory exists
        os.makedirs(UPLOADS_DIR, exist_ok=True)
        
        # Initialize markitdown converter
        self.md_converter = MarkItDown()
        
        # Initialize vector store
        self.vector_store = VectorStore()
        self.vector_store.connect()
        self.vector_store.init_collection('knowledge_chunks')
        
        # Initialize LLM engine
        self.llm_engine = LLMEngine()
        
        # Dictionary to track processing status of documents
        self.processing_status = {}
        
        # Connect to SQLite database directly
        db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'text2sql.db')
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        
        # Create necessary tables if they don't exist
        self._create_tables()
        
    def _create_tables(self):
        """Create necessary database tables if they don't exist"""
        cursor = self.conn.cursor()
        
        # Create documents table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS knowledge_documents (
                id TEXT PRIMARY KEY,
                original_filename TEXT NOT NULL,
                file_path TEXT NOT NULL,
                content_type TEXT,
                status TEXT NOT NULL,
                created_at TIMESTAMP NOT NULL,
                updated_at TIMESTAMP NOT NULL,
                processed_at TIMESTAMP,
                error TEXT
            )
        ''')
        
        # Create document tags table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS knowledge_document_tags (
                id TEXT PRIMARY KEY,
                document_id TEXT NOT NULL,
                tag TEXT NOT NULL,
                created_at TIMESTAMP NOT NULL,
                FOREIGN KEY (document_id) REFERENCES knowledge_documents(id) ON DELETE CASCADE
            )
        ''')
        
        # Create chunks table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS knowledge_chunks (
                id TEXT PRIMARY KEY,
                document_id TEXT NOT NULL,
                chunk_index INTEGER NOT NULL,
                content TEXT NOT NULL,
                embedding_id TEXT,
                created_at TIMESTAMP NOT NULL,
                FOREIGN KEY (document_id) REFERENCES knowledge_documents(id) ON DELETE CASCADE
            )
        ''')
        
        # Create queries table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS knowledge_queries (
                id TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                query TEXT NOT NULL,
                answer TEXT NOT NULL,
                created_at TIMESTAMP NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        ''')
        
        self.conn.commit()
    
    def process_document(self, file_path: str, original_filename: str, tags: List[str] = None) -> str:
        """Process a document, convert to markdown, chunk it and store in vector database
        
        Args:
            file_path: Path to the uploaded file
            original_filename: Original filename
            tags: List of tags to associate with the document
            
        Returns:
            str: Document ID
        """
        document_id = str(uuid.uuid4())
        now = datetime.now().isoformat()
        
        # Get file extension
        _, ext = os.path.splitext(original_filename)
        content_type = ext.lower().strip('.')
        
        # Save document info to database
        cursor = self.conn.cursor()
        cursor.execute(
            'INSERT INTO knowledge_documents (id, original_filename, file_path, content_type, status, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)',
            (document_id, original_filename, file_path, content_type, 'processing', now, now)
        )
        
        # Save tags if provided
        if tags and isinstance(tags, list) and len(tags) > 0:
            for tag in tags:
                tag = tag.strip().lower()  # Normalize tags
                if tag:
                    tag_id = str(uuid.uuid4())
                    cursor.execute(
                        'INSERT INTO knowledge_document_tags (id, document_id, tag, created_at) VALUES (?, ?, ?, ?)',
                        (tag_id, document_id, tag, now)
                    )
        
        self.conn.commit()
        
        # Update processing status
        self.processing_status[document_id] = {
            'status': 'processing',
            'message': 'Document upload complete, starting conversion'
        }
        
        # Start processing in a separate thread
        threading.Thread(
            target=self._process_document_async,
            args=(document_id, file_path, content_type)
        ).start()
        
        return document_id
        
    def _process_document_async(self, document_id: str, file_path: str, content_type: str):
        """Process document asynchronously
        
        Args:
            document_id: Document ID
            file_path: Path to the document file
            content_type: File type/extension
        """
        try:
            self.logger.info(f"Starting document processing for {document_id}")
            
            # Update status
            self.processing_status[document_id] = {
                'status': 'processing',
                'message': 'Converting document to markdown'
            }
            
            # Convert document to markdown using markitdown
            self.logger.info(f"Converting {file_path} to markdown")
            result = self.md_converter.convert(file_path)
            markdown_content = result.text_content
            
            # Update status
            self.processing_status[document_id] = {
                'status': 'processing',
                'message': 'Chunking document content'
            }
            
            # Chunk the markdown content
            chunks = self._chunk_text(markdown_content, CHUNK_SIZE, CHUNK_OVERLAP)
            self.logger.info(f"Created {len(chunks)} chunks for document {document_id}")
            
            # Save chunks to database and create embeddings
            self.logger.info(f"Saving chunks and creating embeddings for document {document_id}")
            self._save_chunks(document_id, chunks)
            
            # Update document status to completed
            now = datetime.now().isoformat()
            cursor = self.conn.cursor()
            cursor.execute(
                'UPDATE knowledge_documents SET status = ?, updated_at = ?, processed_at = ? WHERE id = ?',
                ('completed', now, now, document_id)
            )
            self.conn.commit()
            
            # Update processing status
            self.processing_status[document_id] = {
                'status': 'completed',
                'message': 'Document processing completed successfully'
            }
            
            self.logger.info(f"Document {document_id} processing completed successfully")
            
        except Exception as e:
            self.logger.error(f"Error processing document {document_id}: {str(e)}", exc_info=True)
            
            # Update document status to error
            now = datetime.now().isoformat()
            cursor = self.conn.cursor()
            cursor.execute(
                'UPDATE knowledge_documents SET status = ?, updated_at = ?, error = ? WHERE id = ?',
                ('error', now, str(e), document_id)
            )
            self.conn.commit()
            
            # Update processing status
            self.processing_status[document_id] = {
                'status': 'error',
                'message': f'Error processing document: {str(e)}'
            }
    
    def _chunk_text(self, text: str, chunk_size: int, chunk_overlap: int) -> List[str]:
        """Split text into overlapping chunks
        
        Args:
            text: Text to chunk
            chunk_size: Size of each chunk in characters
            chunk_overlap: Overlap between chunks in characters
            
        Returns:
            List of text chunks
        """
        if not text:
            return []
            
        chunks = []
        
        # Split text by paragraphs to avoid breaking mid-paragraph
        paragraphs = text.split('\n\n')
        current_chunk = ""
        
        for para in paragraphs:
            # If adding this paragraph would exceed chunk size, save current chunk and start a new one
            if len(current_chunk) + len(para) > chunk_size and current_chunk:
                chunks.append(current_chunk.strip())
                # Start new chunk with overlap from previous chunk
                words = current_chunk.split()
                # Calculate how many words to keep for overlap
                overlap_word_count = min(len(words), int(chunk_overlap / 5))  # Approximate 5 chars per word
                current_chunk = ' '.join(words[-overlap_word_count:]) + '\n\n'
            
            current_chunk += para + '\n\n'
            
            # If current chunk exceeds chunk size, break it down further
            while len(current_chunk) > chunk_size:
                chunks.append(current_chunk[:chunk_size].strip())
                # Start new chunk with overlap from previous chunk
                current_chunk = current_chunk[chunk_size - chunk_overlap:]
        
        # Add the last chunk if not empty
        if current_chunk.strip():
            chunks.append(current_chunk.strip())
        
        return chunks
    
    def process_text_content(self, content_name: str, content_type: str, content: str, tags: List[str] = None) -> str:
        """Process text content, chunk it and store in vector database
        
        Args:
            content_name: Name of the content
            content_type: Type of content
            content: The actual text content
            tags: List of tags to associate with the document
            
        Returns:
            str: Document ID
        """
        document_id = str(uuid.uuid4())
        now = datetime.now().isoformat()
        
        # Temporary file for consistency with file-based implementation
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as temp_file:
            temp_file.write(content)
            temp_file_path = temp_file.name
        
        # Save document info to database
        cursor = self.conn.cursor()
        cursor.execute(
            'INSERT INTO knowledge_documents (id, original_filename, file_path, content_type, status, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)',
            (document_id, content_name, temp_file_path, content_type, 'processing', now, now)
        )
        
        # Save tags if provided
        if tags and isinstance(tags, list) and len(tags) > 0:
            for tag in tags:
                tag = tag.strip().lower()  # Normalize tags
                if tag:
                    tag_id = str(uuid.uuid4())
                    cursor.execute(
                        'INSERT INTO knowledge_document_tags (id, document_id, tag, created_at) VALUES (?, ?, ?, ?)',
                        (tag_id, document_id, tag, now)
                    )
        
        self.conn.commit()
        
        # Update processing status
        self.processing_status[document_id] = {
            'status': 'processing',
            'message': 'Text content received, starting processing'
        }
        
        # Start processing in a separate thread
        threading.Thread(
            target=self._process_text_content_async,
            args=(document_id, content, temp_file_path)
        ).start()
        
        return document_id
        
    def _process_text_content_async(self, document_id: str, content: str, temp_file_path: str):
        """Process text content asynchronously
        
        Args:
            document_id: Document ID
            content: Text content
            temp_file_path: Path to temporary file
        """
        try:
            self.logger.info(f"Starting text content processing for {document_id}")
            
            # Update status
            self.processing_status[document_id] = {
                'status': 'processing',
                'message': 'Chunking text content'
            }
            
            # Chunk the content directly
            chunks = self._chunk_text(content, CHUNK_SIZE, CHUNK_OVERLAP)
            self.logger.info(f"Created {len(chunks)} chunks for document {document_id}")
            
            # Save chunks to database and create embeddings
            self.logger.info(f"Saving chunks and creating embeddings for document {document_id}")
            self._save_chunks(document_id, chunks)
            
            # Update document status to completed
            now = datetime.now().isoformat()
            cursor = self.conn.cursor()
            cursor.execute(
                'UPDATE knowledge_documents SET status = ?, updated_at = ?, processed_at = ? WHERE id = ?',
                ('completed', now, now, document_id)
            )
            self.conn.commit()
            
            # Update processing status
            self.processing_status[document_id] = {
                'status': 'completed',
                'message': 'Text content processing completed successfully'
            }
            
            # Clean up temporary file
            try:
                os.unlink(temp_file_path)
                self.logger.info(f"Deleted temporary file {temp_file_path}")
            except Exception as e:
                self.logger.warning(f"Failed to delete temporary file {temp_file_path}: {str(e)}")
            
            self.logger.info(f"Document {document_id} processing completed successfully")
            
        except Exception as e:
            self.logger.error(f"Error processing text content {document_id}: {str(e)}", exc_info=True)
            
            # Update document status to error
            now = datetime.now().isoformat()
            cursor = self.conn.cursor()
            cursor.execute(
                'UPDATE knowledge_documents SET status = ?, updated_at = ?, error = ? WHERE id = ?',
                ('error', now, str(e), document_id)
            )
            self.conn.commit()
            
            # Update processing status
            self.processing_status[document_id] = {
                'status': 'error',
                'message': f'Error processing text content: {str(e)}'
            }
            
            # Clean up temporary file
            try:
                os.unlink(temp_file_path)
            except:
                pass
    
    def _save_chunks(self, document_id: str, chunks: List[str]):
        """Save chunks to database and create embeddings
        
        Args:
            document_id: Document ID
            chunks: List of text chunks
        """
        cursor = self.conn.cursor()
        
        for i, chunk in enumerate(chunks):
            # Generate unique chunk ID
            chunk_id = str(uuid.uuid4())
            
            # Create embedding for the chunk
            try:
                # Update status
                self.processing_status[document_id] = {
                    'status': 'processing',
                    'message': f'Creating embedding for chunk {i+1} of {len(chunks)}'
                }
                
                # Create embedding using LLM engine
                embedding = self._get_embedding(chunk)
                
                # Save embedding to vector store
                self.vector_store.insert_embedding(
                    'knowledge_chunks', 
                    i,  # Use chunk index as the ID 
                    embedding,
                    chunk,
                    {'document_id': document_id, 'chunk_id': chunk_id}
                )
                
                # Save chunk to database
                now = datetime.now().isoformat()
                cursor.execute(
                    'INSERT INTO knowledge_chunks (id, document_id, chunk_index, content, embedding_id, created_at) VALUES (?, ?, ?, ?, ?, ?)',
                    (chunk_id, document_id, i, chunk, str(i), now)
                )
                
            except Exception as e:
                self.logger.error(f"Error creating embedding for chunk {i} of document {document_id}: {str(e)}", exc_info=True)
        
        self.conn.commit()
    
    # _get_embedding_model method has been moved to LLMEngine class
        
    def _get_embedding(self, text: str) -> List[float]:
        """Get embedding for a text using the centralized LLM engine
        
        Args:
            text: Text to embed
            
        Returns:
            Vector embedding
        """
        # Use the centralized LLM engine to generate embeddings
        embedding = self.llm_engine.generate_embedding(text)
        
        # Convert to list if it's a numpy array
        if isinstance(embedding, np.ndarray):
            return embedding.tolist()
        return embedding
    
    def get_document_status(self, document_id: str) -> Dict[str, Any]:
        """Get the processing status of a document
        
        Args:
            document_id: Document ID
            
        Returns:
            Status information
        """
        # Check in-memory status first
        if document_id in self.processing_status:
            return self.processing_status[document_id]
        
        # If not in memory, check database
        cursor = self.conn.cursor()
        cursor.execute('SELECT status, error, processed_at FROM knowledge_documents WHERE id = ?', (document_id,))
        row = cursor.fetchone()
        
        if not row:
            return {'status': 'not_found', 'message': 'Document not found'}
        
        status, error, processed_at = row
        
        if status == 'completed':
            return {'status': status, 'message': 'Document processing completed successfully', 'processed_at': processed_at}
        elif status == 'error':
            return {'status': status, 'message': f'Error processing document: {error}'}
        else:
            return {'status': status, 'message': 'Document status unknown'}
    
    def list_documents(self) -> List[Dict[str, Any]]:
        """Get a list of all documents in the knowledge base
        
        Returns:
            List of document information
        """
        cursor = self.conn.cursor()
        cursor.execute(
            'SELECT id, original_filename, content_type, status, created_at, processed_at FROM knowledge_documents ORDER BY created_at DESC'
        )
        
        documents = []
        for row in cursor.fetchall():
            doc_id, filename, content_type, status, created_at, processed_at = row
            
            # Get chunk count for this document
            cursor.execute('SELECT COUNT(*) FROM knowledge_chunks WHERE document_id = ?', (doc_id,))
            chunk_count = cursor.fetchone()[0]
            
            # Get tags for this document
            tags = self.get_document_tags(doc_id)
            
            documents.append({
                'id': doc_id,
                'filename': filename,
                'content_type': content_type,
                'status': status,
                'created_at': created_at,
                'processed_at': processed_at,
                'chunk_count': chunk_count,
                'tags': tags
            })
        
        return documents
        
    def get_document_tags(self, document_id: str) -> List[str]:
        """Get tags for a specific document
        
        Args:
            document_id: Document ID
            
        Returns:
            List of tags
        """
        cursor = self.conn.cursor()
        cursor.execute('SELECT tag FROM knowledge_document_tags WHERE document_id = ?', (document_id,))
        return [row[0] for row in cursor.fetchall()]
        
    def get_all_tags(self) -> List[str]:
        """Get a list of all unique tags in the system
        
        Returns:
            List of unique tags
        """
        cursor = self.conn.cursor()
        cursor.execute('SELECT DISTINCT tag FROM knowledge_document_tags ORDER BY tag')
        return [row[0] for row in cursor.fetchall()]
        
    def _get_document_ids_by_tags(self, tags: List[str]) -> List[str]:
        """Get document IDs that have all the specified tags
        
        Args:
            tags: List of tags to filter by
            
        Returns:
            List of document IDs
        """
        if not tags:
            return None
            
        # Normalize tags
        normalized_tags = [tag.strip().lower() for tag in tags if tag.strip()]
        if not normalized_tags:
            return None
            
        # Construct SQL query to find documents that have ALL the specified tags
        # This uses a GROUP BY and HAVING COUNT to ensure documents have all tags
        cursor = self.conn.cursor()
        placeholders = ','.join(['?' for _ in normalized_tags])
        
        query = f"""
            SELECT document_id FROM knowledge_document_tags
            WHERE tag IN ({placeholders})
            GROUP BY document_id
            HAVING COUNT(DISTINCT tag) = ?
        """
        
        # The params include all tags plus the count of tags
        params = normalized_tags + [len(normalized_tags)]
        
        cursor.execute(query, params)
        return [row[0] for row in cursor.fetchall()]
        
    def add_document_tag(self, document_id: str, tag: str) -> bool:
        """Add a tag to a document
        
        Args:
            document_id: Document ID
            tag: Tag to add
            
        Returns:
            True if successful, False otherwise
        """
        try:
            tag = tag.strip().lower()  # Normalize tag
            if not tag:
                return False
                
            now = datetime.now().isoformat()
            tag_id = str(uuid.uuid4())
            
            # Check if this tag already exists for this document
            cursor = self.conn.cursor()
            cursor.execute('SELECT id FROM knowledge_document_tags WHERE document_id = ? AND tag = ?', 
                        (document_id, tag))
            if cursor.fetchone():
                return True  # Tag already exists
                
            # Add the new tag
            cursor.execute(
                'INSERT INTO knowledge_document_tags (id, document_id, tag, created_at) VALUES (?, ?, ?, ?)',
                (tag_id, document_id, tag, now)
            )
            self.conn.commit()
            return True
        except Exception as e:
            self.logger.error(f"Error adding tag to document {document_id}: {str(e)}", exc_info=True)
            return False
            
    def remove_document_tag(self, document_id: str, tag: str) -> bool:
        """Remove a tag from a document
        
        Args:
            document_id: Document ID
            tag: Tag to remove
            
        Returns:
            True if successful, False otherwise
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute('DELETE FROM knowledge_document_tags WHERE document_id = ? AND tag = ?', 
                        (document_id, tag.strip().lower()))
            self.conn.commit()
            return True
        except Exception as e:
            self.logger.error(f"Error removing tag from document {document_id}: {str(e)}", exc_info=True)
            return False
    
    def get_answer(self, query: str, user_id: int, stream: bool = False, tags: List[str] = None):
        """Get an answer to a query using the knowledge base
        
        Args:
            query: The user's question
            user_id: User ID
            stream: Whether to stream the response
            tags: Optional list of tags to filter documents by
            
        Returns:
            If stream=False: Dictionary with answer and supporting information
            If stream=True: A generator yielding text chunks
        """
        try:
            # Create embedding for the query
            query_embedding = self._get_embedding(query)
            
            # If tags are provided, get the document IDs that have these tags
            filtered_document_ids = None
            if tags and isinstance(tags, list) and len(tags) > 0:
                self.logger.info(f"Filtering documents by tags: {tags}")
                filtered_document_ids = self._get_document_ids_by_tags(tags)
                self.logger.info(f"Filtered document IDs: {filtered_document_ids}")
                if not filtered_document_ids:
                    self.logger.info(f"No documents found with tags: {tags}")
                    if stream:
                        # For streaming requests, we need to return a tuple
                        def empty_generator():
                            yield "No documents found with the selected tags."
                        return empty_generator(), []
                    else:
                        return {
                            'success': False,
                            'answer': 'No documents found with the selected tags.',
                            'sources': []
                        }
            
            # Search for similar chunks in vector database
            filter_expr = None
            if filtered_document_ids:
                # Create a filter expression like "document_id in ['id1', 'id2', ...]"
                doc_ids_str = "', '".join(filtered_document_ids)
                filter_expr = f"document_id in ['{doc_ids_str}']" if doc_ids_str else None
            
            
            top_chunks = self.vector_store.search_similar(
                'knowledge_chunks',
                query_embedding,
                limit=50,
                output_fields=['document_id', 'chunk_id', 'query_text'],
                filter_expr=filter_expr
            )


            if not top_chunks:
                return {
                    'success': False,
                    'answer': 'No relevant information found in the knowledge base.',
                    'sources': []
                }
            
            # Get chunk content from database
            chunk_ids = [chunk.get('chunk_id') for chunk in top_chunks]
            
            # Rerank chunks using LLM
            reranked_chunks = self._rerank_chunks(query, chunk_ids)
            
            # Get top 3 chunks after reranking
            top_3_chunk_ids = reranked_chunks[:3]
            
            self.logger.info(f"Top 3 chunks for query '{query}': {top_3_chunk_ids}")
            # Get context chunks (predecessor and successor for each top chunk)
            context_chunks = self._get_context_chunks(top_3_chunk_ids)
            
            # Get source information for citation
            sources = self._get_sources(context_chunks)
            self.logger.info(f"Sources for query '{query}': {sources}")
            # Handle streaming case
            if stream:
                # Generate streaming answer
                stream_generator = self._generate_answer(query, context_chunks, stream=True)
                
                # Create a new generator that saves the complete answer when done
                def save_and_stream():
                    collected_answer = []
                    try:
                        for chunk in stream_generator:
                            collected_answer.append(chunk)
                            yield chunk
                        
                        # After streaming is complete, save the full answer
                        full_answer = "".join(collected_answer)
                        self._save_query(query, full_answer, user_id)
                    except Exception as e:
                        self.logger.error(f"Error in streaming answer: {str(e)}", exc_info=True)
                        yield "\nError occurred during streaming."
                
                # Return exactly two values as a tuple
                return save_and_stream(), sources
            
            # Handle non-streaming case (original behavior)
            else:
                # Generate answer using LLM
                answer = self._generate_answer(query, context_chunks)
                
                # Save the query and answer to database
                self._save_query(query, answer, user_id)
                
                return {
                    'success': True,
                    'answer': answer,
                    'sources': sources
                }
            
        except Exception as e:
            self.logger.info(f"Error answering query '{query}': {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': str(e),
                'answer': 'Sorry, an error occurred while processing your question.'
            }
    
    # _get_reranking_model method has been moved to LLMEngine class
    # _get_reranking_model method has been moved to LLMEngine class
    def _get_reranking_model(self):
        """Get the reranking model from the centralized LLM engine
        
        Returns:
            CrossEncoder: The initialized reranking model (cross-encoder)
        """
        try:
            from src.utils.llm_engine import LLMEngine
            llm_engine = LLMEngine()
            return llm_engine.get_reranking_model()
        except Exception as e:
            self.logger.error(f"Failed to get reranking model from LLMEngine: {str(e)}", exc_info=True)
            return None
            
    def _rerank_chunks(self, query: str, chunk_ids: List[str]) -> List[str]:
        """Rerank chunks using LLM for better relevance
        
        Args:
            query: User query
            chunk_ids: List of chunk IDs to rerank
            
        Returns:
            Reranked list of chunk IDs (most relevant first)
        """
        # If no chunks to rerank, return empty list
        if not chunk_ids:
            return []
        
        try:
            # Get the content for each chunk from the database
            cursor = self.conn.cursor()
            chunk_contents = {}
            for chunk_id in chunk_ids:
                cursor.execute('SELECT content FROM knowledge_chunks WHERE id = ?', (chunk_id,))
                row = cursor.fetchone()
                if row:
                    chunk_contents[chunk_id] = row[0]
            
            # If we couldn't retrieve any chunk contents, return original order
            if not chunk_contents:
                self.logger.warning("No chunk contents found for reranking, returning original order")
                return chunk_ids[:3]
            
            # Prepare candidate pairs for reranking
            reranker = self._get_reranking_model()
            if not reranker:
                self.logger.warning("Reranker not available, returning original chunk order")
                return chunk_ids[:3]
            
            # Create pairs of (query, chunk_content) for each chunk
            candidate_pairs = []
            chunk_id_list = []
            for chunk_id, content in chunk_contents.items():
                candidate_pairs.append((query, content))
                chunk_id_list.append(chunk_id)
            
            # Get reranking scores
            self.logger.info(f"Reranking {len(candidate_pairs)} chunks using cross-encoder")
            rerank_scores = reranker.predict(candidate_pairs)
            
            # Create list of (chunk_id, score) tuples
            ranked_chunks = list(zip(chunk_id_list, rerank_scores))
            
            # Sort by score in descending order
            ranked_chunks.sort(key=lambda x: x[1], reverse=True)
            self.logger.info(f"Reranking complete, top score: {ranked_chunks[0][1] if ranked_chunks else 'N/A'}")
            
            # Extract ordered chunk IDs (most relevant first)
            reranked_ids = [chunk_id for chunk_id, _ in ranked_chunks]
            
            return reranked_ids
            
        except Exception as e:
            self.logger.error(f"Error during chunk reranking: {str(e)}", exc_info=True)
            # If reranking fails, return original order (top 3)
            return chunk_ids[:3]
    
    def _get_context_chunks(self, chunk_ids: List[str]) -> List[Dict[str, Any]]:
        """Get chunks with context (predecessor and successor chunks)
        
        Args:
            chunk_ids: List of primary chunk IDs
            
        Returns:
            List of chunks with their content and metadata
        """
        chunks = []
        cursor = self.conn.cursor()
        
        for chunk_id in chunk_ids:
            # Get the main chunk
            cursor.execute(
                '''
                SELECT c.id, c.document_id, c.chunk_index, c.content, d.original_filename 
                FROM knowledge_chunks c
                JOIN knowledge_documents d ON c.document_id = d.id
                WHERE c.id = ?
                ''',
                (chunk_id,)
            )
            main_chunk = cursor.fetchone()
            
            if not main_chunk:
                continue
                
            chunk_id, doc_id, chunk_index, content, filename = main_chunk
            
            # Get predecessor chunk
            cursor.execute(
                'SELECT id, content FROM knowledge_chunks WHERE document_id = ? AND chunk_index = ?',
                (doc_id, chunk_index - 1)
            )
            predecessor = cursor.fetchone()
            
            # Get successor chunk
            cursor.execute(
                'SELECT id, content FROM knowledge_chunks WHERE document_id = ? AND chunk_index = ?',
                (doc_id, chunk_index + 1)
            )
            successor = cursor.fetchone()
            
            chunk_data = {
                'id': chunk_id,
                'document_id': doc_id,
                'chunk_index': chunk_index,
                'content': content,
                'filename': filename
            }
            
            if predecessor:
                chunk_data['predecessor'] = {
                    'id': predecessor[0],
                    'content': predecessor[1]
                }
                
            if successor:
                chunk_data['successor'] = {
                    'id': successor[0],
                    'content': successor[1]
                }
                
            chunks.append(chunk_data)
        
        return chunks
    
    def _generate_answer(self, query: str, context_chunks: List[Dict[str, Any]], stream: bool = False):
        """Generate an answer to the query using LLM and context chunks
        
        Args:
            query: User query
            context_chunks: Context chunks with their content
            stream: Whether to stream the response
            
        Returns:
            If stream=False: Generated answer as a string
            If stream=True: A generator yielding text chunks
        """
        # Build the context string from the chunks
        context = ""
        
        for i, chunk in enumerate(context_chunks):
            context += f"\n\nDocument: {chunk['filename']}\n"
            
            if 'predecessor' in chunk:
                context += chunk['predecessor']['content'] + "\n\n"
                
            context += chunk['content'] + "\n\n"
            
            if 'successor' in chunk:
                context += chunk['successor']['content']
        
        # Create prompt for LLM
        prompt = [
            {"role": "system", "content": """You are a helpful AI assistant that provides accurate answers based on the given context. 
            If the answer cannot be found in the context, acknowledge that you don't know instead of making up information.
            Provide clear, concise answers and use markdown formatting in your response to improve readability.
            When referring to information from the context, cite the document name."""},
            {"role": "user", "content": f"Context information:\n{context}\n\nQuestion: {query}\n\nProvide a detailed answer to the question based only on the context provided. Use markdown formatting for better readability."}
        ]
        
        try:
            # Generate answer using LLM engine
            return self.llm_engine.generate_completion(prompt, log_prefix="Knowledge QA", stream=stream)
        except Exception as e:
            self.logger.error(f"Error generating answer: {str(e)}", exc_info=True)
            if stream:
                def error_generator():
                    yield "I'm sorry, I couldn't generate an answer based on the available information."
                return error_generator()
            return "I'm sorry, I couldn't generate an answer based on the available information."
    
    def _save_query(self, query: str, answer: str, user_id: int):
        """Save the query and answer to database
        
        Args:
            query: User query
            answer: Generated answer
            user_id: User ID
        """
        query_id = str(uuid.uuid4())
        now = datetime.now().isoformat()
        
        cursor = self.conn.cursor()
        cursor.execute(
            'INSERT INTO knowledge_queries (id, user_id, query, answer, created_at) VALUES (?, ?, ?, ?, ?)',
            (query_id, user_id, query, answer, now)
        )
        self.conn.commit()
    
    def _get_sources(self, context_chunks: List[Dict[str, Any]]) -> List[Dict[str, str]]:
        """Get source information for citation
        
        Args:
            context_chunks: Context chunks with their metadata
            
        Returns:
            List of sources
        """
        sources = []
        
        for chunk in context_chunks:
            sources.append({
                'document': chunk['filename'],
                'chunk_id': chunk['id']
            })
            
        return sources
    
    def _get_document_ids_by_tags(self, tags: List[str]) -> List[str]:
        """Get document IDs that have all the specified tags
        
        Args:
            tags: List of tags to filter by
            
        Returns:
            List of document IDs
        """
        if not tags:
            return None
            
        # Normalize tags
        normalized_tags = [tag.strip().lower() for tag in tags if tag.strip()]
        if not normalized_tags:
            return None
            
        # Construct SQL query to find documents that have ALL the specified tags
        # This uses a GROUP BY and HAVING COUNT to ensure documents have all tags
        cursor = self.conn.cursor()
        placeholders = ','.join(['?' for _ in normalized_tags])
        
        query = f"""
            SELECT document_id FROM knowledge_document_tags
            WHERE tag IN ({placeholders})
            GROUP BY document_id
            HAVING COUNT(DISTINCT tag) = ?
        """
        
        # The params include all tags plus the count of tags
        params = normalized_tags + [len(normalized_tags)]
        
        cursor.execute(query, params)
        return [row[0] for row in cursor.fetchall()]

    def delete_document(self, document_id: str) -> bool:
        """Delete a document and its chunks from the system
        
        Args:
            document_id: Document ID
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Get file path
            cursor = self.conn.cursor()
            cursor.execute('SELECT file_path FROM knowledge_documents WHERE id = ?', (document_id,))
            row = cursor.fetchone()
            
            if not row:
                return False
                
            file_path = row[0]
            
            # Delete file if it exists
            if os.path.exists(file_path):
                os.remove(file_path)
            
            # Get chunk IDs before deleting them from the database
            chunk_ids = []
            cursor.execute('SELECT id FROM knowledge_chunks WHERE document_id = ?', (document_id,))
            for row in cursor.fetchall():
                chunk_ids.append(row[0])
            
            # Delete from database (cascade will delete chunks)
            cursor.execute('DELETE FROM knowledge_documents WHERE id = ?', (document_id,))
            self.conn.commit()
            
            # Remove from processing status dict if present
            if document_id in self.processing_status:
                del self.processing_status[document_id]                # Delete embeddings from vector store
            if chunk_ids and self.vector_store:
                try:
                    # Process deletions in smaller batches to avoid syntax errors
                    self.logger.info(f"Deleting {len(chunk_ids)} chunks from vector store in batches")
                    batch_size = 15  # A reasonable batch size to prevent filter syntax errors
                    
                    # Create batches of chunk IDs
                    for i in range(0, len(chunk_ids), batch_size):
                        batch_chunk_ids = chunk_ids[i:i+batch_size]
                        self.logger.info(f"Processing batch {i//batch_size + 1} with {len(batch_chunk_ids)} chunks")
                        
                        # Delete each chunk individually to avoid syntax issues with the filter expression
                        for chunk_id in batch_chunk_ids:
                            try:
                                # Try to determine if ID is numeric or string
                                try:
                                    # Check if the chunk_id can be converted to an integer
                                    int_id = int(chunk_id)
                                    # If it's a number, use without quotes
                                    filter_expr = f'chunk_id == {int_id}'
                                except ValueError:
                                    # If it's not a number, use with quotes
                                    filter_expr = f'chunk_id == "{chunk_id}"'
                                
                                self.logger.info(f"Deleting chunk with filter: {filter_expr}")
                                self.vector_store.client.delete(
                                    collection_name='knowledge_chunks',
                                    filter=filter_expr
                                )
                            except Exception as chunk_err:
                                self.logger.error(f"Error deleting chunk {chunk_id}: {str(chunk_err)}")
                        
                        # Flush after each batch
                        self.vector_store.client.flush('knowledge_chunks')
                    
                    # Reload the collection after all deletions
                    self.vector_store.client.load_collection('knowledge_chunks')
                    self.logger.info(f"Successfully deleted chunks from vector store for document {document_id}")
                except Exception as e:
                    self.logger.error(f"Error deleting chunks from vector store: {str(e)}", exc_info=True)
                    # Continue despite vector store errors - document is already removed from DB
            
            return True
        except Exception as e:
            self.logger.error(f"Error deleting document {document_id}: {str(e)}", exc_info=True)
            return False