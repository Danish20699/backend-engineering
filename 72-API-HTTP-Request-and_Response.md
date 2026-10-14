# Lab 72: API HTTP Request and Response Deep Dive

![Backend Engineering](https://img.shields.io/badge/Backend-Engineering-00599C?style=for-the-badge&logo=backend&logoColor=white)
![HTTP Protocol](https://img.shields.io/badge/Protocol-HTTP%2F1.1%20%7C%20HTTP%2F2-blue?style=for-the-badge)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100%2B-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![Status](https://img.shields.io/badge/Status-Completed-success?style=for-the-badge)

---

## 📌 1. Lab Overview & Real-World Context

Every web API, mobile application, microservice, and machine learning model serving endpoint operates on a universal foundation: the **HTTP Request-Response Protocol**. 

When a frontend client (like a browser or React app) or another microservice communicates with a backend (such as FastAPI, Flask, or Node.js), communication occurs via discrete, structured messages exchanged over a TCP/IP network:
1. The **HTTP Request**: Sent by the client to ask the server to perform an action or return data.
2. The **HTTP Response**: Returned by the server to convey the outcome of the request along with status information and requested payloads.

Understanding the wire-level mechanics of requests and responses is essential for backend engineering, debugging API failures (such as CORS errors, 422 validation errors, and 415 media type errors), and building high-performance microservices.

---

## 🔍 2. Wire-Level Anatomy of an HTTP Request

At the network transport level, an HTTP/1.1 request is an ASCII text stream composed of four distinct sections separated by standard carriage return line feed characters (`\r\n`):

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│ 1. Request Line (Method + Path + Protocol Version)                          │
│    POST /api/v1/packages HTTP/1.1\r\n                                       │
├─────────────────────────────────────────────────────────────────────────────┤
│ 2. Request Headers (Key-Value Metadata)                                     │
│    Host: api.travelkashmir.com\r\n                                          │
│    User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64)\r\n               │
│    Accept: application/json\r\n                                             │
│    Content-Type: application/json; charset=utf-8\r\n                        │
│    Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...\r\n        │
│    Content-Length: 78\r\n                                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│ 3. Empty Line (Protocol Boundary Separator)                                 │
│    \r\n                                                                     │
├─────────────────────────────────────────────────────────────────────────────┤
│ 4. Request Body / Payload (Optional Data)                                   │
│    {"name": "Gulmarg Skiing Adventure", "price": 45000, "duration": "5D"}  │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Breakdown of Request Components:

#### A. The Request Line
Format: `<METHOD> <REQUEST-TARGET> <HTTP-VERSION>\r\n`
* **HTTP Method**: Indicates the action (`GET`, `POST`, `PUT`, `PATCH`, `DELETE`).
* **Request Target**: The path and optional query parameters (`/api/v1/packages?category=winter`).
* **Protocol Version**: The HTTP version used by the client (`HTTP/1.1` or `HTTP/2`).

#### B. Essential Request Headers
Headers provide critical metadata to tell the server how to interpret and authenticate the request:

| Header Name | Category | Purpose | Example |
| :--- | :--- | :--- | :--- |
| `Host` | Routing | Mandatory in HTTP/1.1; specifies target server domain and port. | `Host: api.kashmir.com:8000` |
| `Content-Type` | Representation | Tells the server the media format of the request body. | `Content-Type: application/json` |
| `Accept` | Content Negotiation | Tells the server what format the client is capable of parsing. | `Accept: application/json` |
| `Authorization` | Security | Passes credentials or tokens for authentication. | `Authorization: Bearer <JWT_TOKEN>` |
| `User-Agent` | Client Info | Identifies the client software, OS, and browser runtime. | `User-Agent: cURL/8.4.0` |
| `Content-Length` | Framing | Specifies the exact size of the request body in bytes. | `Content-Length: 78` |
| `Origin` | Security | Sent in CORS requests to specify the origin domain of the client. | `Origin: http://localhost:3000` |

#### C. The Empty Line (`\r\n`)
* Critical protocol delimiter. It tells the web server's parser that all headers have been read and any subsequent bytes belong to the request body.

#### D. The Request Body (Payload)
* Present in methods like `POST`, `PUT`, and `PATCH`.
* Contains the actual data being sent to the server (typically serialized JSON, form-data, or binary uploads).

---

## 📨 3. Wire-Level Anatomy of an HTTP Response

Once the server processes the request through its business logic, database queries, or ML models, it formats an HTTP Response:

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│ 1. Status Line (Protocol Version + Status Code + Reason Phrase)             │
│    HTTP/1.1 201 Created\r\n                                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│ 2. Response Headers (Server Metadata & Controls)                            │
│    Date: Wed, 14 Oct 2026 06:15:00 GMT\r\n                                  │
│    Server: uvicorn\r\n                                                      │
│    Content-Type: application/json; charset=utf-8\r\n                        │
│    Content-Length: 104\r\n                                                  │
│    Access-Control-Allow-Origin: *\r\n                                       │
│    Cache-Control: no-cache, no-store, must-revalidate\r\n                   │
│    ETag: "33a64df551425fcc55e4d42a148795d9f25f89d4"\r\n                    │
├─────────────────────────────────────────────────────────────────────────────┤
│ 3. Empty Line (Protocol Boundary Separator)                                 │
│    \r\n                                                                     │
├─────────────────────────────────────────────────────────────────────────────┤
│ 4. Response Body / Payload (Result Data)                                    │
│    {"id": 101, "name": "Gulmarg Skiing Adventure", "status": "active"}     │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Breakdown of Response Components:

#### A. The Status Line
Format: `<HTTP-VERSION> <STATUS-CODE> <REASON-PHRASE>\r\n`
* **HTTP Version**: `HTTP/1.1` or `HTTP/2`.
* **Status Code**: A 3-digit integer conveying the outcome:
  * `200 OK`: Request succeeded.
  * `201 Created`: Resource successfully created.
  * `400 Bad Request`: Malformed request syntax.
  * `401 Unauthorized`: Authentication required or token invalid.
  * `403 Forbidden`: Authenticated, but lacks permission.
  * `404 Not Found`: Resource does not exist.
  * `422 Unprocessable Entity`: Semantic/validation failure (Pydantic standard).
  * `500 Internal Server Error`: Unhandled backend exception.
* **Reason Phrase**: Human-readable text corresponding to the status code (`OK`, `Created`, `Not Found`).

#### B. Essential Response Headers

| Header Name | Category | Purpose | Example |
| :--- | :--- | :--- | :--- |
| `Content-Type` | Representation | Tells the client how to parse the payload. | `Content-Type: application/json` |
| `Content-Length` | Framing | Byte size of the response body. | `Content-Length: 104` |
| `Server` | Metadata | Software running the application server. | `Server: uvicorn` |
| `Access-Control-Allow-Origin` | Security (CORS) | Permits cross-origin browser requests. | `Access-Control-Allow-Origin: *` |
| `Cache-Control` | Performance | Dictates if and how proxies and browsers can cache responses. | `Cache-Control: public, max-age=3600` |
| `Set-Cookie` | State Management | Sends a cookie or session ID to be stored by the client. | `Set-Cookie: session_id=xyz; HttpOnly; Secure` |

---

## ⚙️ 4. How Things Work Under the Hood: The Full Lifecycle

Here is the exact step-by-step path a message takes from client action to backend execution and back:

```text
 ┌───────────────┐                                                     ┌────────────────┐
 │ Client Browser│                                                     │ FastAPI Server │
 └───────┬───────┘                                                     └────────┬───────┘
         │                                                                      │
         │ 1. Serialize object to JSON: JSON.stringify(data)                   │
         │ 2. Create socket & DNS resolution                                    │
         │ 3. Establish TCP connection (SYN, SYN-ACK, ACK)                      │
         │ 4. Transmit HTTP Request Bytes over network                          │
         │─────────────────────────────────────────────────────────────────────►│
         │                                                                      │
         │                                   5. ASGI Server (Uvicorn) reads     │
         │                                      raw socket bytes into scope     │
         │                                   6. Routing: match path & method    │
         │                                   7. Middleware: CORS & Auth checks  │
         │                                   8. Pydantic validation: validates  │
         │                                      types & required fields         │
         │                                   9. Controller / Handler executes   │
         │                                      (queries DB, runs ML model)     │
         │                                  10. Serialize output to JSON &      │
         │                                      construct HTTP response headers │
         │                                                                      │
         │◄─────────────────────────────────────────────────────────────────────│
         │ 11. Transmit HTTP Response Bytes over network                        │
         │                                                                      │
         │ 12. Client reads Status Line & Headers                              │
         │ 13. Deserializes JSON body: response.json()                         │
         │ 14. Updates UI or triggers downstream event                          │
         ▼                                                                      ▼
```

---

## 💻 5. Hands-On Verification Lab: Raw Request & Response Inspector

To see this working live without any black-box abstractions, we implement a lightweight Python backend server that inspects incoming raw HTTP request lines, headers, and payloads, and replies with standard HTTP response headers:

```python
# request_response_inspector.py
from http.server import HTTPServer, BaseHTTPRequestHandler
import json

class InspectorHandler(BaseHTTPRequestHandler):
    def _set_headers(self, status_code=200):
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Server", "Python-Inspector-Lab72")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()

    def do_GET(self):
        # Extract Request Line details
        print(f"\n[RECEIVED GET REQUEST]")
        print(f"Command (Method): {self.command}")
        print(f"Path: {self.path}")
        print(f"Protocol: {self.request_version}")
        
        # Inspect Headers
        print("--- Headers Received ---")
        for header, val in self.headers.items():
            print(f"{header}: {val}")
        
        self._set_headers(200)
        response_payload = {
            "message": "GET Request processed successfully",
            "method": self.command,
            "path": self.path,
            "received_headers_count": len(self.headers)
        }
        self.wfile.write(json.dumps(response_payload, indent=2).encode("utf-8"))

    def do_POST(self):
        print(f"\n[RECEIVED POST REQUEST]")
        content_length = int(self.headers.get("Content-Length", 0))
        content_type = self.headers.get("Content-Type", "")
        
        # Read request body based on Content-Length
        body_bytes = self.rfile.read(content_length)
        body_str = body_bytes.decode("utf-8")
        
        try:
            parsed_json = json.loads(body_str) if body_str else {}
        except json.JSONDecodeError:
            self._set_headers(400)
            self.wfile.write(json.dumps({"error": "Invalid JSON payload"}).encode("utf-8"))
            return

        self._set_headers(201)
        response_payload = {
            "status": "success",
            "message": "Resource created",
            "contentTypeReceived": content_type,
            "payloadReceived": parsed_json
        }
        self.wfile.write(json.dumps(response_payload, indent=2).encode("utf-8"))

def main(port=8080):
    server = HTTPServer(("0.0.0.0", port), InspectorHandler)
    print(f"Inspector Server listening on http://localhost:{port}")
    server.serve_forever()

if __name__ == "__main__":
    main()
```

---

## 🧪 6. Testing & Wire-Level Header Verification

### Test 1: Testing a GET Request with Verbose cURL (`curl -v`)
```bash
curl -v http://localhost:8080/api/v1/packages?category=trekking
```

#### Verbose Network Output:
```text
*   Trying 127.0.0.1:8080...
* Connected to localhost (127.0.0.1) port 8080
> GET /api/v1/packages?category=trekking HTTP/1.1
> Host: localhost:8080
> User-Agent: curl/8.4.0
> Accept: */*
> 
< HTTP/1.1 200 OK
< Server: Python-Inspector-Lab72
< Content-Type: application/json
< Access-Control-Allow-Origin: *
< Date: Wed, 14 Oct 2026 06:20:00 GMT
< 
{
  "message": "GET Request processed successfully",
  "method": "GET",
  "path": "/api/v1/packages?category=trekking",
  "received_headers_count": 3
}
```

---

### Test 2: Testing a POST Request with JSON Body & Custom Headers
```bash
curl -v -X POST http://localhost:8080/api/v1/packages \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer test_token_mlops_123" \
  -d '{"name": "Sonamarg Glacier Camp", "price": 18000}'
```

#### Verbose Network Output:
```text
> POST /api/v1/packages HTTP/1.1
> Host: localhost:8080
> User-Agent: curl/8.4.0
> Accept: */*
> Content-Type: application/json
> Authorization: Bearer test_token_mlops_123
> Content-Length: 48
> 
< HTTP/1.1 201 Created
< Server: Python-Inspector-Lab72
< Content-Type: application/json
< Access-Control-Allow-Origin: *
< 
{
  "status": "success",
  "message": "Resource created",
  "contentTypeReceived": "application/json",
  "payloadReceived": {
    "name": "Sonamarg Glacier Camp",
    "price": 18000
  }
}
```

---

## ⚠️ 7. Common Pitfalls & Real-World Troubleshooting

| Failure Symptom | Underlying Cause | Fix |
| :--- | :--- | :--- |
| **`415 Unsupported Media Type`** | Client sent a JSON body but omitted `Content-Type: application/json`. | Always include `-H "Content-Type: application/json"` in requests. |
| **`422 Unprocessable Entity`** | Client sent a payload where a required field was missing or had the wrong data type (e.g. string instead of int). | Verify request JSON matches backend Pydantic schema types. |
| **CORS Blocked in Browser** | Backend response did not include `Access-Control-Allow-Origin` matching client origin. | Configure `CORSMiddleware` in FastAPI with allowed origins. |
| **Request Hanging / Timeout** | Client specified a `Content-Length` larger than the actual bytes sent, or server socket failed to read full buffer. | Ensure automated HTTP clients compute byte lengths accurately. |

---

## 🗺️ 8. Next Step in Series

Now that the request and response structures are understood at the wire level:
* ➡️ **Lab 73: `73-API-Request-Methods.md`** &mdash; Deep dive into REST verbs (`GET`, `POST`, `PUT`, `PATCH`, `DELETE`, `OPTIONS`) and the critical concept of **Idempotency**.

---

## 👨‍💻 Author & Attribution
* **Engineer**: Danish
* **Track**: MLOps / DevOps Engineering (APR26)
* **Module**: 13 - FastAPI Backend & Backend Engineering
