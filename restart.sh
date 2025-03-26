#!/bin/bash

echo "Stopping any running Flask processes..."
pkill -f "python app.py" || true

echo "Clearing any Python cache files..."
find . -type d -name "__pycache__" -exec rm -rf {} +
find . -name "*.pyc" -delete

echo "Starting Flask application with auto-reload..."
export FLASK_DEBUG=1
export FLASK_ENV=development
/home/vijay/anaconda3/bin/python app.py