#!/bin/bash

# MCP Skill Library Server Startup Script

# Get the script directory (this script is in the project root)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$SCRIPT_DIR"

# Configuration
HOST="${MCP_SKILL_HOST:-localhost}"
PORT="${MCP_SKILL_PORT:-8002}"
DEBUG="${MCP_SKILL_DEBUG:-false}"

# Python environment
PYTHON_PATH="${PYTHON_PATH:-/home/vijay/anaconda3/bin/python}"

# Set PYTHONPATH
export PYTHONPATH="$PROJECT_ROOT:$PYTHONPATH"

# Change to project directory
cd "$PROJECT_ROOT"

echo "Starting MCP Skill Library Server..."
echo "Host: $HOST"
echo "Port: $PORT"
echo "Debug: $DEBUG"
echo "Project Root: $PROJECT_ROOT"
echo "Python: $PYTHON_PATH"

# Start the server
if [ "$DEBUG" = "true" ]; then
    "$PYTHON_PATH" src/services/mcp_skill_server.py --host "$HOST" --port "$PORT" --debug
else
    "$PYTHON_PATH" src/services/mcp_skill_server.py --host "$HOST" --port "$PORT"
fi
