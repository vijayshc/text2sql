# src/routes/tool_confirmation_routes.py
from flask import Blueprint, request, jsonify

# Store confirmation flags for tool calls: None = pending, True/False = user decision
confirm_flags = {}

tool_confirmation_bp = Blueprint('tool_confirmation', __name__)

@tool_confirmation_bp.route('/agent/confirm_tool', methods=['POST'])
def confirm_tool():
    """Endpoint to receive user confirmation for sensitive tool execution."""
    data = request.get_json()
    call_id = data.get('call_id')
    confirm = data.get('confirm', False)
    if call_id in confirm_flags:
        confirm_flags[call_id] = bool(confirm)
        return jsonify({'success': True}), 200
    else:
        return jsonify({'success': False, 'error': 'Invalid call_id'}), 400