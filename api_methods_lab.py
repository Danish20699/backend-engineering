"""
Lab 73 — API Request Methods & Idempotency Deep Dive
=====================================================
Backend Engineering Course
Module 13 — FastAPI Backend & Backend Engineering

A zero-dependency HTTP server built with Python's http.server that
demonstrates ALL standard HTTP methods (GET, POST, PUT, PATCH,
DELETE, OPTIONS, HEAD) using an in-memory Kashmir tourism packages
database.

Run:
    python api_methods_lab.py

Server starts on:
    http://localhost:8081

Test with:
    curl -v http://localhost:8081/api/v1/packages
    curl -v http://localhost:8081/api/v1/packages/1
    curl -v -X POST http://localhost:8081/api/v1/packages -H "Content-Type: application/json" -d '{"name":"Test","price":1000}'
    curl -v -X PUT http://localhost:8081/api/v1/packages/1 -H "Content-Type: application/json" -d '{"name":"Updated","price":2000,"duration":"3D","category":"winter"}'
    curl -v -X PATCH http://localhost:8081/api/v1/packages/1 -H "Content-Type: application/json" -d '{"price":99999}'
    curl -v -X DELETE http://localhost:8081/api/v1/packages/3
    curl -v -X OPTIONS http://localhost:8081/api/v1/packages
    curl -v --head http://localhost:8081/api/v1/packages/1

Engineer : Danish
Track    : MLOps / DevOps Engineering (APR26)
"""

import json
import sys
import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler

# ---------------------------------------------------------------------------
# Force UTF-8 on Windows consoles so emoji / special chars don't crash
# ---------------------------------------------------------------------------
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# ---------------------------------------------------------------------------
# In-Memory "Database" — pre-populated with 3 Kashmir tourism packages
# ---------------------------------------------------------------------------
packages_db = {
    1: {"id": 1, "name": "Gulmarg Skiing Adventure", "price": 45000, "duration": "5D", "category": "winter"},
    2: {"id": 2, "name": "Dal Lake Houseboat Stay",  "price": 12000, "duration": "3D", "category": "leisure"},
    3: {"id": 3, "name": "Sonamarg Glacier Trek",     "price": 18000, "duration": "4D", "category": "trekking"},
}

# Auto-incrementing ID counter (next available ID)
next_id = 4


# ═══════════════════════════════════════════════════════════════════════════
#  Helper: pretty-print wire-level inspection to the console
# ═══════════════════════════════════════════════════════════════════════════
SEPARATOR = "═" * 72


def log_request_details(handler, body=None):
    """
    Print detailed wire-level request information to the console.
    This mirrors what you'd see in a packet capture or 'curl -v' output,
    helping you understand exactly what the client sent over the wire.
    """
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"\n{SEPARATOR}")
    print(f"  ⏱  {timestamp}")
    print(f"  ➤  {handler.command} {handler.path} {handler.request_version}")
    print(f"{SEPARATOR}")
    print("  Request Headers:")
    for header, value in handler.headers.items():
        print(f"    {header}: {value}")
    if body:
        print(f"  Request Body ({len(body)} bytes):")
        try:
            parsed = json.loads(body)
            print(f"    {json.dumps(parsed, indent=4, ensure_ascii=False)}")
        except (json.JSONDecodeError, UnicodeDecodeError):
            print(f"    (raw) {body[:200]}")
    else:
        print("  Request Body: (none)")
    print(SEPARATOR)


def log_response_details(status_code, response_body=None):
    """
    Print detailed wire-level response information to the console.
    Shows the status code and body that the server is sending back.
    """
    print(f"  ◄── Response: {status_code}")
    if response_body:
        try:
            parsed = json.loads(response_body)
            print(f"  Response Body:\n    {json.dumps(parsed, indent=4, ensure_ascii=False)}")
        except (json.JSONDecodeError, UnicodeDecodeError):
            print(f"  Response Body:\n    {response_body[:300]}")
    else:
        print("  Response Body: (none)")
    print(SEPARATOR + "\n")


# ═══════════════════════════════════════════════════════════════════════════
#  Helper: send a JSON response
# ═══════════════════════════════════════════════════════════════════════════
def send_json(handler, status_code, data, headers=None):
    """
    Serialise `data` to JSON and send it with the given status code.
    This is the standard way our API returns structured responses.
    """
    body = json.dumps(data, ensure_ascii=False).encode("utf-8")
    handler.send_response(status_code)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    if headers:
        for k, v in headers.items():
            handler.send_header(k, v)
    handler.end_headers()
    handler.wfile.write(body)
    log_response_details(status_code, body.decode("utf-8"))


