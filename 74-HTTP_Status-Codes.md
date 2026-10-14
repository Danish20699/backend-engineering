# Lab 74: HTTP Status Codes & Error Standardization

![Backend Engineering](https://img.shields.io/badge/Backend-Engineering-blue)
![HTTP Protocol](https://img.shields.io/badge/HTTP-Protocol-green)
![FastAPI](https://img.shields.io/badge/FastAPI-Framework-teal)
![Status](https://img.shields.io/badge/Status-Active-brightgreen)

---

## 📌 1. Lab Overview & Real-World Context

In modern distributed software architecture, HTTP status codes are **the universal contract of the web**. They form the standardized, machine-readable signaling protocol that bridges client applications, browser rendering engines, content delivery networks (CDNs), reverse proxies, load balancers, API gateways, and downstream microservices.

When an HTTP client initiates a TCP socket connection and dispatches an HTTP request across the internet, the three-digit status code in the server's response line dictates **how every intermediary and client system must react**:

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│                          HTTP Response Status Line                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│       HTTP/1.1  201  Created                                                │
│       ────────  ───  ───────                                                │
│          ▲       ▲      ▲                                                   │
│          │       │      └──── Reason Phrase (Human-readable hint)           │
│          │       └─────────── Status Code (3-digit machine-readable signal) │
│          └─────────────────── Protocol Version                              │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

The first digit defines the **status code family**:

* **`1xx` (Informational)**: Request received, protocol handshake continuing.
* **`2xx` (Success)**: Action successfully received, understood, and accepted.
* **`3xx` (Redirection)**: Further action must be taken by the client to complete the request.
* **`4xx` (Client Error)**: The request contains bad syntax, missing authentication, or violates business validation.
* **`5xx` (Server Error)**: The server failed to fulfill an apparently valid request due to a backend bug or upstream outage.

---

### The Deadly Anti-Pattern: `200 OK` with `{"error": true}`

Among backend developers, the single most destructive architectural anti-pattern is returning an HTTP `200 OK` status code while embedding an error payload inside the JSON body:

```text
❌ THE DEADLY "200 OK WITH ERROR" ANTI-PATTERN

Client Request:
  POST /api/v1/bookings/KB-901/cancel HTTP/1.1
  Host: api.kashmir-tourism.gov.in

Server Response:
  HTTP/1.1 200 OK                              <-- The web infrastructure thinks this succeeded!
  Content-Type: application/json
  
  {
      "success": false,
      "error": "Booking KB-901 cannot be cancelled within 24 hours of Gulmarg ski pass start time."
  }
```

Why does this seemingly harmless shortcut wreak havoc in production systems?

```text
┌─────────────────────────────────────────────────────────────────────────────────────────────────┐
│              WHY "200 OK WITH ERROR" DESTROYS ENTERPRISE INFRASTRUCTURE                        │
├─────────────────────────┬───────────────────────────────────────────────────────────────────────┤
│ Infrastructure Layer    │ Destructive Impact of Masquerading Errors as 200 OK                   │
├─────────────────────────┼───────────────────────────────────────────────────────────────────────┤
│ 1. CDNs & Edge Caches   │ Cloudflare, CloudFront, and Fastly cache 200 OK responses by default. │
│    (Cloudflare/Fastly)  │ A temporary failure (e.g. database timeout) disguised as 200 OK gets  │
│                         │ cached at the edge, serving broken responses to millions of users!   │
├─────────────────────────┼───────────────────────────────────────────────────────────────────────┤
│ 2. Load Balancers &     │ Nginx, Envoy, and AWS ALBs health-check backends via HTTP status. If  │
│    Circuit Breakers     │ crashing microservices emit 200 OK with error bodies, circuit         │
│                         │ breakers NEVER trip, routing real traffic directly into black holes.   │
├─────────────────────────┼───────────────────────────────────────────────────────────────────────┤
│ 3. Automated Retry      │ HTTP clients (e.g., Axios, urllib3, Tenacity) automatically retry     │
│    Engines              │ idempotent requests on 502/503/504 or back off on 429. If the server │
│                         │ sends 200 OK, the retry machinery never fires, failing the operation! │
├─────────────────────────┼───────────────────────────────────────────────────────────────────────┤
│ 4. Observability &      │ Datadog, Prometheus, Grafana, and AWS CloudWatch compute Error Rates  │
│    SLO / SLA Metrics    │ as: (4xx + 5xx) / Total Requests. Returning 200 OK hides outages from │
│                         │ APM alerts, leaving PagerDuty silent while tourists are stranded!    │
├─────────────────────────┼───────────────────────────────────────────────────────────────────────┤
│ 5. Frontend & Mobile    │ In JavaScript (`fetch` / `axios`), status 200 resolves the promise    │
│    SDKs                 │ (`then()`), while 4xx/5xx triggers `catch()`. Disguised errors force  │
│                         │ frontend engineers to write defensive `if (res.data.error)` checks!   │
└─────────────────────────┴───────────────────────────────────────────────────────────────────────┘
```

---

### How Status Codes Drive Automated Client Behavior

Proper status codes transform dumb HTTP clients into self-healing, intelligent distributed systems:

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│                 Automated Client Reactions by Status Code                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   HTTP Status Code      Automated Client / Network Reaction                 │
│   ────────────────      ───────────────────────────────────                 │
│   401 Unauthorized   →  Refresh OAuth token via refresh endpoint & retry    │
│   304 Not Modified   →  Serve cached bytes directly from disk (0 network)   │
│   429 Too Many Req   →  Pause execution for 'Retry-After' seconds           │
│   503 Service Unav   →  Trigger exponential backoff with jitter             │
│   307 Temp Redirect  →  Resend exact original request to target URI         │
│   422 Unprocessable  →  Highlight specific invalid input fields in UI       │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

In this lab, we build a production-grade Kashmir Tourism API service (`http_status_codes_lab.py`) covering ski passes in Gulmarg, luxury Shikara cruises on Dal Lake, and glacier trekking permits in Sonamarg, demonstrating correct status code mechanics and RFC 7807 problem standardization.

---

## 🔍 2. Complete Status Code Families Reference

Below is the definitive reference manual for HTTP status codes across all five families (`1xx` through `5xx`).

---

### 2.1 — 1xx Informational (Protocol Handshakes)

Informational codes indicate that the client request has been acknowledged by the server socket and the transfer or protocol upgrade is underway.

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│                        1xx Status Family Matrix                             │
├──────┬──────────────────────┬───────────────────────────────────────────────┤
│ Code │ Meaning              │ Real-World Backend Application                │
├──────┼──────────────────────┼───────────────────────────────────────────────┤
│ 100  │ Continue             │ Pre-flight payload check for huge uploads     │
│ 101  │ Switching Protocols  │ HTTP connection upgrade to WebSocket / gRPC   │
│ 103  │ Early Hints          │ Link pre-loading before headers are finalized │
└──────┴──────────────────────┴───────────────────────────────────────────────┘
```

#### Detailed Code Analysis:

* **`100 Continue`**:
  * **Wire Mechanics**: When a client needs to upload a massive payload (e.g. 500 MB high-resolution aerial drone survey of Gulmarg ski slopes), transmitting all bytes only to have the server reject the request due to missing auth or file size limit is wasteful. The client sends only headers with `Expect: 100-continue`. If the server approves auth and content length, it returns `100 Continue`, signaling the client to push the body bytes.
  * **Wire Example**:
    ```text
    Client > POST /api/v1/surveys/upload HTTP/1.1
    Client > Host: api.kashmir-tourism.gov.in
    Client > Content-Length: 524288000
    Client > Expect: 100-continue

    Server < HTTP/1.1 100 Continue
    (Client now streams the 500 MB payload)
    ```

* **`101 Switching Protocols`**:
  * **Wire Mechanics**: Sent when the client requests an upgrade from HTTP/1.1 to a persistent full-duplex protocol (such as WebSockets for real-time Shikara GPS tracking on Dal Lake).
  * **Headers**: `Upgrade: websocket`, `Connection: Upgrade`.

---

### 2.2 — 2xx Success (Operation Fulfilled)

The `2xx` series certifies that the client's request was understood, validated, and successfully processed.

```text
┌─────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                   2xx Status Family Matrix                                      │
├──────┬────────────────────┬───────────┬────────────┬────────────────────────────────────────────┤
│ Code │ Semantics          │ Has Body? │ Idempotent │ Mandatory Response Headers                 │
├──────┼────────────────────┼───────────┼────────────┼────────────────────────────────────────────┤
│ 200  │ OK                 │ ✅ Yes    │ ✅ Yes     │ Content-Type, Content-Length               │
│ 201  │ Created            │ ✅ Yes    │ ❌ No      │ Location (URI of created resource)         │
│ 202  │ Accepted           │ ✅ Yes    │ ❌ No      │ Location (Task monitor URI)                │
│ 204  │ No Content         │ ❌ Never  │ ✅ Yes     │ Content-Length: 0                          │
│ 206  │ Partial Content    │ ✅ Yes    │ ✅ Yes     │ Content-Range, Content-Type                │
└──────┴────────────────────┴───────────┴────────────┴────────────────────────────────────────────┘
```

#### Detailed Code Analysis:

* **`200 OK`**:
  * Standard successful response for synchronous operations (`GET`, `PUT`, `PATCH`, or `POST` that does not create a new REST resource).

* **`201 Created`**:
  * **Semantics**: Confirms a new resource was created and persisted in the database.
  * **Mandatory Header**: `Location: /api/v1/bookings/KB-704`. The client uses this header to immediately locate and access the new entity without parsing the JSON payload.
  * **Wire Example**:
    ```text
    HTTP/1.1 201 Created
    Location: /api/v1/bookings/KB-704
    Content-Type: application/json; charset=utf-8
    Content-Length: 142

    {"booking_id": "KB-704", "customer_name": "Tariq Mir", "item_type": "Gulmarg Heli-Skiing", "status": "confirmed"}
    ```

* **`202 Accepted`**:
  * **Semantics**: The request has been accepted for processing, but processing has **not been completed**. Used in asynchronous, distributed, or batch workloads (e.g. Celery workers, RabbitMQ queues, Kafka consumers).
  * **Headers & Body**: Must return a status polling URL or job receipt with a task identifier.
  * **Wire Example**:
    ```text
    HTTP/1.1 202 Accepted
    Location: /api/v1/tasks/task-9982-fbc
    Content-Type: application/json; charset=utf-8

    {"task_id": "task-9982-fbc", "status": "Queued", "message": "Bulk Shikara permit watermarking underway"}
    ```

* **`204 No Content`**:
  * **Semantics**: The action was successfully executed, but the server deliberately sends **zero body bytes**.
  * **Primary Usage**: Successful `DELETE` operations, or `PUT`/`PATCH` updates where the client already has the latest state.
  * **Rule**: Sending any response body with a `204` violates RFC 7230 and triggers protocol parsing errors in compliant HTTP proxies.

* **`206 Partial Content`**:
  * **Semantics**: Returned when the client sends a `Range: bytes=0-1048575` header (e.g., seeking inside video tours of Sonamarg glaciers or resuming interrupted downloads).

---

### 2.3 — 3xx Redirection (Resource Navigation & Caching)

Redirection status codes instruct the client to seek the requested resource at an alternate URI or to utilize local cache storage.

```text
┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│                            3xx Redirection Comparison Matrix                                │
├──────┬──────────────────────┬─────────────┬─────────────────────┬───────────────────────────┤
│ Code │ Meaning              │ Permanent?  │ Method Preserved?   │ Typical Modern Usage      │
├──────┼──────────────────────┼─────────────┼─────────────────────┼───────────────────────────┤
│ 301  │ Moved Permanently    │ ✅ Yes      │ ⚠️ Ambiguous (POST→GET)| Canonical domain redirects │
│ 302  │ Found                │ ❌ No       │ ⚠️ Ambiguous (POST→GET)| Legacy temporary reroute  │
│ 304  │ Not Modified         │ N/A         │ N/A                 │ Conditional GET / ETag    │
│ 307  │ Temporary Redirect   │ ❌ No       │ ✅ Strictly Preserved| REST API temp reroutes     │
│ 308  │ Permanent Redirect   │ ✅ Yes      │ ✅ Strictly Preserved| Modern API URI migrations  │
└──────┴──────────────────────┴─────────────┴─────────────────────┴───────────────────────────┘
```

#### The Critical Distinction: 301/302 vs 307/308

In the early days of HTTP/1.0, user-agents (browsers) erroneously mutated `POST` requests into `GET` requests when following a `301` or `302` redirect. RFC 7231 and RFC 7538 explicitly resolved this ambiguity by establishing `307` and `308`:

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│                      Method Preservation Comparison                         │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   Legacy Behavior (302 Found):                                              │
│   Client POST /v1/orders ──► [302 Found] ──► Client GET /v2/orders ❌ BUG! │
│                                                                             │
│   Modern Standard (307 Temporary Redirect):                                 │
│   Client POST /v1/orders ──► [307 Temp]  ──► Client POST /v2/orders ✅ PRESERVED │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

> [!IMPORTANT]
> When engineering RESTful APIs where clients dispatch `POST`, `PUT`, `PATCH`, or `DELETE` payloads, **always use `307` (Temporary) or `308` (Permanent)** instead of `301` or `302`. This guarantees the client does not strip the body or alter the HTTP verb when following the `Location` header.

#### Conditional Requests with `304 Not Modified`

`304 Not Modified` is the cornerstone of high-performance web applications. It allows the server to tell the client: *"Your local cached version of this resource is identical to what is in my database — do not waste bandwidth downloading it again."*

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│                  Wire Protocol Flow: ETag & 304 Not Modified                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   Client                                                    Server          │
│     │                                                         │             │
│     │──── Step 1: Initial GET /api/v1/vouchers/VOUCH-GUL-01 ─►│             │
│     │                                                         │             │
│     │◄─── Step 2: 200 OK + ETag: "w/gul-phase2-v1" ───────────│             │
│     │     Body: {"discount": 15, "resort": "Apharwat"}        │             │
│     │     (Client caches response and ETag locally)           │             │
│     │                                                         │             │
│     │──── Step 3: Conditional GET with If-None-Match ────────►│             │
│     │     Header: If-None-Match: "w/gul-phase2-v1"            │             │
│     │                                                         │             │
│     │◄─── Step 4: 304 Not Modified ───────────────────────────│             │
│     │     Content-Length: 0 (ZERO body bytes transferred!)    │             │
│     │     (Client serves data from local cache instantly)     │             │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

### 2.4 — 4xx Client Error (Caller Fault)

The `4xx` family indicates that the client made an error in the request: malformed syntax, missing authorization, requested an entity that does not exist, or violated domain business logic.

```text
┌─────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                   4xx Status Family Matrix                                      │
├──────┬────────────────────────────┬─────────────────────────────────────────────────────────────┤
│ Code │ Meaning                    │ Precise Backend Usage                                       │
├──────┼────────────────────────────┼─────────────────────────────────────────────────────────────┤
│ 400  │ Bad Request                │ Malformed syntax, unparseable JSON, illegal query params    │
│ 401  │ Unauthorized               │ Unauthenticated: Missing or invalid token/credentials       │
│ 403  │ Forbidden                  │ Authenticated, but lacking role/permission to act           │
│ 404  │ Not Found                  │ Resource URI does not exist in registry                     │
│ 405  │ Method Not Allowed         │ Verb not supported on route (Must return `Allow` header)    │
│ 409  │ Conflict                   │ State conflict: Duplicate unique key, version mismatch      │
│ 410  │ Gone                       │ Resource permanently deleted; will never return             │
│ 415  │ Unsupported Media Type     │ Client sent XML/text when server strictly expects JSON      │
│ 422  │ Unprocessable Entity       │ Semantic failure: Valid JSON, but fields violate validation │
│ 429  │ Too Many Requests          │ Rate limit quota exceeded (Must return `Retry-After`)       │
└──────┴────────────────────────────┴─────────────────────────────────────────────────────────────┘
```

#### The Critical Distinction: `401 Unauthorized` vs `403 Forbidden`

Developers constantly confuse 401 and 403. The difference is authentication vs authorization:

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│                    401 Unauthorized vs 403 Forbidden                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   401 Unauthorized (Identity Unknown):                                      │
│     • Meaning: "Who are you? You have not proved your identity."            │
│     • RFC Mandate: MUST include the WWW-Authenticate header.                │
│     • Remediation: Client presents valid credentials / logs in.             │
│                                                                             │
│   403 Forbidden (Identity Verified, Permission Denied):                     │
│     • Meaning: "I know who you are (e.g. Tourist User), but you are NOT     │
│       permitted to access the Kashmir State Tourism Audit Logs."            │
│     • Remediation: Client must acquire elevated administrative privileges.  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

#### `400 Bad Request` vs `422 Unprocessable Entity`

In modern backend engineering (especially FastAPI and Pydantic):

* **`400 Bad Request`**: Structural or syntax error. The server cannot even parse the payload into an object (e.g. corrupted JSON with trailing commas or unquoted strings).
* **`422 Unprocessable Entity`**: Semantic error. The JSON syntax is pristine, but the values fail schema validation (e.g. `quantity: -5` or `email: "not-an-email"`). FastAPI defaults to `422` for all request validation errors.

---

### 2.5 — 5xx Server Error (Backend Infrastructure Fault)

The `5xx` family signals that the client request was syntactically valid and properly authorized, but the server failed to fulfill it due to an unexpected backend failure, unhandled crash, or upstream gateway outage.

```text
┌─────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                   5xx Status Family Matrix                                      │
├──────┬────────────────────────────┬─────────────────────────────────────────────────────────────┤
│ Code │ Meaning                    │ Production Trigger Scenario                                 │
├──────┼────────────────────────────┼─────────────────────────────────────────────────────────────┤
│ 500  │ Internal Server Error      │ Unhandled exception (e.g. ZeroDivisionError, null pointer) │
│ 502  │ Bad Gateway                │ Reverse proxy (Nginx) cannot reach ASGI app (Uvicorn dead)  │
│ 503  │ Service Unavailable        │ Server under maintenance or capacity exhaustion (overload)  │
│ 504  │ Gateway Timeout            │ Upstream database or microservice exceeded gateway timeout  │
└──────┴────────────────────────────┴─────────────────────────────────────────────────────────────┘
```

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│                       502 Bad Gateway vs 504 Gateway Timeout                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   Client ──► [ Nginx / Kong ] ──► [ Uvicorn / FastAPI Backend ]            │
│                   │                                                         │
│                   ├──► Uvicorn process crashed / Connection Refused         │
│                   │    └── Returns: 502 Bad Gateway                         │
│                   │                                                         │
│                   └──► Uvicorn query took 65 seconds (Nginx timeout is 60s) │
│                        └── Returns: 504 Gateway Timeout                     │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

> [!CAUTION]
> **Never leak raw stack traces to the client in a 500 response!** Exposing Python tracebacks, database table names, SQL queries, or internal file paths provides malicious actors with vital architectural intelligence for exploitation. Always log the stack trace internally, assign a unique correlation UUID (`trace_id`), and return a sanitized error envelope to the caller.

---

## 🧠 3. RFC 7807 & Structured Error Standardization

In real-world production systems, returning ad-hoc error formats like `{"msg": "failed"}` or `{"error": "invalid"}` causes massive integration pain across teams.

### Why Ad-Hoc Error Envelopes Fail

```text
Team A:  {"err": "Booking failed"}
Team B:  {"error": {"message": "Invalid date", "code": 4001}}
Team C:  {"status": "error", "description": "Out of memory"}
Team D:  {"errors": ["Field 'quantity' must be positive"]}
```

When four microservices emit four different error schemas:
1. Client developers must write four distinct error parsing adapters.
2. Automated observability pipelines cannot reliably extract error messages.
3. Troubleshooting incidents across microservices is nearly impossible because there is no standardized correlation ID.

---

### The RFC 7807 Standard: Problem Details for HTTP APIs

To solve this chaos, the Internet Engineering Task Force (IETF) created **RFC 7807 (Problem Details for HTTP APIs)**, specifying a uniform JSON schema and media type: `application/problem+json`.

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│                 RFC 7807 Standard Problem Details Anatomy                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   Field Name     RFC Role and Definition                                    │
│   ──────────     ───────────────────────                                    │
│   type           URI identifier specifying the error type documentation.    │
│   title          Short, human-readable summary (does not change per call).  │
│   status         The HTTP status code (must match response line).           │
│   detail         Human-readable explanation specific to THIS occurrence.    │
│   instance       URI reference identifying the exact resource or endpoint.  │
│                                                                             │
│   Enterprise Extensions:                                                    │
│   error_code     Stable, machine-readable string enum (e.g. INVALID_PASS).  │
│   trace_id       UUID correlation token mapped across distributed logs.     │
│   timestamp      ISO-8601 UTC timestamp of the incident.                   │
│   errors         Array of field-level validation issues.                    │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Side-by-Side Comparison: Bad vs Enterprise RFC 7807

```text
❌ BAD / JUNIOR DEVELOPER ERROR RESPONSE:
HTTP/1.1 200 OK
Content-Type: application/json

{
    "success": false,
    "error": "Invalid booking input"
}
```

```text
✅ ENTERPRISE RFC 7807 PROBLEM DETAILS RESPONSE:
HTTP/1.1 422 Unprocessable Entity
Content-Type: application/problem+json; charset=utf-8
X-Trace-Id: 9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d

{
    "type": "https://api.kashmir-tourism.gov.in/errors/validation-failed",
    "title": "Semantic Validation Failed",
    "status": 422,
    "detail": "The submitted booking payload contains invalid field values or missing required attributes.",
    "instance": "/api/v1/bookings",
    "error_code": "VALIDATION_FAILED",
    "trace_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
    "timestamp": "2026-03-14T10:15:30.104291Z",
    "errors": [
        {
            "field": "quantity",
            "issue": "Field must be an integer strictly greater than 0"
        },
        {
            "field": "total_price",
            "issue": "Field must be a positive numerical amount in INR"
        }
    ]
}
```

---

## ⚙️ 4. Status Code Decision Tree

Use this deterministic ASCII decision tree when architecting any RESTful API endpoint to ensure you select the exact RFC-compliant status code every single time:

```text
                                 [ Incoming Client Request ]
                                              │
                                              ▼
                                   Is Content-Type supported?
                                      /               \
                                   [NO]              [YES]
                                    │                  │
                         415 Unsupported Media         ▼
                                            Is Authorization Header valid?
                                               /               \
                                            [NO]              [YES]
                                             │                  │
                                     401 Unauthorized           ▼
                                                     Does user have permission?
                                                        /               \
                                                     [NO]              [YES]
                                                      │                  │
                                              403 Forbidden              ▼
                                                               Is HTTP Method supported?
                                                                  /               \
                                                               [NO]              [YES]
                                                                │                  │
                                                     405 Method Not Allowed        ▼
                                                                        Does Target Resource exist?
                                                                           /               \
                                                                        [NO]              [YES]
                                                                         │                  │
                                                                   404 Not Found            ▼
                                                                                  Is JSON syntax valid?
                                                                                     /               \
                                                                                  [NO]              [YES]
                                                                                   │                  │
                                                                           400 Bad Request            ▼
                                                                                           Did business validation pass?
                                                                                              /               \
                                                                                           [NO]              [YES]
                                                                                            │                  │
                                                                                 422 Unprocessable             ▼
                                                                                                    Is there a state conflict?
                                                                                                       /               \
                                                                                                    [YES]             [NO]
                                                                                                     │                  │
                                                                                               409 Conflict             ▼
                                                                                                             Is operation asynchronous?
                                                                                                                /               \
                                                                                                             [YES]             [NO]
                                                                                                              │                  │
                                                                                                        202 Accepted             ▼
                                                                                                                      Did it create a resource?
                                                                                                                         /               \
                                                                                                                      [YES]             [NO]
                                                                                                                       │                  │
                                                                                                                  201 Created             ▼
                                                                                                                               Does response return data?
                                                                                                                                  /               \
                                                                                                                               [YES]             [NO]
                                                                                                                                │                  │
                                                                                                                             200 OK          204 No Content
```

---

## 💻 5. Hands-On Lab: Kashmir Tourism API Server

We now implement our dedicated demonstration server: `http_status_codes_lab.py`.

### Architecture & Design
* **Runtime**: Zero external dependencies, pure Python 3 standard library (`http.server`, `json`, `uuid`, `time`, `datetime`).
* **Port**: **`8082`** (Running independently from Lab 72 and Lab 73).
* **Console Safety**: Explicit `sys.stdout.reconfigure(encoding="utf-8")` to guarantee Unicode stability on Windows terminal consoles.
* **RFC 7807 Engine**: Built-in `send_error_problem()` helper standardizing error envelopes, generating trace UUIDs, and formatting ISO timestamps.
* **Demonstrated Endpoints**:
  1. `GET /api/v1/health` → `200 OK`
  2. `POST /api/v1/bookings` → `201 Created` with `Location`, or `422 Unprocessable Entity`, or `409 Conflict`
  3. `POST /api/v1/bookings/async` → `202 Accepted` with task ID and status URL
  4. `DELETE /api/v1/bookings/{id}` → `204 No Content` or `404 Not Found`
  5. `GET /api/v1/vouchers/{id}` → `200 OK` with `ETag` or `304 Not Modified` on cache hit
  6. `GET /api/v1/admin/audit` → `401 Unauthorized` (missing/bad token) vs `403 Forbidden` (tourist role) vs `200 OK` (admin role)
  7. `GET /api/v1/weather/reports` → `200 OK` or `429 Too Many Requests` with `Retry-After`
  8. `GET /api/v1/redirect-test` → `307 Temporary Redirect`
  9. `GET /api/v1/simulate-crash` → `500 Internal Server Error` (sanitized with correlation trace ID)
  10. `GET /api/v1/maintenance` → `503 Service Unavailable` with `Retry-After: 120`

### Full Python Source Code (`http_status_codes_lab.py`)

```python
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
```

---

## 🧪 6. Testing & Wire-Level Verification

Let us now execute comprehensive wire-level tests against `http://localhost:8082` using `curl -v`. The `-v` flag reveals the exact raw HTTP request headers, response status lines, and server headers over the TCP socket.

### Test 1 — Health Check (`200 OK`)

```bash
curl -v http://localhost:8082/api/v1/health
```

**Expected Wire Output:**
```text
> GET /api/v1/health HTTP/1.1
> Host: localhost:8082
> User-Agent: curl/8.4.0
> Accept: */*
> 
< HTTP/1.1 200 OK
< Content-Type: application/json; charset=utf-8
< Content-Length: 172
< X-Powered-By: Kashmir-Tourism-Engine/1.0
< 
{
    "status": "healthy",
    "service": "kashmir-tourism-core-gateway",
    "version": "1.4.0",
    "environment": "production",
    "cluster_region": "in-north-srinagar",
    "timestamp": "2026-03-14T10:00:00Z"
}
```

---

### Test 2 — Resource Creation (`201 Created` with `Location` Header)

Create a new Gulmarg Heli-Skiing pass:

```bash
curl -v -X POST http://localhost:8082/api/v1/bookings \
  -H "Content-Type: application/json" \
  -d '{"booking_id": "KB-704", "customer_name": "Tariq Mir", "item_type": "Gulmarg Heli-Skiing Pass", "quantity": 1, "total_price": 22500}'
```

**Expected Wire Output:**
```text
> POST /api/v1/bookings HTTP/1.1
> Host: localhost:8082
> Content-Type: application/json
> Content-Length: 141
> 
< HTTP/1.1 201 Created
< Content-Type: application/json; charset=utf-8
< Content-Length: 228
< Location: /api/v1/bookings/KB-704
< X-Powered-By: Kashmir-Tourism-Engine/1.0
< 
{
    "booking_id": "KB-704",
    "customer_name": "Tariq Mir",
    "item_type": "Gulmarg Heli-Skiing Pass",
    "quantity": 1,
    "status": "confirmed",
    "total_price": 22500,
    "created_at": "2026-03-14T10:01:15.129000Z"
}
```

> **Key Observation:** The response includes `Location: /api/v1/bookings/KB-704`, pointing directly to the newly created entity.

---

### Test 3 — Semantic Validation Failure (`422 Unprocessable Entity`)

Send negative quantity and price:

```bash
curl -v -X POST http://localhost:8082/api/v1/bookings \
  -H "Content-Type: application/json" \
  -d '{"booking_id": "KB-705", "customer_name": "Tariq Mir", "item_type": "Ski Pass", "quantity": -2, "total_price": 0}'
```

**Expected Wire Output:**
```text
< HTTP/1.1 422 Unprocessable Entity
< Content-Type: application/problem+json; charset=utf-8
< Content-Length: 468
< X-Trace-Id: 4f1a6021-9d2a-4a25-a83a-1cf0a58a7428
< 
{
    "type": "https://api.kashmir-tourism.gov.in/errors/validation-failed",
    "title": "Semantic Validation Failed",
    "status": 422,
    "detail": "The submitted booking payload contains invalid field values or missing required attributes.",
    "instance": "/api/v1/bookings",
    "error_code": "VALIDATION_FAILED",
    "trace_id": "4f1a6021-9d2a-4a25-a83a-1cf0a58a7428",
    "timestamp": "2026-03-14T10:02:10Z",
    "errors": [
        {"field": "quantity", "issue": "Field must be an integer strictly greater than 0"},
        {"field": "total_price", "issue": "Field must be a positive numerical amount in INR"}
    ]
}
```

---

### Test 4 — Duplicate Key Conflict (`409 Conflict`)

Attempt to re-create booking `KB-701`:

```bash
curl -v -X POST http://localhost:8082/api/v1/bookings \
  -H "Content-Type: application/json" \
  -d '{"booking_id": "KB-701", "customer_name": "Ayesha Khan", "item_type": "Gulmarg Pass", "quantity": 1, "total_price": 45000}'
```

**Expected Wire Output:**
```text
< HTTP/1.1 409 Conflict
< Content-Type: application/problem+json; charset=utf-8
< X-Trace-Id: b8e5d070-5d62-422f-a9cb-f4e912aa4512
< 
{
    "type": "https://api.kashmir-tourism.gov.in/errors/resource-conflict-duplicate",
    "title": "Resource Conflict",
    "status": 409,
    "detail": "A Kashmir tourism booking with ID 'KB-701' already exists in active ledger. Duplicate booking IDs are rejected.",
    "instance": "/api/v1/bookings",
    "error_code": "RESOURCE_CONFLICT_DUPLICATE",
    "trace_id": "b8e5d070-5d62-422f-a9cb-f4e912aa4512",
    "timestamp": "2026-03-14T10:03:00Z"
}
```

---

### Test 5 — Asynchronous Task Initiation (`202 Accepted`)

Initiate bulk Shikara permit generation:

```bash
curl -v -X POST http://localhost:8082/api/v1/bookings/async \
  -H "Content-Type: application/json" \
  -d '{"batch_name": "Spring Shikara Fleet Permits", "total_permits": 150}'
```

**Expected Wire Output:**
```text
< HTTP/1.1 202 Accepted
< Location: /api/v1/tasks/task-91fc4b22
< Content-Type: application/json; charset=utf-8
< 
{
    "task_id": "task-91fc4b22",
    "status": "Accepted",
    "message": "Bulk Shikara fleet permits queued for asynchronous batch validation and digital watermarking.",
    "status_url": "/api/v1/tasks/task-91fc4b22",
    "estimated_duration_seconds": 25,
    "created_at": "2026-03-14T10:04:12Z"
}
```

---

### Test 6 — Resource Deletion (`204 No Content`)

Delete existing booking `KB-701`:

```bash
curl -v -X DELETE http://localhost:8082/api/v1/bookings/KB-701
```

**Expected Wire Output:**
```text
> DELETE /api/v1/bookings/KB-701 HTTP/1.1
> Host: localhost:8082
> 
< HTTP/1.1 204 No Content
< Content-Length: 0
< X-Powered-By: Kashmir-Tourism-Engine/1.0
< 
```

> **Key Observation:** Notice `Content-Length: 0` and **zero body bytes transmitted**.

---

### Test 7 — Deletion of Non-Existent Entity (`404 Not Found`)

Attempt to delete `KB-701` a second time (already purged):

```bash
curl -v -X DELETE http://localhost:8082/api/v1/bookings/KB-701
```

**Expected Wire Output:**
```text
< HTTP/1.1 404 Not Found
< Content-Type: application/problem+json; charset=utf-8
< 
{
    "type": "https://api.kashmir-tourism.gov.in/errors/resource-not-found",
    "title": "Resource Not Found",
    "status": 404,
    "detail": "Cannot delete booking 'KB-701'. The record does not exist or was already removed.",
    "instance": "/api/v1/bookings/KB-701",
    "error_code": "RESOURCE_NOT_FOUND"
}
```

---

### Test 8 & 9 — Conditional Caching (`200 OK` vs `304 Not Modified`)

#### Step 1: Initial fetch without cache:
```bash
curl -v http://localhost:8082/api/v1/vouchers/VOUCH-GUL-01
```

**Expected Wire Output:**
```text
< HTTP/1.1 200 OK
< Content-Type: application/json; charset=utf-8
< ETag: "w/gul-phase2-v1"
< Cache-Control: public, max-age=300
< 
{
    "voucher_id": "VOUCH-GUL-01",
    "title": "Gulmarg Gondola Phase-2 Alpine Access Voucher",
    "discount_percent": 15,
    "resort": "Apharwat Highland Lodge",
    "valid_until": "2026-12-31",
    "etag": "\"w/gul-phase2-v1\""
}
```

#### Step 2: Conditional fetch with matching `If-None-Match`:
```bash
curl -v http://localhost:8082/api/v1/vouchers/VOUCH-GUL-01 \
  -H 'If-None-Match: "w/gul-phase2-v1"'
```

**Expected Wire Output:**
```text
> GET /api/v1/vouchers/VOUCH-GUL-01 HTTP/1.1
> If-None-Match: "w/gul-phase2-v1"
> 
< HTTP/1.1 304 Not Modified
< Content-Length: 0
< ETag: "w/gul-phase2-v1"
< Cache-Control: public, max-age=300
< 
```

> **Performance Verification:** Server returned `304 Not Modified` with `Content-Length: 0`. The client skipped downloading 240 bytes of JSON and rendered directly from local cache!

---

### Test 10, 11, 12 — Authentication (`401` vs `403` vs `200`)

#### Scenario 1: Missing credentials (`401 Unauthorized` with `WWW-Authenticate`)
```bash
curl -v http://localhost:8082/api/v1/admin/audit
```

**Expected Wire Output:**
```text
< HTTP/1.1 401 Unauthorized
< Content-Type: application/problem+json; charset=utf-8
< WWW-Authenticate: Bearer realm="kashmir-api", error="invalid_token", error_description="The access token is missing or malformed"
< 
{
    "type": "https://api.kashmir-tourism.gov.in/errors/auth-credentials-missing",
    "title": "Authentication Required",
    "status": 401,
    "detail": "Access to the Kashmir administrative audit log requires a valid Bearer token.",
    "error_code": "AUTH_CREDENTIALS_MISSING"
}
```

#### Scenario 2: Valid tourist token, but lacking admin role (`403 Forbidden`)
```bash
curl -v http://localhost:8082/api/v1/admin/audit \
  -H "Authorization: Bearer kashmir-tourist-token"
```

**Expected Wire Output:**
```text
< HTTP/1.1 403 Forbidden
< Content-Type: application/problem+json; charset=utf-8
< 
{
    "type": "https://api.kashmir-tourism.gov.in/errors/forbidden-insufficient-permissions",
    "title": "Insufficient Privileges",
    "status": 403,
    "detail": "Caller authenticated as role 'tourist-user'. Access to audit logs strictly requires 'kashmir-state-admin'.",
    "error_code": "FORBIDDEN_INSUFFICIENT_PERMISSIONS"
}
```

#### Scenario 3: Valid admin token (`200 OK`)
```bash
curl -v http://localhost:8082/api/v1/admin/audit \
  -H "Authorization: Bearer kashmir-admin-secret-2026"
```

**Expected Wire Output:**
```text
< HTTP/1.1 200 OK
< Content-Type: application/json; charset=utf-8
< 
{
    "audit_id": "AUD-SRN-9982",
    "authority": "Directorate of Kashmir Tourism Enforcement",
    "records": [
        {"timestamp": "2026-03-14T08:12:00Z", "action": "SKI_PASS_QUOTA_ADJUSTMENT", "operator": "superadmin"},
        {"timestamp": "2026-03-14T09:45:00Z", "action": "SHIKARA_LICENSE_RENEWAL", "operator": "enforcement_officer_3"}
    ]
}
```

---

### Test 13 — Unsupported Media Type (`415`)

Send raw plain text instead of JSON:

```bash
curl -v -X POST http://localhost:8082/api/v1/bookings \
  -H "Content-Type: text/plain" \
  -d "booking_id=KB-999"
```

**Expected Wire Output:**
```text
< HTTP/1.1 415 Unsupported Media Type
< Content-Type: application/problem+json; charset=utf-8
< 
{
    "type": "https://api.kashmir-tourism.gov.in/errors/unsupported-media-type",
    "title": "Unsupported Media Type",
    "status": 415,
    "detail": "Content-Type 'text/plain' is not supported. Request payload must be formatted as 'application/json'.",
    "error_code": "UNSUPPORTED_MEDIA_TYPE"
}
```

---

### Test 14 — Malformed JSON Syntax (`400 Bad Request`)

Send broken JSON with missing closing brace:

```bash
curl -v -X POST http://localhost:8082/api/v1/bookings \
  -H "Content-Type: application/json" \
  -d '{"booking_id": "KB-777", "customer_name": "Rashid"'
```

**Expected Wire Output:**
```text
< HTTP/1.1 400 Bad Request
< Content-Type: application/problem+json; charset=utf-8
< 
{
    "type": "https://api.kashmir-tourism.gov.in/errors/malformed-json-syntax",
    "title": "Malformed JSON Syntax",
    "status": 400,
    "detail": "The JSON parser encountered a fatal syntax error: Expecting ',' delimiter: line 1 column 47 (char 46)",
    "error_code": "MALFORMED_JSON_SYNTAX"
}
```

---

### Test 15 — Method Not Allowed (`405` with `Allow` Header)

Attempt `PUT` on `/api/v1/health`:

```bash
curl -v -X PUT http://localhost:8082/api/v1/health
```

**Expected Wire Output:**
```text
< HTTP/1.1 405 Method Not Allowed
< Allow: GET, HEAD, OPTIONS
< Content-Type: application/problem+json; charset=utf-8
< 
{
    "type": "https://api.kashmir-tourism.gov.in/errors/method-not-allowed",
    "title": "Method Not Allowed",
    "status": 405,
    "detail": "PUT verb is not permitted on the /api/v1/health endpoint.",
    "error_code": "METHOD_NOT_ALLOWED"
}
```

---

### Test 16 — Rate Limiting (`429 Too Many Requests` with `Retry-After`)

Execute 4 rapid requests to the weather telemetry endpoint:

```bash
curl -s http://localhost:8082/api/v1/weather/reports > /dev/null
curl -s http://localhost:8082/api/v1/weather/reports > /dev/null
curl -s http://localhost:8082/api/v1/weather/reports > /dev/null
curl -v http://localhost:8082/api/v1/weather/reports
```

**Expected Wire Output on 4th Request:**
```text
< HTTP/1.1 429 Too Many Requests
< Content-Type: application/problem+json; charset=utf-8
< Retry-After: 30
< X-RateLimit-Limit: 3
< X-RateLimit-Remaining: 0
< X-RateLimit-Reset: 1773489812
< 
{
    "type": "https://api.kashmir-tourism.gov.in/errors/rate-limit-exceeded",
    "title": "Too Many Requests",
    "status": 429,
    "detail": "Rate limit quota exceeded. Maximum allowed: 3 requests per 30 seconds.",
    "error_code": "RATE_LIMIT_EXCEEDED"
}
```

---

### Test 17 — Verb Preservation Redirect (`307 Temporary Redirect`)

```bash
curl -v http://localhost:8082/api/v1/redirect-test
```

**Expected Wire Output:**
```text
< HTTP/1.1 307 Temporary Redirect
< Location: /api/v1/health
< Content-Type: application/json; charset=utf-8
< 
{
    "message": "Resource temporarily moved to /api/v1/health",
    "redirect_target": "/api/v1/health"
}
```

---

### Test 18 — Unhandled Server Crash (`500 Internal Server Error`)

```bash
curl -v http://localhost:8082/api/v1/simulate-crash
```

**Expected Wire Output (Client receives sanitized response):**
```text
< HTTP/1.1 500 Internal Server Error
< Content-Type: application/problem+json; charset=utf-8
< X-Trace-Id: 2c19e34a-9b55-4081-a75e-cf715891d4e0
< 
{
    "type": "https://api.kashmir-tourism.gov.in/errors/internal-server-error",
    "title": "Internal Server Error",
    "status": 500,
    "detail": "A critical runtime anomaly occurred while settling the transaction. An incident ticket has been dispatched.",
    "instance": "/api/v1/simulate-crash",
    "error_code": "INTERNAL_SERVER_ERROR",
    "trace_id": "2c19e34a-9b55-4081-a75e-cf715891d4e0",
    "timestamp": "2026-03-14T10:08:45Z"
}
```

**Server Console Output (Internal Observability):**
```text
  [CRASH SIMULATION] Triggering intentional ZeroDivisionError in booking settlement engine...
  [CRITICAL ALARM] Server Exception Captured:
Traceback (most recent call last):
  File "http_status_codes_lab.py", line 287, in do_GET
    critical_calculation = 1000 / 0
ZeroDivisionError: division by zero
```

> **Security Verification:** The internal stack trace was cleanly printed to server console logs, but **never leaked across the wire to the client!**

---

### Test 19 — Scheduled Service Maintenance (`503 Service Unavailable`)

```bash
curl -v http://localhost:8082/api/v1/maintenance
```

**Expected Wire Output:**
```text
< HTTP/1.1 503 Service Unavailable
< Content-Type: application/problem+json; charset=utf-8
< Retry-After: 120
< 
{
    "type": "https://api.kashmir-tourism.gov.in/errors/service-maintenance-in-progress",
    "title": "Service Unavailable",
    "status": 503,
    "detail": "The Gulmarg Gondola ticketing cluster is temporarily offline for scheduled database shard migration.",
    "instance": "/api/v1/maintenance",
    "error_code": "SERVICE_MAINTENANCE_IN_PROGRESS"
}
```

---

## ⚠️ 7. Common Pitfalls & Anti-Patterns

Below are the most critical status code and error handling mistakes encountered in production systems:

| # | Anti-Pattern | Why It Breaks Systems | Correct Architectural Fix |
|---|---|---|---|
| **1** | **Returning `200 OK` with `{"error": "..."}`** | CDNs cache broken responses; circuit breakers fail to trip; client error handlers (`catch`) never fire. | Always emit standard `4xx` for caller errors and `5xx` for server outages. |
| **2** | **Confusing `401` and `403`** | Clients cannot know whether to prompt for login/refresh token (`401`) or display an access denied warning (`403`). | Use `401` when unauthenticated (include `WWW-Authenticate`); use `403` when authenticated but lacking permissions. |
| **3** | **Leaking raw tracebacks in `500` responses** | Exposes Python versions, internal file paths, and database schema, enabling reconnaissance attacks. | Catch unhandled exceptions, log the trace internally with a UUID, and return sanitized RFC 7807 problem details. |
| **4** | **Returning `400` instead of `422` for schema validation** | Client SDKs cannot distinguish unparseable corrupted JSON (`400`) from field-level constraint violations (`422`). | Use `400` for syntax/framing failures; use `422` with an `errors` array for semantic/validation issues. |
| **5** | **Omitting `Location` header on `201 Created`** | Clients must guess the URI of the newly created entity or rely on parsing the response body. | Always include `Location: /api/v1/resources/{id}` in `201` and `202` responses. |
| **6** | **Omitting `Retry-After` on `429` and `503`** | Clients immediately hammer the server with aggressive retries, causing an avalanche crash (thundering herd). | Always supply `Retry-After: <seconds>` or an HTTP-date so clients back off cleanly. |
| **7** | **Omitting `Allow` header on `405 Method Not Allowed`** | Violates RFC 7231; clients and automated API explorers cannot discover supported verbs. | Always emit `Allow: GET, POST, OPTIONS` when returning `405`. |
| **8** | **Returning a body with `204 No Content` or `304 Not Modified`** | Strictly violates HTTP specs; causes framing errors and connection drops in HTTP proxies. | Guarantee `Content-Length: 0` and transmit zero payload bytes for `204` and `304`. |
| **9** | **Using `302 Found` instead of `307/308`** | Browsers erroneously convert `POST`/`PUT`/`DELETE` into `GET` across redirects, losing request bodies. | Use `307 Temporary Redirect` or `308 Permanent Redirect` to preserve HTTP verbs. |
| **10**| **Inconsistent Ad-Hoc Error JSON Schemas** | Frontend and mobile teams must implement disparate parsing logic for every microservice. | Mandate **RFC 7807 Problem Details** (`application/problem+json`) across all engineering teams. |

---

## 🗺️ 8. Next Step in Series

Now that you have mastered the HTTP protocol wire contract, HTTP verbs, status codes, and enterprise RFC 7807 error standardization, you are ready to evaluate how distributed architectures exchange data at scale.

In **Lab 75 — API Architecture Styles & Paradigms (`75-API-ARchitecture-Types.md`)**, we will explore:
* **REST (Representational State Transfer)**: Uniform interfaces, statelessness, and HATEOAS.
* **GraphQL**: Client-driven queries, schema resolvers, solving over-fetching and under-fetching.
* **gRPC & Protocol Buffers**: High-throughput binary RPC, HTTP/2 multiplexing, microservice-to-microservice communication.
* **WebSockets**: Persistent full-duplex bi-directional streams for real-time telemetry (GPS tracking for Dal Lake Shikaras, live avalanche sensors on Gulmarg Apharwat Peak).
* **Architecture Decision Framework**: When to use REST vs GraphQL vs gRPC vs WebSockets in modern MLOps and cloud engineering stacks.

---

## 👨‍💻 Author & Attribution

| Field | Value |
|---|---|
| **Engineer** | Danish |
| **Track** | MLOps / DevOps Engineering (APR26) |
| **Module** | 13 — FastAPI Backend & Backend Engineering |
| **Lab** | 74 — HTTP Status Codes & Error Standardization |
| **Domain** | Kashmir Tourism Gateway API (Gulmarg Ski Passes, Shikara Permits) |
| **Server Port** | 8082 |
| **Dependencies** | None (Python 3 Standard Library only) |
| **Standard** | RFC 7231, RFC 7235, RFC 6585, RFC 7807 |

