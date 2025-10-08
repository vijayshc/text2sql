from flask import Blueprint, request, jsonify, Response, stream_with_context, session
import asyncio
import logging
import json
import time
import traceback

from src.utils.auth_utils import login_required
from src.models.agent_team import AgentTeam
from src.models.agent_workflow import AgentWorkflow
from src.services.autogen_orchestrator import AutoGenOrchestrator
from src.services.run_monitor import RunMonitor
from src.models.mcp_server import MCPServer, MCPServerStatus
from src.utils.mcp_client_manager import MCPClientManager

logger = logging.getLogger('text2sql')

autogen_bp = Blueprint('autogen', __name__)

@autogen_bp.route('/api/agent/teams', methods=['GET','POST'])
@login_required
def teams():
    if request.method == 'POST':
        data = request.get_json() or {}
        team_id = data.get('id')
        
        if team_id:
            # This is an update request with ID - redirect to PUT logic
            team = AgentTeam.get_by_id(team_id)
            if not team:
                return jsonify({'error': 'Team not found'}), 404
            team.name = data.get('name', team.name)
            team.description = data.get('description', team.description)
            if 'config' in data:
                team.config = data['config']
            team.save()
            return jsonify({'success': True, 'team': {'id': team.id, 'name': team.name}})
        else:
            # This is a new team creation
            team = AgentTeam(name=data.get('name'), description=data.get('description'), config=data.get('config') or {})
            team.save()
            return jsonify({'success': True, 'team': {'id': team.id, 'name': team.name}})
    else:
        AgentTeam.create_table()
        teams = AgentTeam.get_all()
        return jsonify({'success': True, 'teams': [
            {
                'id': t.id,
                'name': t.name,
                'description': t.description,
                'config': t.config
            } for t in teams
        ]})

@autogen_bp.route('/api/agent/teams/<int:team_id>', methods=['GET','PUT','DELETE'])
@login_required
def team_detail(team_id):
    team = AgentTeam.get_by_id(team_id)
    if not team:
        return jsonify({'error':'Team not found'}), 404
    if request.method == 'GET':
        return jsonify({'id': team.id, 'name': team.name, 'description': team.description, 'config': team.config})
    if request.method == 'PUT':
        data = request.get_json() or {}
        team.name = data.get('name', team.name)
        team.description = data.get('description', team.description)
        if 'config' in data:
            team.config = data['config']
        team.save()
        return jsonify({'success': True})
    if request.method == 'DELETE':
        team.delete()
        return jsonify({'success': True})

@autogen_bp.route('/api/agent/workflows', methods=['GET','POST'])
@login_required
def workflows():
    if request.method == 'POST':
        data = request.get_json() or {}
        name = data.get('name')
        if not name:
            return jsonify({'error': 'Workflow name is required'}), 400
        
        # Check if workflow already exists
        existing_wf = AgentWorkflow.get_by_name(name)
        if existing_wf:
            # Update existing workflow
            existing_wf.description = data.get('description', existing_wf.description)
            existing_wf.team_id = data.get('team_id', existing_wf.team_id)
            existing_wf.graph = data.get('graph', existing_wf.graph)
            existing_wf.save()
            return jsonify({'success': True, 'workflow': {'id': existing_wf.id, 'name': existing_wf.name}, 'updated': True})
        else:
            # Create new workflow
            wf = AgentWorkflow(name=name, description=data.get('description'), team_id=data.get('team_id'), graph=data.get('graph') or {})
            wf.save()
            return jsonify({'success': True, 'workflow': {'id': wf.id, 'name': wf.name}, 'created': True})
    else:
        AgentWorkflow.create_table()
        wfs = AgentWorkflow.get_all()
        return jsonify({'success': True, 'workflows':[{
            'id': w.id, 'name': w.name, 'description': w.description, 'team_id': w.team_id, 'graph': w.graph
        } for w in wfs]})

@autogen_bp.route('/api/agent/workflows/<int:wf_id>', methods=['GET','PUT','DELETE'])
@login_required
def workflow_detail(wf_id):
    wf = AgentWorkflow.get_by_id(wf_id)
    if not wf:
        return jsonify({'error':'Workflow not found'}), 404
    if request.method == 'GET':
        return jsonify({'id': wf.id, 'name': wf.name, 'description': wf.description, 'team_id': wf.team_id, 'graph': wf.graph})
    if request.method == 'PUT':
        data = request.get_json() or {}
        wf.name = data.get('name', wf.name)
        wf.description = data.get('description', wf.description)
        wf.team_id = data.get('team_id', wf.team_id)
        if 'graph' in data:
            wf.graph = data['graph']
        wf.save()
        return jsonify({'success': True})
    if request.method == 'DELETE':
        wf.delete()
        return jsonify({'success': True})

@autogen_bp.route('/api/agent/run/team/<int:team_id>', methods=['POST'])
@login_required
def run_team(team_id):
    team = AgentTeam.get_by_id(team_id)
    if not team:
        return jsonify({'error':'Team not found'}), 404
    data = request.get_json() or {}
    task = data.get('task') or data.get('query') or ''
    context = data.get('context')
    orch = AutoGenOrchestrator()
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    result = loop.run_until_complete(orch.run_team(team, task, context))
    loop.close()
    return jsonify(result)