def send_no_body(handler, status_code, headers=None):
    """
    Send a response with headers only — no body.
    Used by OPTIONS (204 No Content) and error cases in HEAD.
    """
    handler.send_response(status_code)
    handler.send_header("Content-Length", "0")
    if headers:
        for k, v in headers.items():
            handler.send_header(k, v)
    handler.end_headers()
    log_response_details(status_code)


# ═══════════════════════════════════════════════════════════════════════════
#  URL parser — extract resource path and optional ID
# ═══════════════════════════════════════════════════════════════════════════
def parse_path(path):
    """
    Parse the URL path to determine the resource type and optional ID.

    Examples:
        /api/v1/packages      → ("collection", None)
        /api/v1/packages/3    → ("item", 3)
        /anything/else        → (None, None)
    """
    parts = [p for p in path.strip("/").split("/") if p]
    # Expected: ["api", "v1", "packages"] or ["api", "v1", "packages", "<id>"]
    if len(parts) == 3 and parts == ["api", "v1", "packages"]:
        return ("collection", None)
    if len(parts) == 4 and parts[:3] == ["api", "v1", "packages"]:
        try:
            return ("item", int(parts[3]))
        except ValueError:
            return (None, None)
    return (None, None)


# ═══════════════════════════════════════════════════════════════════════════
#  Request body reader
# ═══════════════════════════════════════════════════════════════════════════
def read_body(handler):
    """
    Read and return the raw request body bytes.
    Returns None if there is no body (Content-Length is 0 or missing).
    """
    content_length = int(handler.headers.get("Content-Length", 0))
    if content_length > 0:
        return handler.rfile.read(content_length)
    return None


