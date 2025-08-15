"""
Finch Database Intelligence MCP Server (stdio)

This MCP server exposes a minimal, efficient set of tools to interact with:
- The application's SQLite database (read-only operations: list schema, run SELECT)
- Metadata JSON files under config/data (schema.json and condition.json)

All intelligence (SQL construction, reasoning) is expected to be handled by the LLM
through the AutoGen workflows. This server only provides tools to fetch metadata
and execute read-only queries.

Inspired by Uber's Finch article: keep the server simple and focused on tools.
"""

from __future__ import annotations

import asyncio
import json
import os
from typing import Any, Dict, List, Optional

import aiosqlite
from mcp.server.fastmcp import FastMCP


# Initialize stdio MCP server
mcp = FastMCP("finch_db")


def _project_root() -> str:
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))


def _resolve_sqlite_db_path() -> str:
    """Resolve the SQLite DB file path from config.DATABASE_URI or fallbacks."""
    # Try to import config lazily
    db_path: Optional[str] = None
    try:
        import config.config as app_config  # type: ignore

        uri = getattr(app_config, "DATABASE_URI", "sqlite:///text2sql.db")
        # Expected formats: sqlite:///absolute/or/relative/path.db or sqlite:///:memory:
        if uri.startswith("sqlite:///") and uri != "sqlite:///:memory:":
            candidate = uri.replace("sqlite:///", "", 1)
            # If relative, make it relative to project root
            if not os.path.isabs(candidate):
                candidate = os.path.join(_project_root(), candidate)
            db_path = candidate
    except Exception:
        pass

    # Fallbacks
    candidates = [
        db_path,
        os.path.join(_project_root(), "text2sql.db"),
        os.path.join(_project_root(), "database.db"),
    ]
    for c in candidates:
        if c and os.path.exists(c):
            return c
    # Last resort: create path under project root
    return os.path.join(_project_root(), "text2sql","text2sql.db")


def _metadata_dir() -> str:
    return os.path.join(_project_root(), "config", "data")


