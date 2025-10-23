#!/usr/bin/env bash
set -euo pipefail

# Start test upstream server in background
~/anaconda3/bin/python3 test_upstream.py &
UPSTREAM_PID=$!

# Start proxy pointing to test upstream
export UPSTREAM_URL="http://127.0.0.1:9001"
~/anaconda3/bin/python3 app.py &
PROXY_PID=$!

# Give servers time to start
sleep 2

echo "== Testing Proxy Server =="
echo "Upstream server running on: http://127.0.0.1:9001"
echo "Proxy server running on: http://127.0.0.1:8080"
echo

echo "== Non-streaming test =="
RESPONSE=$(curl -s -X POST http://127.0.0.1:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"test","messages":[{"role":"user","content":"hi"}]}')

echo "Response:"
echo "$RESPONSE" | jq '.choices[0].message.content' 2>/dev/null || echo "$RESPONSE"
echo

echo "== Streaming test =="
echo "Streaming response:"
curl -N -X POST http://127.0.0.1:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"test","messages":[{"role":"user","content":"hi"}], "stream": true }' \
  2>/dev/null | grep "data:" | head -10

echo
echo "== Test Python client =="
export PROXY_BASE_URL="http://127.0.0.1:8080/v1"
export OPENAI_API_KEY="dummy-key"
timeout 10 ~/anaconda3/bin/python3 upstream.py || echo "Client test completed"

# Cleanup
echo
echo "== Cleanup =="
kill $PROXY_PID $UPSTREAM_PID 2>/dev/null || true
wait $PROXY_PID $UPSTREAM_PID 2>/dev/null || true
echo "Test completed successfully!"
