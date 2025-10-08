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

    @staticmethod
    def get_filtered_events(run_id: int):
        """Get only essential events for UI display, filtering for LLM message events"""
        essential_event_types = {
            'llm_input',       # LLM input
            'llm_result',      # LLM output
            'llm_first_input', # First LLM input
            'agent_response',  # Agent selection
            'tool_call',       # Tool calling input
            'tool_result',     # Tool calling output
            'error',           # Errors
            'status',           # Status updates
            'message_event',    # Message-based events
            'autogen_event',    # General autogen events
            'autogen_text_event', # Additional autogen text events
        }

        conn = get_db_connection()
        conn.row_factory = lambda cursor, row: {
            col[0]: row[idx] for idx, col in enumerate(cursor.description)
        }
        cur = conn.cursor()
        # Get only essential event types
        placeholders = ','.join(['?' for _ in essential_event_types])
        query = f'SELECT * FROM agent_run_events WHERE run_id = ? AND event_type IN ({placeholders}) ORDER BY id ASC'
        cur.execute(query, (run_id, *essential_event_types))
        rows = cur.fetchall()
        conn.close()

        # Parse detail JSON and clean up data
        filtered_rows = []
        seen_events = set()  # Track unique events by content

        for r in rows:
            try:
                r['detail'] = json.loads(r.get('detail') or '{}')
            except Exception:
                pass

            # For filtered view: exclude events with MessageKind.PUBLISH or MessageKind.RESPOND
            # Check both direct MessageKind field and embedded kind in message JSON
            detail = r.get('detail', {})
            message_kind = detail.get('MessageKind') or detail.get('message_kind')

            # Also check for embedded MessageKind in the message field (escaped JSON)
            if not message_kind and 'message' in detail:
                message_str = detail['message']
                try:
                    # Try to parse the message field as JSON to extract kind
                    message_data = json.loads(message_str)
                    embedded_kind = message_data.get('kind', '')
                    if embedded_kind == 'MessageKind.PUBLISH':
                        message_kind = 'PUBLISH'
                    elif embedded_kind == 'MessageKind.RESPOND':
                        message_kind = 'RESPOND'
                    elif embedded_kind == 'MessageKind.DIRECT':
                        message_kind = 'DIRECT'
                except:
                    pass  # Silently fail if message is not parseable JSON

            # Exclude message events that have MessageKind.PUBLISH, RESPOND, or DIRECT
            filtered_out = False
            if message_kind in ('PUBLISH', 'RESPOND', 'DIRECT'):
                filtered_out = True  # Exclude these
            elif r['event_type'] not in essential_event_types:
                filtered_out = True  # Exclude non-essential events

            if filtered_out:
                continue

            # Enhanced duplicate detection - create comprehensive key
            if r['event_type'] in ('tool_call', 'tool_result', 'message_event', 'autogen_event', 'autogen_text_event'):
                # For autogen events with payload, extract more specific identifiers
                payload_content = ''
                if r['event_type'] in ('autogen_text_event', 'autogen_event'):
                    message_str = detail.get('message', '')
                    if message_str and '"payload":' in message_str:
                        try:
                            # Handle the complex JSON structure with escaped quotes
                            # First, parse the outer JSON
                            outer_data = json.loads(message_str)

                            # Get the payload string which contains escaped JSON
                            payload_str = outer_data.get('payload', '')
                            if payload_str:
                                # The payload is a string containing escaped JSON, unescape it
                                payload_json = payload_str.replace('\\"', '"').replace('\\\\', '\\')
                                payload_data = json.loads(payload_json)

                                # Extract key fields like message id, source, etc.
                                if isinstance(payload_data, dict):
                                    if 'message' in payload_data and isinstance(payload_data['message'], dict):
                                        msg_data = payload_data['message']
                                        payload_content = f"{msg_data.get('id', '')}_{msg_data.get('source', '')}_{str(msg_data.get('content', ''))[:100]}"
                                    elif 'response' in payload_data and isinstance(payload_data['response'], dict):
                                        resp_data = payload_data['response']
                                        if 'chat_message' in resp_data and isinstance(resp_data['chat_message'], dict):
                                            msg_data = resp_data['chat_message']
                                            payload_content = f"{msg_data.get('id', '')}_{msg_data.get('source', '')}_{str(msg_data.get('content', ''))[:100]}"
                        except Exception as e:
                            # Silently fail JSON parsing and use fallback content
                            payload_content = str(message_str)[:200]  # Use part of message as fallback

                # Include more fields for uniqueness - ensure all values are strings
                event_key_parts = [
                    str(r.get('event_type', '')),
                    str(r.get('tool_name') or ''),
                    str(r.get('agent_name') or ''),
                    str(r.get('ts') or ''),  # Use 'ts' not 'timestamp'
                    str(detail.get('content', ''))[:200],  # First 200 chars of content
                    str(detail.get('message', ''))[:200],   # First 200 chars of message
                    str(detail.get('MessageKind', '')),
                    str(detail.get('message_kind', '')),
                    payload_content  # Additional content for autogen events
                ]
                event_key = '|'.join(event_key_parts)

                if event_key in seen_events:
                    continue
                seen_events.add(event_key)

            # Clean up verbose autogen data in detail
            if isinstance(detail, dict):
                # Remove overly verbose nested payload data
                if 'payload' in detail and isinstance(detail['payload'], str):
                    try:
                        payload_obj = json.loads(detail['payload'])
                        # Keep only essential payload info
                        if 'task' in payload_obj:
                            detail = {'task': payload_obj['task']}
                        elif 'message' in payload_obj:
                            detail = {'message': payload_obj.get('message', '')[:200] + '...'}
                    except:
                        pass

                # Limit message content to reasonable size
                # if 'message' in detail and isinstance(detail['message'], str):
                #     if len(detail['message']) > 300:
                #         detail['message'] = detail['message'][:300] + '...'

                # Include MessageKind in the detail for UI visibility if present
                if message_kind:
                    detail['MessageKind'] = mes
            filtered_rows.append(r)

        return filtered_rows


class _Timer:
    def __enter__(self):
        self.t0 = time.time()
        return self
    def __exit__(self, exc_type, exc, tb):
        self.elapsed = time.time() - self.t0
        return False
