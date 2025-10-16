"""
Gunicorn configuration for Text2SQL application
Optimized for handling high concurrency (50+ concurrent users)
"""

import multiprocessing

# Server socket
bind = '0.0.0.0:5000'
backlog = 2048  # Listen backlog - how many requests can queue before server is ready

# Worker processes
# For I/O bound applications (which this is), workers = (2 * CPU) + 1 is typical
# We use threads instead for better async handling
workers = 1  # Single worker process
worker_class = 'gthread'  # Use threaded worker
threads = 50  # 50 threads per worker to handle 50+ concurrent connections
max_requests = 1000  # Restart worker after 1000 requests to prevent memory leaks
max_requests_jitter = 50  # Random jitter to prevent thundering herd

# Timeouts
timeout = 30  # Worker timeout (seconds)
keepalive = 5  # Seconds to wait for next request on Keep-Alive connections

# Logging
accesslog = '/home/vijay/gitrepo/copilot/text2sql/logs/gunicorn_access.log'
errorlog = '/home/vijay/gitrepo/copilot/text2sql/logs/gunicorn_error.log'
loglevel = 'info'
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Server mechanics
daemon = False  # Don't daemonize (let docker/supervisor manage)
pidfile = '/home/vijay/gitrepo/copilot/text2sql/logs/gunicorn.pid'

# Server lifecycle
graceful_timeout = 30  # Grace period for graceful shutdown

# Process naming
proc_name = 'text2sql'

# Settings for production
forwarded_allow_ips = '127.0.0.1'  # For X-Forwarded-* headers from reverse proxy

print(f"""
================================================================================
Gunicorn Configuration for Text2SQL
================================================================================
Bind: {bind}
Worker Class: {worker_class}
Threads per Worker: {threads}
Backlog: {backlog}
Max Requests: {max_requests}
Timeout: {timeout}s
================================================================================
This configuration can handle 50+ concurrent users with proper thread pooling.
""")
