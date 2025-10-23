"""
Code Generation History Model

Tracks all code generation operations including user, timing, and results
"""

import sqlite3
import json
from datetime import datetime
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger('text2sql.code_generation_history')


class CodeGenerationHistory:
    """Model for code generation history tracking"""
    
    DB_PATH = 'text2sql.db'
    
    def __init__(self, id=None, user_id=None, username=None, project_name=None, 
                 mapping_name=None, status=None, started_at=None, completed_at=None,
                 duration_seconds=None, table_names=None, output_file=None, 
                 code_lines=None, had_existing_code=False, error_message=None):
        self.id = id
        self.user_id = user_id
        self.username = username
        self.project_name = project_name
        self.mapping_name = mapping_name
        self.status = status  # 'success', 'error', 'in_progress'
        self.started_at = started_at
        self.completed_at = completed_at
        self.duration_seconds = duration_seconds
        self.table_names = table_names  # JSON array
        self.output_file = output_file
        self.code_lines = code_lines
        self.had_existing_code = had_existing_code
        self.error_message = error_message
    
    @staticmethod
    def create_table():
        """Create the code_generation_history table if it doesn't exist"""
        try:
            conn = sqlite3.connect(CodeGenerationHistory.DB_PATH)
            cursor = conn.cursor()
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS code_generation_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    username TEXT,
                    project_name TEXT NOT NULL,
                    mapping_name TEXT NOT NULL,
                    status TEXT NOT NULL,
                    started_at TEXT NOT NULL,
                    completed_at TEXT,
                    duration_seconds REAL,
                    table_names TEXT,
                    output_file TEXT,
                    code_lines INTEGER,
                    had_existing_code INTEGER DEFAULT 0,
                    error_message TEXT,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            ''')
            
            # Create indexes for common queries
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_generation_user 
                ON code_generation_history(user_id)
            ''')
            
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_generation_project 
                ON code_generation_history(project_name)
            ''')
            
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_generation_status 
                ON code_generation_history(status)
            ''')
            
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_generation_started 
                ON code_generation_history(started_at DESC)
            ''')
            
            conn.commit()
            conn.close()
            logger.info("Code generation history table created/verified")
            
        except Exception as e:
            logger.error(f"Error creating code generation history table: {str(e)}")
    
    def save(self) -> int:
        """Save or update the history record"""
        try:
            conn = sqlite3.connect(self.DB_PATH)
            cursor = conn.cursor()
            
            if self.id is None:
                # Insert new record
                cursor.execute('''
                    INSERT INTO code_generation_history 
                    (user_id, username, project_name, mapping_name, status, started_at, 
                     completed_at, duration_seconds, table_names, output_file, code_lines, 
                     had_existing_code, error_message)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    self.user_id, self.username, self.project_name, self.mapping_name,
                    self.status, self.started_at, self.completed_at, self.duration_seconds,
                    json.dumps(self.table_names) if self.table_names else None,
                    self.output_file, self.code_lines, 
                    1 if self.had_existing_code else 0, self.error_message
                ))
                self.id = cursor.lastrowid
            else:
                # Update existing record
                cursor.execute('''
                    UPDATE code_generation_history 
                    SET status=?, completed_at=?, duration_seconds=?, table_names=?,
                        output_file=?, code_lines=?, error_message=?
                    WHERE id=?
                ''', (
                    self.status, self.completed_at, self.duration_seconds,
                    json.dumps(self.table_names) if self.table_names else None,
                    self.output_file, self.code_lines, self.error_message, self.id
                ))
            
            conn.commit()
            conn.close()
            return self.id
            
        except Exception as e:
            logger.error(f"Error saving code generation history: {str(e)}")
            return None
    
    @staticmethod
    def get_by_id(history_id: int) -> Optional['CodeGenerationHistory']:
        """Get a history record by ID"""
        try:
            conn = sqlite3.connect(CodeGenerationHistory.DB_PATH)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT id, user_id, username, project_name, mapping_name, status, 
                       started_at, completed_at, duration_seconds, table_names, 
                       output_file, code_lines, had_existing_code, error_message
                FROM code_generation_history 
                WHERE id = ?
            ''', (history_id,))
            
            row = cursor.fetchone()
            conn.close()
            
            if row:
                return CodeGenerationHistory._from_row(row)
            return None
            
        except Exception as e:
            logger.error(f"Error getting history by ID: {str(e)}")
            return None
    
    @staticmethod
    def get_all(limit: int = 100, offset: int = 0, user_id: Optional[int] = None,
                project_name: Optional[str] = None) -> List['CodeGenerationHistory']:
        """Get all history records with optional filtering"""
        try:
            conn = sqlite3.connect(CodeGenerationHistory.DB_PATH)
            cursor = conn.cursor()
            
            query = '''
                SELECT id, user_id, username, project_name, mapping_name, status, 
                       started_at, completed_at, duration_seconds, table_names, 
                       output_file, code_lines, had_existing_code, error_message
                FROM code_generation_history 
                WHERE 1=1
            '''
            params = []
            
            if user_id is not None:
                query += ' AND user_id = ?'
                params.append(user_id)
            
            if project_name:
                query += ' AND project_name = ?'
                params.append(project_name)
            
            query += ' ORDER BY started_at DESC LIMIT ? OFFSET ?'
            params.extend([limit, offset])
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            conn.close()
            
            return [CodeGenerationHistory._from_row(row) for row in rows]
            
        except Exception as e:
            logger.error(f"Error getting all history: {str(e)}")
            return []
    
    @staticmethod
    def get_stats() -> Dict[str, Any]:
        """Get statistics about code generation history"""
        try:
            conn = sqlite3.connect(CodeGenerationHistory.DB_PATH)
            cursor = conn.cursor()
            
            # Total generations
            cursor.execute('SELECT COUNT(*) FROM code_generation_history')
            total = cursor.fetchone()[0]
            
            # Success count
            cursor.execute("SELECT COUNT(*) FROM code_generation_history WHERE status = 'success'")
            success = cursor.fetchone()[0]
            
            # Error count
            cursor.execute("SELECT COUNT(*) FROM code_generation_history WHERE status = 'error'")
            errors = cursor.fetchone()[0]
            
            # Average duration for successful generations
            cursor.execute('''
                SELECT AVG(duration_seconds) 
                FROM code_generation_history 
                WHERE status = 'success' AND duration_seconds IS NOT NULL
            ''')
            avg_duration = cursor.fetchone()[0] or 0
            
            # Most common projects
            cursor.execute('''
                SELECT project_name, COUNT(*) as count 
                FROM code_generation_history 
                GROUP BY project_name 
                ORDER BY count DESC 
                LIMIT 5
            ''')
            top_projects = [{'project': row[0], 'count': row[1]} for row in cursor.fetchall()]
            
            conn.close()
            
            return {
                'total_generations': total,
                'successful': success,
                'errors': errors,
                'success_rate': (success / total * 100) if total > 0 else 0,
                'avg_duration_seconds': round(avg_duration, 2),
                'top_projects': top_projects
            }
            
        except Exception as e:
            logger.error(f"Error getting stats: {str(e)}")
            return {}
    
    @staticmethod
    def _from_row(row) -> 'CodeGenerationHistory':
        """Create CodeGenerationHistory instance from database row"""
        table_names = json.loads(row[9]) if row[9] else []
        
        return CodeGenerationHistory(
            id=row[0],
            user_id=row[1],
            username=row[2],
            project_name=row[3],
            mapping_name=row[4],
            status=row[5],
            started_at=row[6],
            completed_at=row[7],
            duration_seconds=row[8],
            table_names=table_names,
            output_file=row[10],
            code_lines=row[11],
            had_existing_code=bool(row[12]),
            error_message=row[13]
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'username': self.username,
            'project_name': self.project_name,
            'mapping_name': self.mapping_name,
            'status': self.status,
            'started_at': self.started_at,
            'completed_at': self.completed_at,
            'duration_seconds': self.duration_seconds,
            'table_names': self.table_names,
            'output_file': self.output_file,
            'code_lines': self.code_lines,
            'had_existing_code': self.had_existing_code,
            'error_message': self.error_message
        }
    
    @property
    def created_at(self):
        """Alias for started_at to match template expectations"""
        return self.started_at

