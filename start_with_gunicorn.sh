#!/bin/bash

# Start Text2SQL with Gunicorn (production WSGI server)
# This configuration handles 50+ concurrent users efficiently

cd /home/vijay/gitrepo/copilot/text2sql

echo "Starting Text2SQL with Gunicorn..."
echo "Configuration: 1 worker, 50 threads"
echo "Ready to handle 50+ concurrent users"
echo ""

export GITHUB_TOKEN="${GITHUB_TOKEN:-github_token_placeholder}"

# Run gunicorn with the configuration file
~/anaconda3/bin/gunicorn \
  --config gunicorn_config.py \
  --workers 1 \
  --worker-class gthread \
  --threads 50 \
  --bind 0.0.0.0:5000 \
  --backlog 2048 \
  --timeout 30 \
  --access-logfile logs/gunicorn_access.log \
  --error-logfile logs/gunicorn_error.log \
  app:app
