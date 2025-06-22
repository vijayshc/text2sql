#!/bin/bash

# Text2SQL Application Startup Script
# This script starts both the ChromaDB service and the main application

echo "🚀 Starting Text2SQL Application..."
echo "=================================="

# Set Python path
PYTHON_PATH="/home/vijay/anaconda3/bin/python"

# Check if Python is available
if [ ! -f "$PYTHON_PATH" ]; then
    echo "❌ Python not found at $PYTHON_PATH"
    echo "Please update PYTHON_PATH in this script"
    exit 1
fi

# Function to check if port is in use
check_port() {
    local port=$1
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
        return 0  # Port is in use
    else
        return 1  # Port is free
    fi
}

# Start ChromaDB service
echo "🔧 Starting ChromaDB service..."
cd chromadb_service

if check_port 8001; then
    echo "⚠️  Port 8001 is already in use. ChromaDB service may already be running."
    echo "   To stop existing service: ps aux | grep 'python app.py' | grep chromadb"
else
    echo "   Starting service on port 8001..."
    $PYTHON_PATH app.py > service.log 2>&1 &
    CHROMADB_PID=$!
    echo "   ChromaDB service started with PID: $CHROMADB_PID"
    
    # Wait a moment for service to start
    sleep 3
    
    # Check if service is running
    if kill -0 $CHROMADB_PID 2>/dev/null; then
        echo "✅ ChromaDB service is running"
    else
        echo "❌ Failed to start ChromaDB service"
        echo "   Check chromadb_service/service.log for errors"
        exit 1
    fi
fi

# Go back to main directory
cd ..

# Start main application
echo "🔧 Starting main application..."
if check_port 5000; then
    echo "⚠️  Port 5000 is already in use. Main application may already be running."
else
    echo "   Starting application on port 5000..."
    $PYTHON_PATH app.py > logs/app.log 2>&1 &
    APP_PID=$!
    echo "   Main application started with PID: $APP_PID"
    
    # Wait a moment for application to start
    sleep 3
    
    # Check if application is running
    if kill -0 $APP_PID 2>/dev/null; then
        echo "✅ Main application is running"
    else
        echo "❌ Failed to start main application"
        echo "   Check logs/app.log for errors"
        exit 1
    fi
fi

echo ""
echo "🎉 Text2SQL Application is running!"
echo "=================================="
echo "📱 Main Application: http://localhost:5000"
echo "🔧 ChromaDB Service: http://localhost:8001"
echo ""
echo "📋 To stop the application:"
echo "   Main app: ps aux | grep 'python app.py' | grep -v chromadb"
echo "   ChromaDB: ps aux | grep 'python app.py' | grep chromadb"
echo ""
echo "📄 Logs:"
echo "   Main app: tail -f logs/app.log"
echo "   ChromaDB: tail -f chromadb_service/service.log"
echo ""
echo "Press Ctrl+C to stop this script (services will continue running)"

# Keep script running to show status
trap 'echo ""; echo "Script stopped. Services are still running."; exit 0' INT

# Wait indefinitely
while true; do
    sleep 60
done