def _read_json_file(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


async def _list_tables_sqlite(db_path: str) -> List[str]:
    try:
        async with aiosqlite.connect(db_path) as db:
            async with db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';") as cur:
                rows = await cur.fetchall()
                return [r[0] for r in rows]
    except Exception:
        return []


async def _get_table_info_sqlite(db_path: str, table_name: str) -> Dict[str, Any]:
    info: Dict[str, Any] = {"table": table_name, "columns": [], "primary_keys": [], "foreign_keys": []}
    try:
        async with aiosqlite.connect(db_path) as db:
            # Columns
            async with db.execute(f"PRAGMA table_info({table_name})") as cur:
                cols = await cur.fetchall()
                for c in cols:
                    # cid, name, type, notnull, dflt_value, pk
                    col = {
                        "name": c[1],
                        "type": c[2],
                        "not_null": bool(c[3]),
                        "default": c[4],
                        "is_pk": bool(c[5]),
                    }
                    info["columns"].append(col)
                    if col["is_pk"]:
                        info["primary_keys"].append(col["name"])

            # FKs
            async with db.execute(f"PRAGMA foreign_key_list({table_name})") as cur:
                fks = await cur.fetchall()
                for fk in fks:
                    # id, seq, table, from, to, on_update, on_delete, match
                    info["foreign_keys"].append(
                        {
                            "id": fk[0],
                            "to_table": fk[2],
                            "from_column": fk[3],
                            "to_column": fk[4],
                            "on_update": fk[5],
                            "on_delete": fk[6],
                        }
                    )
    except Exception as e:
        info["error"] = str(e)
    return info


def _get_metadata_paths() -> Dict[str, str]:
    basedir = _metadata_dir()
    return {
        "schema": os.path.join(basedir, "schema.json"),
        "conditions": os.path.join(basedir, "condition.json"),
    }


def _load_metadata() -> Dict[str, Any]:
    paths = _get_metadata_paths()
    result: Dict[str, Any] = {}
    for k, p in paths.items():
        try:
            if os.path.exists(p):
                result[k] = _read_json_file(p)
            else:
                result[k] = {"error": f"File not found: {p}"}
        except Exception as e:
            result[k] = {"error": str(e)}
    return result


@mcp.tool()
async def health_check() -> Dict[str, Any]:
    """Quick health check for the Finch MCP server and data files."""
    db_path = _resolve_sqlite_db_path()
    meta_paths = _get_metadata_paths()
    return {
        "status": "ok",
        "server": "finch_db",
        "db_path": db_path,
        "db_exists": os.path.exists(db_path),
        "metadata_paths": meta_paths,
        "metadata_exists": {k: os.path.exists(v) for k, v in meta_paths.items()},
    }


@mcp.tool()
async def list_tables() -> Dict[str, Any]:
    """List available SQLite tables in the application database (excluding sqlite_internal)."""
    db_path = _resolve_sqlite_db_path()
    tables = await _list_tables_sqlite(db_path)
    return {"success": True, "db_path": db_path, "tables": tables}


@mcp.tool()
async def get_table_info(table: str) -> Dict[str, Any]:
    """Get column definitions, PKs, and FKs for a table."""
    if not table:
        return {"success": False, "error": "Missing 'table' parameter"}
    db_path = _resolve_sqlite_db_path()
    info = await _get_table_info_sqlite(db_path, table)
    info.update({"success": "error" not in info, "db_path": db_path})
    return info


@mcp.tool()
async def run_select(query: str, limit: int = 100) -> Dict[str, Any]:
    """Execute a read-only SELECT query against the SQLite database.

    Notes:
    - Only queries starting with SELECT or WITH are allowed
    - A LIMIT will be enforced if not present and limit > 0
    """
    if not query or not isinstance(query, str):
        return {"success": False, "error": "Query must be a non-empty string"}
    # Normalize whitespace and strip trailing semicolons to avoid accidental multi-statements
    raw = query.strip()
    # Remove all trailing semicolons and whitespace
    while raw.endswith(';') or raw.endswith('\n') or raw.endswith('\r') or raw.endswith('\t') or raw.endswith(' '):
        raw = raw[:-1].rstrip()
    q_upper = raw.upper()
    if not (q_upper.startswith("SELECT") or q_upper.startswith("WITH")):
        return {"success": False, "error": "Only SELECT/WITH queries are allowed"}

    # Append LIMIT if missing
    effective_query = raw
    # naive check for LIMIT presence; avoids adding if already present
    if limit:
        import re as _re
        has_limit = bool(_re.search(r"\bLIMIT\b", q_upper))
        if not has_limit:
            effective_query = f"{effective_query} LIMIT {int(limit)}"

    db_path = _resolve_sqlite_db_path()
    try:
        async with aiosqlite.connect(db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(effective_query) as cur:
                rows = await cur.fetchall()
                cols = [d[0] for d in (cur.description or [])]
                data = [dict(r) for r in rows]
                return {
                    "success": True,
                    "db_path": db_path,
                    "columns": cols,
                    "row_count": len(data),
                    "data": data,
                }
    except Exception as e:
        return {"success": False, "db_path": db_path, "error": str(e)}


@mcp.tool()
async def explain_query_plan(query: str) -> Dict[str, Any]:
    """Return SQLite EXPLAIN QUERY PLAN for a SELECT/WITH query."""
    if not query or not isinstance(query, str):
        return {"success": False, "error": "Query must be a non-empty string"}
    # Strip trailing semicolons/whitespace to ensure single statement
    raw = query.strip()
    while raw.endswith(';') or raw.endswith('\n') or raw.endswith('\r') or raw.endswith('\t') or raw.endswith(' '):
        raw = raw[:-1].rstrip()
    q_upper = raw.upper()
    if not (q_upper.startswith("SELECT") or q_upper.startswith("WITH")):
        return {"success": False, "error": "Only SELECT/WITH queries are allowed"}

    db_path = _resolve_sqlite_db_path()
    try:
        async with aiosqlite.connect(db_path) as db:
            async with db.execute(f"EXPLAIN QUERY PLAN {raw}") as cur:
                rows = await cur.fetchall()
                # Columns: selectid, order, from, detail (varies by SQLite version)
                plan = [list(r) for r in rows]
                return {"success": True, "db_path": db_path, "plan": plan}
    except Exception as e:
        return {"success": False, "db_path": db_path, "error": str(e)}


@mcp.tool()
async def get_metadata_overview() -> Dict[str, Any]:
    """Return a summarized view of schema.json and condition.json."""
    meta = _load_metadata()
    overview: Dict[str, Any] = {"workspaces": [], "joins": []}

    schema = meta.get("schema") or {}
    ws = schema.get("workspaces") or []
    for w in ws:
        overview["workspaces"].append(
            {
                "name": w.get("name"),
                "table_count": len(w.get("tables", [])),
            }
        )

    cond = meta.get("conditions") or {}
    joins = cond.get("joins") or []
    for j in joins:
        overview["joins"].append(
            {
                "name": j.get("name"),
                "left_table": j.get("left_table"),
                "right_table": j.get("right_table"),
                "join_type": j.get("join_type"),
            }
        )

    return {"success": True, "overview": overview}


@mcp.tool()
async def get_table_metadata(table: str) -> Dict[str, Any]:
    """Get metadata for a table from schema.json (searches all workspaces)."""
    if not table:
        return {"success": False, "error": "Missing 'table' parameter"}
    meta = _load_metadata()
    schema = meta.get("schema") or {}
    for w in schema.get("workspaces", []):
        for t in w.get("tables", []):
            if t.get("name") == table:
                return {"success": True, "workspace": w.get("name"), "table": t}
    return {"success": False, "error": f"Table not found in metadata: {table}"}


@mcp.tool()
async def search_columns(keyword: str) -> Dict[str, Any]:
    """Search columns by name/description across metadata schema.json."""
    if not keyword:
        return {"success": False, "error": "Missing 'keyword' parameter"}
    kw = keyword.lower()
    meta = _load_metadata()
    schema = meta.get("schema") or {}
    matches: List[Dict[str, Any]] = []
    for w in schema.get("workspaces", []):
        for t in w.get("tables", []):
            for c in t.get("columns", []):
                name = (c.get("name") or "").lower()
                desc = (c.get("description") or "").lower()
                if kw in name or kw in desc:
                    matches.append(
                        {
                            "workspace": w.get("name"),
                            "table": t.get("name"),
                            "column": c.get("name"),
                            "datatype": c.get("datatype"),
                            "description": c.get("description"),
                        }
                    )
    return {"success": True, "count": len(matches), "matches": matches}


@mcp.tool()
async def list_joins() -> Dict[str, Any]:
    """List join definitions from condition.json."""
    meta = _load_metadata()
    cond = meta.get("conditions") or {}
    return {"success": True, "joins": cond.get("joins", [])}


if __name__ == "__main__":
    # Run as stdio MCP server
    mcp.run(transport="stdio")
