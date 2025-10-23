import os
import requests
from flask import Flask, request, Response, stream_with_context

app = Flask(__name__)
UPSTREAM_URL = os.environ.get("UPSTREAM_URL")
if not UPSTREAM_URL:
    # sensible default for testing; prefer setting UPSTREAM_URL explicitly
    UPSTREAM_URL = "https://api.groq.com/openai/v1"

# Helper: build upstream URL by preserving the path and query

def build_upstream_url(path: str, query_string: str) -> str:
    if query_string:
        return f"{UPSTREAM_URL}{path}?{query_string}"
    return f"{UPSTREAM_URL}{path}"


@app.route("/", defaults={"path": ""}, methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"])
@app.route("/<path:path>", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"])
def proxy(path: str):
    """Proxy any request to the UPSTREAM_URL preserving headers and body. Supports streaming responses.

    Behavior:
    - Receives incoming request from a client (OpenAI API client)
    - Forwards headers and body as-is to the upstream OpenAI-compatible server
    - Streams the upstream response back to the client unchanged (both streaming and non-streaming)
    """
    upstream_url = build_upstream_url(request.path, request.query_string.decode("utf-8"))

    # Prepare headers: copy incoming headers but remove/adjust hop-by-hop headers
    headers = {}
    for k, v in request.headers.items():
        # Skip Host header; requests will set it from upstream_url
        if k.lower() == "host":
            continue
        # Skip content-length when streaming with chunked transfer
        if k.lower() == "content-length" and request.headers.get("transfer-encoding"):
            continue
        headers[k] = v

    # Choose streaming or not based on client's request body (if `stream` field present) or incoming query
    # However, safest is to forward request body as-is and let upstream decide. For client streaming, they will
    # open a streaming response (Transfer-Encoding: chunked) and expect streaming back. We'll stream upstream
    # response back when upstream responds with chunked/streaming.

    # Prepare data/stream: forward raw body bytes
    data = request.get_data()

    try:
        # Stream the request to the upstream and stream back the response
        upstream_resp = requests.request(
            method=request.method,
            url=upstream_url,
            headers=headers,
            data=data if data else None,
            stream=True,
            allow_redirects=False,
            timeout=60,
        )
    except requests.RequestException as e:
        return (f"Upstream request failed: {e}", 502)

    # Build response headers for client, copying upstream headers except some hop-by-hop ones
    def generate():
        try:
            for chunk in upstream_resp.iter_content(chunk_size=8192):
                if chunk:
                    yield chunk
        finally:
            upstream_resp.close()

    excluded_headers = [
        'transfer-encoding',
        'content-encoding',
        'connection',
        'keep-alive',
        'proxy-authenticate',
        'proxy-authorization',
        'te',
        'trailers',
        'upgrade'
    ]

    response_headers = []
    for k, v in upstream_resp.headers.items():
        if k.lower() in excluded_headers:
            continue
        response_headers.append((k, v))

    # Preserve status code and streamed body
    return Response(stream_with_context(generate()), status=upstream_resp.status_code, headers=response_headers)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8080"))
    app.run(host="0.0.0.0", port=port)
