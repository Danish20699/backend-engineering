"""
Lab 74 — HTTP Status Codes & Error Standardization
===================================================
Backend Engineering Course
Module 13 — FastAPI Backend & Backend Engineering

A zero-dependency HTTP server built with Python's http.server that
demonstrates the full spectrum of HTTP status code families (1xx, 2xx, 3xx,
4xx, 5xx) and RFC 7807 (Problem Details for HTTP APIs) structured error
standardization using Kashmir Tourism booking, voucher, and weather domain models.

Run:
    python http_status_codes_lab.py

Server starts on:
    http://localhost:8082

Test Endpoints:
    curl -v http://localhost:8082/api/v1/health                                # 200 OK
    curl -v -X POST http://localhost:8082/api/v1/bookings ...                  # 201 Created / 422 / 409
    curl -v -X POST http://localhost:8082/api/v1/bookings/async ...            # 202 Accepted
    curl -v -X DELETE http://localhost:8082/api/v1/bookings/KB-701             # 204 No Content
    curl -v http://localhost:8082/api/v1/vouchers/VOUCH-GUL-01                 # 200 OK with ETag
    curl -v http://localhost:8082/api/v1/vouchers/VOUCH-GUL-01 -H 'If-None-Match: "w/gul-phase2-v1"' # 304 Not Modified
    curl -v http://localhost:8082/api/v1/admin/audit                           # 401 Unauthorized
    curl -v http://localhost:8082/api/v1/admin/audit -H "Authorization: Bearer kashmir-tourist-token" # 403 Forbidden
    curl -v http://localhost:8082/api/v1/weather/reports                       # 200 OK / 429 Too Many Requests
    curl -v http://localhost:8082/api/v1/redirect-test                         # 307 Temporary Redirect
    curl -v http://localhost:8082/api/v1/simulate-crash                        # 500 Internal Server Error
    curl -v http://localhost:8082/api/v1/maintenance                           # 503 Service Unavailable

Engineer : Danish
Track    : MLOps / DevOps Engineering (APR26)
"""

import json
import sys
import time
import uuid
import datetime
import traceback
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse

# ---------------------------------------------------------------------------
# Force UTF-8 encoding on Windows consoles so emoji / special chars don't crash
# ---------------------------------------------------------------------------
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# ═══════════════════════════════════════════════════════════════════════════
#  In-Memory Data Stores — Kashmir Tourism Domain
# ═══════════════════════════════════════════════════════════════════════════

# Bookings database: permits, ski passes, and luxury houseboats
bookings_db = {
    "KB-701": {
        "booking_id": "KB-701",
        "customer_name": "Ayesha Khan",
        "item_type": "Gulmarg Heli-Skiing Pass",
        "quantity": 2,
        "status": "confirmed",
        "total_price": 45000,
        "created_at": "2026-03-10T09:00:00Z"
    },
    "KB-702": {
        "booking_id": "KB-702",
        "customer_name": "Farooq Lone",
        "item_type": "Dal Lake Luxury Shikara Cruise",
        "quantity": 1,
        "status": "confirmed",
        "total_price": 2500,
        "created_at": "2026-03-11T14:30:00Z"
    },
    "KB-703": {
        "booking_id": "KB-703",
        "customer_name": "Zubair Ahmad",
        "item_type": "Sonamarg Thajiwas Glacier Trek Permit",
        "quantity": 4,
        "status": "confirmed",
        "total_price": 6000,
        "created_at": "2026-03-12T11:15:00Z"
    }
}

# Vouchers database: resort and excursion vouchers for conditional caching (ETag)
vouchers_db = {
    "VOUCH-GUL-01": {
        "voucher_id": "VOUCH-GUL-01",
        "title": "Gulmarg Gondola Phase-2 Alpine Access Voucher",
        "discount_percent": 15,
        "resort": "Apharwat Highland Lodge",
        "valid_until": "2026-12-31",
        "etag": '"w/gul-phase2-v1"'
    },
    "VOUCH-PAH-02": {
        "voucher_id": "VOUCH-PAH-02",
        "title": "Betaab Valley Pine Chalet Retreat Voucher",
        "discount_percent": 20,
        "resort": "Lidder River Sanctuary",
        "valid_until": "2026-11-30",
        "etag": '"w/pah-lidder-v1"'
    }
}

