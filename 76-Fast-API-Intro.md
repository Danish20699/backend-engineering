# Lab 76: FastAPI Architecture, Pydantic v2 & OpenAPI Engine

![FastAPI](https://img.shields.io/badge/FastAPI-0.110%2B-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Pydantic](https://img.shields.io/badge/Pydantic-v2.5%2B-E92063?style=for-the-badge&logo=pydantic&logoColor=white)
![ASGI](https://img.shields.io/badge/ASGI-Starlette%20%7C%20Uvicorn-blueviolet?style=for-the-badge)
![Status](https://img.shields.io/badge/Status-Completed-success?style=for-the-badge)

---

## 📌 1. Executive Overview & The Python API Revolution

For over a decade, Python web development was dominated by two venerable frameworks:
1. **Django (2005)**: The batteries-included monolith designed around relational databases, HTML templating, and server-rendered form validation.
2. **Flask (2010)**: The minimalist microframework giving developers total routing freedom, but leaving validation, serialization, asynchronous I/O, and API documentation to fragmented third-party plugins.

Both frameworks were architected on the **WSGI (Web Server Gateway Interface, PEP 3333)** standard. While WSGI powered the web for years, modern cloud computing, distributed microservices, and high-concurrency Machine Learning model inference exposed fundamental limitations:
* **Synchronous Thread Blocking**: WSGI operates on a blocking, one-thread-per-request model. Slow database queries or downstream third-party HTTP calls stall worker threads.
* **Manual Data Parsing & Validation**: Developers had to manually parse JSON bodies, write repetitive boilerplate to validate field types, and manually construct HTTP 400 error messages.
* **Documentation Drift**: Swagger/OpenAPI documentation had to be written and maintained manually in YAML files or docstrings, inevitably falling out of sync with actual Python route code.

```text
┌─────────────────────────────────────────────────────────────────────────────────────────────────┐
│                           The Python Backend Framework Evolution                                │
├─────────────────────┬──────────────────────────┬──────────────────────┬─────────────────────────┤
│ Feature             │ Django (2005)            │ Flask (2010)         │ FastAPI (2018+)         │
├─────────────────────┼──────────────────────────┼──────────────────────┼─────────────────────────┤
│ Server Interface    │ WSGI (Synchronous)       │ WSGI (Synchronous)   │ ASGI (Asynchronous I/O) │
│ Async Concurrency   │ Limited / Bolted-on      │ Limited (Gevent/sync)│ Native async/await      │
│ Data Validation     │ Django Forms / Serializers│ Manual / Marshmallow │ Pydantic v2 (Rust Core) │
│ Type Hinting        │ Optional / Untyped       │ Untyped              │ Native Python 3.10+ PEP │
│ API Documentation   │ Manual / DRF Swagger     │ Manual (Flasgger)    │ Automatic Live OpenAPI  │
│ Performance (RPS)   │ ~1,500 - 3,500 req/s     │ ~2,000 - 4,500 req/s │ ~18,000 - 35,000 req/s  │
└─────────────────────┴──────────────────────────┴──────────────────────┴─────────────────────────┘
```

Created in 2018 by **Sebastián Ramírez**, **FastAPI** fundamentally revolutionized Python backend engineering. It achieved what was previously thought impossible in Python: **blistering near-Go/NodeJS performance combined with world-class developer ergonomics and zero-config automated documentation.**

---

## 🏛️ 2. Architectural Anatomy: The Trinity of FastAPI

FastAPI is not an isolated monolith. It stands as an orchestrator upon two world-class software foundations: **Starlette** and **Pydantic**. 

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│                           FastAPI Architectural Triad                       │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│                        FastAPI High-Level Framework                         │
│   (Routing, OpenAPI 3.0 Generation, Swagger UI, Dependency Injection,       │
│    OAuth2 / Security, Parameter Extraction, Automatic 422 Error Handling)   │
│                                                                             │
│                 ┌─────────────────────────────┐                             │
│                 ▼                             ▼                             │
│       Starlette ASGI Toolkit          Pydantic v2 Data Engine               │
│  ┌───────────────────────────────┐ ┌──────────────────────────────┐         │
│  │ * High-performance ASGI Core │ │ * Rust-based pydantic-core   │         │
│  │ * HTTP / WebSocket routing    │ │ * High-speed JSON parsing    │         │
│  │ * Middleware stack (CORS/Gzip)│ │ * Strict schema validation   │         │
│  │ * StreamingResponse & Files   │ │ * Data coercion & typing     │         │
│  │ * BackgroundTasks execution   │ │ * OpenAPI JSON Schema export │         │
│  └──────────────┬────────────────┘ └──────────────────────────────┘         │
│                 │                                                           │
│                 ▼                                                           │
│     Uvicorn Lightning ASGI Server (uvloop + httptools C-parsers)            │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2.1 The ASGI vs WSGI Paradigm Shift

To understand FastAPI's throughput, we must contrast **WSGI** and **ASGI**:

```text
WSGI (Synchronous Thread-per-Request):
Client A ──► [Thread 1: DB Query (Wait 80ms) ──────────► Response]
Client B ──► [Thread 2: API Call (Wait 120ms) ─────────► Response]
Client C ──► [Thread 3: Disk I/O (Wait 40ms) ──────────► Response]
Client D ──► [BLOCKED: All worker threads occupied waiting on I/O!] ❌

───────────────────────────────────────────────────────────────────────────────

ASGI (Single Event-Loop Asynchronous Multiplexing):
Client A ──► [Event Loop: Task A pauses at DB await] ─────────────┐
Client B ──► [Event Loop picks up Task B while A waits] ──────────┼──► Fast!
Client C ──► [Event Loop picks up Task C while B awaits API] ─────┤    Zero idle
Client D ──► [Event Loop processes Task D concurrently] ──────────┘    threads!
```

* **WSGI (PEP 3333)**: Takes two arguments: `environ` (a dictionary of request variables) and `start_response` (a callback callable). It is fundamentally synchronous.
* **ASGI (Asynchronous Server Gateway Interface)**: Takes three arguments:
  ```python
  async def app(scope, receive, send):
      # scope: Connection metadata dictionary (type: "http" or "websocket")
      # receive: Awaitable callable to receive incoming HTTP request chunk events
      # send: Awaitable callable to send outgoing HTTP response events
      ...
  ```
Because FastAPI is a native ASGI framework running on **Uvicorn** (powered by `uvloop`—a fast C-replacement for Python's `asyncio` event loop), a single Python process can effortlessly handle **tens of thousands of concurrent open socket connections** without thread starvation.

---

## 🛡️ 3. The Power of Python Type Hints & Pydantic v2

Before FastAPI, type annotations in Python were merely documentation hints for IDEs and static analyzers (like Mypy). FastAPI transformed type annotations into **active, runtime-enforced contracts**.

### 3.1 Pydantic v2: Powered by Rust (`pydantic-core`)

In late 2023, Pydantic underwent a complete rewrite from the ground up. In **Pydantic v2**, the entire validation loop was rewritten in **Rust** (`pydantic-core`). 

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│                       Pydantic v1 vs Pydantic v2 Performance                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   JSON Parsing & Validation Speed:                                          │
│   Pydantic v1 (Pure Python):  ████████████ 1,200 ops/sec                    │
│   Pydantic v2 (Rust Core):    ████████████████████████████████████ 22,000+  │
│                               (Up to 17x to 20x faster!)                    │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 3.2 Declarative Schema Definition & Cross-Field Validation

Let us examine the domain schema used in our lab (`fastapi_intro_lab.py`):

```python
from enum import Enum
from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict

class DifficultyLevel(str, Enum):
    EASY = "EASY"
    MODERATE = "MODERATE"
    DIFFICULT = "DIFFICULT"
    EXTREME = "EXTREME"

class GpsCoordinates(BaseModel):
    latitude: float = Field(..., ge=32.0, le=37.0)
    longitude: float = Field(..., ge=73.0, le=77.5)
    elevation_meters: int = Field(..., ge=1500, le=8611)

    model_config = ConfigDict(extra="forbid")

class ExpeditionBase(BaseModel):
    name: str = Field(..., min_length=5, max_length=100)
    base_camp: str = Field(..., min_length=3, max_length=80)
    difficulty: DifficultyLevel
    max_altitude_meters: int = Field(..., ge=1500, le=8611)
    duration_days: int = Field(..., ge=1, le=30)
    price_inr: float = Field(..., gt=0.0)
    max_participants: int = Field(..., ge=1, le=40)
    emergency_beacon_code: str = Field(..., pattern=r"^KMR-[A-Z0-9]{4,8}$")
    coordinates: GpsCoordinates

    @field_validator("name")
    @classmethod
    def validate_title_casing(cls, v: str) -> str:
        clean = v.strip()
        if not clean[0].isupper():
            raise ValueError("Expedition name must begin with a capital letter.")
        return clean

    @model_validator(mode="after")
    def validate_altitude_vs_difficulty(self) -> "ExpeditionBase":
        if self.difficulty == DifficultyLevel.EXTREME and self.max_altitude_meters < 4000:
            raise ValueError(
                f"Expeditions rated EXTREME must attain an altitude of at least 4000m (provided: {self.max_altitude_meters}m)."
            )
        return self
```

### 3.3 What Pydantic Automatically Handles:
1. **Type Coercion**: If a client sends `"price_inr": "18500.0"` as a string, Pydantic safely coerces it into a `float`. If the client sends `"duration_days": "seven"`, Pydantic rejects it with a precision error.
2. **Boundary Validation**: Validates ranges (`ge`, `le`, `gt`), string bounds (`min_length`), and regular expression patterns (`pattern`).
3. **Structured Nested Models**: Validates nested JSON sub-objects (`coordinates: GpsCoordinates`) recursively.
4. **Descriptive 422 Errors**: If any rule fails, FastAPI halts execution immediately before reaching your route handler and returns a clean, detailed RFC-compliant JSON response:

```json
{
  "detail": [
    {
      "type": "value_error",
      "loc": ["body"],
      "msg": "Value error, Expeditions rated EXTREME must attain an altitude of at least 4000m (provided: 2500m).",
      "input": { ... }
    }
  ]
}
```

---

## 📖 4. Zero-Config Automatic Documentation: OpenAPI 3.0, Swagger & ReDoc

One of FastAPI's most celebrated innovations is **automatic documentation generation**.

### 4.1 How OpenAPI Generation Works Under the Hood

When FastAPI boots up:
1. It inspects all registered route decorators (`@app.get`, `@app.post`, etc.).
2. It reflects over Python function signatures, docstrings, path parameters, query parameters, header definitions, and return type annotations.
3. It inspects all Pydantic request models (`payload: TrekExpeditionCreate`) and response models (`response_model=TrekExpeditionResponse`).
4. It compiles an industry-standard **OpenAPI 3.0 JSON specification** served at `/openapi.json`.
5. It renders two interactive client-side web UIs directly from that schema:
   * **Swagger UI** (`/docs`): An interactive sandbox where developers can inspect schemas, enter payloads, execute live API calls (`Try it out`), and inspect server responses.
   * **ReDoc** (`/redoc`): A clean, publication-grade three-panel technical reference manual ideal for external partner integration.

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│                       OpenAPI Reflection & Rendering Pipeline               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   Python Code & Type Annotations                                            │
│   async def get_expedition(expedition_id: str = Path(pattern=...))          │
│                               │                                             │
│                               ▼ (FastAPI Introspection Engine)              │
│   OpenAPI 3.0 Schema (/openapi.json)                                        │
│   ┌────────────────────────────────────────────────────────┐                │
│   │ "paths": {                                             │                │
│   │   "/api/v1/expeditions/{expedition_id}": {             │                │
│   │     "get": { "parameters": [...], "responses": {...} } │                │
│   │   }                                                    │                │
│   │ }                                                      │                │
│   └───────────────────────────┬────────────────────────────┘                │
│                               │                                             │
│               ┌───────────────┴───────────────┐                             │
│               ▼                               ▼                             │
│   Swagger UI (/docs)                  ReDoc UI (/redoc)                     │
│   * Interactive "Try it out"          * 3-panel documentation layout        │
│   * Live cURL generator               * Searchable navigation tree          │
│   * Payload sandboxing                * Publication-grade API spec          │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 💉 5. The Dependency Injection System (`Depends`)

In software engineering, **Dependency Injection (DI)** is a design pattern where an object or function receives other dependencies rather than hardcoding them internally.

In traditional frameworks, developers rely on global variables, middleware monkey-patching, or complex decorators. FastAPI introduces a **type-safe, hierarchical Dependency Injection system** using `Depends()`.

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│                     FastAPI Dependency Injection Hierarchy                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│                            Incoming HTTP Request                            │
│                                      │                                      │
│                                      ▼                                      │
│                      ┌───────────────────────────────┐                      │
│                      │ verify_sar_admin_key(Depends) │                      │
│                      │ Extracts 'X-API-Key' Header   │                      │
│                      └───────────────┬───────────────┘                      │
│                                      │ Passes Validation                    │
│                                      ▼                                      │
│                      ┌───────────────────────────────┐                      │
│                      │ PaginationParams(Depends)     │                      │
│                      │ Extracts & validates skip/limit│                      │
│                      └───────────────┬───────────────┘                      │
│                                      │ Injected as Clean Typed Object       │
│                                      ▼                                      │
│                      ┌───────────────────────────────┐                      │
│                      │ Endpoint Route Handler        │                      │
│                      │ async def delete_expedition() │                      │
│                      └───────────────────────────────┘                      │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Real Implementation from `fastapi_intro_lab.py`:
```python
ADMIN_API_KEY = "kashmir-sar-rescue-key-2026"

def verify_sar_admin_key(
    x_api_key: Optional[str] = Header(None, alias="X-API-Key")
) -> str:
    if not x_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "UNAUTHORIZED_ADMIN_ACTION", "message": "Missing 'X-API-Key' header."}
        )
    if x_api_key != ADMIN_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": "FORBIDDEN_CREDENTIALS", "message": "Invalid SAR admin key."}
        )
    return x_api_key

# Route declaration with dependency enforcement:
@app.delete("/api/v1/expeditions/{expedition_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_expedition(
    expedition_id: str = Path(..., pattern=r"^TREK-[0-9]{3}$"),
    _: str = Depends(verify_sar_admin_key)  # <── Injected security guard
):
    del EXPEDITIONS_DB[expedition_id]
    return None
```

### Why FastAPI Dependency Injection is Unmatched:
1. **Shared Logic**: Authentication, database sessions, and query filters are written once and reused across hundreds of routes.
2. **Automatic OpenAPI Integration**: Dependencies that declare headers or queries (such as `Header(alias="X-API-Key")`) are **automatically documented in Swagger UI** as required inputs.
3. **Effortless Mocking in Tests**: In testing, dependencies can be swapped instantly using `app.dependency_overrides[verify_sar_admin_key] = lambda: "test-token"`.

---

## 🔄 6. Complete Request-Response Lifecycle on the Wire

When a client transmits an HTTP request to a FastAPI application, it traverses a finely tuned, asynchronous pipeline:

```text
Client (cURL / Browser / Mobile App)
  │
  │ 1. HTTP Request (POST /api/v1/expeditions)
  ▼
[ Uvicorn ASGI Server ]
  │  * Reads socket buffer via uvloop
  │  * Parses HTTP headers & method via C-based httptools
  │  * Packages connection into ASGI scope dictionary
  ▼
[ Starlette Middleware Stack ]
  │  * CORS validation (Access-Control-Allow-*)
  │  * Security headers / Gzip decompression
  ▼
[ FastAPI Router Resolution ]
  │  * Matches URL path against registered routes
  │  * Extracts path parameters (/api/v1/expeditions/{id})
  ▼
[ Dependency Injection Resolution ]
  │  * Resolves Depends() callables in topological order
  │  * Authenticates headers / Initializes DB connections
  ▼
[ Pydantic v2 Parsing & Validation ]
  │  * Deserializes JSON payload through Rust core
  │  * Checks field types, boundaries, regexes, and model validators
  │  * ❌ If validation fails: Immediately short-circuits with HTTP 422 JSON
  ▼
[ Route Handler Execution (async def) ]
  │  * Executes business logic
  │  * Interacts with database / caches / SAR telemetry
  ▼
[ Pydantic Response Serialization ]
  │  * Filters payload through response_model schema
  │  * Strips internal / private fields safely
  ▼
[ Starlette JSONResponse / StreamingResponse ]
  │  * Encodes payload to UTF-8 JSON bytes
  │  * Attaches Content-Type, Content-Length, Status Code
  ▼
[ Uvicorn ASGI Server ]
  │  * Flushes bytes through TCP socket to client
  ▼
Client Receives HTTP 201 Created Response
```

---

## 🛠️ 7. Hands-on Implementation: Kashmir Mountain Operations API

In this lab, we implement an enterprise-grade backend service:
* **Script**: `fastapi_intro_lab.py` (and entrypoint `main.py`)
* **Test Suite**: `test_fastapi_lab.py`
* **Default Port**: `8000`

### Complete Endpoint Reference Table:

| Method | Path | Summary | Auth Required | Success Status | Error Codes |
|---|---|---|:---:|:---:|:---:|
| `GET` | `/` | API Root & Ecosystem Discovery | No | `200 OK` | — |
| `GET` | `/health` | Kubernetes / Cloud Health Probe | No | `200 OK` | — |
| `GET` | `/docs` | Interactive Swagger UI Sandbox | No | `200 OK` | — |
| `GET` | `/redoc` | Interactive ReDoc Technical Manual | No | `200 OK` | — |
| `GET` | `/openapi.json` | Machine-Readable OpenAPI 3.0 Schema | No | `200 OK` | — |
| `GET` | `/api/v1/expeditions` | List Expeditions (Pagination & Filter) | No | `200 OK` | `422` (invalid query) |
| `GET` | `/api/v1/expeditions/{id}` | Retrieve Single Expedition (Regex ID) | No | `200 OK` | `404`, `422` (bad regex) |
| `POST` | `/api/v1/expeditions` | Register New Expedition | No | `201 Created` | `422` (schema violation) |
| `PUT` | `/api/v1/expeditions/{id}` | Idempotent Full Record Update | No | `200 OK` | `404`, `422` |
| `PATCH`| `/api/v1/expeditions/{id}/status`| Partial State Transition | No | `200 OK` | `404`, `422` |
| `DELETE`| `/api/v1/expeditions/{id}`| Privileged Deletion of Record | **Yes (`X-API-Key`)** | `204 No Content`| `401`, `403`, `404` |
| `GET` | `/api/v1/telemetry/gondola-stream`| Live SSE Cable Car Telemetry Stream | No | `200 OK (Stream)` | — |

---

## 🧪 8. Step-by-Step Hands-on Verification Guide

Follow these live verification steps to test every architectural component.

### Step 1: Launch the FastAPI Application
```bash
# Option A: Run directly with Python
python fastapi_intro_lab.py

# Option B: Run with Uvicorn ASGI Server
uvicorn main:app --reload --port 8000
```

---

### Step 2: Run the Automated Verification Suite
In a separate terminal, execute our automated test suite covering all 21 verification assertions:
```bash
python test_fastapi_lab.py
```
**Expected Output:**
```text
================================================================================
🧪 RUNNING AUTOMATED VERIFICATION SUITE FOR LAB 76 (FASTAPI)
================================================================================
  [PASS] 1. GET / (Root Discovery Endpoint) 
  [PASS] 2. GET /health (Kubernetes / Cloud Probe) 
  [PASS] 3. GET /openapi.json (Automated OpenAPI Spec Generation) 
  [PASS] 4a. GET /docs (Swagger UI HTML rendering) 
  [PASS] 4b. GET /redoc (ReDoc UI HTML rendering) 
  [PASS] 5a. GET /api/v1/expeditions (Default pagination) 
  [PASS] 6. GET /api/v1/expeditions?difficulty=EXTREME (Enum Query Filtering) 
  [PASS] 7. GET /api/v1/expeditions?q=Lakes (Search Query) 
  [PASS] 8. GET /api/v1/expeditions/TREK-001 (Valid Path Param Regex) 
  [PASS] 9. GET /api/v1/expeditions/TREK-999 (Resource Not Found Handling) 
  [PASS] 10. GET /api/v1/expeditions/INVALID_TREK_ID (Path Regex 422 Validation Error) 
  [PASS] 11. POST /api/v1/expeditions (Pydantic v2 Creation & 201 Created) 
  [PASS] 12a. POST /api/v1/expeditions (Pydantic Missing Fields 422 Error) 
  [PASS] 12b. POST /api/v1/expeditions (Pydantic Custom Model Validator 422 Error) 
  [PASS] 13. PUT /api/v1/expeditions/{id} (Full Resource Idempotent Update) 
  [PASS] 14. PATCH /api/v1/expeditions/{id}/status (Partial State Transition) 
  [PASS] 15a. DELETE /api/v1/expeditions/{id} (Missing X-API-Key -> 401 Unauthorized) 
  [PASS] 15b. DELETE /api/v1/expeditions/{id} (Invalid X-API-Key -> 403 Forbidden) 
  [PASS] 15c. DELETE /api/v1/expeditions/{id} (Valid X-API-Key -> 204 No Content) 
  [PASS] 15d. Verification: Deleted item returns 404 
  [PASS] 16. GET /api/v1/telemetry/gondola-stream (Starlette StreamingResponse SSE) 
================================================================================
🎉 VERIFICATION COMPLETE: 21/21 tests passed (100% SUCCESS)
================================================================================
```

---

### Step 3: Interactive Live Testing with cURL

#### Test 1 — Root Discovery & Ecosystem Index
```bash
curl -s http://127.0.0.1:8000/
```
**Response (HTTP 200 OK):**
```json
{
  "engine": "FastAPI 0.110+ (Starlette ASGI + Pydantic v2)",
  "service": "Kashmir Mountain Operations & Expeditions Hub",
  "lab": "Lab 76 — FastAPI Architecture & Internal Engine",
  "engineer": "Danish Nazir (@Danish20699)",
  "endpoints": {
    "interactive_swagger_ui": "http://127.0.0.1:8000/docs",
    "interactive_redoc_ui": "http://127.0.0.1:8000/redoc",
    "openapi_json_schema": "http://127.0.0.1:8000/openapi.json",
    "health_check": "http://127.0.0.1:8000/health",
    "expeditions_collection": "http://127.0.0.1:8000/api/v1/expeditions",
    "live_gondola_stream": "http://127.0.0.1:8000/api/v1/telemetry/gondola-stream"
  },
  "status": "OPERATIONAL_ONLINE",
  "timestamp": "2026-10-14T17:05:00Z"
}
```

---

#### Test 2 — Query Filtering with Enum Validation
```bash
curl -s "http://127.0.0.1:8000/api/v1/expeditions?difficulty=EXTREME"
```
**Response (HTTP 200 OK):**
```json
[
  {
    "name": "Kolahoi Glacier North Face Expedition",
    "base_camp": "Lidderwat Alpine Staging",
    "difficulty": "EXTREME",
    "max_altitude_meters": 5425,
    "duration_days": 9,
    "price_inr": 34000.0,
    "max_participants": 8,
    "emergency_beacon_code": "KMR-KH003",
    "coordinates": {
      "latitude": 34.175,
      "longitude": 75.318,
      "elevation_meters": 3050
    },
    "id": "TREK-003",
    "status": "ACTIVE",
    "registered_participants": 6,
    "created_at": "2026-03-10T11:00:00Z"
  }
]
```

---

#### Test 3 — Path Parameter Regex Validation Failure (HTTP 422)
Attempt to pass an invalid expedition ID format (violating `^TREK-[0-9]{3}$`):
```bash
curl -i -s "http://127.0.0.1:8000/api/v1/expeditions/INVALID_ID"
```
**Wire Output:**
```text
HTTP/1.1 422 Unprocessable Entity
date: Wed, 14 Oct 2026 17:05:10 GMT
server: uvicorn
content-length: 161
content-type: application/json

{"detail":[{"type":"string_pattern_mismatch","loc":["path","expedition_id"],"msg":"String should match pattern '^TREK-[0-9]{3}$'","input":"INVALID_ID"}]}
```
> **Observation:** Notice that FastAPI trapped the invalid path parameter and returned a 422 error **without executing a single line of database lookup logic**!

---

#### Test 4 — Register New Expedition (HTTP 201 Created)
```bash
curl -i -s -X POST http://127.0.0.1:8000/api/v1/expeditions \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Gangabal High Altitude Glacier Trek",
    "base_camp": "Naranag Staging Area",
    "difficulty": "DIFFICULT",
    "max_altitude_meters": 3800,
    "duration_days": 5,
    "price_inr": 14500.0,
    "max_participants": 12,
    "emergency_beacon_code": "KMR-GB005",
    "coordinates": {
      "latitude": 34.2541,
      "longitude": 74.9812,
      "elevation_meters": 2240
    }
  }'
```
**Wire Output:**
```text
HTTP/1.1 201 Created
date: Wed, 14 Oct 2026 17:05:15 GMT
server: uvicorn
content-length: 374
content-type: application/json

{"name":"Gangabal High Altitude Glacier Trek","base_camp":"Naranag Staging Area","difficulty":"DIFFICULT","max_altitude_meters":3800,"duration_days":5,"price_inr":14500.0,"max_participants":12,"emergency_beacon_code":"KMR-GB005","coordinates":{"latitude":34.2541,"longitude":74.9812,"elevation_meters":2240},"id":"TREK-005","status":"SCHEDULED","registered_participants":0,"created_at":"2026-10-14T17:05:15Z"}
```

---

#### Test 5 — Cross-Field Validation Failure (HTTP 422)
Attempt to register an `EXTREME` expedition with `max_altitude_meters: 2500` (violating our `@model_validator` requiring >= 4000m):
```bash
curl -i -s -X POST http://127.0.0.1:8000/api/v1/expeditions \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Invalid Lowland Extreme Expedition",
    "base_camp": "Aru Valley",
    "difficulty": "EXTREME",
    "max_altitude_meters": 2500,
    "duration_days": 4,
    "price_inr": 12000.0,
    "max_participants": 10,
    "emergency_beacon_code": "KMR-EX006",
    "coordinates": {
      "latitude": 34.0864,
      "longitude": 75.2638,
      "elevation_meters": 2415
    }
  }'
```
**Wire Output:**
```text
HTTP/1.1 422 Unprocessable Entity
content-type: application/json

{"detail":[{"type":"value_error","loc":["body"],"msg":"Value error, Expeditions rated EXTREME must attain an altitude of at least 4000m (provided: 2500m)."}]}
```

---

#### Test 6 — Dependency Injection Security: Unauthorized Deletion (HTTP 401 & 403)
Attempt deletion without the required `X-API-Key` administrative header:
```bash
curl -i -s -X DELETE http://127.0.0.1:8000/api/v1/expeditions/TREK-001
```
**Wire Output:**
```text
HTTP/1.1 401 Unauthorized
content-type: application/json

{"detail":{"error":"UNAUTHORIZED_ADMIN_ACTION","message":"Missing 'X-API-Key' authentication header.","hint":"Provide 'X-API-Key: kashmir-sar-rescue-key-2026'"}}
```

Now supply the valid administrative key:
```bash
curl -i -s -X DELETE http://127.0.0.1:8000/api/v1/expeditions/TREK-001 \
  -H "X-API-Key: kashmir-sar-rescue-key-2026"
```
**Wire Output:**
```text
HTTP/1.1 204 No Content
date: Wed, 14 Oct 2026 17:05:25 GMT
server: uvicorn
```
> **Observation:** The endpoint returned HTTP 204 No Content with a completely empty body, strictly following REST standards!

---

#### Test 7 — Real-Time Cable Car Telemetry Streaming (SSE)
Connect to the live cable car telemetry stream using `curl -N` (no buffering):
```bash
curl -N http://127.0.0.1:8000/api/v1/telemetry/gondola-stream
```
**Wire Output (Pushed Live Every 500ms):**
```text
HTTP/1.1 200 OK
content-type: text/event-stream; charset=utf-8
cache-control: no-cache
connection: keep-alive

event: telemetry
data: {"event":"GONDOLA_PHASE2_PING","tick":1,"cable_car_id":"CAR-042","altitude_meters":2690,"wind_speed_kmh":26.6,"cable_tension_kilonewtons":142.8,"status":"NOMINAL_ASCENT"}

event: telemetry
data: {"event":"GONDOLA_PHASE2_PING","tick":2,"cable_car_id":"CAR-042","altitude_meters":2950,"wind_speed_kmh":28.7,"cable_tension_kilonewtons":143.6,"status":"NOMINAL_ASCENT"}

event: telemetry
data: {"event":"GONDOLA_PHASE2_PING","tick":6,"cable_car_id":"CAR-042","altitude_meters":3980,"wind_speed_kmh":37.1,"cable_tension_kilonewtons":146.8,"status":"SUMMIT_DOCK_REACHED"}
```

---

## ⚡ 9. Performance Benchmarks: FastAPI vs The World

FastAPI is recognized as one of the fastest web frameworks in existence, competing directly with **Node.js (Express)** and **Go (Gin)**:

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│                       Requests Per Second (TechEmpower Benchmark)           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   FastAPI (Uvicorn + uvloop):   ████████████████████████ 32,500 req/s       │
│   Node.js (Express):            ████████████████ 21,000 req/s               │
│   Flask (Gunicorn sync):        ████ 4,200 req/s                            │
│   Django (Gunicorn sync):       ███ 3,100 req/s                             │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### The Secret to FastAPI's Concurrency: `def` vs `async def`
In FastAPI, how you define your path operation functions affects how the server executes them:

1. **`async def` Functions**:
   * Executed directly on the **ASGI Event Loop**.
   * Ideal for non-blocking I/O operations (e.g. `await database.fetch_all()`, `await httpx_client.get()`, `await asyncio.sleep()`).
   * **⚠️ Critical Rule**: You must NEVER call blocking synchronous code (like `time.sleep()`, synchronous `requests.get()`, or standard blocking database drivers) inside an `async def`. Doing so freezes the entire event loop for all users!

2. **Standard `def` Functions**:
   * FastAPI automatically detects synchronous functions and offloads them to an internal **threadpool** (`anyio.to_thread.run_sync`).
   * This prevents blocking operations from freezing the event loop, ensuring that legacy synchronous libraries can still be used safely.

---

## ⚠️ 10. Common Pitfalls & Anti-Patterns

| # | Anti-Pattern | Why It's Dangerous | Correct Architectural Solution |
|---|---|---|---|
| **1** | **Calling blocking sync code in `async def`** | `time.sleep(5)` or `requests.get()` freezes the entire single-threaded event loop for all concurrent users. | Use `await asyncio.sleep(5)` or `await httpx.AsyncClient().get()`, OR declare the function as standard `def`. |
| **2** | **Omitting `response_model`** | Returning raw database models or dictionaries can accidentally leak hashed passwords, secret tokens, or internal database keys. | Always declare `response_model=TrekExpeditionResponse` to filter and validate output payloads strictly. |
| **3** | **Mutating Default Dependency Arguments** | Declaring `def my_dep(data: list = []): data.append(1)` persists mutated state across all subsequent requests. | Use immutable defaults: `data: Optional[List] = None`, and initialize inside the dependency. |
| **4** | **Using Pydantic v1 Syntax in v2** | Calling `.dict()` or using `@validator` triggers deprecation warnings and misses out on Rust-core optimizations. | Use Pydantic v2 syntax: `model_dump()`, `model_validate()`, `@field_validator`, and `@model_validator`. |
| **5** | **Manually Constructing HTTP Error Dictionaries** | Returning `{"error": "not found"}` with a `200 OK` status code breaks REST standards and confuses API clients. | Always raise `HTTPException(status_code=404, detail=...)` so proper HTTP headers and schemas are generated. |

---

## 🗺️ 11. Next Step in Series

With Lab 76 completed, you understand the internal architecture of FastAPI, the power of ASGI and Starlette, Pydantic v2 validation mechanics, and automated OpenAPI documentation.

In **Lab 77 — Building Your First Production FastAPI Microservice (`77-fastapi-hello-world.md`)**, we will:
* Build a standalone, containerized microservice running on Docker.
* Implement structured logging with JSON formatting for cloud aggregators (Datadog, Loki).
* Configure environment variables and secrets management via `pydantic-settings`.
* Add Kubernetes readiness and liveness probes.

---

## 👨‍💻 Author & Attribution

| Field | Value |
|---|---|
| **Engineer** | Danish Nazir |
| **GitHub** | [@Danish20699](https://github.com/Danish20699) |
| **Track** | MLOps / DevOps Engineering (APR26) |
| **Module** | 13 — FastAPI Backend & Backend Engineering |
| **Lab** | 76 — FastAPI Architecture, Pydantic v2 & OpenAPI Engine |
| **Domain** | Kashmir Mountain Operations & Himalayan Expeditions API |
| **Default Port** | 8000 |
| **Frameworks** | FastAPI 0.110+, Starlette, Pydantic v2, Uvicorn |
| **License** | MIT License |
