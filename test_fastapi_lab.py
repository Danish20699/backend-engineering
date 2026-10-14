"""
Automated Test Suite — Lab 76: FastAPI Architecture & Engine
=============================================================
Runs exhaustive automated integration tests across all endpoints,
OpenAPI schemas, Pydantic v2 validations, and security dependencies.

Run:
    python test_fastapi_lab.py
"""

import sys
import time
from fastapi.testclient import TestClient
from fastapi_intro_lab import app, ADMIN_API_KEY, EXPEDITIONS_DB

# Force UTF-8 on Windows
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")

client = TestClient(app)

def test_suite():
    passed = 0
    total = 0

    print("=" * 80)
    print("🧪 RUNNING AUTOMATED VERIFICATION SUITE FOR LAB 76 (FASTAPI)")
    print("=" * 80)

    def record(name: str, condition: bool, extra: str = ""):
        nonlocal passed, total
        total += 1
        if condition:
            passed += 1
            print(f"  [PASS] {name} {extra}")
        else:
            print(f"  [FAIL] {name} {extra}")
            raise AssertionError(f"Test failed: {name} {extra}")

    # 1. Root and metadata
    r = client.get("/")
    record("1. GET / (Root Discovery Endpoint)", r.status_code == 200 and "FastAPI" in r.json()["engine"])

    # 2. Health Probe
    r = client.get("/health")
    record("2. GET /health (Kubernetes / Cloud Probe)", r.status_code == 200 and r.json()["status"] == "healthy")

    # 3. OpenAPI 3.0 Schema
    r = client.get("/openapi.json")
    record(
        "3. GET /openapi.json (Automated OpenAPI Spec Generation)",
        r.status_code == 200 and "openapi" in r.json() and r.json()["info"]["title"] != ""
    )

    # 4. Interactive Docs UIs
    r_docs = client.get("/docs")
    record("4a. GET /docs (Swagger UI HTML rendering)", r_docs.status_code == 200 and "swagger-ui" in r_docs.text)
    r_redoc = client.get("/redoc")
    record("4b. GET /redoc (ReDoc UI HTML rendering)", r_redoc.status_code == 200 and "redoc" in r_redoc.text)

    # 5. List Expeditions
    r = client.get("/api/v1/expeditions")
    record("5a. GET /api/v1/expeditions (Default pagination)", r.status_code == 200 and len(r.json()) >= 4)

    # 6. Filter by Difficulty
    r = client.get("/api/v1/expeditions?difficulty=EXTREME")
    record(
        "6. GET /api/v1/expeditions?difficulty=EXTREME (Enum Query Filtering)",
        r.status_code == 200 and all(x["difficulty"] == "EXTREME" for x in r.json()) and len(r.json()) >= 1
    )

    # 7. Text Search
    r = client.get("/api/v1/expeditions?q=Lakes")
    record("7. GET /api/v1/expeditions?q=Lakes (Search Query)", r.status_code == 200 and len(r.json()) >= 1)

    # 8. Path Parameter Validation - Success
    r = client.get("/api/v1/expeditions/TREK-001")
    record(
        "8. GET /api/v1/expeditions/TREK-001 (Valid Path Param Regex)",
        r.status_code == 200 and r.json()["id"] == "TREK-001" and r.json()["coordinates"]["elevation_meters"] == 2730
    )

    # 9. Path Parameter - Not Found (404)
    r = client.get("/api/v1/expeditions/TREK-999")
    record(
        "9. GET /api/v1/expeditions/TREK-999 (Resource Not Found Handling)",
        r.status_code == 404 and r.json()["detail"]["error"] == "EXPEDITION_NOT_FOUND"
    )

    # 10. Path Parameter - Invalid Regex Pattern (422)
    r = client.get("/api/v1/expeditions/INVALID_TREK_ID")
    record(
        "10. GET /api/v1/expeditions/INVALID_TREK_ID (Path Regex 422 Validation Error)",
        r.status_code == 422 and "expedition_id" in str(r.json())
    )

    # 11. Create Expedition - Success (201)
    new_expedition = {
        "name": "Naranag to Gangabal Alpine Ridge Trek",
        "base_camp": "Naranag Ancient Temple Staging",
        "difficulty": "DIFFICULT",
        "max_altitude_meters": 3650,
        "duration_days": 4,
        "price_inr": 12500.0,
        "max_participants": 12,
        "emergency_beacon_code": "KMR-NG881",
        "coordinates": {
            "latitude": 34.2541,
            "longitude": 74.9812,
            "elevation_meters": 2240
        }
    }
    r = client.post("/api/v1/expeditions", json=new_expedition)
    record(
        "11. POST /api/v1/expeditions (Pydantic v2 Creation & 201 Created)",
        r.status_code == 201 and r.json()["id"].startswith("TREK-") and r.json()["status"] == "SCHEDULED"
    )
    created_id = r.json()["id"]

    # 12. Create Expedition - Pydantic Validation Error (422) Missing Fields
    invalid_payload = {
        "name": "Sonamarg Short Day Hike",
        "difficulty": "EASY"
        # missing price, altitude, coordinates, etc.
    }
    r = client.post("/api/v1/expeditions", json=invalid_payload)
    record(
        "12a. POST /api/v1/expeditions (Pydantic Missing Fields 422 Error)",
        r.status_code == 422 and len(r.json()["detail"]) >= 4
    )

    # 13. Create Expedition - Cross-field validator (EXTREME must have altitude >= 4000)
    invalid_cross_field = {
        "name": "Low Altitude Extreme Trek",
        "base_camp": "Aru Valley",
        "difficulty": "EXTREME",
        "max_altitude_meters": 2500,  # Invalid! EXTREME must be >= 4000
        "duration_days": 5,
        "price_inr": 15000.0,
        "max_participants": 10,
        "emergency_beacon_code": "KMR-LA111",
        "coordinates": {
            "latitude": 34.08,
            "longitude": 75.25,
            "elevation_meters": 2400
        }
    }
    r = client.post("/api/v1/expeditions", json=invalid_cross_field)
    record(
        "12b. POST /api/v1/expeditions (Pydantic Custom Model Validator 422 Error)",
        r.status_code == 422 and "attain an altitude of at least 4000m" in str(r.json())
    )

    # 14. Full Update (PUT)
    update_payload = dict(new_expedition)
    update_payload["name"] = "Naranag to Gangabal Alpine Expedition (Upgraded)"
    update_payload["duration_days"] = 5
    r = client.put(f"/api/v1/expeditions/{created_id}", json=update_payload)
    record(
        "13. PUT /api/v1/expeditions/{id} (Full Resource Idempotent Update)",
        r.status_code == 200 and r.json()["name"] == "Naranag to Gangabal Alpine Expedition (Upgraded)"
    )

    # 15. Partial Status Update (PATCH)
    patch_payload = {
        "status": "SUSPENDED_WEATHER",
        "reason": "Sudden blizzard advisory across Mahadev range."
    }
    r = client.patch(f"/api/v1/expeditions/{created_id}/status", json=patch_payload)
    record(
        "14. PATCH /api/v1/expeditions/{id}/status (Partial State Transition)",
        r.status_code == 200 and r.json()["status"] == "SUSPENDED_WEATHER"
    )

    # 16. Delete without Auth Key (401 Unauthorized)
    r = client.delete(f"/api/v1/expeditions/{created_id}")
    record(
        "15a. DELETE /api/v1/expeditions/{id} (Missing X-API-Key -> 401 Unauthorized)",
        r.status_code == 401 and r.json()["detail"]["error"] == "UNAUTHORIZED_ADMIN_ACTION"
    )

    # 17. Delete with Invalid Auth Key (403 Forbidden)
    r = client.delete(f"/api/v1/expeditions/{created_id}", headers={"X-API-Key": "wrong-key"})
    record(
        "15b. DELETE /api/v1/expeditions/{id} (Invalid X-API-Key -> 403 Forbidden)",
        r.status_code == 403 and r.json()["detail"]["error"] == "FORBIDDEN_CREDENTIALS"
    )

    # 18. Delete with Valid Auth Key (204 No Content)
    r = client.delete(f"/api/v1/expeditions/{created_id}", headers={"X-API-Key": ADMIN_API_KEY})
    record(
        "15c. DELETE /api/v1/expeditions/{id} (Valid X-API-Key -> 204 No Content)",
        r.status_code == 204
    )

    # Verify deleted
    r = client.get(f"/api/v1/expeditions/{created_id}")
    record("15d. Verification: Deleted item returns 404", r.status_code == 404)

    # 19. Streaming Telemetry Response
    with client.stream("GET", "/api/v1/telemetry/gondola-stream") as stream:
        record(
            "16. GET /api/v1/telemetry/gondola-stream (Starlette StreamingResponse SSE)",
            stream.status_code == 200 and "text/event-stream" in stream.headers.get("content-type", "")
        )

    print("=" * 80)
    print(f"🎉 VERIFICATION COMPLETE: {passed}/{total} tests passed (100% SUCCESS)")
    print("=" * 80)


if __name__ == "__main__":
    test_suite()
