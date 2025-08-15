"""
Full seed script: Register a comprehensive Finch-style AutoGen team with multiple agents and workflows.

Creates/updates:
- MCP server reference check (expects 'finch_db' already registered and running)
- AgentTeam: "Finch Analytics Team" with 4 agents wired to finch_db tools
  1) Analyst (planner) - no tools; plans and coordinates
  2) MetadataExpert - metadata discovery tools
  3) DBEngineer - DB execution tools (read-only)
  4) SQLReviewer - validation/safety checks
- AgentWorkflow: "Finch Analytics Workflow" with a 4-node sequence (Analyst → MetadataExpert → DBEngineer → SQLReviewer)
- AgentWorkflow: "Finch Quick QA" (single-node DBEngineer as a fast path)

Idempotent: re-running updates existing rows.
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


def ensure_full_team_and_workflows() -> Dict[str, Any]:
    # Ensure tables exist
    MCPServer.create_table()
    AgentTeam.create_table()
    AgentWorkflow.create_table()

    finch = _find_finch_server()
    if not finch:
        return {"success": False, "error": "Finch MCP server not found in mcp_servers. Please add/register it first."}

    finch_sid = int(finch.id)

    # Tool groupings from finch_db server
    tools_metadata = ['get_metadata_overview', 'get_table_metadata', 'search_columns', 'list_joins', 'list_tables']
    tools_db_read = ['health_check', 'list_tables', 'get_table_info', 'run_select', 'explain_query_plan']

    # Define multi-agent team
    team_name = 'Finch Analytics Team'
    team_desc = 'Comprehensive multi-agent team inspired by Finch (Uber) using finch_db MCP tools.'
    team_cfg: Dict[str, Any] = {
        'agents': [
            {
                'name': 'Analyst',
                'role': 'planner',
                'system_prompt': (
                    'You are the planning analyst. You NEVER write SQL or call tools.\n'
                    'Your job: understand the user request, create a short plan, and DELEGATE FIRST to MetadataExpert to discover schema details.\n\n'
                    'Flow you MUST follow for every task:\n'
                    '1) Delegate to MetadataExpert to: list_tables; search_columns with key terms from the user request; get_table_metadata on candidate tables; list_joins if >1 table likely.\n'
                    '2) After MetadataExpert returns findings, delegate to DBEngineer to write and execute SQL using run_select, referencing the discovered tables/columns/joins.\n'
                    '3) Finally, delegate to SQLReviewer to validate and provide the final answer.\n\n'
                    'Output format:\n'
                    '- A very brief plan\n'
                    '- One explicit delegation line for the next agent.\n\n'
                    'Example delegation:\n'
                    "NEXT: MetadataExpert -> list_tables; search_columns('customers'); get_table_metadata('customers')\n\n"
                    'Do not propose or include SQL. End your final message with: TERMINATE'
                ),
                'tools': []  # Planner does not call tools directly
            },
            {
                'name': 'MetadataExpert',
                'role': 'metadata',
                'system_prompt': (
                    'You perform schema discovery ONLY. You NEVER write SQL.\n'
                    'Use: list_tables, search_columns, get_table_metadata, get_metadata_overview, list_joins.\n'
                    'Goal: identify exact table/column names and any join keys required to answer the request.\n'
                    'Produce a concise summary of findings:\n'
                    '- Candidate tables\n'
                    '- Relevant columns\n'
                    '- Join keys (if multi-table)\n'
                    '- Suggested filters/aggregations in natural language (no SQL)\n\n'
                    'Then delegate to DBEngineer to WRITE AND EXECUTE the SQL using run_select, referencing these findings.\n'
                    "Example: NEXT: DBEngineer -> Use table 'customers'. Compute count of rows. Execute with run_select.\n\n"
                    'End your final message with: TERMINATE'
                ),
                'tools': [{'server_id': finch_sid, 'tool_name': t} for t in tools_metadata],
            },
            {
                'name': 'DBEngineer',
                'role': 'executor',
                'system_prompt': (
                    'You write and execute READ-ONLY SQL (SELECT/WITH only) based on MetadataExpert findings.\n'
                    'Steps:\n'
                    '- Construct a minimal correct SQL using the discovered table/column/joins.\n'
                    "- For counts, prefer: SELECT COUNT(*) AS count FROM <table>;\n"
                    '- If join is needed, use join keys discovered by MetadataExpert.\n'
                    '- If uncertain, use get_table_info to inspect columns, then adjust.\n'
                    '- Execute with run_select and summarize the result succinctly.\n'
                    '- On errors, explain briefly and retry after inspecting schema.\n\n'
                    'Always produce a short, direct answer and end with: TERMINATE'
                ),
                'tools': [{'server_id': finch_sid, 'tool_name': t} for t in tools_db_read],
            },
            {
                'name': 'SQLReviewer',
                'role': 'reviewer',
                'system_prompt': (
                    'You verify safety/performance/correctness. If results are available, present the final concise answer.\n'
                    'If only SQL is present, you may run explain_query_plan or run_select to confirm before concluding.\n'
                    'Keep it brief and end with: TERMINATE'
                ),
                'tools': [
                    {'server_id': finch_sid, 'tool_name': 'get_table_info'},
                    {'server_id': finch_sid, 'tool_name': 'explain_query_plan'},
                    {'server_id': finch_sid, 'tool_name': 'run_select'},
                ],
            },
        ],
        'controller': {
            # Keep controller simple; RoundRobinGroupChat in orchestrator manages flow and termination
        },
        'settings': {'max_rounds': 8},
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

    # Primary workflow: 4-node sequence
    wf1_name = 'Finch Analytics Workflow'
    wf1_desc = 'Analyst → MetadataExpert → DBEngineer → SQLReviewer'
    graph1 = {
        'nodes': [
            {'id': 1, 'name': 'Plan', 'agent': 'Analyst'},
            {'id': 2, 'name': 'Discover Metadata', 'agent': 'MetadataExpert'},
            {'id': 3, 'name': 'Execute SQL', 'agent': 'DBEngineer'},
            {'id': 4, 'name': 'Review SQL', 'agent': 'SQLReviewer'},
        ],
        'edges': [
            {'from': 1, 'to': 2},
            {'from': 2, 'to': 3},
            {'from': 3, 'to': 4},
        ]
    }

    wf1 = AgentWorkflow.get_by_name(wf1_name)
    if wf1:
        wf1.description = wf1_desc
        wf1.team_id = int(team.id)
        wf1.graph = graph1
        wf1.save()
    else:
        wf1 = AgentWorkflow(name=wf1_name, description=wf1_desc, team_id=int(team.id), graph=graph1)
        wf1.save()

    # Secondary quick path: single DBEngineer node
    wf2_name = 'Finch Quick QA'
    wf2_desc = 'Fast path DB Q&A using DBEngineer only'
    graph2 = {
        'nodes': [
            {'id': 1, 'name': 'DB QA', 'agent': 'DBEngineer'},
        ],
        'edges': []
    }

    wf2 = AgentWorkflow.get_by_name(wf2_name)
    if wf2:
        wf2.description = wf2_desc
        wf2.team_id = int(team.id)
        wf2.graph = graph2
        wf2.save()
    else:
        wf2 = AgentWorkflow(name=wf2_name, description=wf2_desc, team_id=int(team.id), graph=graph2)
        wf2.save()

    return {
        'success': True,
        'server': {'id': finch.id, 'name': finch.name},
        'team': {'id': team.id, 'name': team.name},
        'workflows': [
            {'id': wf1.id, 'name': wf1.name},
            {'id': wf2.id, 'name': wf2.name},
        ],
    }


if __name__ == '__main__':
    print(ensure_full_team_and_workflows())