# Rate limiting in-memory state: IP/Client request history
# Format: { "ip_address": [timestamp1, timestamp2, ...] }
rate_limit_records = {}
RATE_LIMIT_MAX_REQUESTS = 3
RATE_LIMIT_WINDOW_SECONDS = 30


# ═══════════════════════════════════════════════════════════════════════════
#  Logging & Terminal Inspection Utilities
# ═══════════════════════════════════════════════════════════════════════════
SEPARATOR = "═" * 74


def log_request_details(handler, body=None):
    """
    Log wire-level incoming HTTP request headers and payload.
    Emulates production reverse proxy or packet capture visibility.
    """
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"\n{SEPARATOR}")
    print(f"  ⏱  {timestamp} | INCOMING REQUEST")
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
            print(f"    (raw) {body[:250]}")
    else:
        print("  Request Body: (none)")
    print(SEPARATOR)


def log_response_details(status_code, response_body=None, headers=None):
    """
    Log wire-level HTTP response headers and payload dispatched to client.
    """
    print(f"  ◄── Outgoing Response Status: {status_code}")
    if headers:
        print("  Response Headers:")
        for k, v in headers.items():
            print(f"    {k}: {v}")
    if response_body:
        try:
            parsed = json.loads(response_body)
            print(f"  Response Body ({len(response_body)} bytes):\n    {json.dumps(parsed, indent=4, ensure_ascii=False)}")
        except (json.JSONDecodeError, UnicodeDecodeError):
            print(f"  Response Body: {response_body[:300]}")
    else:
        print("  Response Body: (none - zero length)")
    print(SEPARATOR + "\n")


# ═══════════════════════════════════════════════════════════════════════════
#  Response Builders: Success, No-Body, and RFC 7807 Problem Details
# ═══════════════════════════════════════════════════════════════════════════
def send_json(handler, status_code, data, headers=None):
    """
    Serialize data dictionary to JSON and emit with standard HTTP headers.
    """
    body = json.dumps(data, ensure_ascii=False).encode("utf-8")
    handler.send_response(status_code)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.send_header("X-Powered-By", "Kashmir-Tourism-Engine/1.0")
    if headers:
        for k, v in headers.items():
            handler.send_header(k, v)
    handler.end_headers()
    handler.wfile.write(body)
    log_response_details(status_code, body.decode("utf-8"), headers)


def send_no_body(handler, status_code, headers=None):
    """
    Send an HTTP response with headers only and zero body bytes.
    Used for 204 No Content, 304 Not Modified, and HEAD responses.
    """
    handler.send_response(status_code)
    handler.send_header("Content-Length", "0")
    handler.send_header("X-Powered-By", "Kashmir-Tourism-Engine/1.0")
    if headers:
        for k, v in headers.items():
            handler.send_header(k, v)
    handler.end_headers()
    log_response_details(status_code, "(zero bytes body)", headers)


