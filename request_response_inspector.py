"""
Lab 72: API HTTP Request & Response Inspector
A minimal, zero-dependency Python HTTP server to inspect wire-level request
headers, methods, paths, and query parameters, and send formatted JSON responses
with standard HTTP response headers.

Usage:
    python request_response_inspector.py
    
Test in another terminal:
    # 1. GET Request:
    curl -v http://localhost:8080/api/v1/packages?category=trekking

    # 2. POST Request:
    curl -v -X POST http://localhost:8080/api/v1/packages \
      -H "Content-Type: application/json" \
      -H "Authorization: Bearer dev_token_kashmir" \
      -d '{"name": "Pahalgam Valley Tour", "price": 22000}'
"""

from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import time

class InspectorHandler(BaseHTTPRequestHandler):
    def _set_headers(self, status_code=200):
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Server", "Python-Inspector-Lab72")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.end_headers()

    def do_OPTIONS(self):
        """Handle CORS pre-flight requests."""
        self._set_headers(204)

    def do_GET(self):
        """Handle GET requests and inspect incoming request lines and headers."""
        print("\n" + "=" * 60)
        print("[HTTP REQUEST RECEIVED: GET]")
        print(f"Command / Method : {self.command}")
        print(f"Resource Path    : {self.path}")
        print(f"HTTP Version     : {self.request_version}")
        print("-" * 60)
        print("Incoming Request Headers:")
        for header, val in self.headers.items():
            print(f"  {header}: {val}")
        print("=" * 60)

        self._set_headers(200)
        response_payload = {
            "status": "success",
            "message": "GET request processed successfully",
            "method": self.command,
            "path": self.path,
            "headers_count": len(self.headers),
            "timestamp": time.time()
        }
        self.wfile.write(json.dumps(response_payload, indent=2).encode("utf-8"))

    def do_POST(self):
        """Handle POST requests, validate Content-Type, read Content-Length bytes."""
        print("\n" + "=" * 60)
        print("[HTTP REQUEST RECEIVED: POST]")
        print(f"Command / Method : {self.command}")
        print(f"Resource Path    : {self.path}")
        
        content_length = int(self.headers.get("Content-Length", 0))
        content_type = self.headers.get("Content-Type", "")
        auth_header = self.headers.get("Authorization", "None provided")
        
        print(f"Content-Type     : {content_type}")
        print(f"Content-Length   : {content_length} bytes")
        print(f"Authorization    : {auth_header}")
        print("-" * 60)

        # Read exact body bytes according to Content-Length
        body_bytes = self.rfile.read(content_length)
        body_str = body_bytes.decode("utf-8")
        print(f"Raw Request Body :\n{body_str}")
        print("=" * 60)

        try:
            parsed_json = json.loads(body_str) if body_str else {}
        except json.JSONDecodeError:
            self._set_headers(400)
            error_response = {
                "status": "error",
                "statusCode": 400,
                "message": "Malformed JSON in request body"
            }
            self.wfile.write(json.dumps(error_response, indent=2).encode("utf-8"))
            return

        self._set_headers(201)
        response_payload = {
            "status": "success",
            "statusCode": 201,
            "message": "Resource created successfully",
            "receivedPayload": parsed_json,
            "receivedContentType": content_type
        }
        self.wfile.write(json.dumps(response_payload, indent=2).encode("utf-8"))

def main(port=8080):
    server = HTTPServer(("0.0.0.0", port), InspectorHandler)
    print(f"🚀 Lab 72 Inspector running on http://localhost:{port}")
    print("Press Ctrl+C to stop the server.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping server gracefully...")
        server.server_close()

if __name__ == "__main__":
    main()
