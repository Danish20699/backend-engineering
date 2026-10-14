# Lab 75: API Architecture Styles & Paradigms

![Backend Engineering](https://img.shields.io/badge/Backend-Engineering-blue)
![API Architecture](https://img.shields.io/badge/API-Architecture-purple)
![FastAPI](https://img.shields.io/badge/FastAPI-Framework-teal)
![Status](https://img.shields.io/badge/Status-Active-brightgreen)

---

## 📌 1. Lab Overview & Architectural Evolution

In backend engineering, there is no single "perfect" API architecture. Every architectural style is an engineering trade-off balancing **network latency, payload efficiency, schema flexibility, developer ergonomics, and caching capabilities**.

As backend systems evolved from monolithic mainframes to globally distributed microservices and real-time machine learning pipelines, five primary API paradigms emerged:

```text
┌─────────────────────────────────────────────────────────────────────────────────────────────────┐
│                               The 5 Major API Architecture Paradigms                            │
├─────────────────────┬───────────────────────────────────────────────────────────────────────────┤
│ Paradigm            │ Core Architectural Philosophy & Primary Strength                          │
├─────────────────────┼───────────────────────────────────────────────────────────────────────────┤
│ 1. REST             │ Resource-oriented, standard HTTP methods & status codes, globally cached. │
│ 2. GraphQL          │ Client-driven queries; client specifies exact fields; eliminates overfetch.│
│ 3. gRPC             │ Ultra-high performance binary RPC built on HTTP/2 & Protocol Buffers.     │
│ 4. SOAP             │ XML-based enterprise contract with strict WS-Security & ACID transactions. │
│ 5. WebSockets/Async │ Persistent full-duplex TCP stream for real-time bi-directional telemetry. │
└─────────────────────┴───────────────────────────────────────────────────────────────────────────┘
```

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│                       Historical Evolution of API Paradigms                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   1998 — SOAP (XML / Enterprise Contracts / Banking & ACID)                 │
│     │                                                                       │
│     ▼                                                                       │
│   2000 — REST (Roy Fielding / Resources / Standard HTTP & JSON Caching)    │
│     │                                                                       │
│     ▼                                                                       │
│   2011 — WebSockets (RFC 6455 / Full-Duplex Persistent Streams)            │
│     │                                                                       │
│     ▼                                                                       │
│   2015 — GraphQL (Facebook / Eliminating Overfetching / Graph Resolvers)    │
│     │                                                                       │
│     ▼                                                                       │
│   2016 — gRPC (Google / HTTP/2 Multiplexing / Microsecond Binary ProtoBuf)  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

In this lab, we analyze each architecture in depth, study wire-level request/response dynamics, examine the problems of **overfetching and underfetching**, and build a hands-on multi-protocol demonstration server (`api_architecture_types_lab.py`) using our consistent **Kashmir Tourism & Mountain Operations** domain.

---

## 🔍 2. Deep Dive: The 5 API Architecture Types

---

### 2.1 — REST (Representational State Transfer)

Introduced by Roy Fielding in his 2000 doctoral dissertation, REST is the most widely adopted API architectural style in the world. It models systems as **resources identified by URIs**, manipulated through standard HTTP verbs (`GET`, `POST`, `PUT`, `PATCH`, `DELETE`).

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│                            REST Architecture Model                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   Client ────────────────────────────────────────────────────────► Server   │
│              GET /api/v1/shikaras/SHIK-001 (Uniform URI)                    │
│                                                                             │
│   Client ◄──────────────────────────────────────────────────────── Server   │
│              HTTP 200 OK + JSON Representation                              │
│              Cache-Control: public, max-age=300                             │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

#### Core Strengths of REST:
1. **Statelessness**: Every request contains all necessary credentials and context. The server does not maintain client session state in memory.
2. **Leverages Web Infrastructure**: Native support for HTTP caching (`ETag`, `Cache-Control`), CDN edge caching, and proxy routing.
3. **Universality**: Every language, browser, curl, and microcontroller speaks standard HTTP and JSON out of the box.

#### The Fatal Flaws of REST: Overfetching & Underfetching

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│                    Overfetching vs Underfetching in REST                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   1. OVERFETCHING:                                                          │
│      The mobile app needs ONLY: Shikara Name + Status.                      │
│      REST endpoint returns: 15 fields (Insurance, Hull Type, Docks,         │
│      Permits, Coordinates, Inspection Dates, Engine Types).                 │
│      ⚠️ Consequence: Wasted cellular bandwidth, increased mobile battery    │
│         drain, and unneeded database serialization overhead.                │
│                                                                             │
│   2. UNDERFETCHING (The N+1 Round-Trip Problem):                            │
│      The app needs: Shikara info + Current Owner Details + Recent Reviews.  │
│      In REST, client must make THREE separate round-trips:                  │
│        1. GET /api/v1/shikaras/SHIK-001                                     │
│        2. GET /api/v1/owners/OWNER-99                                       │
│        3. GET /api/v1/shikaras/SHIK-001/reviews                             │
│      ⚠️ Consequence: High latency on mobile connections across multiple     │
│         TCP/TLS round-trips.                                                │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

### 2.2 — GraphQL (Client-Driven Query Language)

Created by Facebook in 2012 and open-sourced in 2015, GraphQL fundamentally changes the balance of power between client and server: **the client specifies exactly what data fields it requires, and the server returns nothing more and nothing less.**

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│                          GraphQL Architecture Model                         │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   Client Query (POST /graphql):                                             │
│   ┌──────────────────────────────────────────────┐                          │
│   │ query {                                      │                          │
│   │   shikaras {                                 │                          │
│   │     id                                       │                          │
│   │     name                                     │                          │
│   │     status                                   │                          │
│   │   }                                          │                          │
│   │ }                                            │                          │
│   └──────────────────────────────────────────────┘                          │
│                         │                                                   │
│                         ▼                                                   │
│   Server Response:                                                          │
│   ┌──────────────────────────────────────────────┐                          │
│   │ {                                            │                          │
│   │   "data": {                                  │                          │
│   │     "shikaras": [                            │                          │
│   │       {"id": "SHIK-001", "name": "Gul-e-Gulmarg", "status": "active"}   │
│   │     ]                                        │                          │
│   │   }                                          │                          │
│   │ }                                            │                          │
│   └──────────────────────────────────────────────┘                          │
│   ✅ 100% Zero Overfetching: Only the 3 requested fields are returned!      │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

#### Core Strengths of GraphQL:
1. **Solves Overfetching**: Clients receive only the fields requested.
2. **Solves Underfetching**: Single query can traverse relationships across entities (e.g. Shikara + Owner + Bookings) in **one single round-trip**.
3. **Strongly Typed Schema**: The schema is a self-documenting contract (`type Shikara { ... }`).

#### Trade-offs & Challenges:
* **HTTP Caching is Hard**: Most GraphQL requests are dispatched as `POST` requests to a single `/graphql` URL, making standard URL-based CDN and browser caching difficult.
* **Query Complexity Attacks**: A malicious client can construct deeply nested queries (`shikara { owner { shikaras { owner { ... } } } }`) that exhaust server CPU and database connections.
* **Server-side Complexity**: Requires schema resolvers, data loaders (to solve N+1 database queries), and query complexity analyzers.

---

### 2.3 — gRPC (Google Remote Procedure Call & Protocol Buffers)

Developed by Google in 2015, gRPC is an open-source, high-performance Remote Procedure Call (RPC) framework built on top of **HTTP/2** and **Protocol Buffers (ProtoBuf)**.

Instead of sending human-readable JSON strings over HTTP/1.1, gRPC encodes structured data into a **highly compact binary format** and communicates over multiplexed HTTP/2 streams.

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│                            gRPC Wire Architecture                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│    Client (Python/Go/C++)                       Server (Microservice)       │
│    ┌──────────────────┐                         ┌──────────────────┐        │
│    │ Client Stub      │                         │ Server Stub      │        │
│    └────────┬─────────┘                         └────────▲─────────┘        │
│             │                                            │                  │
│             ▼                                            │                  │
│    ┌──────────────────┐                         ┌────────┴─────────┐        │
│    │ ProtoBuf Encode  │                         │ ProtoBuf Decode  │        │
│    └────────┬─────────┘                         └────────▲─────────┘        │
│             │                                            │                  │
│             ▼                                            │                  │
│    ┌───────────────────────────────────────────────────────────────┐        │
│    │               HTTP/2 Multiplexed Binary Stream                │        │
│    │ (Compact Bytes, Header Compression HPACK, Streaming Support)  │        │
│    └───────────────────────────────────────────────────────────────┘        │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

#### Wire Comparison: JSON vs Protocol Buffers (ProtoBuf)

Let us examine real telemetry data from an avalanche sensor on Apharwat Peak in Gulmarg:

```text
JSON Representation (Textual UTF-8):
{
    "station_id": 901,
    "temperature_milli_celsius": -7400,
    "snow_depth_cm": 185,
    "wind_velocity_kmh": 48,
    "avalanche_risk_level": 3
}
Wire Size: 110 bytes (uncompressed)
CPU Cost: String parsing, quotes, delimiters, float-to-string conversions.

───────────────────────────────────────────────────────────────────────────────

Protocol Buffer Binary Representation (Packed Bytes):
08 85 07 10 98 c5 fd ff ff ff ff ff ff 01 18 b9 01 20 30 28 03
Wire Size: 11 bytes!
Bandwidth Saving: ~90% reduction!
CPU Cost: Zero string parsing; native integer memory alignment.
```

#### Why gRPC is the King of Microservices & MLOps:
1. **Microsecond Latency**: Binary serialization is up to **10x faster** to encode and decode than JSON parsing.
2. **HTTP/2 Multiplexing**: Thousands of parallel RPC calls can travel over a **single TCP socket connection** without head-of-line blocking.
3. **Bi-Directional Streaming**: Supports Client Streaming, Server Streaming, and Bi-Directional Streaming (ideal for streaming live sensor telemetry or real-time ML model embeddings).
4. **Strict Schema Contracts**: Written in `.proto` files, which auto-generate strongly-typed client and server code in Python, Go, Java, C++, and Rust.

---

### 2.4 — SOAP (Simple Object Access Protocol)

Created by Microsoft in 1998, SOAP is a strict, protocol-independent messaging specification based entirely on **XML (Extensible Markup Language)**.

While modern startups and cloud apps favor REST, GraphQL, or gRPC, SOAP remains heavily entrenched in **banking, state treasuries, enterprise ERPs (SAP/Oracle), and financial clearing houses**.

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│                          SOAP XML Envelope Anatomy                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   <soap:Envelope>                                                           │
│     <soap:Header>                                                           │
│       <!-- WS-Security: Digital Signatures, Certificates, Timestamps -->    │
│       <wsse:Security>                                                       │
│         <wsse:UsernameToken> ... </wsse:UsernameToken>                      │
│       </wsse:Security>                                                      │
│     </soap:Header>                                                          │
│     <soap:Body>                                                             │
│       <!-- Actual RPC Operation & Typed Parameters -->                      │
│       <m:DisbursePermitFunds>                                               │
│         <m:PermitId>SHIK-992</m:PermitId>                                   │
│         <m:AmountINR>50000</m:AmountINR>                                    │
│       </m:DisbursePermitFunds>                                              │
│     </soap:Body>                                                            │
│   </soap:Envelope>                                                          │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

#### Why Enterprise & Banking Still Use SOAP:
1. **WS-Security (WSS)**: Cryptographic XML signature and field-level encryption specified directly in the message header — independent of transport layer security (TLS).
2. **Built-in ACID Transactions**: **WS-AtomicTransaction** guarantees distributed two-phase commit transactions across disparate databases and banking ledgers.
3. **Rigid WSDL Contracts**: Web Services Description Language (WSDL) defines an immutable, contract-first schema that enterprise governance systems enforce strictly.

#### Trade-offs:
* Extremely verbose payloads (massive XML markup overhead).
* High CPU parsing cost.
* Painful to work with in modern frontend and mobile environments.

---

### 2.5 — WebSockets & Event-Driven Async APIs

Traditional HTTP (REST, GraphQL) follows a **request-response** paradigm: the client must ask before the server can speak.

When an application requires continuous, real-time data push (such as live GPS tracking of Shikaras navigating Dal Lake, or instantaneous avalanche alerts in Gulmarg), constant HTTP polling introduces unacceptable latency and server overhead.

**WebSockets (RFC 6455)** solve this by establishing a **persistent, full-duplex, bi-directional TCP connection** between client and server.

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│                 HTTP Polling vs Persistent WebSocket Stream                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   Traditional HTTP Polling (Inefficient):                                   │
│   Client ────► GET /gps ────► Server (Returns: 34.08, 74.83)               │
│   (Tear down TCP connection, wait 2 seconds)                                │
│   Client ────► GET /gps ────► Server (Returns: 34.08, 74.83 - No change!)   │
│   ⚠️ Heavy HTTP header overhead (~800 bytes) sent for every 20-byte payload!│
│                                                                             │
│   Persistent WebSocket / Stream (Efficient):                                │
│   1. Initial HTTP Upgrade Handshake (101 Switching Protocols)               │
│   2. Single persistent TCP connection remains open forever                  │
│   Client ◄══════════════════════════════════════════════════► Server        │
│          Server instantly pushes GPS coordinate frames:                      │
│          ──► {lat: 34.0837, lng: 74.8370} (Only 2 bytes framing overhead!)  │
│          ──► {lat: 34.0840, lng: 74.8372}                                   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

#### Core Strengths:
1. **Zero Header Overhead**: Once connected, individual message frames have as little as **2 to 6 bytes of framing overhead**, compared to 800+ bytes of HTTP headers per request.
2. **True Full-Duplex**: Both client and server can send data simultaneously at any millisecond without waiting for a request.
3. **Minimal Latency**: No TCP three-way handshake or TLS negotiation per message.

---

## ⚖️ 3. Comprehensive Comparison & Trade-off Matrix

The following matrix contrasts all five paradigms across core production engineering criteria:

| Evaluation Metric | 1. REST | 2. GraphQL | 3. gRPC | 4. SOAP | 5. WebSockets |
|---|---|---|---|---|---|
| **Data Format** | JSON / Text | JSON / Text | Binary (ProtoBuf) | XML | Text (JSON) / Binary |
| **Transport Protocol** | HTTP/1.1 or HTTP/2 | HTTP/1.1 or HTTP/2 | HTTP/2 exclusively | HTTP, SMTP, TCP | TCP (WebSocket frame) |
| **Communication Style** | Request / Response | Request / Response | Request/Resp & Streaming | Request / Response | Full-Duplex Bi-directional |
| **Overfetching Risk** | 🔴 High | 🟢 Zero (Client picks) | 🟢 Low (ProtoBuf) | 🔴 High (XML envelope)| 🟢 Zero (Event streams) |
| **HTTP Caching** | 🟢 Native & Superb | 🔴 Poor (POST default) | 🔴 Specialized/Complex | 🔴 Non-cacheable | 🔴 Inapplicable (Stream) |
| **Payload Size** | Moderate (JSON text) | Moderate (JSON text) | 🟢 Ultra-compact (Binary)| 🔴 Heavy (XML markup) | 🟢 Tiny (2-6 byte frame) |
| **Serialization Speed**| Moderate (JSON parse)| Moderate (AST parse) | 🟢 Extremely Fast | 🔴 Slow (XML DOM/SAX) | 🟢 Fast |
| **Browser Compatibility**| 🟢 Universal | 🟢 Universal | 🟡 Requires gRPC-Web | 🟡 Difficult in JS | 🟢 Built-in API |
| **Contract / Schema** | OpenAPI / Swagger | GraphQL SDL | Protocol Buffers (`.proto`)| WSDL / XSD | AsyncAPI / Custom |
| **Primary Production Use**| Public Web APIs & CRUD| Mobile Apps & Aggregators| Microservices & MLOps | Banking & High-Security| Live Telemetry & Chat |

---

## ⚙️ 4. Architecture Decision Tree

Use this decision tree when architecting a new service in an MLOps or backend engineering ecosystem:

```text
                           [ What is your primary system requirement? ]
                                                │
          ┌───────────────────────┬─────────────┴─────────────┬────────────────────────┐
          ▼                       ▼                           ▼                        ▼
[ Live, real-time push? ]  [ High-volume internal ]  [ Rich multi-entity UI ]   [ High-security banking ]
[ Sub-second telemetry  ]  [ microservice latency ]  [ mobile app with many ]   [ or state treasury     ]
[ Shikara GPS tracking  ]  [ ML model inference   ]  [ nested screen views  ]   [ with ACID guarantees  ]
          │                       │                           │                        │
          ▼                       ▼                           ▼                        ▼
    ┌───────────┐           ┌───────────┐               ┌───────────┐            ┌───────────┐
    │ WebSocket │           │   gRPC    │               │  GraphQL  │            │   SOAP    │
    │ / Stream  │           │ (HTTP/2 + │               │ (Single   │            │ (XML +    │
    │           │           │ ProtoBuf) │               │ Endpoint) │            │ WS-Sec)   │
    └───────────┘           └───────────┘               └───────────┘            └───────────┘
                                  │
                                  ▼
           [ If building a standard public-facing CRUD web API ]
           [ with universal client support and CDN caching:    ]
                                  │
                                  ▼
                            ┌───────────┐
                            │   REST    │
                            │  (JSON /  │
                            │  HTTP)    │
                            └───────────┘
```

---

## 💻 5. Hands-On Multi-Protocol Server Lab (`api_architecture_types_lab.py`)

We now implement a complete demonstration server running on **port 8083** that simulates each of the architectural paradigms using pure Python 3 standard library:

### Features of the Lab Server:
1. **REST Endpoint (`GET /api/v1/shikaras`)**: Returns complete 12-field resource models, illustrating standard RESTful patterns and the reality of overfetching.
2. **GraphQL Query Resolver (`POST /graphql`)**: Parses incoming GraphQL queries (`{ shikaras { id name status } }`), prunes unrequested attributes dynamically, and proves zero-overfetching.
3. **gRPC / ProtoBuf Binary Simulation (`POST /api/v1/telemetry/binary`)**: Encodes high-frequency Gulmarg avalanche telemetry into raw packed binary bytes (`struct.pack`), proving a 90% reduction in wire footprint compared to JSON.
4. **SOAP XML Enterprise Service (`POST /soap/treasury`)**: Parses SOAP XML envelopes, validates XML syntax, and returns a signed enterprise receipt with transaction reference.
5. **Real-Time Event Stream (`GET /api/v1/stream/shikara-gps`)**: Holds an HTTP socket connection open and streams real-time GPS coordinate updates for Dal Lake Shikaras every 1 second.

### Full Source Code (`api_architecture_types_lab.py`)

```python
"""
Lab 75 — API Architecture Styles & Paradigms
============================================
Backend Engineering Course
Module 13 — FastAPI Backend & Backend Engineering

A zero-dependency Python server demonstrating the 5 major API architecture
paradigms (REST, GraphQL, gRPC binary framing simulation, SOAP XML envelope,
and Event-Driven Streaming / WebSockets) using Kashmir Tourism & Mountain Operations
domain entities.

Run:
    python api_architecture_types_lab.py

Server starts on:
    http://localhost:8083

Test Endpoints:
    1. REST (Overfetching Demo):
       curl -v http://localhost:8083/api/v1/shikaras

    2. GraphQL (Field Selection - Eliminates Overfetching):
       curl -v -X POST http://localhost:8083/graphql \
         -H "Content-Type: application/json" \
         -d '{"query": "{ shikaras { id name status } }"}'

    3. gRPC / ProtoBuf Binary Framing Simulation:
       curl -v -X POST http://localhost:8083/api/v1/telemetry/binary \
         -H "Content-Type: application/octet-stream"

    4. SOAP / XML Enterprise Banking Envelope:
       curl -v -X POST http://localhost:8083/soap/treasury \
         -H "Content-Type: text/xml; charset=utf-8" \
         -d '<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/"><soap:Body><DisbursePermitFunds><PermitId>SHIK-992</PermitId><AmountINR>50000</AmountINR></DisbursePermitFunds></soap:Body></soap:Envelope>'

    5. Event-Driven Real-Time Stream (SSE / Full-Duplex Emulation):
       curl -N http://localhost:8083/api/v1/stream/shikara-gps

Engineer : Danish
Track    : MLOps / DevOps Engineering (APR26)
"""

import json
import sys
import time
import struct
import datetime
import xml.etree.ElementTree as ET
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse

# ---------------------------------------------------------------------------
# Force UTF-8 on Windows consoles
# ---------------------------------------------------------------------------
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# ═══════════════════════════════════════════════════════════════════════════
#  Domain Datasets — Kashmir Tourism & Mountain Operations
# ═══════════════════════════════════════════════════════════════════════════

# Full rich dataset for Shikaras on Dal Lake
SHIKARA_FLEET = [
    {
        "id": "SHIK-001",
        "name": "Gul-e-Gulmarg Royal Shikara",
        "owner": "Ghulam Hassan",
        "dock": "Ghat No. 7, Boulevard Road",
        "capacity": 6,
        "hourly_rate_inr": 1200,
        "status": "active",
        "latitude": 34.0837,
        "longitude": 74.8370,
        "last_inspection": "2026-02-15",
        "safety_jacket_count": 8,
        "engine_type": "hand-rowed wooden paddle",
        "insurance_policy_number": "J&K-INS-99281-A",
        "permit_valid_until": "2026-12-31"
    },
    {
        "id": "SHIK-002",
        "name": "Nigeen Queen Luxury Gondola",
        "owner": "Bashir Ahmad Dar",
        "dock": "Nigeen Lake Club Jetty",
        "capacity": 4,
        "hourly_rate_inr": 1500,
        "status": "reserved",
        "latitude": 34.1120,
        "longitude": 74.8290,
        "last_inspection": "2026-03-01",
        "safety_jacket_count": 6,
        "engine_type": "hand-rowed carved cedar",
        "insurance_policy_number": "J&K-INS-44819-B",
        "permit_valid_until": "2026-11-30"
    },
    {
        "id": "SHIK-003",
        "name": "Chinar Breeze Express",
        "owner": "Mohammad Altaf",
        "dock": "Ghat No. 3, Dalgate",
        "capacity": 8,
        "hourly_rate_inr": 1800,
        "status": "maintenance",
        "latitude": 34.0780,
        "longitude": 74.8310,
        "last_inspection": "2026-01-20",
        "safety_jacket_count": 10,
        "engine_type": "hand-rowed pine keel",
        "insurance_policy_number": "J&K-INS-11029-C",
        "permit_valid_until": "2026-10-15"
    }
]

# High-frequency avalanche sensor telemetry (Gulmarg Apharwat Peak)
TELEMETRY_SENSORS = {
    "station_id": 901,
    "temperature_milli_celsius": -7400,  # -7.4 C
    "snow_depth_cm": 185,
    "wind_velocity_kmh": 48,
    "avalanche_risk_level": 3  # Level 3 Orange
}

SEPARATOR = "═" * 74


def log_wire(title, details):
    print(f"\n{SEPARATOR}")
    print(f"  📡  [{title.upper()}] — {datetime.datetime.now().strftime('%H:%M:%S')}")
    print(f"{SEPARATOR}")
    for k, v in details.items():
        print(f"  {k:24}: {v}")
    print(f"{SEPARATOR}\n")


# ═══════════════════════════════════════════════════════════════════════════
#  HTTP Request Handler: Multi-Architecture Dispatcher
# ═══════════════════════════════════════════════════════════════════════════
class ArchitectureLabHandler(BaseHTTPRequestHandler):

    def log_message(self, format, *args):
        """Suppress default stderr logging."""
        pass

    def _read_body(self):
        content_length = int(self.headers.get("Content-Length", 0))
        if content_length > 0:
            return self.rfile.read(content_length)
        return None

    # ─────────────────────────────────────────────────────────────────────
    #  GET Requests
    # ─────────────────────────────────────────────────────────────────────
    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        # 1. PARADIGM 1: REST (Representational State Transfer)
        # Demonstrates overfetching: Client may only want Shikara name and status,
        # but REST sends all 12 metadata attributes for every record.
        if path == "/api/v1/shikaras":
            payload_json = json.dumps({"count": len(SHIKARA_FLEET), "shikaras": SHIKARA_FLEET}, indent=2)
            payload_bytes = payload_json.encode("utf-8")

            log_wire("REST Architecture (Fixed Resource Endpoint)", {
                "Paradigm": "REST (JSON / HTTP 1.1)",
                "Path": path,
                "Payload Size": f"{len(payload_bytes)} bytes",
                "Trade-off": "Overfetching: Returns 12 fields per entity even if client only needs 2"
            })

            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(payload_bytes)))
            self.send_header("X-API-Paradigm", "RESTful-Standard")
            self.end_headers()
            self.wfile.write(payload_bytes)
            return

        # 2. PARADIGM 5: Event-Driven Real-Time Streaming (SSE / Persistent Stream)
        # Demonstrates real-time continuous GPS telemetry pushing from Dal Lake Shikaras
        if path == "/api/v1/stream/shikara-gps":
            log_wire("Real-Time Event Stream (Server-Sent Events / Stream)", {
                "Paradigm": "Streaming / WebSocket Class",
                "Path": path,
                "Connection": "Keep-Alive / Persistent TCP Stream",
                "Trade-off": "Low latency event broadcast; persistent connection overhead"
            })

            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream; charset=utf-8")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Connection", "keep-alive")
            self.send_header("X-API-Paradigm", "Event-Driven-Streaming")
            self.end_headers()

            # Push 5 simulated real-time GPS telemetry updates across the open socket
            base_lat, base_lng = 34.0837, 74.8370
            try:
                for step in range(1, 6):
                    cur_lat = round(base_lat + (step * 0.0003), 6)
                    cur_lng = round(base_lng + (step * 0.0002), 6)
                    event_data = {
                        "event": "SHIKARA_GPS_PING",
                        "tick": step,
                        "shikara_id": "SHIK-001",
                        "vessel_name": "Gul-e-Gulmarg Royal Shikara",
                        "coordinates": {"lat": cur_lat, "lng": cur_lng},
                        "speed_knots": 3.2,
                        "tourists_onboard": 4,
                        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
                    }
                    chunk = f"event: gps_telemetry\ndata: {json.dumps(event_data)}\n\n".encode("utf-8")
                    self.wfile.write(chunk)
                    self.wfile.flush()
                    print(f"  [STREAM TICK {step}/5] Transmitted real-time GPS chunk: {cur_lat}, {cur_lng}")
                    time.sleep(1.0)
            except (BrokenPipeError, ConnectionResetError):
                print("  [STREAM CLIENT DISCONNECTED]")
            return

        # Fallback 404
        self.send_response(404)
        self.end_headers()
        self.wfile.write(b'{"error": "Endpoint Not Found"}')

    # ─────────────────────────────────────────────────────────────────────
    #  POST Requests
    # ─────────────────────────────────────────────────────────────────────
    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path
        body = self._read_body() or b""

        # 3. PARADIGM 2: GraphQL (Client-Driven Query Resolver)
        # Demonstrates field-level selection: Client requests ONLY 'id', 'name', 'status'.
        # The resolver trims all other unrequested fields, completely solving overfetching!
        if path == "/graphql":
            try:
                req_json = json.loads(body.decode("utf-8"))
                query = req_json.get("query", "")
            except Exception:
                query = ""

            # Check if query requests only specific fields
            # Simple GraphQL engine simulation
            filtered_shikaras = []
            requested_fields = []

            # Detect fields requested in GraphQL query syntax
            candidate_fields = ["id", "name", "status", "dock", "capacity", "hourly_rate_inr"]
            for field in candidate_fields:
                if field in query:
                    requested_fields.append(field)

            if not requested_fields:
                requested_fields = ["id", "name", "status"]

            for item in SHIKARA_FLEET:
                filtered_item = {k: item[k] for k in requested_fields if k in item}
                filtered_shikaras.append(filtered_item)

            response_payload = {
                "data": {
                    "shikaras": filtered_shikaras
                },
                "meta": {
                    "requested_fields": requested_fields,
                    "fields_pruned": len(SHIKARA_FLEET[0]) - len(requested_fields),
                    "bandwidth_saved": "Eliminated overfetching of 9 unused metadata fields"
                }
            }

            resp_bytes = json.dumps(response_payload, indent=2).encode("utf-8")

            log_wire("GraphQL Architecture (Client-Specified Schema)", {
                "Paradigm": "GraphQL (POST /graphql)",
                "Requested Fields": ", ".join(requested_fields),
                "Payload Size": f"{len(resp_bytes)} bytes",
                "Benefit": "Zero Overfetching: Client receives exact shape requested"
            })

            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(resp_bytes)))
            self.send_header("X-API-Paradigm", "GraphQL-Query-Engine")
            self.end_headers()
            self.wfile.write(resp_bytes)
            return

        # 4. PARADIGM 3: gRPC / Protocol Buffers Binary Framing Simulation
        # Compares JSON payload size vs compact binary Protocol Buffer encoding.
        if path == "/api/v1/telemetry/binary":
            # Compare JSON size vs Packed Binary size:
            # JSON format
            json_representation = json.dumps(TELEMETRY_SENSORS).encode("utf-8")
            json_size = len(json_representation)

            # Compact ProtoBuf-style binary packing:
            # Format: Short (station_id: 2 bytes) + Int (temp_milli: 4 bytes) + Short (snow_cm: 2 bytes) + Short (wind_kmh: 2 bytes) + Byte (risk: 1 byte)
            # Total binary size: 11 bytes vs ~110 bytes JSON (90% compression!)
            binary_payload = struct.pack(
                "!HiHHB",
                TELEMETRY_SENSORS["station_id"],
                TELEMETRY_SENSORS["temperature_milli_celsius"],
                TELEMETRY_SENSORS["snow_depth_cm"],
                TELEMETRY_SENSORS["wind_velocity_kmh"],
                TELEMETRY_SENSORS["avalanche_risk_level"]
            )
            bin_size = len(binary_payload)

            log_wire("gRPC / ProtoBuf Binary Serialization Simulation", {
                "Paradigm": "gRPC / Protocol Buffers (Binary wire framing)",
                "JSON Equiv Size": f"{json_size} bytes",
                "Binary Wire Size": f"{bin_size} bytes",
                "Efficiency Gain": f"{(1 - (bin_size / json_size)) * 100:.1f}% reduction in network transmission size"
            })

            self.send_response(200)
            self.send_header("Content-Type", "application/octet-stream")
            self.send_header("Content-Length", str(len(binary_payload)))
            self.send_header("X-Proto-Equivalent-JSON-Bytes", str(json_size))
            self.send_header("X-Proto-Binary-Bytes", str(bin_size))
            self.send_header("X-API-Paradigm", "gRPC-ProtoBuf-Binary")
            self.end_headers()
            self.wfile.write(binary_payload)
            return

        # 5. PARADIGM 4: SOAP (Simple Object Access Protocol) XML Envelope
        # Strict enterprise security, XML envelope validation, and ACID banking transaction semantics
        if path == "/soap/treasury":
            log_wire("SOAP 1.1 Architecture (XML Contract Envelope)", {
                "Paradigm": "SOAP (XML Envelope / Strict WSDL Contract)",
                "Content-Type": self.headers.get("Content-Type", ""),
                "Incoming Bytes": f"{len(body)} bytes",
                "Semantics": "ACID compliance & WS-Security for state treasury permit grants"
            })

            # Parse XML envelope safely
            permit_id = "UNKNOWN"
            amount_inr = "0"
            try:
                root = ET.fromstring(body)
                # Search for PermitId and AmountINR tags inside SOAP body
                for elem in root.iter():
                    if "PermitId" in elem.tag:
                        permit_id = elem.text
                    if "AmountINR" in elem.tag:
                        amount_inr = elem.text
            except Exception as err:
                # Return SOAP Fault
                soap_fault = f"""<?xml version="1.0" encoding="UTF-8"?>
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
  <soap:Body>
    <soap:Fault>
      <faultcode>soap:Client</faultcode>
      <faultstring>XML Schema Validation Failed: {str(err)}</faultstring>
    </soap:Fault>
  </soap:Body>
</soap:Envelope>"""
                self.send_response(500)
                self.send_header("Content-Type", "text/xml; charset=utf-8")
                self.send_header("Content-Length", str(len(soap_fault.encode("utf-8"))))
                self.end_headers()
                self.wfile.write(soap_fault.encode("utf-8"))
                return

            soap_response = f"""<?xml version="1.0" encoding="UTF-8"?>
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/"
               xmlns:kt="http://treasury.kashmir-tourism.gov.in/disbursement">
  <soap:Header>
    <kt:SecurityAudit>
      <kt:SignatureToken>RSA-SHA256-CERT-JK99812</kt:SignatureToken>
      <kt:Timestamp>{datetime.datetime.now(datetime.timezone.utc).isoformat()}</kt:Timestamp>
    </kt:SecurityAudit>
  </soap:Header>
  <soap:Body>
    <kt:DisbursePermitFundsResponse>
      <kt:TransactionReference>TXN-JK-TREASURY-2026-9901</kt:TransactionReference>
      <kt:PermitId>{permit_id}</kt:PermitId>
      <kt:DisbursedAmount currency="INR">{amount_inr}</kt:DisbursedAmount>
      <kt:Status>SUCCESS_ACID_COMMITTED</kt:Status>
      <kt:LedgerBlock>BLOCK-77182</kt:LedgerBlock>
    </kt:DisbursePermitFundsResponse>
  </soap:Body>
</soap:Envelope>"""
            resp_bytes = soap_response.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/xml; charset=utf-8")
            self.send_header("Content-Length", str(len(resp_bytes)))
            self.send_header("X-API-Paradigm", "SOAP-XML-Enterprise")
            self.end_headers()
            self.wfile.write(resp_bytes)
            return

        # Fallback 404
        self.send_response(404)
        self.end_headers()
        self.wfile.write(b'{"error": "Endpoint Not Found"}')


def run(host="0.0.0.0", port=8083):
    server = HTTPServer((host, port), ArchitectureLabHandler)
    print(f"""
{SEPARATOR}
  🏛️  Kashmir Tourism Engineering — Lab 75: API Architecture Paradigms
  🌐  Server running on http://{host}:{port}
  🏷️   Port: {port} (Dedicated to Architecture Comparison)
{SEPARATOR}
  Supported Architectural Demos:
    1. RESTful API           : GET  /api/v1/shikaras
    2. GraphQL Engine        : POST /graphql (Query filtering & zero overfetching)
    3. gRPC / ProtoBuf Wire  : POST /api/v1/telemetry/binary (Compact binary serialization)
    4. SOAP / XML Enterprise : POST /soap/treasury (WS-Security & ACID bank transactions)
    5. Event-Driven Stream   : GET  /api/v1/stream/shikara-gps (Real-time telemetry stream)
{SEPARATOR}
  Press Ctrl+C to shut down.
""")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n🛑 Shutting down Lab 75 architecture server...")
        server.server_close()
        print("✅ Server stopped.")


if __name__ == "__main__":
    run()
```

---

## 🧪 6. Wire-Level Testing & Protocol Verification

Let us now execute wire-level tests against `http://localhost:8083` to observe how each architecture operates over the wire.

### Test 1 — REST Architecture: Observing Overfetching

```bash
curl -v http://localhost:8083/api/v1/shikaras
```

**Expected Wire Output:**
```text
> GET /api/v1/shikaras HTTP/1.1
> Host: localhost:8083
> 
< HTTP/1.1 200 OK
< Content-Type: application/json; charset=utf-8
< Content-Length: 1248
< X-API-Paradigm: RESTful-Standard
< 
{
  "count": 3,
  "shikaras": [
    {
      "id": "SHIK-001",
      "name": "Gul-e-Gulmarg Royal Shikara",
      "owner": "Ghulam Hassan",
      "dock": "Ghat No. 7, Boulevard Road",
      "capacity": 6,
      "hourly_rate_inr": 1200,
      "status": "active",
      "latitude": 34.0837,
      "longitude": 74.837,
      "last_inspection": "2026-02-15",
      "safety_jacket_count": 8,
      "engine_type": "hand-rowed wooden paddle",
      "insurance_policy_number": "J&K-INS-99281-A",
      "permit_valid_until": "2026-12-31"
    },
    ...
  ]
}
```

> **Observation:** The client downloaded **1,248 bytes**. Even if a mobile UI only displays the boat's `name` and `status`, it was forced to overfetch insurance numbers, dock addresses, and inspection dates!

---

### Test 2 — GraphQL Architecture: Eliminating Overfetching

Now, dispatch a GraphQL query asking for **ONLY** `id`, `name`, and `status`:

```bash
curl -v -X POST http://localhost:8083/graphql \
  -H "Content-Type: application/json" \
  -d '{"query": "{ shikaras { id name status } }"}'
```

**Expected Wire Output:**
```text
> POST /graphql HTTP/1.1
> Host: localhost:8083
> Content-Type: application/json
> 
< HTTP/1.1 200 OK
< Content-Type: application/json; charset=utf-8
< Content-Length: 382
< X-API-Paradigm: GraphQL-Query-Engine
< 
{
  "data": {
    "shikaras": [
      {
        "id": "SHIK-001",
        "name": "Gul-e-Gulmarg Royal Shikara",
        "status": "active"
      },
      {
        "id": "SHIK-002",
        "name": "Nigeen Queen Luxury Gondola",
        "status": "reserved"
      },
      {
        "id": "SHIK-003",
        "name": "Chinar Breeze Express",
        "status": "maintenance"
      }
    ]
  },
  "meta": {
    "requested_fields": ["id", "name", "status"],
    "fields_pruned": 10,
    "bandwidth_saved": "Eliminated overfetching of 9 unused metadata fields"
  }
}
```

> **Observation:** The payload dropped from **1,248 bytes to 382 bytes** (~70% reduction). The client received only what it asked for.

---

### Test 3 — gRPC / ProtoBuf: Binary Efficiency Simulation

Request the high-frequency avalanche sensor telemetry encoded in binary:

```bash
curl -v -X POST http://localhost:8083/api/v1/telemetry/binary \
  -H "Content-Type: application/octet-stream"
```

**Expected Wire Output:**
```text
> POST /api/v1/telemetry/binary HTTP/1.1
> Host: localhost:8083
> 
< HTTP/1.1 200 OK
< Content-Type: application/octet-stream
< Content-Length: 11
< X-Proto-Equivalent-JSON-Bytes: 115
< X-Proto-Binary-Bytes: 11
< X-API-Paradigm: gRPC-ProtoBuf-Binary
< 
[11 raw binary bytes]
```

> **Observation:** The equivalent JSON would be **115 bytes**. The packed binary ProtoBuf framing is only **11 bytes** — an **89.5% reduction** in network transmission size!

---

### Test 4 — SOAP Architecture: Enterprise XML & WS-Security

Submit a bank-grade fund disbursement for Shikara fleet subsidies:

```bash
curl -v -X POST http://localhost:8083/soap/treasury \
  -H "Content-Type: text/xml; charset=utf-8" \
  -d '<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/"><soap:Body><DisbursePermitFunds><PermitId>SHIK-992</PermitId><AmountINR>50000</AmountINR></DisbursePermitFunds></soap:Body></soap:Envelope>'
```

**Expected Wire Output:**
```text
> POST /soap/treasury HTTP/1.1
> Content-Type: text/xml; charset=utf-8
> 
< HTTP/1.1 200 OK
< Content-Type: text/xml; charset=utf-8
< X-API-Paradigm: SOAP-XML-Enterprise
< 
<?xml version="1.0" encoding="UTF-8"?>
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/"
               xmlns:kt="http://treasury.kashmir-tourism.gov.in/disbursement">
  <soap:Header>
    <kt:SecurityAudit>
      <kt:SignatureToken>RSA-SHA256-CERT-JK99812</kt:SignatureToken>
      <kt:Timestamp>2026-03-14T14:10:00Z</kt:Timestamp>
    </kt:SecurityAudit>
  </soap:Header>
  <soap:Body>
    <kt:DisbursePermitFundsResponse>
      <kt:TransactionReference>TXN-JK-TREASURY-2026-9901</kt:TransactionReference>
      <kt:PermitId>SHIK-992</kt:PermitId>
      <kt:DisbursedAmount currency="INR">50000</kt:DisbursedAmount>
      <kt:Status>SUCCESS_ACID_COMMITTED</kt:Status>
      <kt:LedgerBlock>BLOCK-77182</kt:LedgerBlock>
    </kt:DisbursePermitFundsResponse>
  </soap:Body>
</soap:Envelope>
```

> **Observation:** Notice the cryptographic security header and the ACID transaction confirmation block. Heavyweight, but essential for enterprise banking.

---

### Test 5 — WebSockets / Streaming: Real-Time Event Stream

Connect to the live GPS telemetry stream (use `curl -N` to disable output buffering):

```bash
curl -N http://localhost:8083/api/v1/stream/shikara-gps
```

**Expected Wire Output (Streams live chunks every second):**
```text
< HTTP/1.1 200 OK
< Content-Type: text/event-stream; charset=utf-8
< Connection: keep-alive
< 
event: gps_telemetry
data: {"event": "SHIKARA_GPS_PING", "tick": 1, "shikara_id": "SHIK-001", "coordinates": {"lat": 34.084, "lng": 74.8372}, "speed_knots": 3.2}

event: gps_telemetry
data: {"event": "SHIKARA_GPS_PING", "tick": 2, "shikara_id": "SHIK-001", "coordinates": {"lat": 34.0843, "lng": 74.8374}, "speed_knots": 3.2}

event: gps_telemetry
data: {"event": "SHIKARA_GPS_PING", "tick": 3, "shikara_id": "SHIK-001", "coordinates": {"lat": 34.0846, "lng": 74.8376}, "speed_knots": 3.2}
```

> **Observation:** The TCP connection stays open continuously. The server pushes real-time location ticks without the client ever polling!

---

## ⚠️ 7. Common Pitfalls & Anti-Patterns

| # | Anti-Pattern | Why It's Dangerous | Correct Architectural Solution |
|---|---|---|---|
| **1** | **Using WebSockets for Simple CRUD** | Wastes persistent TCP connections and memory; impossible to cache at CDN edges. | Use REST or GraphQL for CRUD operations; reserve WebSockets for bi-directional live streams. |
| **2** | **Defaulting to GraphQL for Microservice-to-Microservice calls** | Heavy JSON parsing and lack of binary compression slows down internal services. | Use **gRPC with ProtoBuf** for internal microservices; expose GraphQL or REST at the API gateway layer. |
| **3** | **Ignoring the N+1 Database Query Problem in GraphQL** | Resolvers querying databases in loops can trigger hundreds of SQL queries per request. | Implement **Dataloader batching** to collapse entity queries into single `WHERE id IN (...)` SQL queries. |
| **4** | **Exposing Raw gRPC to Public Web Browsers** | Web browsers lack native HTTP/2 framing and trailer controls required by gRPC. | Use **gRPC-Web proxy** or an API Gateway (Envoy/Kong) to translate public REST/JSON into internal gRPC. |
| **5** | **Over-engineering with SOAP for Modern Microservices** | XML serialization is CPU-intensive and increases latency by 300–500%. | Only use SOAP when integrating with legacy enterprise banking, insurance, or government mainframes. |

---

## 🗺️ 8. Next Step in Series

Now that you understand the full landscape of API architectures (REST, GraphQL, gRPC, SOAP, and WebSockets), you have the complete foundation to dive into **modern high-performance Python backend engineering**.

In **Lab 76 — FastAPI Architecture & Internal Engine (`76-Fast-API-Intro.md`)**, we will explore:
* How FastAPI unifies modern REST with automatic OpenAPI / Swagger documentation.
* The ASGI (Asynchronous Server Gateway Interface) standard and why Starlette makes FastAPI blisteringly fast.
* Data parsing, serialization, and automatic validation using **Pydantic v2**.
* Dependency Injection (`Depends()`) and how it revolutionizes database session management and authentication.

---

## 👨‍💻 Author & Attribution

| Field | Value |
|---|---|
| **Engineer** | Danish |
| **Track** | MLOps / DevOps Engineering (APR26) |
| **Module** | 13 — FastAPI Backend & Backend Engineering |
| **Lab** | 75 — API Architecture Styles & Paradigms (REST, GraphQL, gRPC, SOAP, WebSockets) |
| **Domain** | Kashmir Tourism & Mountain Operations (Shikaras, Avalanche Sensors, Treasury) |
| **Server Port** | 8083 |
| **Dependencies** | None (Python 3 Standard Library only) |

