import asyncio
import os
import sys

# Ensure project root in path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, PROJECT_ROOT)

from src.utils.mcp_client_manager import MCPClient

async def main():
    server_script = os.path.join(PROJECT_ROOT, 'src', 'utils', 'mcp_finch_server.py')
    client = MCPClient(server_id='local-finch', server_name='finch_db', server_type='stdio')
    client.server_config = {
        'command': sys.executable,
        'args': [server_script],
        'env': os.environ.copy(),
    }
    ok = await client.connect_to_stdio_server(client.server_config['command'], client.server_config['args'], client.server_config['env'])
    print('Connected:', ok)
    tools = await client.get_available_tools()
    print('Tools:', [t['function']['name'] for t in (tools or [])])

    # Call a couple of tools
    if ok:
        res = await client.session.call_tool('health_check', {})
        print('health_check:', res.content)
        res = await client.session.call_tool('list_tables', {})
        print('list_tables:', res.content)

    await client.cleanup()

if __name__ == '__main__':
    asyncio.run(main())
