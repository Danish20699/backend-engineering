# Backend Engineering & API Mastery

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-Framework-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Track](https://img.shields.io/badge/Track-MLOps%20%7C%20DevOps-orange)](#)

A comprehensive hands-on repository covering backend engineering fundamentals, HTTP/HTTPS protocols, RESTful API design, request-response lifecycles, and modern high-performance FastAPI backend services.

---

## 📚 Curriculum & Lab Series Roadmap

| Lab # | Lab Document | Focus Area | Status |
| :---: | :--- | :--- | :---: |
| **71** | [Lab 71: Backend Technology Basics](71-Backend-technology-basics.md) | Client-Server Model, 3-Tier Architecture, URL Anatomy, ASGI vs WSGI | ✅ Completed |
| **72** | [Lab 72: API HTTP Request & Response](72-API-HTTP-Request-and_Response.md) | In-depth HTTP Request/Response cycle, Headers, Body, and Encoding | ✅ Completed |
| **73** | [Lab 73: API Request Methods](73-API-Request-Methods.md) | REST Verbs: GET, POST, PUT, PATCH, DELETE & Idempotency | ✅ Completed |
| **74** | [Lab 74: HTTP Status Codes & Error Standardization](74-HTTP_Status-Codes.md) | Status Categories: 1xx, 2xx, 3xx, 4xx, 5xx & Error Standardization | ✅ Completed |
| **75** | [Lab 75: API Architecture Types](75-API-ARchitecture-Types.md) | REST, GraphQL, gRPC, SOAP, and WebSockets comparison & trade-offs | ✅ Completed |
| **76** | [Lab 76: FastAPI Architecture & Internal Engine](76-Fast-API-Intro.md) | FastAPI architecture, Starlette, Pydantic, and automatic Swagger docs | ✅ Completed |
| **77** | `77-fastapi-hello-world.md` | First FastAPI Microservice, ASGI server run with Uvicorn | ⏳ Next |

---

## 🏛️ Architecture Overview

Modern backend engineering decouples presentation from data processing, enabling distributed scalability, secure persistence, and rapid machine learning model serving:

```text
┌─────────────────┐           HTTP/HTTPS Request           ┌──────────────────────────────────────────────┐
│  Client Tier    │  ────────────────────────────────────► │                  Server Tier                 │
│ (Browser, Mobile│                                        │ ┌──────────────┐   ┌───────────────────────┐ │
│  Frontend, cURL)│  ◄──────────────────────────────────── │ │ Reverse Proxy│──►│ ASGI Server (Uvicorn) │ │
└─────────────────┘           HTTP/HTTPS Response          │ │ (Nginx)      │   │   ▼                   │ │
                                                           │ └──────────────┘   │ FastAPI Backend Logic │ │
                                                           │                    └───────────┬───────────┘ │
                                                           │                                │             │
                                                           │                                ▼             │
                                                           │                    ┌───────────────────────┐ │
                                                           │                    │ Data Persistence Tier │ │
                                                           │                    │ (PostgreSQL, Redis)   │ │
                                                           │                    └───────────────────────┘ │
                                                           └──────────────────────────────────────────────┘
```

---

## 🚀 Quick Start

### 1. Clone the Repository
```bash
git clone https://github.com/Danish20699/backend-engineering.git
cd backend-engineering
```

### 2. Explore Lab 71
Read the foundational concepts and architectural diagrams in [71-Backend-technology-basics.md](71-Backend-technology-basics.md).

---

## 👤 Author
* **Engineer**: Danish ([@Danish20699](https://github.com/Danish20699))
* **Program**: MLOps & Cloud DevOps Engineering (APR26)

