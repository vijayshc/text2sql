"""
Database schema initialization for admin features.
Creates tables for samples and other admin functionality.
"""

import sqlite3
from datetime import datetime

def init_admin_schema():
    """Initialize admin-related database tables"""
    try:
        conn = sqlite3.connect('text2sql.db')
        cursor = conn.cursor()
        
        # Create samples table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS samples (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                category TEXT,
                sql_query TEXT NOT NULL,
                natural_language TEXT NOT NULL,
                database_schema TEXT,
                tags TEXT,  -- JSON array of tags
                difficulty TEXT DEFAULT 'beginner',  -- beginner, intermediate, advanced
                is_active BOOLEAN DEFAULT 1,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        
        # Create configurations table (if needed in future)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS configurations (
                id TEXT PRIMARY KEY,
                key TEXT UNIQUE NOT NULL,
                value TEXT,
                value_type TEXT DEFAULT 'string',  -- string, integer, float, boolean, text
                category TEXT,
                description TEXT,
                is_sensitive BOOLEAN DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        
        # Create skills table (if needed in future)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS skills (
                skill_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                category TEXT,
                status TEXT DEFAULT 'active',  -- active, draft, deprecated
                version TEXT DEFAULT '1.0',
                tags TEXT,  -- JSON array of tags
                prerequisites TEXT,  -- JSON array of prerequisites
                steps TEXT,  -- JSON array of steps
                examples TEXT,  -- JSON array of examples
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        
        # Create knowledge_documents table (if needed in future)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS knowledge_documents (
                id TEXT PRIMARY KEY,
                filename TEXT NOT NULL,
                content_type TEXT,
                status TEXT DEFAULT 'pending',  -- pending, processing, completed, error
                tags TEXT,  -- JSON array of tags
                chunk_count INTEGER DEFAULT 0,
                error_message TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        
        conn.commit()
        conn.close()
        
        print("Admin schema initialized successfully")
        return True
        
    except Exception as e:
        print(f"Error initializing admin schema: {e}")
        return False

if __name__ == "__main__":
    init_admin_schema()