# Lab 73: API Request Methods & Idempotency Deep Dive

![Backend Engineering](https://img.shields.io/badge/Backend-Engineering-blue)
![HTTP Protocol](https://img.shields.io/badge/HTTP-Protocol-green)
![FastAPI](https://img.shields.io/badge/FastAPI-Framework-teal)
![Status](https://img.shields.io/badge/Status-Active-brightgreen)

---

## 📌 1. Lab Overview & Real-World Context

Every time a client talks to a server, it must declare **what action** it wants
to perform. HTTP methods (sometimes called "verbs") are exactly that declaration.
Think of them as instructions on a shipping label:

* **GET** → "Send me the contents"
* **POST** → "Here is something new — store it"
* **PUT** → "Replace everything inside with this"
* **PATCH** → "Change only the fields I mention"
* **DELETE** → "Remove this item"

Understanding these methods is not academic — it is **critical** for every
backend engineer because:

| Reason | Why It Matters |
|---|---|
| **REST architecture** | The entire REST contract is built on using the right method for the right action |
| **Caching** | Browsers and CDNs cache GET responses but never cache POST |
| **Idempotency** | Knowing which methods are safe to retry prevents double-charges and data corruption |
| **Security** | CORS pre-flight checks use OPTIONS; firewalls can filter by method |
| **API design** | Misusing methods (e.g., GET with a body) causes subtle bugs across proxies and clients |

### How This Connects to REST

REST (Representational State Transfer) treats every URL as a **resource** and
every HTTP method as a **uniform operation** on that resource.  The beauty of
REST is that you do not need to invent custom action names — the method *is*
the action:

```text
┌──────────────────────────────────────────────────────────┐
│                   RESTful Resource Model                 │
├──────────────────────────────────────────────────────────┤
│                                                          │
│   Resource: /api/v1/packages                             │
│                                                          │
│   GET     /api/v1/packages        → List all packages    │
│   POST    /api/v1/packages        → Create new package   │
│   GET     /api/v1/packages/101    → Read one package     │
│   PUT     /api/v1/packages/101    → Replace package      │
│   PATCH   /api/v1/packages/101    → Partial update       │
│   DELETE  /api/v1/packages/101    → Remove package       │
│   OPTIONS /api/v1/packages        → Discover methods     │
│   HEAD    /api/v1/packages/101    → Headers only (meta)  │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

---

## 🔍 2. Complete HTTP Methods Reference

Below is a comprehensive reference for **every standard HTTP method** you will
encounter as a backend engineer.

### 2.1 — GET (Retrieve a Resource)

| Property | Value |
|---|---|
| **Purpose** | Retrieve a representation of the target resource |
| **Has Request Body?** | ❌ No (ignored by most servers even if sent) |
| **Has Response Body?** | ✅ Yes |
| **Safe?** | ✅ Yes — must not modify server state |
| **Idempotent?** | ✅ Yes — calling it N times yields the same result |
| **Cacheable?** | ✅ Yes |
| **Typical Status Codes** | `200 OK`, `304 Not Modified`, `404 Not Found` |

```text
Wire-Level Example:

GET /api/v1/packages/1 HTTP/1.1        ← Request line (method + path + version)
Host: localhost:8081                     ← Mandatory header
Accept: application/json                ← Client prefers JSON
                                        ← Empty line = end of headers, NO body
```

### 2.2 — POST (Create a New Resource)

| Property | Value |
|---|---|
| **Purpose** | Submit data to be processed; typically creates a new resource |
| **Has Request Body?** | ✅ Yes |
| **Has Response Body?** | ✅ Yes (the created resource) |
| **Safe?** | ❌ No — modifies server state |
| **Idempotent?** | ❌ **No** — calling it twice creates **two** resources |
| **Cacheable?** | ❌ No (unless response explicitly allows it) |
| **Typical Status Codes** | `201 Created`, `400 Bad Request`, `409 Conflict` |

```text
Wire-Level Example:

POST /api/v1/packages HTTP/1.1
Host: localhost:8081
Content-Type: application/json
Content-Length: 92

{"name": "Pahalgam Valley Retreat", "price": 15000, "duration": "3D", "category": "leisure"}
```

### 2.3 — PUT (Replace an Entire Resource)

| Property | Value |
|---|---|
| **Purpose** | Replace the **entire** target resource with the request payload |
| **Has Request Body?** | ✅ Yes (full resource representation) |
| **Has Response Body?** | ✅ Yes (the updated resource) |
| **Safe?** | ❌ No — modifies server state |
| **Idempotent?** | ✅ **Yes** — the same PUT 10 times = same final state |
| **Cacheable?** | ❌ No |
| **Typical Status Codes** | `200 OK`, `204 No Content`, `404 Not Found` |

```text
Wire-Level Example:

PUT /api/v1/packages/1 HTTP/1.1
Host: localhost:8081
Content-Type: application/json
Content-Length: 104

{"name": "Gulmarg Skiing Premium", "price": 55000, "duration": "7D", "category": "winter"}
```

> **Key insight:** PUT replaces the *entire* resource.  If you omit a field
> (e.g., `category`), the resource should lose that field.

### 2.4 — PATCH (Partial Update)

| Property | Value |
|---|---|
| **Purpose** | Apply **partial** modifications to a resource |
| **Has Request Body?** | ✅ Yes (only the fields to change) |
| **Has Response Body?** | ✅ Yes (the updated resource) |
| **Safe?** | ❌ No |
| **Idempotent?** | ✅ In practice, yes (when using merge-patch semantics) |
| **Cacheable?** | ❌ No |
| **Typical Status Codes** | `200 OK`, `404 Not Found`, `422 Unprocessable Entity` |

```text
Wire-Level Example:

PATCH /api/v1/packages/1 HTTP/1.1
Host: localhost:8081
Content-Type: application/json
Content-Length: 16

{"price": 48000}
```

> Only the `price` field changes; `name`, `duration`, `category` remain intact.

### 2.5 — DELETE (Remove a Resource)

| Property | Value |
|---|---|
| **Purpose** | Remove the target resource |
| **Has Request Body?** | ❌ Usually no |
| **Has Response Body?** | ✅ Optional (confirmation message) |
| **Safe?** | ❌ No |
| **Idempotent?** | ✅ **Yes** — deleting an already-deleted resource does not change server state |
| **Cacheable?** | ❌ No |
| **Typical Status Codes** | `200 OK`, `204 No Content`, `404 Not Found` |

```text
Wire-Level Example:

DELETE /api/v1/packages/3 HTTP/1.1
Host: localhost:8081
                                        ← No body
```

### 2.6 — OPTIONS (Discover Allowed Methods / CORS Pre-flight)

| Property | Value |
|---|---|
| **Purpose** | Describe the communication options for the target resource |
| **Has Request Body?** | ❌ No |
| **Has Response Body?** | ❌ Usually no (uses headers instead) |
| **Safe?** | ✅ Yes |
| **Idempotent?** | ✅ Yes |
| **Cacheable?** | ❌ No |
| **Typical Status Codes** | `204 No Content`, `200 OK` |

```text
Wire-Level Example:

OPTIONS /api/v1/packages HTTP/1.1
Host: localhost:8081
Origin: https://kashmir-tourism.com     ← CORS pre-flight header
```

Response:
```text
HTTP/1.1 204 No Content
Allow: GET, POST, PUT, PATCH, DELETE, OPTIONS, HEAD
Access-Control-Allow-Methods: GET, POST, PUT, PATCH, DELETE
```

### 2.7 — HEAD (Headers Only — No Body)

| Property | Value |
|---|---|
| **Purpose** | Identical to GET but the server **must not** return a response body |
| **Has Request Body?** | ❌ No |
| **Has Response Body?** | ❌ **No** (only headers) |
| **Safe?** | ✅ Yes |
| **Idempotent?** | ✅ Yes |
| **Cacheable?** | ✅ Yes |
| **Typical Status Codes** | `200 OK`, `404 Not Found` |

```text
Wire-Level Example:

HEAD /api/v1/packages/2 HTTP/1.1
Host: localhost:8081
                                        ← No body sent, no body returned
```

> **Use case:** Check if a resource exists, get its `Content-Length` before
> downloading, or validate cache freshness — all without transferring the body.

### Summary Comparison Table

| Method | Body? | Safe? | Idempotent? | Cacheable? | Primary Use |
|---|---|---|---|---|---|
| **GET** | ❌ | ✅ | ✅ | ✅ | Read / retrieve |
| **POST** | ✅ | ❌ | ❌ | ❌ | Create new resource |
| **PUT** | ✅ | ❌ | ✅ | ❌ | Full replace |
| **PATCH** | ✅ | ❌ | ✅* | ❌ | Partial update |
| **DELETE** | ❌ | ❌ | ✅ | ❌ | Remove resource |
| **OPTIONS** | ❌ | ✅ | ✅ | ❌ | Discover / CORS |
| **HEAD** | ❌ | ✅ | ✅ | ✅ | Headers-only GET |

*\*PATCH is idempotent when using JSON merge-patch semantics (RFC 7396).*

---

## 🧠 3. Idempotency Deep Dive

### 3.1 — What Is Idempotency?

> **Idempotent** (adj.): Making the same request **N times** produces the
> **same server state** as making it **once**.

This does **not** mean the response is always identical — it means the
**side-effects** on the server are the same.

```text
┌───────────────────────────────────────────────────────────────────┐
│                 Idempotency Visualised                            │
├───────────────────────────────────────────────────────────────────┤
│                                                                   │
│  PUT /packages/1  {"price": 55000}                                │
│                                                                   │
│  Call 1 → Server state: package 1 price = 55000   ← Changed      │
│  Call 2 → Server state: package 1 price = 55000   ← Same state!  │
│  Call 3 → Server state: package 1 price = 55000   ← Same state!  │
│                                                                   │
│  ──────────────────────────────────────────────────                │
│                                                                   │
│  POST /packages   {"name": "New Trek", ...}                       │
│                                                                   │
│  Call 1 → Server state: 4 packages   ← 1 created                 │
│  Call 2 → Server state: 5 packages   ← Another created!          │
│  Call 3 → Server state: 6 packages   ← And another!  DANGER!     │
│                                                                   │
└───────────────────────────────────────────────────────────────────┘
```

### 3.2 — Why Idempotency Matters

| Scenario | Problem Without Idempotency |
|---|---|
| **Network timeout** | Client retries a POST → duplicate booking created |
| **Load balancer retry** | Proxy retries a failed POST → double payment charge |
| **Distributed systems** | Message queue delivers same event twice → data corruption |
| **Mobile networks** | Flaky 4G drops connection mid-request → user taps "Book" again |

### 3.3 — Real-World Example: Kashmir Tour Booking

Imagine a tourist on a 3G connection in Pahalgam tries to book the Gulmarg
Skiing Adventure package:

```text
Scenario A — POST (NOT idempotent):

  Tourist clicks "Book Now"
  ├─→ POST /bookings {"package_id": 1, "tourist": "Alice"}
  │   ... network timeout, no response received ...
  ├─→ Tourist clicks "Book Now" again (retry)
  │   POST /bookings {"package_id": 1, "tourist": "Alice"}
  │   
  └─→ Result: TWO bookings created, Alice is charged ₹90,000 (2 × ₹45,000)
       😱 Double-booking!


Scenario B — PUT with known ID (idempotent):

  Tourist clicks "Book Now"
  ├─→ PUT /bookings/booking-uuid-abc {"package_id": 1, "tourist": "Alice"}
  │   ... network timeout, no response received ...
  ├─→ Tourist clicks "Book Now" again (retry)
  │   PUT /bookings/booking-uuid-abc {"package_id": 1, "tourist": "Alice"}
  │   
  └─→ Result: ONE booking exists (same UUID), Alice is charged ₹45,000
       ✅ Safe retry!
```

### 3.4 — Idempotency Keys (Making POST Safe)

For operations that *must* use POST (e.g., payment processing), add an
**Idempotency-Key** header:

```text
POST /api/v1/bookings HTTP/1.1
Host: kashmir-tours.com
Content-Type: application/json
Idempotency-Key: booking-2024-alice-gulmarg-uuid-xyz    ← Unique per operation

{"package_id": 1, "tourist": "Alice", "amount": 45000}
```

The server stores the idempotency key after the first request.  If the same
key arrives again, it returns the **cached response** without creating a
duplicate.

### 3.5 — Method Idempotency Quick-Reference

| Method | Idempotent? | Safe to Retry? | Why |
|---|---|---|---|
| GET | ✅ | ✅ | Only reads — never changes state |
| PUT | ✅ | ✅ | Sets state to X; doing it again still sets state to X |
| DELETE | ✅ | ✅ | Resource gone after first call; still gone after Nth call |
| PATCH | ✅* | ✅* | Merge-patch is idempotent; some patch formats are not |
| POST | ❌ | ❌ | Each call creates a new resource / triggers a new action |
| HEAD | ✅ | ✅ | Same as GET but no body |
| OPTIONS | ✅ | ✅ | Only reads — metadata discovery |

---

## ⚙️ 4. How Methods Map to CRUD Operations

Backend engineers often think in terms of **CRUD** (Create, Read, Update,
Delete).  Here is the direct mapping:

```text
┌─────────────────┬──────────────┬──────────────────┬──────────────────────────────┐
│ CRUD Operation  │ HTTP Method  │ SQL Equivalent   │ Example Endpoint             │
├─────────────────┼──────────────┼──────────────────┼──────────────────────────────┤
│ Create          │ POST         │ INSERT           │ POST /api/v1/packages        │
│ Read (all)      │ GET          │ SELECT *         │ GET /api/v1/packages         │
│ Read (one)      │ GET          │ SELECT ... WHERE │ GET /api/v1/packages/101     │
│ Update (full)   │ PUT          │ UPDATE (all col) │ PUT /api/v1/packages/101     │
│ Update (partial)│ PATCH        │ UPDATE (some)    │ PATCH /api/v1/packages/101   │
│ Delete          │ DELETE       │ DELETE ... WHERE │ DELETE /api/v1/packages/101  │
└─────────────────┴──────────────┴──────────────────┴──────────────────────────────┘
```

### Full Request Lifecycle

```text
   Client                                          Server
     │                                               │
     │  ── POST /api/v1/packages ──────────────────► │
     │     Content-Type: application/json             │  ← INSERT INTO packages ...
     │     {"name":"Yusmarg Meadow Camp",...}         │
     │  ◄──────────────────── 201 Created ──────────  │
     │     Location: /api/v1/packages/4               │
     │                                               │
     │  ── GET /api/v1/packages/4 ─────────────────► │
     │                                               │  ← SELECT * FROM packages
     │  ◄──────────────────── 200 OK ───────────────  │     WHERE id = 4
     │     {"id":4,"name":"Yusmarg Meadow Camp",...}  │
     │                                               │
     │  ── PATCH /api/v1/packages/4 ───────────────► │
     │     {"price": 22000}                           │  ← UPDATE packages
     │  ◄──────────────────── 200 OK ───────────────  │     SET price=22000
     │                                               │     WHERE id = 4
     │  ── DELETE /api/v1/packages/4 ──────────────► │
     │                                               │  ← DELETE FROM packages
     │  ◄──────────────────── 200 OK ───────────────  │     WHERE id = 4
     │                                               │
```

---

## 💻 5. Hands-On Lab: Full CRUD API Methods Server

### 5.1 — Architecture Overview

```text
┌──────────────────────────────────────────────────────────────┐
│                    api_methods_lab.py                         │
│                    (Port 8081)                                │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────────────────────────────────┐                │
│  │         In-Memory "Database"             │                │
│  │                                          │                │
│  │  packages_db = {                         │                │
│  │    1: {Gulmarg Skiing Adventure, ₹45000} │                │
│  │    2: {Dal Lake Houseboat Stay,  ₹12000} │                │
│  │    3: {Sonamarg Glacier Trek,    ₹18000} │                │
│  │  }                                       │                │
│  └──────────────────────────────────────────┘                │
│                                                              │
│  Routes:                                                     │
│    /api/v1/packages       → Collection (GET, POST, OPTIONS)  │
│    /api/v1/packages/{id}  → Item (GET, PUT, PATCH, DELETE)   │
│                                                              │
│  Methods Handled:                                            │
│    GET | POST | PUT | PATCH | DELETE | OPTIONS | HEAD         │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

### 5.2 — Complete Server Code

> The file `api_methods_lab.py` contains the full implementation.
> Here is the same code inline for reference:

```python
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
    """Print detailed wire-level request information to the console."""
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
    """Print detailed wire-level response information to the console."""
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
    """Serialise `data` to JSON and send it with the given status code."""
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
    """Send a response with headers only — no body (used by OPTIONS, HEAD errors)."""
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
    Parse /api/v1/packages      → ("collection", None)
    Parse /api/v1/packages/3    → ("item", 3)
    Anything else               → (None, None)
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
    """Read and return the raw request body bytes (if any)."""
    content_length = int(handler.headers.get("Content-Length", 0))
    if content_length > 0:
        return handler.rfile.read(content_length)
    return None


# ═══════════════════════════════════════════════════════════════════════════
#  Main Request Handler
# ═══════════════════════════════════════════════════════════════════════════
class KashmirPackagesHandler(BaseHTTPRequestHandler):
    """Handles GET, POST, PUT, PATCH, DELETE, OPTIONS, HEAD for /api/v1/packages."""

    # ── Silence default stderr log (we do our own logging) ──────────
    def log_message(self, format, *args):
        pass  # suppress default one-line log

    # ───────────────────────────── GET ──────────────────────────────
    def do_GET(self):
        body_raw = read_body(self)
        log_request_details(self, body_raw)

        resource_type, pkg_id = parse_path(self.path)

        if resource_type == "collection":
            # List all packages
            all_packages = list(packages_db.values())
            send_json(self, 200, {"count": len(all_packages), "packages": all_packages})

        elif resource_type == "item":
            # Get single package
            if pkg_id in packages_db:
                send_json(self, 200, packages_db[pkg_id])
            else:
                send_json(self, 404, {"error": f"Package {pkg_id} not found"})

        else:
            send_json(self, 404, {"error": "Unknown endpoint. Use /api/v1/packages"})

    # ───────────────────────────── POST ─────────────────────────────
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

        send_json(
            self, 201, new_package,
            headers={"Location": f"/api/v1/packages/{created_id}"}
        )

    # ───────────────────────────── PUT ──────────────────────────────
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

        # PUT = full replace (keep the original ID)
        packages_db[pkg_id] = {
            "id":       pkg_id,
            "name":     data.get("name", "Unnamed Package"),
            "price":    data.get("price", 0),
            "duration": data.get("duration", "N/A"),
            "category": data.get("category", "general"),
        }
        send_json(self, 200, packages_db[pkg_id])

    # ───────────────────────────── PATCH ────────────────────────────
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

        # PATCH = merge only the supplied fields
        existing = packages_db[pkg_id]
        for key, value in data.items():
            if key != "id":  # Don't allow changing the ID
                existing[key] = value

        send_json(self, 200, existing)

    # ───────────────────────────── DELETE ───────────────────────────
    def do_DELETE(self):
        body_raw = read_body(self)
        log_request_details(self, body_raw)

        resource_type, pkg_id = parse_path(self.path)

        if resource_type != "item":
            send_json(self, 405, {"error": "DELETE requires a specific resource ID, e.g. /api/v1/packages/1"})
            return

        if pkg_id in packages_db:
            deleted = packages_db.pop(pkg_id)
            send_json(self, 200, {"message": f"Package {pkg_id} deleted", "deleted": deleted})
        else:
            send_json(self, 404, {"error": f"Package {pkg_id} not found — already deleted or never existed"})

    # ───────────────────────────── OPTIONS ──────────────────────────
    def do_OPTIONS(self):
        log_request_details(self)

        allowed = "GET, POST, PUT, PATCH, DELETE, OPTIONS, HEAD"
        send_no_body(self, 204, headers={
            "Allow": allowed,
            "Access-Control-Allow-Methods": allowed,
            "Access-Control-Allow-Headers": "Content-Type, Idempotency-Key",
            "Access-Control-Allow-Origin": "*",
        })

    # ───────────────────────────── HEAD ─────────────────────────────
    def do_HEAD(self):
        """HEAD = same as GET but with NO response body."""
        log_request_details(self)

        resource_type, pkg_id = parse_path(self.path)

        if resource_type == "collection":
            all_packages = list(packages_db.values())
            body = json.dumps({"count": len(all_packages), "packages": all_packages}).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            # NOTE: No body is written — that's the whole point of HEAD
            log_response_details(200, "(HEAD — body suppressed)")

        elif resource_type == "item" and pkg_id in packages_db:
            body = json.dumps(packages_db[pkg_id]).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
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
```

### 5.3 — Running the Server

```bash
# Start the server
python api_methods_lab.py
```

You should see:

```text
════════════════════════════════════════════════════════════
  🏔️  Kashmir Tourism Packages API — Lab 73
  🌐  Server running on http://0.0.0.0:8081
  📍  Endpoints:
        GET    /api/v1/packages         — List all
        ...
  📦  Pre-loaded packages: 3
  🛑  Press Ctrl+C to stop
════════════════════════════════════════════════════════════
```

---

## 🧪 6. Testing & Verification

Open a **separate terminal** and run each curl command.  The `-v` flag shows
the full wire-level exchange.

### Test 1 — GET All Packages

```bash
curl -v http://localhost:8081/api/v1/packages
```

**Expected output (key parts):**

```text
> GET /api/v1/packages HTTP/1.1
> Host: localhost:8081
> Accept: */*
>
< HTTP/1.1 200 OK
< Content-Type: application/json; charset=utf-8
<
{"count": 3, "packages": [
  {"id": 1, "name": "Gulmarg Skiing Adventure", "price": 45000, "duration": "5D", "category": "winter"},
  {"id": 2, "name": "Dal Lake Houseboat Stay",  "price": 12000, "duration": "3D", "category": "leisure"},
  {"id": 3, "name": "Sonamarg Glacier Trek",     "price": 18000, "duration": "4D", "category": "trekking"}
]}
```

### Test 2 — GET Single Package by ID

```bash
curl -v http://localhost:8081/api/v1/packages/2
```

**Expected:**

```text
< HTTP/1.1 200 OK
{"id": 2, "name": "Dal Lake Houseboat Stay", "price": 12000, "duration": "3D", "category": "leisure"}
```

```bash
# Non-existent package:
curl -v http://localhost:8081/api/v1/packages/999
```

**Expected:**

```text
< HTTP/1.1 404 Not Found
{"error": "Package 999 not found"}
```

### Test 3 — POST Create a New Package

```bash
curl -v -X POST http://localhost:8081/api/v1/packages \
  -H "Content-Type: application/json" \
  -d '{"name": "Pahalgam Valley Retreat", "price": 15000, "duration": "3D", "category": "leisure"}'
```

**Expected:**

```text
< HTTP/1.1 201 Created
< Location: /api/v1/packages/4
{"id": 4, "name": "Pahalgam Valley Retreat", "price": 15000, "duration": "3D", "category": "leisure"}
```

> Note: Call it again → you get `id: 5` → POST is **NOT** idempotent!

### Test 4 — PUT Replace an Existing Package

```bash
curl -v -X PUT http://localhost:8081/api/v1/packages/1 \
  -H "Content-Type: application/json" \
  -d '{"name": "Gulmarg Skiing Premium", "price": 55000, "duration": "7D", "category": "winter"}'
```

**Expected:**

```text
< HTTP/1.1 200 OK
{"id": 1, "name": "Gulmarg Skiing Premium", "price": 55000, "duration": "7D", "category": "winter"}
```

> Note: Call it 10 times → same result → PUT **IS** idempotent.

### Test 5 — PATCH Partial Update (Change Only the Price)

```bash
curl -v -X PATCH http://localhost:8081/api/v1/packages/2 \
  -H "Content-Type: application/json" \
  -d '{"price": 14000}'
```

**Expected:**

```text
< HTTP/1.1 200 OK
{"id": 2, "name": "Dal Lake Houseboat Stay", "price": 14000, "duration": "3D", "category": "leisure"}
```

> Only `price` changed from 12000 → 14000.  All other fields remain intact.

### Test 6 — DELETE a Package

```bash
curl -v -X DELETE http://localhost:8081/api/v1/packages/3
```

**Expected:**

```text
< HTTP/1.1 200 OK
{"message": "Package 3 deleted", "deleted": {"id": 3, "name": "Sonamarg Glacier Trek", ...}}
```

### Test 7 — DELETE Same Package Again (Idempotency Demonstration)

```bash
curl -v -X DELETE http://localhost:8081/api/v1/packages/3
```

**Expected:**

```text
< HTTP/1.1 404 Not Found
{"error": "Package 3 not found — already deleted or never existed"}
```

> The server state didn't change (package 3 is still gone).
> The *response* is different (404 vs 200), but the *server state* is the
> same — this is what idempotent means.

### Test 8 — OPTIONS Pre-flight

```bash
curl -v -X OPTIONS http://localhost:8081/api/v1/packages
```

**Expected:**

```text
< HTTP/1.1 204 No Content
< Allow: GET, POST, PUT, PATCH, DELETE, OPTIONS, HEAD
< Access-Control-Allow-Methods: GET, POST, PUT, PATCH, DELETE, OPTIONS, HEAD
< Access-Control-Allow-Headers: Content-Type, Idempotency-Key
< Access-Control-Allow-Origin: *
```

### Test 9 — HEAD (Headers Only, No Body)

```bash
curl -v --head http://localhost:8081/api/v1/packages/1
```

**Expected:**

```text
< HTTP/1.1 200 OK
< Content-Type: application/json; charset=utf-8
< Content-Length: 95
```

> Note: `Content-Length` is present (tells the client how big the body
> *would* be), but no body bytes are transmitted.

---

## ⚠️ 7. Common Pitfalls & Method Misuse

| # | Mistake | Why It's Wrong | Correct Approach |
|---|---|---|---|
| 1 | Using **GET with a request body** | RFC 7231 says GET body has no defined semantics; proxies and caches may strip it | Use query parameters: `GET /packages?category=winter` |
| 2 | Using **POST for updates** instead of PUT/PATCH | POST is not idempotent — retries can create duplicates | Use PUT for full replace, PATCH for partial update |
| 3 | **Not returning 404** for PUT/PATCH/DELETE on missing resources | Client thinks the operation succeeded on nothing | Always check if the resource exists first and return 404 |
| 4 | **Forgetting OPTIONS** for CORS | Browser pre-flight requests will fail, blocking your frontend | Always implement do_OPTIONS with proper CORS headers |
| 5 | **PUT vs PATCH confusion** | PUT with partial data silently wipes un-sent fields to defaults | PUT = send ALL fields; PATCH = send only changed fields |
| 6 | **Returning 200 for POST** instead of 201 | Client doesn't know a resource was *created* vs merely *processed* | Use `201 Created` + `Location` header for new resources |
| 7 | **Not setting Content-Type** | Client cannot parse the response correctly | Always send `Content-Type: application/json` for JSON APIs |
| 8 | **Treating DELETE as non-idempotent** | Returning an error only on the 2nd delete breaks retry logic | Return 404 (resource already gone) — state is still the same |

### PUT vs PATCH — Visual Comparison

```text
Original Resource:
  {"id": 1, "name": "Gulmarg Skiing", "price": 45000, "duration": "5D", "category": "winter"}

──────────────────────────────────────────────────────────────────

PUT /api/v1/packages/1
  Body: {"name": "Gulmarg Updated", "price": 50000}
  Result: {"id": 1, "name": "Gulmarg Updated", "price": 50000, "duration": "N/A", "category": "general"}
                                                                  ↑ LOST!           ↑ LOST!
  ⚠️  Fields not in the PUT body are reset to defaults!

──────────────────────────────────────────────────────────────────

PATCH /api/v1/packages/1
  Body: {"price": 50000}
  Result: {"id": 1, "name": "Gulmarg Skiing", "price": 50000, "duration": "5D", "category": "winter"}
                                                                  ↑ KEPT            ↑ KEPT
  ✅  Only the specified field changed!
```

---

## 🗺️ 8. Next Step in Series

In **Lab 74 — HTTP Status Codes & Structured Error Handling**, we will:

- Deep-dive into every status code family (1xx → 5xx)
- Build a structured error-response format with timestamps, error codes, and trace IDs
- Implement proper error handling middleware patterns
- Cover conditional requests (304 Not Modified, ETags)
- Learn why `422 Unprocessable Entity` matters for validation errors

---

## 👨‍💻 Author & Attribution

| Field | Value |
|---|---|
| **Engineer** | Danish |
| **Track** | MLOps / DevOps Engineering (APR26) |
| **Module** | 13 — FastAPI Backend & Backend Engineering |
| **Lab** | 73 — API Request Methods & Idempotency Deep Dive |
| **Domain** | Kashmir Tourism Packages API |
| **Server Port** | 8081 |
| **Dependencies** | None (Python standard library only) |