@autogen_bp.route('/api/agent/run/workflow/<int:wf_id>', methods=['POST'])
@login_required
def run_workflow(wf_id):
    wf = AgentWorkflow.get_by_id(wf_id)
    if not wf:
        return jsonify({'error':'Workflow not found'}), 404
    data = request.get_json() or {}
    task = data.get('task') or data.get('query') or ''
    context = data.get('context')
    orch = AutoGenOrchestrator()
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    result = loop.run_until_complete(orch.run_workflow(wf, task, context))
    loop.close()
    
    # Ensure result is JSON serializable
    try:
        # Create a clean result that's guaranteed to be JSON serializable
        clean_result = {
            "success": result.get("success", False),
            "reply": result.get("reply", ""),
            "run_id": result.get("run_id"),
            "error": result.get("error"),
            "trace": result.get("trace")
        }
        # Remove None values
        clean_result = {k: v for k, v in clean_result.items() if v is not None}
        return jsonify(clean_result)
    except Exception as e:
        logger.error(f"JSON serialization error: {e}")
        return jsonify({
            "success": False,
            "error": "Result serialization failed",
            "trace": str(e)
        })

@autogen_bp.route('/api/agent/autogen/chat', methods=['POST'])
@login_required
def autogen_chat_stream():
    """SSE stream wrapper to run AutoGen team/workflow and stream status + final reply."""
    data = request.get_json() or {}
    query = data.get('query') or data.get('task')
    team_id = data.get('team_id')
    workflow_id = data.get('workflow_id')
    context = data.get('conversation_history')

    if not query:
        return jsonify({'error': 'Missing query'}), 400
    if not team_id and not workflow_id:
        return jsonify({'error': 'team_id or workflow_id required'}), 400

    def generate():
        collected = []
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        orch = AutoGenOrchestrator()
        try:
            # Resolve entity (workflow or team)
            entity = None
            if workflow_id:
                wf = AgentWorkflow.get_by_id(int(workflow_id))
                if not wf:
                    yield f"data: {json.dumps({'type':'error','message':'Workflow not found'})}\n\n"
                    yield f"data: {json.dumps({'type':'done'})}\n\n"
                    return
                entity = wf
            elif team_id:
                tm = AgentTeam.get_by_id(int(team_id))
                if not tm:
                    yield f"data: {json.dumps({'type':'error','message':'Team not found'})}\n\n"
                    yield f"data: {json.dumps({'type':'done'})}\n\n"
                    return
                entity = tm

            # Status update
            yield f"data: {json.dumps({'type':'status','message':'Running AutoGen orchestration...'})}\n\n"
            try:
                if isinstance(entity, AgentWorkflow):
                    res = loop.run_until_complete(orch.run_workflow(entity, query, context))
                else:
                    res = loop.run_until_complete(orch.run_team(entity, query, context))
                if res.get('success'):
                    reply = res.get('reply') or res.get('final') or ''
                    collected.append(reply)
                    
                    # Fetch llm_result from run events if run_id is available
                    llm_result_data = None
                    run_id = res.get('run_id')
                    if run_id:
                        try:
                            events = RunMonitor.get_events(run_id)
                            # Find the last llm_result event
                            for event in reversed(events):
                                if event.get('event_type') == 'llm_result':
                                    llm_result_data = event.get('detail', {})
                                    break
                        except Exception as e:
                            logger.warning(f"Failed to fetch llm_result: {e}")
                    
                    yield f"data: {json.dumps({'type':'llm_response','content': reply, 'is_final': True, 'run_id': run_id, 'llm_result': llm_result_data})}\n\n"
                else:
                    err_msg = res.get('error', 'Unknown error')
                    collected.append(f"ERROR: {err_msg}")
                    yield f"data: {json.dumps({'type':'error','message': err_msg, 'trace': res.get('trace'), 'run_id': res.get('run_id')})}\n\n"
            except Exception as e:
                err_msg = str(e)
                tb = traceback.format_exc()
                collected.append(f"ERROR: {err_msg}")
                yield f"data: {json.dumps({'type':'error','message': err_msg, 'trace': tb})}\n\n"

            # Done
            yield f"data: {json.dumps({'type':'done'})}\n\n"
        finally:
            try:
                loop.close()
            except Exception:
                pass

    return Response(stream_with_context(generate()), mimetype='text/event-stream')

@autogen_bp.route('/api/agent/runs', methods=['GET'])
@login_required
def list_runs():
    limit = int(request.args.get('limit', 50))
    runs = RunMonitor.list_runs(limit=limit)
    return jsonify({'success': True, 'runs': runs})

@autogen_bp.route('/api/agent/runs/<int:run_id>', methods=['GET'])
@login_required
def get_run(run_id: int):
    run = RunMonitor.get_run(run_id)
    if not run:
        return jsonify({'error': 'Run not found'}), 404
    
    # Use filtered events by default, allow full events with ?full=1
    use_filtered = request.args.get('full') != '1'
    if use_filtered:
        events = RunMonitor.get_filtered_events(run_id)
    else:
        events = RunMonitor.get_events(run_id)
    
    return jsonify({'success': True, 'run': run, 'events': events, 'filtered': use_filtered})

@autogen_bp.route('/api/agent/mcp/servers-with-tools', methods=['GET'])
@login_required
def list_servers_with_tools():
    """Returns MCP servers and their available tools for UI-driven agent config."""
    servers = MCPServer.get_all()
    result = []
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        for s in servers:
            if s.status != MCPServerStatus.RUNNING.value:
                continue
            tools = []
            try:
                client = loop.run_until_complete(MCPClientManager.get_client(s.id, connect=True))
                if client:
                    tlist = loop.run_until_complete(client.get_available_tools())
                    for t in tlist or []:
                        tools.append({
                            'name': t['function']['name'],
                            'title': t.get('name') or t['function']['name'],
                            'description': t.get('description'),
                            'schema': t['function'].get('parameters')
                        })
            except Exception as e:
                logger.warning(f"Failed to list tools for server {s.name}: {e}")
            result.append({
                'id': s.id,
                'name': s.name,
                'description': s.description,
                'tools': tools
            })
    finally:
        try:
            loop.close()
        except Exception:
            pass
    return jsonify({'success': True, 'servers': result})
