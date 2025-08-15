#!/bin/bash

# Start Finch MCP Server
# This script starts the Finch Database Intelligence MCP server

set -e

echo "Starting Finch MCP Database Intelligence Server..."

# Check if Python environment is properly set up
if ! command -v python3 &> /dev/null; then
    echo "Error: Python3 not found. Please install Python3."
    exit 1
fi

# Check if required modules are available
python3 -c "import mcp, sqlite3, json" 2>/dev/null || {
    echo "Error: Required Python modules not found. Please install dependencies."
    echo "Run: pip install -r requirements.txt"
    exit 1
}

# Set working directory
cd "$(dirname "$0")/../.."

# Set environment variables
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# Start the Finch MCP server (stdio-style server should be started by a client)
# For manual debug, we can still run it directly to verify no import errors.
echo "Starting Finch MCP server (stdio mode)..."
python3 src/utils/mcp_finch_server.py

echo "Finch MCP server stopped."