def send_error_problem(handler, status_code, title, detail, error_code, validation_errors=None, headers=None):
    """
    RFC 7807 Problem Details for HTTP APIs.
    Standardized enterprise error envelope containing machine-parseable error codes,
    HTTP status, human-readable explanations, incident trace UUIDs, and field-level validation errors.
    """
    trace_id = str(uuid.uuid4())
    problem_payload = {
        "type": f"https://api.kashmir-tourism.gov.in/errors/{error_code.lower().replace('_', '-')}",
        "title": title,
        "status": status_code,
        "detail": detail,
        "instance": handler.path,
        "error_code": error_code,
        "trace_id": trace_id,
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
    }
    if validation_errors:
        problem_payload["errors"] = validation_errors

    body = json.dumps(problem_payload, ensure_ascii=False).encode("utf-8")

    handler.send_response(status_code)
    # RFC 7807 specifies application/problem+json media type
    handler.send_header("Content-Type", "application/problem+json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.send_header("X-Trace-Id", trace_id)
    handler.send_header("X-Powered-By", "Kashmir-Tourism-Engine/1.0")
    if headers:
        for k, v in headers.items():
            handler.send_header(k, v)
    handler.end_headers()
    handler.wfile.write(body)
    log_response_details(status_code, body.decode("utf-8"), headers)


# ═══════════════════════════════════════════════════════════════════════════
#  HTTP Request Handler Class
# ═══════════════════════════════════════════════════════════════════════════
class KashmirStatusCodeLabHandler(BaseHTTPRequestHandler):
    """
    Comprehensive HTTP request handler demonstrating status codes across all 5 families:
      1xx: 100 Continue (simulated via protocol negotiation)
      2xx: 200 OK, 201 Created, 202 Accepted, 204 No Content
      3xx: 304 Not Modified, 307 Temporary Redirect
      4xx: 400 Bad Request, 401 Unauthorized, 403 Forbidden, 404 Not Found,
           405 Method Not Allowed, 409 Conflict, 415 Unsupported Media Type,
           422 Unprocessable Entity, 429 Too Many Requests
      5xx: 500 Internal Server Error, 502 Bad Gateway (documented),
           503 Service Unavailable, 504 Gateway Timeout (documented)
    """

    def log_message(self, format, *args):
        """Suppress default one-line stderr logging to use our detailed wire logger."""
        pass

    def _read_body(self):
        """Read and return request body bytes based on Content-Length header."""
        content_length = int(self.headers.get("Content-Length", 0))
        if content_length > 0:
            return self.rfile.read(content_length)
        return None

    # ─────────────────────────────────────────────────────────────────────
    #  GET Endpoints
    # ─────────────────────────────────────────────────────────────────────
    def do_GET(self):
        parsed_url = urlparse(self.path)
        path = parsed_url.path
        body = self._read_body()
        log_request_details(self, body)

        # 1. Health Probe — 200 OK
        if path == "/api/v1/health":
            response_data = {
                "status": "healthy",
                "service": "kashmir-tourism-core-gateway",
                "version": "1.4.0",
                "environment": "production",
                "cluster_region": "in-north-srinagar",
                "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
            }
            send_json(self, 200, response_data)
            return

        # 2. Redirect Demonstration — 307 Temporary Redirect
        if path == "/api/v1/redirect-test":
            target_url = "/api/v1/health"
            print("  [REDIRECT] Dispatched 307 Temporary Redirect preserving HTTP verb")
            send_json(self, 307, {
                "message": "Resource temporarily moved to /api/v1/health",
                "redirect_target": target_url
            }, headers={"Location": target_url})
            return

        # 3. Conditional Caching with ETag — 200 OK or 304 Not Modified
        if path.startswith("/api/v1/vouchers/"):
            voucher_id = path.replace("/api/v1/vouchers/", "").strip("/")
            if voucher_id not in vouchers_db:
                send_error_problem(
                    self, 404,
                    title="Resource Not Found",
                    detail=f"Resort voucher '{voucher_id}' does not exist in the tourism registry.",
                    error_code="RESOURCE_NOT_FOUND"
                )
                return

            voucher = vouchers_db[voucher_id]
            client_etag = self.headers.get("If-None-Match")

            # Check if the client's cached ETag matches current resource ETag
            if client_etag and client_etag.strip() == voucher["etag"]:
                print(f"  [CACHE HIT] Client ETag {client_etag} matches server ETag {voucher['etag']}")
                send_no_body(self, 304, headers={
                    "ETag": voucher["etag"],
                    "Cache-Control": "public, max-age=300",
                    "Vary": "Accept-Encoding"
                })
                return

            # Cache miss or first-time fetch: return 200 OK with ETag header
            print(f"  [CACHE MISS] Returning fresh voucher data with ETag {voucher['etag']}")
            send_json(self, 200, voucher, headers={
                "ETag": voucher["etag"],
                "Cache-Control": "public, max-age=300",
                "Vary": "Accept-Encoding"
            })
            return

        # 4. Role-Based Security: 401 Unauthorized vs 403 Forbidden
        if path == "/api/v1/admin/audit":
            auth_header = self.headers.get("Authorization")
            if not auth_header or not auth_header.startswith("Bearer "):
                send_error_problem(
                    self, 401,
                    title="Authentication Required",
                    detail="Access to the Kashmir administrative audit log requires a valid Bearer token.",
                    error_code="AUTH_CREDENTIALS_MISSING",
                    headers={"WWW-Authenticate": 'Bearer realm="kashmir-api", error="invalid_token", error_description="The access token is missing or malformed"'}
                )
                return

            token = auth_header.replace("Bearer ", "").strip()
            # Scenario A: User is authenticated but lacks required administrative privileges
            if token == "kashmir-tourist-token":
                send_error_problem(
                    self, 403,
                    title="Insufficient Privileges",
                    detail="Caller authenticated as role 'tourist-user'. Access to audit logs strictly requires 'kashmir-state-admin'.",
                    error_code="FORBIDDEN_INSUFFICIENT_PERMISSIONS"
                )
                return

            # Scenario B: User possesses valid administrative credentials
            if token == "kashmir-admin-secret-2026":
                audit_logs = {
                    "audit_id": "AUD-SRN-9982",
                    "authority": "Directorate of Kashmir Tourism Enforcement",
                    "records": [
                        {"timestamp": "2026-03-14T08:12:00Z", "action": "SKI_PASS_QUOTA_ADJUSTMENT", "operator": "superadmin"},
                        {"timestamp": "2026-03-14T09:45:00Z", "action": "SHIKARA_LICENSE_RENEWAL", "operator": "enforcement_officer_3"}
                    ]
                }
                send_json(self, 200, audit_logs)
                return

            # Scenario C: Unknown / Invalid token
            send_error_problem(
                self, 401,
                title="Invalid Authentication Token",
                detail="The provided Bearer token was revoked or could not be cryptographically validated.",
                error_code="AUTH_TOKEN_INVALID",
                headers={"WWW-Authenticate": 'Bearer realm="kashmir-api", error="invalid_token", error_description="Token signature expired or unauthorized"'}
            )
            return

        # 5. Rate Limiting — 200 OK or 429 Too Many Requests
        if path == "/api/v1/weather/reports":
            client_ip = self.client_address[0]
            now = time.time()

            if client_ip not in rate_limit_records:
                rate_limit_records[client_ip] = []

            # Purge timestamps outside the sliding window
            rate_limit_records[client_ip] = [
                ts for ts in rate_limit_records[client_ip]
                if now - ts < RATE_LIMIT_WINDOW_SECONDS
            ]

            # Check if rate limit threshold exceeded
            if len(rate_limit_records[client_ip]) >= RATE_LIMIT_MAX_REQUESTS:
                oldest_in_window = rate_limit_records[client_ip][0]
                retry_after = int(RATE_LIMIT_WINDOW_SECONDS - (now - oldest_in_window)) + 1
                print(f"  [RATE LIMIT] Client {client_ip} exceeded {RATE_LIMIT_MAX_REQUESTS} req/{RATE_LIMIT_WINDOW_SECONDS}s. Retry-After: {retry_after}s")
                send_error_problem(
                    self, 429,
                    title="Too Many Requests",
                    detail=f"Rate limit quota exceeded. Maximum allowed: {RATE_LIMIT_MAX_REQUESTS} requests per {RATE_LIMIT_WINDOW_SECONDS} seconds.",
                    error_code="RATE_LIMIT_EXCEEDED",
                    headers={
                        "Retry-After": str(retry_after),
                        "X-RateLimit-Limit": str(RATE_LIMIT_MAX_REQUESTS),
                        "X-RateLimit-Remaining": "0",
                        "X-RateLimit-Reset": str(int(oldest_in_window + RATE_LIMIT_WINDOW_SECONDS))
                    }
                )
                return

            # Record this request
            rate_limit_records[client_ip].append(now)
            remaining = RATE_LIMIT_MAX_REQUESTS - len(rate_limit_records[client_ip])

            weather_data = {
                "station": "Gulmarg Apharwat Peak Weather Telemetry",
                "elevation_meters": 3950,
                "conditions": "Blizzard Warning",
                "temperature_celsius": -7.4,
                "snow_depth_cm": 185,
                "wind_velocity_kmh": 48,
                "avalanche_advisory": "Level 3 - Orange Warning",
                "quota_remaining": remaining
            }
            send_json(self, 200, weather_data, headers={
                "X-RateLimit-Limit": str(RATE_LIMIT_MAX_REQUESTS),
                "X-RateLimit-Remaining": str(remaining),
                "X-RateLimit-Reset": str(int(now + RATE_LIMIT_WINDOW_SECONDS))
            })
            return

        # 6. Unhandled Crash Simulation — 500 Internal Server Error (Sanitized)
        if path == "/api/v1/simulate-crash":
            try:
                print("  [CRASH SIMULATION] Triggering intentional ZeroDivisionError in booking settlement engine...")
                # Simulate critical backend failure
                critical_calculation = 1000 / 0
                send_json(self, 200, {"result": critical_calculation})
            except Exception as exc:
                # Log full unhandled traceback to server stdout for observability
                print("  [CRITICAL ALARM] Server Exception Captured:")
                traceback.print_exc(file=sys.stdout)

                # Return clean, sanitized RFC 7807 response to caller without leaking stack trace
                send_error_problem(
                    self, 500,
                    title="Internal Server Error",
                    detail="A critical runtime anomaly occurred while settling the transaction. An incident ticket has been dispatched.",
                    error_code="INTERNAL_SERVER_ERROR"
                )
            return

        # 7. Scheduled Maintenance — 503 Service Unavailable
        if path == "/api/v1/maintenance":
            print("  [MAINTENANCE] Dispatched 503 Service Unavailable with Retry-After: 120")
            send_error_problem(
                self, 503,
                title="Service Unavailable",
                detail="The Gulmarg Gondola ticketing cluster is temporarily offline for scheduled database shard migration.",
                error_code="SERVICE_MAINTENANCE_IN_PROGRESS",
                headers={"Retry-After": "120"}
            )
            return

        # Fallback: Route Not Found — 404 Not Found
        send_error_problem(
            self, 404,
            title="Endpoint Not Found",
            detail=f"The requested path '{path}' does not map to any active Kashmir Tourism API route.",
            error_code="ROUTE_NOT_FOUND"
        )

    # ─────────────────────────────────────────────────────────────────────
    #  POST Endpoints
    # ─────────────────────────────────────────────────────────────────────
    def do_POST(self):
        parsed_url = urlparse(self.path)
        path = parsed_url.path
        body = self._read_body()
        log_request_details(self, body)

        # Check Content-Type header — enforce 415 Unsupported Media Type
        content_type = self.headers.get("Content-Type", "")
        if "application/json" not in content_type.lower():
            send_error_problem(
                self, 415,
                title="Unsupported Media Type",
                detail=f"Content-Type '{content_type}' is not supported. Request payload must be formatted as 'application/json'.",
                error_code="UNSUPPORTED_MEDIA_TYPE"
            )
            return

        # Ensure body is not empty
        if not body:
            send_error_problem(
                self, 400,
                title="Bad Request",
                detail="Request body cannot be empty for POST resource creation.",
                error_code="EMPTY_PAYLOAD"
            )
            return

        # Parse JSON payload — handle 400 Bad Request if syntax is broken
        try:
            payload = json.loads(body.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as err:
            send_error_problem(
                self, 400,
                title="Malformed JSON Syntax",
                detail=f"The JSON parser encountered a fatal syntax error: {str(err)}",
                error_code="MALFORMED_JSON_SYNTAX"
            )
            return

        # 1. Asynchronous Batch Operation — 202 Accepted
        if path == "/api/v1/bookings/async":
            task_id = f"task-{uuid.uuid4().hex[:8]}"
            status_url = f"/api/v1/tasks/{task_id}"
            accepted_response = {
                "task_id": task_id,
                "status": "Accepted",
                "message": "Bulk Shikara fleet permits queued for asynchronous batch validation and digital watermarking.",
                "status_url": status_url,
                "estimated_duration_seconds": 25,
                "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
            }
            send_json(self, 202, accepted_response, headers={"Location": status_url})
            return

        # 2. Standard Booking Creation — 201 Created vs 422 vs 409
        if path == "/api/v1/bookings":
            validation_errors = []

            # Field validation rules
            required_fields = ["booking_id", "customer_name", "item_type", "quantity", "total_price"]
            for field in required_fields:
                if field not in payload or payload[field] is None:
                    validation_errors.append({
                        "field": field,
                        "issue": f"Missing required parameter '{field}'"
                    })

            if "booking_id" in payload and not isinstance(payload["booking_id"], str):
                validation_errors.append({"field": "booking_id", "issue": "Field must be a valid string identifier (e.g., 'KB-704')"})

            if "quantity" in payload and (not isinstance(payload["quantity"], int) or payload["quantity"] <= 0):
                validation_errors.append({"field": "quantity", "issue": "Field must be an integer strictly greater than 0"})

            if "total_price" in payload and (not isinstance(payload["total_price"], (int, float)) or payload["total_price"] <= 0):
                validation_errors.append({"field": "total_price", "issue": "Field must be a positive numerical amount in INR"})

            # If semantic validation failed, emit 422 Unprocessable Entity
            if validation_errors:
                send_error_problem(
                    self, 422,
                    title="Semantic Validation Failed",
                    detail="The submitted booking payload contains invalid field values or missing required attributes.",
                    error_code="VALIDATION_FAILED",
                    validation_errors=validation_errors
                )
                return

            booking_id = payload["booking_id"]

            # Conflict Detection: Resource already exists — 409 Conflict
            if booking_id in bookings_db:
                send_error_problem(
                    self, 409,
                    title="Resource Conflict",
                    detail=f"A Kashmir tourism booking with ID '{booking_id}' already exists in active ledger. Duplicate booking IDs are rejected.",
                    error_code="RESOURCE_CONFLICT_DUPLICATE"
                )
                return

            # Success: Persist new booking — 201 Created with Location header
            new_booking = {
                "booking_id": booking_id,
                "customer_name": payload["customer_name"],
                "item_type": payload["item_type"],
                "quantity": payload["quantity"],
                "status": "confirmed",
                "total_price": payload["total_price"],
                "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
            }
            bookings_db[booking_id] = new_booking
            resource_uri = f"/api/v1/bookings/{booking_id}"

            send_json(self, 201, new_booking, headers={"Location": resource_uri})
            return

        # Fallback for unrecognized POST paths
        send_error_problem(
            self, 404,
            title="Endpoint Not Found",
            detail=f"No POST handler configured for path '{path}'.",
            error_code="ROUTE_NOT_FOUND"
        )

    # ─────────────────────────────────────────────────────────────────────
    #  DELETE Endpoints
    # ─────────────────────────────────────────────────────────────────────
    def do_DELETE(self):
        parsed_url = urlparse(self.path)
        path = parsed_url.path
        body = self._read_body()
        log_request_details(self, body)

        if path.startswith("/api/v1/bookings/"):
            booking_id = path.replace("/api/v1/bookings/", "").strip("/")
            if booking_id in bookings_db:
                del bookings_db[booking_id]
                print(f"  [DELETED] Successfully purged booking ID {booking_id} from database")
                # 204 No Content indicates complete success with zero body payload
                send_no_body(self, 204)
                return
            else:
                send_error_problem(
                    self, 404,
                    title="Resource Not Found",
                    detail=f"Cannot delete booking '{booking_id}'. The record does not exist or was already removed.",
                    error_code="RESOURCE_NOT_FOUND"
                )
                return

        send_error_problem(
            self, 404,
            title="Endpoint Not Found",
            detail=f"No DELETE handler configured for path '{path}'.",
            error_code="ROUTE_NOT_FOUND"
        )

    # ─────────────────────────────────────────────────────────────────────
    #  PUT / PATCH / OPTIONS / HEAD Handlers
    # ─────────────────────────────────────────────────────────────────────
    def do_PUT(self):
        parsed_url = urlparse(self.path)
        path = parsed_url.path
        log_request_details(self, self._read_body())

        # If client attempts PUT on /api/v1/health, return 405 Method Not Allowed
        if path == "/api/v1/health":
            send_error_problem(
                self, 405,
                title="Method Not Allowed",
                detail="PUT verb is not permitted on the /api/v1/health endpoint.",
                error_code="METHOD_NOT_ALLOWED",
                headers={"Allow": "GET, HEAD, OPTIONS"}
            )
            return

        send_error_problem(
            self, 405,
            title="Method Not Allowed",
            detail=f"PUT verb is not enabled on '{path}'.",
            error_code="METHOD_NOT_ALLOWED",
            headers={"Allow": "GET, POST, DELETE, OPTIONS"}
        )

    def do_PATCH(self):
        parsed_url = urlparse(self.path)
        path = parsed_url.path
        log_request_details(self, self._read_body())
        send_error_problem(
            self, 405,
            title="Method Not Allowed",
            detail=f"PATCH verb is not supported on '{path}'.",
            error_code="METHOD_NOT_ALLOWED",
            headers={"Allow": "GET, POST, DELETE, OPTIONS"}
        )

    def do_OPTIONS(self):
        log_request_details(self)
        allowed_methods = "GET, POST, DELETE, OPTIONS, HEAD"
        send_no_body(self, 204, headers={
            "Allow": allowed_methods,
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": allowed_methods,
            "Access-Control-Allow-Headers": "Content-Type, Authorization, If-None-Match"
        })

    def do_HEAD(self):
        """Handle HEAD requests by generating headers identically to GET, omitting body."""
        parsed_url = urlparse(self.path)
        path = parsed_url.path
        log_request_details(self)

        if path == "/api/v1/health":
            body = json.dumps({"status": "healthy"}).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            log_response_details(200, "(HEAD — body suppressed)")
            return

        if path.startswith("/api/v1/vouchers/"):
            voucher_id = path.replace("/api/v1/vouchers/", "").strip("/")
            if voucher_id in vouchers_db:
                body = json.dumps(vouchers_db[voucher_id]).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.send_header("ETag", vouchers_db[voucher_id]["etag"])
                self.end_headers()
                log_response_details(200, "(HEAD — body suppressed)")
                return

        self.send_response(404)
        self.send_header("Content-Length", "0")
        self.end_headers()
        log_response_details(404)


# ═══════════════════════════════════════════════════════════════════════════
#  Server Launch Entry Point
# ═══════════════════════════════════════════════════════════════════════════
def run(host="0.0.0.0", port=8082):
    """Start the Kashmir Tourism Status Code Demonstration Server."""
    server = HTTPServer((host, port), KashmirStatusCodeLabHandler)
    print(f"""
{SEPARATOR}
  🏔️  Kashmir Tourism API — Lab 74: HTTP Status Codes & Error Standards
  🌐  Listening on: http://{host}:{port}
  🏷️   Port: {port} (Dedicated to Status Code & RFC 7807 Verification)
{SEPARATOR}
  Supported Test Scenarios:
    [200 OK]                  GET    /api/v1/health
    [201 Created]             POST   /api/v1/bookings
    [202 Accepted]            POST   /api/v1/bookings/async
    [204 No Content]          DELETE /api/v1/bookings/<id>
    [304 Not Modified]        GET    /api/v1/vouchers/<id> (with ETag match)
    [307 Temporary Redirect]  GET    /api/v1/redirect-test
    [400 Bad Request]         POST   /api/v1/bookings (malformed JSON syntax)
    [401 Unauthorized]        GET    /api/v1/admin/audit (missing/bad token)
    [403 Forbidden]           GET    /api/v1/admin/audit (tourist role token)
    [404 Not Found]           GET    /api/v1/vouchers/UNKNOWN
    [405 Method Not Allowed]  PUT    /api/v1/health
    [409 Conflict]            POST   /api/v1/bookings (duplicate booking ID)
    [415 Unsupported Media]   POST   /api/v1/bookings (Content-Type: text/plain)
    [422 Unprocessable]       POST   /api/v1/bookings (semantic validation failure)
    [429 Too Many Requests]   GET    /api/v1/weather/reports (burst > 3 in 30s)
    [500 Internal Error]      GET    /api/v1/simulate-crash (sanitized trace ID)
    [503 Service Unavailable] GET    /api/v1/maintenance (with Retry-After)
{SEPARATOR}
  Press Ctrl+C to gracefully shut down.
""")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n🛑 Graceful shutdown signal received. Terminating Kashmir API server...")
        server.server_close()
        print("✅ Server closed successfully.")


if __name__ == "__main__":
    run()

