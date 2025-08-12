import json
import time
from datetime import datetime
from typing import Optional, Dict, Any

from src.utils.database import get_db_connection


class RunMonitor:
    """SQLite-backed monitor to track AutoGen runs and detailed events."""

    def __init__(self):
        self.run_id: Optional[int] = None
        self._ensure_tables()

    def _ensure_tables(self):
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            '''
            CREATE TABLE IF NOT EXISTS agent_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                entity_type TEXT NOT NULL,
                entity_id INTEGER NOT NULL,
                task TEXT,
                status TEXT DEFAULT 'running',
                started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                finished_at TIMESTAMP,
                final_reply TEXT,
                error TEXT
            )
            '''
        )
        cur.execute(
            '''
            CREATE TABLE IF NOT EXISTS agent_run_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id INTEGER NOT NULL,
                ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                event_type TEXT NOT NULL,
                source TEXT,
                agent_name TEXT,
                server_id TEXT,
                tool_name TEXT,
                detail TEXT,
                FOREIGN KEY(run_id) REFERENCES agent_runs(id)
            )
            '''
        )
        conn.commit()
        conn.close()

    def start_run(self, entity_type: str, entity_id: int, task: str) -> int:
        conn = get_db_connection()
        cur = conn.cursor()
        # Use explicit timestamp to be consistent with finished_at
        now = datetime.now()
        cur.execute(
            'INSERT INTO agent_runs (entity_type, entity_id, task, status, started_at) VALUES (?, ?, ?, ?, ?)',
            (entity_type, entity_id, task or '', 'running', now.isoformat(sep=' ', timespec='seconds'))
        )
        self.run_id = cur.lastrowid
        conn.commit()
        conn.close()
        return self.run_id

    def log_event(
        self,
        event_type: str,
        source: str,
        detail: Dict[str, Any] | None = None,
        agent_name: Optional[str] = None,
        server_id: Optional[str] = None,
        tool_name: Optional[str] = None,
    ) -> None:
        if not self.run_id:
            return
        conn = get_db_connection()
        cur = conn.cursor()
        payload = json.dumps(detail or {}, ensure_ascii=False)
        # Use explicit timestamp for consistency
        now = datetime.now()
        cur.execute(
            'INSERT INTO agent_run_events (run_id, ts, event_type, source, agent_name, server_id, tool_name, detail) VALUES (?,?,?,?,?,?,?,?)',
            (self.run_id, now.isoformat(sep=' ', timespec='seconds'), event_type, source, agent_name, server_id, tool_name, payload)
        )
        conn.commit()
        conn.close()

    def end_run(self, status: str, final_reply: Optional[str] = None, error: Optional[str] = None) -> None:
        if not self.run_id:
            return
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            'UPDATE agent_runs SET status = ?, finished_at = ?, final_reply = ?, error = ? WHERE id = ?',
            (status, datetime.now().isoformat(sep=' ', timespec='seconds'), final_reply, error, self.run_id)
        )
        conn.commit()
        conn.close()

    # Query helpers
    @staticmethod
    def list_runs(limit: int = 50):
        conn = get_db_connection()
        conn.row_factory = lambda cursor, row: {
            col[0]: row[idx] for idx, col in enumerate(cursor.description)
        }
        cur = conn.cursor()
        cur.execute('SELECT * FROM agent_runs ORDER BY id DESC LIMIT ?', (limit,))
        rows = cur.fetchall()
        conn.close()
        return rows

    @staticmethod
    def get_run(run_id: int):
        conn = get_db_connection()
        conn.row_factory = lambda cursor, row: {
            col[0]: row[idx] for idx, col in enumerate(cursor.description)
        }
        cur = conn.cursor()
        cur.execute('SELECT * FROM agent_runs WHERE id = ?', (run_id,))
        row = cur.fetchone()
        conn.close()
        return row

    @staticmethod
    def get_events(run_id: int):
        conn = get_db_connection()
        conn.row_factory = lambda cursor, row: {
            col[0]: row[idx] for idx, col in enumerate(cursor.description)
        }
        cur = conn.cursor()
        cur.execute('SELECT * FROM agent_run_events WHERE run_id = ? ORDER BY id ASC', (run_id,))
        rows = cur.fetchall()
        conn.close()
        # parse detail JSON
        for r in rows:
            try:
                r['detail'] = json.loads(r.get('detail') or '{}')
            except Exception:
                pass
        return rows


class _Timer:
    def __enter__(self):
        self.t0 = time.time()
        return self
    def __exit__(self, exc_type, exc, tb):
        self.elapsed = time.time() - self.t0
        return False