# ═══════════════════════════════════════════════════════════════════════════
#  Main Request Handler
# ═══════════════════════════════════════════════════════════════════════════
class KashmirPackagesHandler(BaseHTTPRequestHandler):
    """
    Handles all standard HTTP methods for the Kashmir Tourism Packages API.

    Supported methods:
        GET     — Retrieve packages (collection or single item)
        POST    — Create a new package (collection endpoint only)
        PUT     — Full replace of an existing package (item endpoint only)
        PATCH   — Partial update of an existing package (item endpoint only)
        DELETE  — Remove a package (item endpoint only)
        OPTIONS — Discover allowed methods and CORS headers
        HEAD    — Same as GET but returns only headers, no body
    """

    # ── Silence the default stderr access log (we do our own logging) ──
    def log_message(self, format, *args):
        pass  # suppress default one-line log; our log_request_details is better

    # ─────────────────────────────────────────────────────────────────────
    #  GET — Retrieve resource(s)
    #  Safe: YES  |  Idempotent: YES  |  Cacheable: YES
    # ─────────────────────────────────────────────────────────────────────
    def do_GET(self):
        body_raw = read_body(self)
        log_request_details(self, body_raw)

        resource_type, pkg_id = parse_path(self.path)

        if resource_type == "collection":
            # GET /api/v1/packages → List all packages
            all_packages = list(packages_db.values())
            send_json(self, 200, {"count": len(all_packages), "packages": all_packages})

        elif resource_type == "item":
            # GET /api/v1/packages/{id} → Get single package
            if pkg_id in packages_db:
                send_json(self, 200, packages_db[pkg_id])
            else:
                send_json(self, 404, {"error": f"Package {pkg_id} not found"})

        else:
            send_json(self, 404, {"error": "Unknown endpoint. Use /api/v1/packages"})

    # ─────────────────────────────────────────────────────────────────────
    #  POST — Create a new resource
    #  Safe: NO  |  Idempotent: NO  |  Cacheable: NO
    #
    #  ⚠️  Calling POST twice creates TWO resources (not idempotent!)
    # ─────────────────────────────────────────────────────────────────────
    def do_POST(self):
        global next_id
        body_raw = read_body(self)
        log_request_details(self, body_raw)

        resource_type, _ = parse_path(self.path)

        if resource_type != "collection":
            send_json(self, 405, {"error": "POST is only allowed on /api/v1/packages (collection)"})
            return

        if not body_raw:
            send_json(self, 400, {"error": "Request body is required for POST"})
            return

        try:
            data = json.loads(body_raw)
        except json.JSONDecodeError:
            send_json(self, 400, {"error": "Invalid JSON in request body"})
            return

        # Build new package with auto-incremented ID
        new_package = {
            "id":       next_id,
            "name":     data.get("name", "Unnamed Package"),
            "price":    data.get("price", 0),
            "duration": data.get("duration", "N/A"),
            "category": data.get("category", "general"),
        }
        packages_db[next_id] = new_package
        created_id = next_id
        next_id += 1

        print(f"  📦 Created package {created_id} — DB now has {len(packages_db)} packages")

        # 201 Created + Location header pointing to the new resource
        send_json(
            self, 201, new_package,
            headers={"Location": f"/api/v1/packages/{created_id}"}
        )

    # ─────────────────────────────────────────────────────────────────────
    #  PUT — Full replace of an existing resource
    #  Safe: NO  |  Idempotent: YES  |  Cacheable: NO
    #
    #  PUT replaces the ENTIRE resource. Fields not in the body are
    #  reset to defaults. This is the key difference from PATCH.
    # ─────────────────────────────────────────────────────────────────────
    def do_PUT(self):
        body_raw = read_body(self)
        log_request_details(self, body_raw)

        resource_type, pkg_id = parse_path(self.path)

        if resource_type != "item":
            send_json(self, 405, {"error": "PUT requires a specific resource ID, e.g. /api/v1/packages/1"})
            return

        if pkg_id not in packages_db:
            send_json(self, 404, {"error": f"Package {pkg_id} not found — cannot replace"})
            return

        if not body_raw:
            send_json(self, 400, {"error": "Request body is required for PUT"})
            return

        try:
            data = json.loads(body_raw)
        except json.JSONDecodeError:
            send_json(self, 400, {"error": "Invalid JSON in request body"})
            return

        # PUT = full replace — rebuild the entire resource from scratch
        # The original ID is preserved; everything else comes from the body
        packages_db[pkg_id] = {
            "id":       pkg_id,
            "name":     data.get("name", "Unnamed Package"),
            "price":    data.get("price", 0),
            "duration": data.get("duration", "N/A"),
            "category": data.get("category", "general"),
        }

        print(f"  🔄 Replaced package {pkg_id} — full resource overwritten")

        send_json(self, 200, packages_db[pkg_id])

    # ─────────────────────────────────────────────────────────────────────
    #  PATCH — Partial update of an existing resource
    #  Safe: NO  |  Idempotent: YES (merge-patch)  |  Cacheable: NO
    #
    #  PATCH only modifies the fields you send. All other fields remain
    #  unchanged. This uses JSON Merge Patch semantics (RFC 7396).
    # ─────────────────────────────────────────────────────────────────────
    def do_PATCH(self):
        body_raw = read_body(self)
        log_request_details(self, body_raw)

        resource_type, pkg_id = parse_path(self.path)

        if resource_type != "item":
            send_json(self, 405, {"error": "PATCH requires a specific resource ID, e.g. /api/v1/packages/1"})
            return

        if pkg_id not in packages_db:
            send_json(self, 404, {"error": f"Package {pkg_id} not found — cannot update"})
            return

        if not body_raw:
            send_json(self, 400, {"error": "Request body is required for PATCH"})
            return

        try:
            data = json.loads(body_raw)
        except json.JSONDecodeError:
            send_json(self, 400, {"error": "Invalid JSON in request body"})
            return

        # PATCH = merge only the supplied fields into the existing resource
        existing = packages_db[pkg_id]
        changed_fields = []
        for key, value in data.items():
            if key != "id":  # Don't allow changing the primary key
                old_value = existing.get(key)
                existing[key] = value
                changed_fields.append(f"{key}: {old_value} → {value}")

        print(f"  ✏️  Patched package {pkg_id} — fields changed: {', '.join(changed_fields)}")

        send_json(self, 200, existing)

    # ─────────────────────────────────────────────────────────────────────
    #  DELETE — Remove a resource
    #  Safe: NO  |  Idempotent: YES  |  Cacheable: NO
    #
    #  Idempotent because: deleting an already-deleted resource does
    #  not change the server state. The response may differ (200 vs 404)
    #  but the state is the same.
    # ─────────────────────────────────────────────────────────────────────
    def do_DELETE(self):
        body_raw = read_body(self)
        log_request_details(self, body_raw)

        resource_type, pkg_id = parse_path(self.path)

        if resource_type != "item":
            send_json(self, 405, {"error": "DELETE requires a specific resource ID, e.g. /api/v1/packages/1"})
            return

        if pkg_id in packages_db:
            deleted = packages_db.pop(pkg_id)
            print(f"  🗑️  Deleted package {pkg_id} — DB now has {len(packages_db)} packages")
            send_json(self, 200, {"message": f"Package {pkg_id} deleted", "deleted": deleted})
        else:
            # Idempotent: resource is already gone, state unchanged
            print(f"  🗑️  Package {pkg_id} already deleted / never existed — state unchanged (idempotent)")
            send_json(self, 404, {"error": f"Package {pkg_id} not found — already deleted or never existed"})

    # ─────────────────────────────────────────────────────────────────────
    #  OPTIONS — Discover allowed methods / CORS pre-flight
    #  Safe: YES  |  Idempotent: YES  |  Cacheable: NO
    #
    #  Browsers send an OPTIONS pre-flight request before any
    #  cross-origin request. This handler returns CORS headers.
    # ─────────────────────────────────────────────────────────────────────
    def do_OPTIONS(self):
        log_request_details(self)

        allowed = "GET, POST, PUT, PATCH, DELETE, OPTIONS, HEAD"
        print(f"  ℹ️  OPTIONS pre-flight — Allowed methods: {allowed}")

        send_no_body(self, 204, headers={
            "Allow": allowed,
            "Access-Control-Allow-Methods": allowed,
            "Access-Control-Allow-Headers": "Content-Type, Idempotency-Key",
            "Access-Control-Allow-Origin": "*",
        })

    # ─────────────────────────────────────────────────────────────────────
    #  HEAD — Same as GET but with NO response body
    #  Safe: YES  |  Idempotent: YES  |  Cacheable: YES
    #
    #  The server computes the full response (including Content-Length)
    #  but does NOT write the body bytes. Use HEAD to check if a
    #  resource exists or to get metadata without downloading the body.
    # ─────────────────────────────────────────────────────────────────────
    def do_HEAD(self):
        log_request_details(self)

        resource_type, pkg_id = parse_path(self.path)

        if resource_type == "collection":
            # Compute the body that GET would return (for Content-Length)
            all_packages = list(packages_db.values())
            body = json.dumps({"count": len(all_packages), "packages": all_packages}).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            # NOTE: No body is written — that's the whole point of HEAD
            print(f"  👤 HEAD response — Content-Length: {len(body)} (body suppressed)")
            log_response_details(200, "(HEAD — body suppressed)")

        elif resource_type == "item" and pkg_id in packages_db:
            body = json.dumps(packages_db[pkg_id]).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            print(f"  👤 HEAD response for package {pkg_id} — Content-Length: {len(body)} (body suppressed)")
            log_response_details(200, "(HEAD — body suppressed)")

        else:
            self.send_response(404)
            self.send_header("Content-Length", "0")
            self.end_headers()
            log_response_details(404)


# ═══════════════════════════════════════════════════════════════════════════
#  Server Entry Point
# ═══════════════════════════════════════════════════════════════════════════
def run(host="0.0.0.0", port=8081):
    """Start the Kashmir Tourism Packages API server on the given host:port."""
    server = HTTPServer((host, port), KashmirPackagesHandler)
    print(f"""
{'═' * 60}
  🏔️  Kashmir Tourism Packages API — Lab 73
  🌐  Server running on http://{host}:{port}
  📍  Endpoints:
        GET    /api/v1/packages         — List all
        GET    /api/v1/packages/{{id}}    — Get one
        POST   /api/v1/packages         — Create
        PUT    /api/v1/packages/{{id}}    — Full replace
        PATCH  /api/v1/packages/{{id}}    — Partial update
        DELETE /api/v1/packages/{{id}}    — Remove
        OPTIONS /api/v1/packages        — Allowed methods
        HEAD   /api/v1/packages/{{id}}    — Headers only

  📦  Pre-loaded packages: {len(packages_db)}
  🛑  Press Ctrl+C to stop
{'═' * 60}
""")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n🛑 Server stopped.")
        server.server_close()


if __name__ == "__main__":
    run()
