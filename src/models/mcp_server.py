from datetime import datetime
from enum import Enum
import json
import os

from src.utils.database import get_db_connection


class MCPServerType(Enum):
    STDIO = "stdio"
    HTTP = "http"


class MCPServerStatus(Enum):
    STOPPED = "stopped"
    RUNNING = "running"
    ERROR = "error"


class MCPServer:
    def __init__(self, id=None, name=None, description=None, server_type=None, 
                 config=None, status=MCPServerStatus.STOPPED.value, created_at=None, updated_at=None):
        # Convert string timestamps from DB to datetime
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)
        if isinstance(updated_at, str):
            updated_at = datetime.fromisoformat(updated_at)

        self.id = id
        self.name = name
        self.description = description
        self.server_type = server_type
        self.config = config if isinstance(config, dict) else json.loads(config) if config else {}
        self.status = status
        self.created_at = created_at or datetime.now()
        self.updated_at = updated_at or datetime.now()

    @classmethod
    def create_table(cls):
        """Create the mcp_servers table if it doesn't exist."""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS mcp_servers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            description TEXT,
            server_type TEXT NOT NULL,
            config TEXT NOT NULL,
            status TEXT DEFAULT 'stopped',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        conn.commit()
        conn.close()

    @classmethod
    def get_all(cls):
        """Get all MCP servers from the database."""
        conn = get_db_connection()
        conn.row_factory = cls._dict_factory
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM mcp_servers ORDER BY name')
        servers = [cls(**row) for row in cursor.fetchall()]
        
        conn.close()
        return servers

    @classmethod
    def get_running(cls):
        """Get all running MCP servers."""
        conn = get_db_connection()
        conn.row_factory = cls._dict_factory
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM mcp_servers WHERE status = ? ORDER BY name', (MCPServerStatus.RUNNING.value,))
        servers = [cls(**row) for row in cursor.fetchall()]
        
        conn.close()
        return servers
        
    @classmethod
    def get_by_id(cls, server_id):
        """Get a server by ID."""
        conn = get_db_connection()
        conn.row_factory = cls._dict_factory
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM mcp_servers WHERE id = ?', (server_id,))
        server_data = cursor.fetchone()
        
        conn.close()
        return cls(**server_data) if server_data else None
    
    @classmethod
    def get_by_name(cls, name):
        """Get a server by name."""
        conn = get_db_connection()
        conn.row_factory = cls._dict_factory
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM mcp_servers WHERE name = ?', (name,))
        server_data = cursor.fetchone()
        
        conn.close()
        return cls(**server_data) if server_data else None

    def save(self):
        """Save this MCP server to the database."""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if self.id:
            # Update existing record
            self.updated_at = datetime.now()
            cursor.execute('''
            UPDATE mcp_servers 
            SET name = ?, description = ?, server_type = ?, config = ?, 
                status = ?, updated_at = ?
            WHERE id = ?
            ''', (
                self.name, 
                self.description, 
                self.server_type, 
                json.dumps(self.config), 
                self.status, 
                self.updated_at,
                self.id
            ))
        else:
            # Insert new record
            cursor.execute('''
            INSERT INTO mcp_servers (name, description, server_type, config, status)
            VALUES (?, ?, ?, ?, ?)
            ''', (
                self.name, 
                self.description, 
                self.server_type, 
                json.dumps(self.config), 
                self.status
            ))
            self.id = cursor.lastrowid
        
        conn.commit()
        conn.close()
        
        return self

    def delete(self):
        """Delete this MCP server from the database."""
        if not self.id:
            return False
            
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('DELETE FROM mcp_servers WHERE id = ?', (self.id,))
        
        conn.commit()
        conn.close()
        
        return True

    def update_status(self, status):
        """Update the status of the MCP server."""
        self.status = status
        self.save()

    @staticmethod
    def _dict_factory(cursor, row):
        """Convert row to dictionary for SQLite row factory."""
        d = {}
        for idx, col in enumerate(cursor.description):
            d[col[0]] = row[idx]
        return d
