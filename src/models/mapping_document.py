"""
Mapping Document Model
Manages mapping documents (Excel files) within projects.
"""
import sqlite3
import logging
import os
from datetime import datetime
from typing import List, Optional, Dict, Any
from src.utils.database import get_db_connection

logger = logging.getLogger('text2sql')


class MappingDocument:
    """Model for managing mapping documents"""
    
    def __init__(self, id: Optional[int] = None, project_id: int = 0, filename: str = '',
                 file_path: str = '', uploaded_at: Optional[str] = None, uploaded_by: Optional[int] = None):
        self.id = id
        self.project_id = project_id
        self.filename = filename
        self.file_path = file_path
        self.uploaded_at = uploaded_at or datetime.now().isoformat()
        self.uploaded_by = uploaded_by
    
    @classmethod
    def create_table(cls):
        """Create the mapping_documents table if it doesn't exist"""
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('''
            CREATE TABLE IF NOT EXISTS mapping_documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                filename TEXT NOT NULL,
                file_path TEXT NOT NULL,
                uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                uploaded_by INTEGER,
                FOREIGN KEY (project_id) REFERENCES mapping_projects(id) ON DELETE CASCADE,
                FOREIGN KEY (uploaded_by) REFERENCES users(id) ON DELETE SET NULL
            )
        ''')
        conn.commit()
        conn.close()
        logger.info("Mapping documents table created/verified")
    
    def save(self) -> int:
        """Save the document"""
        conn = get_db_connection()
        cur = conn.cursor()
        
        if self.id:
            # Update existing document
            cur.execute('''
                UPDATE mapping_documents 
                SET project_id = ?, filename = ?, file_path = ?, uploaded_by = ?
                WHERE id = ?
            ''', (self.project_id, self.filename, self.file_path, self.uploaded_by, self.id))
            logger.info(f"Updated mapping document: {self.filename} (ID: {self.id})")
        else:
            # Insert new document
            cur.execute('''
                INSERT INTO mapping_documents (project_id, filename, file_path, uploaded_at, uploaded_by)
                VALUES (?, ?, ?, ?, ?)
            ''', (self.project_id, self.filename, self.file_path, self.uploaded_at, self.uploaded_by))
            self.id = cur.lastrowid
            logger.info(f"Created new mapping document: {self.filename} (ID: {self.id})")
        
        conn.commit()
        conn.close()
        return self.id
    
    @classmethod
    def get_by_id(cls, doc_id: int) -> Optional['MappingDocument']:
        """Get a document by ID"""
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('SELECT * FROM mapping_documents WHERE id = ?', (doc_id,))
        row = cur.fetchone()
        conn.close()
        
        if row:
            return cls(
                id=row[0],
                project_id=row[1],
                filename=row[2],
                file_path=row[3],
                uploaded_at=row[4],
                uploaded_by=row[5] if len(row) > 5 else None
            )
        return None
    
    @classmethod
    def get_by_project(cls, project_id: int) -> List['MappingDocument']:
        """Get all documents for a project"""
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('''
            SELECT md.*, u.username as uploaded_by_name
            FROM mapping_documents md
            LEFT JOIN users u ON md.uploaded_by = u.id
            WHERE md.project_id = ? 
            ORDER BY md.uploaded_at DESC
        ''', (project_id,))
        rows = cur.fetchall()
        conn.close()
        
        documents = []
        for row in rows:
            doc = cls(
                id=row[0],
                project_id=row[1],
                filename=row[2],
                file_path=row[3],
                uploaded_at=row[4],
                uploaded_by=row[5]
            )
            doc.uploaded_by_name = row[6]  # Add username as extra attribute
            documents.append(doc)
        
        return documents
    
    @classmethod
    def get_by_project_and_filename(cls, project_id: int, filename: str) -> Optional['MappingDocument']:
        """Get a document by project and filename"""
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('''
            SELECT * FROM mapping_documents 
            WHERE project_id = ? AND filename = ?
        ''', (project_id, filename))
        row = cur.fetchone()
        conn.close()
        
        if row:
            return cls(
                id=row[0],
                project_id=row[1],
                filename=row[2],
                file_path=row[3],
                uploaded_at=row[4],
                uploaded_by=row[5] if len(row) > 5 else None
            )
        return None
    
    def delete(self):
        """Delete the document and remove the file"""
        if not self.id:
            return
        
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Delete the physical file if it exists
        if os.path.exists(self.file_path):
            try:
                os.remove(self.file_path)
                logger.info(f"Deleted file: {self.file_path}")
            except Exception as e:
                logger.error(f"Failed to delete file {self.file_path}: {e}")
        
        # Delete the database record
        cur.execute('DELETE FROM mapping_documents WHERE id = ?', (self.id,))
        conn.commit()
        conn.close()
        logger.info(f"Deleted mapping document: {self.filename} (ID: {self.id})")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        result = {
            'id': self.id,
            'project_id': self.project_id,
            'filename': self.filename,
            'file_path': self.file_path,
            'uploaded_at': self.uploaded_at,
            'uploaded_by': self.uploaded_by
        }
        # Include uploaded_by_name if it exists
        if hasattr(self, 'uploaded_by_name'):
            result['uploaded_by_name'] = self.uploaded_by_name
        return result
