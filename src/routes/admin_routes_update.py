@admin_bp.route('/mcp-servers')
@admin_required
def mcp_servers():
    """MCP Server management page"""
    return render_template('admin/mcp_servers.html')
