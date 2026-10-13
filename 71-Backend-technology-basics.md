# Lab 71: Backend Technology Basics

![Backend Engineering](https://img.shields.io/badge/Backend-Engineering-00599C?style=for-the-badge&logo=backend&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100%2B-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![HTTP/1.1 & HTTP/2](https://img.shields.io/badge/Protocol-HTTP%2F1.1%20%7C%20HTTP%2F2-blue?style=for-the-badge)
![Status](https://img.shields.io/badge/Status-Completed-success?style=for-the-badge)

---

## 📌 1. Lab Overview & Real-World Context

In software systems and modern MLOps pipelines, the **Backend** acts as the central engine responsible for business logic, data persistence, security, and machine learning model serving. While the frontend provides a user interface (UI), the backend provides the **Application Programming Interfaces (APIs)** and infrastructure that make applications functional, scalable, and secure.

### Why Backend Engineering Matters for DevOps & MLOps Engineers:
1. **Model Serving & Inference**: Machine learning models (PyTorch, TensorFlow, Scikit-learn) do not live in isolation; they are packaged behind backend microservices (such as **FastAPI**) that accept input data and return predictions.
2. **System Scalability**: Backend architectures determine how many concurrent users or requests a system can handle through load balancing, caching, and asynchronous processing.
3. **Data Integrity & Security**: The backend guards the database, validates incoming payloads (via Pydantic/schemas), enforces authentication, and prevents unauthorized data manipulation.

---

## 🏗️ 2. The Client-Server Model & 3-Tier Architecture

At the heart of the internet is the **Client-Server Model**: a distributed application structure that partitions tasks or workloads between service providers (**servers**) and service requesters (**clients**).

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│                             CLIENT TIER                                     │
│     Web Browser (React/Vue), Mobile App (iOS/Android), cURL, Postman        │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
                         HTTP Request  │  HTTP Response
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         APPLICATION / LOGIC TIER                            │
│  ┌─────────────────────────┐             ┌───────────────────────────────┐  │
│  │ Web Server / Reverse    │────────────►│ Application / ASGI Server     │  │
│  │ Proxy (Nginx, Caddy)    │             │ (FastAPI + Uvicorn, Python)   │  │
│  └─────────────────────────┘             └───────────────┬───────────────┘  │
└──────────────────────────────────────────────────────────┼──────────────────┘
                                                           │
                                             Read / Write  │  Query Results
                                                           ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                            DATA / PERSISTENCE TIER                          │
│     Relational DB (PostgreSQL, MySQL)  │  In-Memory Cache (Redis, Memcached)│
└─────────────────────────────────────────────────────────────────────────────┘
```

### The Three Tiers:
* **Presentation Tier (Client)**: Translates user actions into network requests and renders the response data into visual layouts.
* **Logic Tier (Application Server)**: Evaluates business logic, performs mathematical or ML computations, authenticates credentials, and interacts with databases.
* **Data Tier (Storage & Cache)**: Stores persistent application state, transactions, logs, and indexes.

---

## 🌐 3. Web Protocols & Anatomy of a URL

Clients and servers communicate across the Internet using standardized protocols, predominantly **HTTP (Hypertext Transfer Protocol)** and **HTTPS (HTTP Secure over TLS/SSL)**.

### Anatomy of a Uniform Resource Locator (URL)

```text
      Scheme      Domain / Host (Authority)       Port       Path             Query String        Fragment
      ┌────┐     ┌────────────────────────┐      ┌────┐    ┌───────┐    ┌──────────────────────┐    ┌──┐
      https : // api.travelkashmir.com     :      8000  /  packages  ?   category=trekking&page=1   #   faq
```

| Component | Description | Example |
| :--- | :--- | :--- |
| **Scheme / Protocol** | Dictates the rules and encryption mechanism used for communication. | `https://` (encrypted), `http://` (unencrypted) |
| **Domain / Host** | Identifies the physical server, virtual host, or IP address hosting the resource. | `api.travelkashmir.com` or `192.168.56.101` |
| **Port** | The specific network socket port where the target service listens. | `:80` (HTTP default), `:443` (HTTPS default), `:8000`, `:8085` |
| **Path** | The hierarchical path to the specific endpoint or resource. | `/packages` or `/api/v1/predict` |
| **Query Parameters** | Key-value pairs separated by `&` used for filtering, searching, or pagination. | `?category=trekking&limit=10` |
| **Fragment** | An internal anchor inside the document or client application (not sent to the server). | `#faq` |

---

## 🔄 4. The HTTP Request-Response Lifecycle

Every interaction over HTTP follows an atomic, stateless request-response lifecycle:

```text
Client                                                              Server
  │                                                                   │
  ├────────────── 1. DNS Resolution (Domain -> IP) ──────────────────►│
  ├────────────── 2. TCP 3-Way Handshake (SYN, SYN-ACK, ACK) ────────►│
  ├────────────── 3. TLS / SSL Handshake (if HTTPS) ─────────────────►│
  │                                                                   │
  ├────────────── 4. HTTP Request (Method, Path, Headers, Body) ─────►│
  │                                                                   │ ──► [Route Handler]
  │                                                                   │ ──► [Input Validation]
  │                                                                   │ ──► [DB Query / Logic]
  │                                                                   │ ──► [Format JSON Output]
  │                                                                   │
  │◄───────────── 5. HTTP Response (Status Code, Headers, Payload) ───┤
  │                                                                   │
  └────────────── 6. Connection Keep-Alive or Termination ────────────┘
```

### Components of an HTTP Request:
* **HTTP Method / Verb**: Specifies the desired action (`GET`, `POST`, `PUT`, `PATCH`, `DELETE`).
* **Path**: Target resource URI (`/api/v1/items`).
* **Headers**: Key-value metadata describing client capabilities, encoding, authentication, and content format.
  * `Content-Type: application/json`
  * `Authorization: Bearer eyJhbGciOi...`
  * `User-Agent: Mozilla/5.0...`
* **Body / Payload**: The raw data sent to the server (common in `POST`, `PUT`, `PATCH` operations).

### Components of an HTTP Response:
* **Status Line**: HTTP version + Status Code (`HTTP/1.1 200 OK`).
* **Headers**: Server metadata, caching directives, cookie setting, and content type.
  * `Content-Type: application/json`
  * `Server: uvicorn`
* **Body**: The returned representation of the resource (typically JSON).

---

## ⚙️ 5. Server Architecture: Web Server vs. App Server vs. ASGI

In production backend engineering, a distinction is made between the different server roles:

```text
Internet ──► [ Reverse Proxy: Nginx ] ──► [ ASGI Server: Uvicorn ] ──► [ Framework: FastAPI ]
              • SSL Termination             • Handles HTTP/1.1 & WebSockets   • Route Handlers
              • Static Assets               • Async Event Loop (uvloop)       • Pydantic Validation
              • Rate Limiting               • Manages Worker Processes        • Business Logic
```

| Server Type | Examples | Primary Responsibility |
| :--- | :--- | :--- |
| **Web Server / Reverse Proxy** | Nginx, Apache HTTP Server, Caddy | SSL/TLS encryption, static asset caching, load balancing, request buffering. |
| **WSGI Server** (Legacy Python) | Gunicorn, uWSGI | Synchronous, one-thread/process-per-request gateway (Flask, Django). |
| **ASGI Server** (Modern Python) | Uvicorn, Hypercorn, Daphne | Asynchronous Server Gateway Interface; handles concurrent async connections natively. |
| **Application Framework** | FastAPI, Flask, Express.js | Defines business logic, data models, routes, and responses. |

---

## ⚡ 6. Synchronous vs. Asynchronous Execution

### Synchronous (Blocking I/O):
In traditional synchronous frameworks (like Flask or classic PHP), each request blocks the worker thread while waiting for a database query or external API call. To handle 100 concurrent slow queries, the server needs 100 separate threads/processes, leading to high RAM consumption and context-switching overhead.

### Asynchronous (Non-Blocking I/O with `async` / `await`):
FastAPI is built natively on Python's `asyncio` event loop:
* When a route waits for an I/O operation (e.g., `await db.fetch()`), the single worker thread yields execution back to the event loop.
* The event loop immediately processes other incoming requests while waiting for the database to reply.
* This allows a single FastAPI worker process to handle thousands of concurrent connections with minimal memory footprint.

---

## 🛡️ 7. Core Backend Engineering Principles

1. **Statelessness**: REST APIs are stateless. Each request must contain all the information necessary to understand and complete the request without relying on stored session context on the server.
2. **Data Validation & Typing**: Always validate client input before processing. In FastAPI, **Pydantic models** enforce strict typing and automatically reject malformed requests with `422 Unprocessable Entity`.
3. **Idempotency**: An HTTP method is idempotent if making the same request multiple times produces the identical side-effect on the server (`GET`, `PUT`, `DELETE` are idempotent; `POST` is not).
4. **Security & CORS (Cross-Origin Resource Sharing)**: Browsers enforce the Same-Origin Policy. The backend must configure CORS headers (`Access-Control-Allow-Origin`) to permit trusted frontend domains to access the API.

---

## 💻 8. Practical Hands-On Verification: Minimal Backend Server

Here is a minimal, production-grade Python backend verification using standard Python libraries to demonstrate the raw HTTP request/response cycle without third-party dependencies:

```python
# test_server.py
from http.server import HTTPServer, BaseHTTPRequestHandler
import json

class SimpleBackendHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/health":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            response = {"status": "healthy", "service": "backend-core-lab-71"}
            self.wfile.write(json.dumps(response).encode("utf-8"))
        else:
            self.send_response(404)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": "Resource not found"}).encode("utf-8"))

def run(server_class=HTTPServer, handler_class=SimpleBackendHandler, port=8000):
    server_address = ('', port)
    httpd = server_class(server_address, handler_class)
    print(f"Backend Server running on port {port}...")
    httpd.serve_forever()

if __name__ == '__main__':
    run()
```

### Inspecting Request & Response with cURL:
```bash
# Test the endpoint with verbose headers
curl -v http://localhost:8000/health
```

#### Expected Protocol Output:
```text
> GET /health HTTP/1.1
> Host: localhost:8000
> User-Agent: curl/7.88.1
> Accept: */*
> 
< HTTP/1.1 200 OK
< Server: BaseHTTP/0.6 Python/3.10.12
< Content-Type: application/json
< 
{"status": "healthy", "service": "backend-core-lab-71"}
```

---

## 🗺️ 9. Roadmap: Backend Engineering & FastAPI Series

```text
[Lab 71] Backend Technology Basics  ◄── (You Are Here)
   │
   ▼
[Lab 72] API HTTP Request and Response Deep Dive
   │
   ▼
[Lab 73] API Request Methods (GET, POST, PUT, PATCH, DELETE)
   │
   ▼
[Lab 74] HTTP Status Codes & Error Handling
   │
   ▼
[Lab 75] API Architecture Types (REST, GraphQL, gRPC, WebSockets)
   │
   ▼
[Lab 76] FastAPI Framework Introduction
   │
   ▼
[Lab 77] FastAPI Hello World & Swagger Documentation
```

---

## 👨‍💻 Author & Attribution
* **Engineer**: Danish
* **Track**: MLOps / DevOps Engineering (APR26)
* **Module**: 13 - FastAPI Backend & Backend Engineering
