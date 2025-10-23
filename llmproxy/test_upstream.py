#!/usr/bin/env python3
"""
Simple test upstream server that mimics OpenAI API responses.
This is used for testing the proxy server functionality.
"""

from flask import Flask, request, Response, jsonify
import json
import time

app = Flask(__name__)

@app.route('/v1/chat/completions', methods=['POST'])
def completions():
    try:
        body = request.get_json(force=True)
    except Exception:
        body = {}

    if body.get('stream'):
        def gen():
            messages = ["Hello", " from", " test", " upstream", " server", " stream!"]
            for i, m in enumerate(messages):
                chunk = {
                    "id": f"chatcmpl-test-{i}",
                    "object": "chat.completion.chunk",
                    "choices": [{"delta": {"content": m}, "index": 0, "finish_reason": None}]
                }
                yield f"data: {json.dumps(chunk)}\n\n"
                time.sleep(0.1)

            # Send final chunk
            final_chunk = {
                "id": f"chatcmpl-test-final",
                "object": "chat.completion.chunk",
                "choices": [{"delta": {}, "index": 0, "finish_reason": "stop"}]
            }
            yield f"data: {json.dumps(final_chunk)}\n\n"
            yield "data: [DONE]\n\n"

        return Response(gen(), status=200, content_type='text/event-stream')

    # Non-streaming response
    resp = {
        "id": "chatcmpl-test",
        "object": "chat.completion",
        "choices": [{
            "message": {
                "role": "assistant",
                "content": "Hello from test upstream server non-stream!"
            },
            "index": 0,
            "finish_reason": "stop"
        }],
        "usage": {
            "prompt_tokens": 10,
            "completion_tokens": 8,
            "total_tokens": 18
        }
    }
    return jsonify(resp)

if __name__ == '__main__':
    print("Starting test upstream server on port 9001...")
    app.run(host='127.0.0.1', port=9001, debug=False)
