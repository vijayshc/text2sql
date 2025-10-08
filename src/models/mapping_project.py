"""
Mapping Project Model
Manages project-based organization of mapping documents.
"""
import sqlite3
import logging
from datetime import datetime
from typing import List, Optional, Dict, Any
from src.utils.database import get_db_connection

logger = logging.getLogger('text2sql')


class MappingProject:
    """Model for managing mapping projects"""
    
    def __init__(self, id: Optional[int] = None, name: str = '', description: str = '', 
                 created_at: Optional[str] = None, updated_at: Optional[str] = None):
        self.id = id
        self.name = name
        self.description = description
        self.created_at = created_at or datetime.now().isoformat()
        self.updated_at = updated_at or datetime.now().isoformat()
    
    @classmethod
    def create_table(cls):
        """Create the mapping_projects table if it doesn't exist"""
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('''
            CREATE TABLE IF NOT EXISTS mapping_projects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()
        conn.close()
        logger.info("Mapping projects table created/verified")
    
    def save(self) -> int:
        """Save or update the project"""
        conn = get_db_connection()
        cur = conn.cursor()
        
        self.updated_at = datetime.now().isoformat()
        
        if self.id:
            # Update existing project
            cur.execute('''
                UPDATE mapping_projects 
                SET name = ?, description = ?, updated_at = ?
                WHERE id = ?
            ''', (self.name, self.description, self.updated_at, self.id))
            logger.info(f"Updated mapping project: {self.name} (ID: {self.id})")
        else:
            # Insert new project
            cur.execute('''
                INSERT INTO mapping_projects (name, description, created_at, updated_at)
                VALUES (?, ?, ?, ?)
            ''', (self.name, self.description, self.created_at, self.updated_at))
            self.id = cur.lastrowid
            logger.info(f"Created new mapping project: {self.name} (ID: {self.id})")
        
        conn.commit()
        conn.close()
        return self.id
    
    @classmethod
    def get_by_id(cls, project_id: int) -> Optional['MappingProject']:
        """Get a project by ID"""
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('SELECT * FROM mapping_projects WHERE id = ?', (project_id,))
        row = cur.fetchone()
        conn.close()
        
        if row:
            return cls(
                id=row[0],
                name=row[1],
                description=row[2],
                created_at=row[3],
                updated_at=row[4]
            )
        return None
    
    @classmethod
    def get_by_name(cls, name: str) -> Optional['MappingProject']:
        """Get a project by name"""
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('SELECT * FROM mapping_projects WHERE name = ?', (name,))
        row = cur.fetchone()
        conn.close()
        
        if row:
            return cls(
                id=row[0],
                name=row[1],
                description=row[2],
                created_at=row[3],
                updated_at=row[4]
            )
        return None
    
    @classmethod
    def get_all(cls) -> List['MappingProject']:
        """Get all projects"""
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('SELECT * FROM mapping_projects ORDER BY name ASC')
        rows = cur.fetchall()
        conn.close()
        
        return [
            cls(
                id=row[0],
                name=row[1],
                description=row[2],
                created_at=row[3],
                updated_at=row[4]
            )
            for row in rows
        ]
    
    def delete(self):
        """Delete the project and all associated documents"""
        if not self.id:
            return
        
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Delete associated mapping documents (will be handled by the MappingDocument model)
        from src.models.mapping_document import MappingDocument
        documents = MappingDocument.get_by_project(self.id)
        for doc in documents:
            doc.delete()
        
        # Delete the project
        cur.execute('DELETE FROM mapping_projects WHERE id = ?', (self.id,))
        conn.commit()
        conn.close()
        logger.info(f"Deleted mapping project: {self.name} (ID: {self.id})")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }
