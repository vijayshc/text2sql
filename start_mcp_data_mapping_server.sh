#!/bin/bash

# Start MCP Data Mapping Analyst Server
# This script starts the data mapping server on port 8003

echo "Starting MCP Data Mapping Analyst Server..."

# Set the Python path to include the project root
export PYTHONPATH="/home/vijay/text2sql_react:$PYTHONPATH"

# Change to the project directory
cd /home/vijay/text2sql_react

# Check if virtual environment exists and activate it
if [ -d "venv" ]; then
    echo "Activating virtual environment..."
    source venv/bin/activate
elif [ -d ".venv" ]; then
    echo "Activating virtual environment..."
    source .venv/bin/activate
fi

# Check if required dependencies are installed
echo "Checking dependencies..."
python -c "import uvicorn, mcp, networkx" 2>/dev/null || {
    echo "Installing required dependencies..."
    pip install uvicorn mcp networkx
}

# Start the server
echo "Starting MCP Data Mapping Analyst Server on http://localhost:8003"
python -m src.services.mcp_data_mapping_server --host 0.0.0.0 --port 8003

echo "MCP Data Mapping Analyst Server stopped."
