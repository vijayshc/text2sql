"""
Seed script: Register AutoGen team (with MCP Finch tools) and a basic workflow

This creates/updates:
- AgentTeam: "Finch DB Team" with one agent "DBAgent" allowed to use finch_db tools
- AgentWorkflow: "Finch DB QA" single-node workflow using DBAgent

Idempotent: running multiple times updates existing records.
"""
from __future__ import annotations

import os
import sys
from typing import Any, Dict, List


def _project_root() -> str:
    return os.path.abspath(os.path.dirname(__file__))


# Ensure project root on sys.path
PROJECT_ROOT = _project_root()
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


from src.models.mcp_server import MCPServer  # noqa: E402
from src.models.agent_team import AgentTeam  # noqa: E402
from src.models.agent_workflow import AgentWorkflow  # noqa: E402


def _find_finch_server() -> MCPServer | None:
    # Prefer exact name
    server = MCPServer.get_by_name('finch_db')
    if server:
        return server
    # Fallback: search by args/path hint
    for s in MCPServer.get_all():
        try:
            cfg = s.config or {}
            args: List[str] = cfg.get('args') or []
            arg_str = ' '.join(args).lower()
            if 'mcp_finch_server.py' in arg_str or 'finch' in (s.name or '').lower():
                return s
        except Exception:
            continue
    return None


def ensure_team_and_workflow() -> Dict[str, Any]:
    # Ensure tables
    MCPServer.create_table()
    AgentTeam.create_table()
    AgentWorkflow.create_table()

    finch = _find_finch_server()
    if not finch:
        return {"success": False, "error": "Finch MCP server not found in mcp_servers. Please add/register it first."}

    finch_sid = int(finch.id)

    # Define allowed tools for DBAgent (all finch tools)
    finch_tools = [
        'health_check',
        'list_tables',
        'get_table_info',
        'run_select',
        'explain_query_plan',
        'get_metadata_overview',
        'get_table_metadata',
        'search_columns',
        'list_joins',
    ]

    # Build team config
    team_name = 'Finch DB Team'
    team_desc = 'AutoGen team with a DBAgent using tools from finch_db (stdio MCP).'
    team_cfg: Dict[str, Any] = {
        'agents': [
            {
                'name': 'DBAgent',
                'role': 'executor',
                'system_prompt': (
                    'You are a database and metadata operator. Use the provided tools to inspect schema, '
                    'search columns, and execute READ-ONLY SQL (SELECT/WITH only). Do not attempt writes. '
                    'Explain results clearly and end your final answer with the word: TERMINATE'
                ),
                'tools': [{'server_id': finch_sid, 'tool_name': t} for t in finch_tools],
            }
        ],
        'controller': {},
        'settings': {'max_rounds': 3},
    }

    # Upsert team
    team = AgentTeam.get_by_name(team_name)
    if team:
        team.description = team_desc
        team.config = team_cfg
        team.save()
    else:
        team = AgentTeam(name=team_name, description=team_desc, config=team_cfg)
        team.save()

    # Build simple workflow graph: single node with DBAgent
    wf_name = 'Finch DB QA'
    wf_desc = 'Single-agent workflow using DBAgent to answer DB/metadata questions.'
    graph = {
        'nodes': [
            {'id': 1, 'name': 'DB Query/Inspect', 'agent': 'DBAgent'},
        ],
        'edges': []
    }

    wf = AgentWorkflow.get_by_name(wf_name)
    if wf:
        wf.description = wf_desc
        wf.team_id = int(team.id)
        wf.graph = graph
        wf.save()
    else:
        wf = AgentWorkflow(name=wf_name, description=wf_desc, team_id=int(team.id), graph=graph)
        wf.save()

    return {
        'success': True,
        'team': {'id': team.id, 'name': team.name},
        'workflow': {'id': wf.id, 'name': wf.name},
        'server': {'id': finch.id, 'name': finch.name},
    }


if __name__ == '__main__':
    result = ensure_team_and_workflow()
    print(result)
