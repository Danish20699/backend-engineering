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

