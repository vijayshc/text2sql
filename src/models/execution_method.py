from datetime import datetime
import json
from typing import Optional, Dict, Any, List

from src.utils.database import get_db_connection


class ExecutionMethodType:
    REFLECTION = 'reflection'
    SEQUENTIAL = 'sequential'
    DEBATE = 'debate'
    CONCURRENT = 'concurrent'
    GROUP_CHAT = 'group_chat'
    HANDOFF = 'handoff'
    MIXTURE = 'mixture'
    CODE_EXEC_GROUPCHAT = 'code_exec_groupchat'

    @classmethod
    def all(cls) -> List[str]:
        return [
            cls.REFLECTION,
            cls.SEQUENTIAL,
            cls.DEBATE,
            cls.CONCURRENT,
            cls.GROUP_CHAT,
            cls.HANDOFF,
            cls.MIXTURE,
            cls.CODE_EXEC_GROUPCHAT,
        ]


class ExecutionMethod:
    """Represents an execution method (design pattern) configuration.

    Columns:
    - id INTEGER PRIMARY KEY AUTOINCREMENT
    - name TEXT UNIQUE NOT NULL
    - description TEXT
    - type TEXT NOT NULL (one of ExecutionMethodType)
    - team_id INTEGER NOT NULL REFERENCES agent_teams(id)
    - config TEXT (JSON) with pattern-specific configuration
    - created_at TIMESTAMP
    - updated_at TIMESTAMP
    """

    def __init__(
        self,
        id: Optional[int] = None,
        name: Optional[str] = None,
        description: Optional[str] = None,
        type: Optional[str] = None,
        team_id: Optional[int] = None,
        config: Optional[Dict[str, Any]] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ):
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)
        if isinstance(updated_at, str):
            updated_at = datetime.fromisoformat(updated_at)

        self.id = id
        self.name = name
        self.description = description
        self.type = type
        self.team_id = team_id
        self.config = config if isinstance(config, dict) else json.loads(config) if config else {}
        self.created_at = created_at or datetime.now()
        self.updated_at = updated_at or datetime.now()

    @classmethod
    def create_table(cls):
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            '''
            CREATE TABLE IF NOT EXISTS execution_methods (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                description TEXT,
                type TEXT NOT NULL,
                team_id INTEGER NOT NULL,
                config TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(team_id) REFERENCES agent_teams(id)
            )
            '''
        )
        conn.commit()
        conn.close()

    @classmethod
    def get_all(cls) -> List["ExecutionMethod"]:
        conn = get_db_connection()
        conn.row_factory = cls._dict_factory
        cur = conn.cursor()
        cur.execute('SELECT * FROM execution_methods ORDER BY name')
        rows = cur.fetchall()
        conn.close()
        return [cls(**row) for row in rows]

    @classmethod
    def get_by_id(cls, method_id: int) -> Optional["ExecutionMethod"]:
        conn = get_db_connection()
        conn.row_factory = cls._dict_factory
        cur = conn.cursor()
        cur.execute('SELECT * FROM execution_methods WHERE id = ?', (method_id,))
        row = cur.fetchone()
        conn.close()
        return cls(**row) if row else None

    @classmethod
    def get_by_name(cls, name: str) -> Optional["ExecutionMethod"]:
        conn = get_db_connection()
        conn.row_factory = cls._dict_factory
        cur = conn.cursor()
        cur.execute('SELECT * FROM execution_methods WHERE name = ?', (name,))
        row = cur.fetchone()
        conn.close()
        return cls(**row) if row else None

    def save(self) -> "ExecutionMethod":
        conn = get_db_connection()
        cur = conn.cursor()
        if self.id:
            self.updated_at = datetime.now()
            cur.execute(
                '''
                UPDATE execution_methods
                SET name = ?, description = ?, type = ?, team_id = ?, config = ?, updated_at = ?
                WHERE id = ?
                ''',
                (self.name, self.description, self.type, self.team_id, json.dumps(self.config), self.updated_at, self.id)
            )
        else:
            cur.execute(
                '''
                INSERT INTO execution_methods (name, description, type, team_id, config)
                VALUES (?, ?, ?, ?, ?)
                ''',
                (self.name, self.description, self.type, self.team_id, json.dumps(self.config))
            )
            self.id = cur.lastrowid
        conn.commit()
        conn.close()
        return self

    def delete(self) -> bool:
        if not self.id:
            return False
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('DELETE FROM execution_methods WHERE id = ?', (self.id,))
        conn.commit()
        conn.close()
        return True

    @staticmethod
    def _dict_factory(cursor, row):
        d = {}
        for idx, col in enumerate(cursor.description):
            d[col[0]] = row[idx]
        return d
