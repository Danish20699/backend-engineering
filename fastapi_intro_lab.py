"""
Lab 76 — FastAPI Architecture, Pydantic v2 & OpenAPI Engine
===========================================================
Backend Engineering & Cloud DevOps Track
Module 13 — High-Performance Python Backend Microservices

Domain: Kashmir High-Altitude Operations & Mountain Expeditions API
Author: Danish Nazir (@Danish20699)
License: MIT
"""

import sys
import asyncio
from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict, Any

from fastapi import (
    FastAPI,
    Path,
    Query,
    Header,
    status,
    HTTPException,
    Depends,
    Request,
)
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import (
    BaseModel,
    Field,
    field_validator,
    model_validator,
    ConfigDict,
)

# ---------------------------------------------------------------------------
# Force UTF-8 on Windows Consoles
# ---------------------------------------------------------------------------
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# ===========================================================================
# 1. Domain Enums
# ===========================================================================

class DifficultyLevel(str, Enum):
    EASY = "EASY"
    MODERATE = "MODERATE"
    DIFFICULT = "DIFFICULT"
    EXTREME = "EXTREME"


class ExpeditionStatus(str, Enum):
    SCHEDULED = "SCHEDULED"
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    SUSPENDED_WEATHER = "SUSPENDED_WEATHER"
    CANCELLED = "CANCELLED"


# ===========================================================================
# 2. Pydantic v2 Data Models (Validation & Serialization Core)
# ===========================================================================

class GpsCoordinates(BaseModel):
    """Geographic coordinates for high-altitude mountain basecamps."""
    latitude: float = Field(
        ...,
        ge=32.0,
        le=37.0,
        description="Latitude in the Jammu & Kashmir Himalayan coordinate box (32.0 - 37.0)",
        examples=[34.3015]
    )
    longitude: float = Field(
        ...,
        ge=73.0,
        le=77.5,
        description="Longitude in the Jammu & Kashmir Himalayan coordinate box (73.0 - 77.5)",
        examples=[75.2985]
    )
    elevation_meters: int = Field(
        ...,
        ge=1500,
        le=8611,
        description="Elevation in meters above sea level",
        examples=[2730]
    )

    model_config = ConfigDict(extra="forbid")


class ExpeditionBase(BaseModel):
    """Base expedition schema containing shared business attributes."""
    name: str = Field(
        ...,
        min_length=5,
        max_length=100,
        description="Official expedition title",
        examples=["Kashmir Great Lakes Alpine Traverse"]
    )
    base_camp: str = Field(
        ...,
        min_length=3,
        max_length=80,
        description="Starting staging camp location",
        examples=["Sonamarg - Shitkadi Base"]
    )
    difficulty: DifficultyLevel = Field(
        ...,
        description="Technical mountain difficulty rating",
        examples=[DifficultyLevel.DIFFICULT]
    )
    max_altitude_meters: int = Field(
        ...,
        ge=1500,
        le=8611,
        description="Maximum peak altitude reached during expedition",
        examples=[4191]
    )
    duration_days: int = Field(
        ...,
        ge=1,
        le=30,
        description="Total duration in days",
        examples=[7]
    )
    price_inr: float = Field(
        ...,
        gt=0.0,
        description="Expedition cost per mountaineer in INR",
        examples=[18500.0]
    )
    max_participants: int = Field(
        ...,
        ge=1,
        le=40,
        description="Maximum climber capacity permitted for eco-preservation",
        examples=[14]
    )
    emergency_beacon_code: str = Field(
        ...,
        pattern=r"^KMR-[A-Z0-9]{4,8}$",
        description="J&K Mountain Rescue SAR Beacon ID (e.g., KMR-GL992)",
        examples=["KMR-GL992"]
    )
    coordinates: GpsCoordinates = Field(
        ...,
        description="Basecamp GPS telemetry coordinates"
    )

    @field_validator("name")
    @classmethod
    def validate_title_casing(cls, v: str) -> str:
        clean = v.strip()
        if not clean[0].isupper():
            raise ValueError("Expedition name must begin with a capital letter.")
        return clean

    @model_validator(mode="after")
    def validate_altitude_vs_difficulty(self) -> "ExpeditionBase":
        """Cross-field validation: EXTREME expeditions must reach >= 4000 meters."""
        if self.difficulty == DifficultyLevel.EXTREME and self.max_altitude_meters < 4000:
            raise ValueError(
                f"Expeditions rated EXTREME must attain an altitude of at least 4000m (provided: {self.max_altitude_meters}m)."
            )
        return self


class TrekExpeditionCreate(ExpeditionBase):
    """Creation payload for high-altitude expeditions."""
    pass


class TrekExpeditionUpdate(BaseModel):
    """Optional fields for modifying an existing expedition."""
    name: Optional[str] = Field(None, min_length=5, max_length=100)
    base_camp: Optional[str] = Field(None, min_length=3, max_length=80)
    difficulty: Optional[DifficultyLevel] = None
    max_altitude_meters: Optional[int] = Field(None, ge=1500, le=8611)
    duration_days: Optional[int] = Field(None, ge=1, le=30)
    price_inr: Optional[float] = Field(None, gt=0.0)
    max_participants: Optional[int] = Field(None, ge=1, le=40)
    emergency_beacon_code: Optional[str] = Field(None, pattern=r"^KMR-[A-Z0-9]{4,8}$")
    coordinates: Optional[GpsCoordinates] = None


class ExpeditionStatusUpdate(BaseModel):
    """Payload for partial status transitions."""
    status: ExpeditionStatus = Field(..., description="Target lifecycle state")
    reason: Optional[str] = Field(
        None,
        max_length=200,
        description="Operational justification (e.g. avalanche alert, snowfall)",
        examples=["Avalanche advisory issued by SASE for Apharwat ridge"]
    )


class TrekExpeditionResponse(ExpeditionBase):
    """Complete public representation returned to clients."""
    id: str = Field(..., description="Unique expedition identifier", examples=["TREK-001"])
    status: ExpeditionStatus = Field(..., description="Current operational status")
    registered_participants: int = Field(..., ge=0, description="Active registered climbers")
    created_at: str = Field(..., description="ISO 8601 creation timestamp")

    model_config = ConfigDict(from_attributes=True)


# ===========================================================================
# 3. In-Memory Persistent Store (Kashmir Mountain Domain)
# ===========================================================================

EXPEDITIONS_DB: Dict[str, Dict[str, Any]] = {
    "TREK-001": {
        "id": "TREK-001",
        "name": "Kashmir Great Lakes Alpine Traverse",
        "base_camp": "Sonamarg - Shitkadi Base",
        "difficulty": DifficultyLevel.DIFFICULT,
        "max_altitude_meters": 4191,
        "duration_days": 7,
        "price_inr": 18500.0,
        "max_participants": 16,
        "emergency_beacon_code": "KMR-GL001",
        "coordinates": {
            "latitude": 34.3015,
            "longitude": 75.2985,
            "elevation_meters": 2730
        },
        "status": ExpeditionStatus.ACTIVE,
        "registered_participants": 12,
        "created_at": "2026-03-01T08:00:00Z"
    },
    "TREK-002": {
        "id": "TREK-002",
        "name": "Tarsar Marsar Twin Lakes Circuit",
        "base_camp": "Aru Valley - Pahalgam",
        "difficulty": DifficultyLevel.MODERATE,
        "max_altitude_meters": 3962,
        "duration_days": 6,
        "price_inr": 15500.0,
        "max_participants": 18,
        "emergency_beacon_code": "KMR-TM002",
        "coordinates": {
            "latitude": 34.0864,
            "longitude": 75.2638,
            "elevation_meters": 2415
        },
        "status": ExpeditionStatus.SCHEDULED,
        "registered_participants": 10,
        "created_at": "2026-03-05T09:30:00Z"
    },
    "TREK-003": {
        "id": "TREK-003",
        "name": "Kolahoi Glacier North Face Expedition",
        "base_camp": "Lidderwat Alpine Staging",
        "difficulty": DifficultyLevel.EXTREME,
        "max_altitude_meters": 5425,
        "duration_days": 9,
        "price_inr": 34000.0,
        "max_participants": 8,
        "emergency_beacon_code": "KMR-KH003",
        "coordinates": {
            "latitude": 34.1750,
            "longitude": 75.3180,
            "elevation_meters": 3050
        },
        "status": ExpeditionStatus.ACTIVE,
        "registered_participants": 6,
        "created_at": "2026-03-10T11:00:00Z"
    },
    "TREK-004": {
        "id": "TREK-004",
        "name": "Apharwat Ridge Mountain Patrol",
        "base_camp": "Gulmarg Highland Base",
        "difficulty": DifficultyLevel.EASY,
        "max_altitude_meters": 3980,
        "duration_days": 2,
        "price_inr": 4800.0,
        "max_participants": 25,
        "emergency_beacon_code": "KMR-AP004",
        "coordinates": {
            "latitude": 34.0484,
            "longitude": 74.3805,
            "elevation_meters": 2690
        },
        "status": ExpeditionStatus.SCHEDULED,
        "registered_participants": 14,
        "created_at": "2026-03-12T14:15:00Z"
    }
}

# ===========================================================================
# 4. FastAPI Dependency Injection System (`Depends`)
# ===========================================================================

ADMIN_API_KEY = "kashmir-sar-rescue-key-2026"

def verify_sar_admin_key(
    x_api_key: Optional[str] = Header(
        None,
        alias="X-API-Key",
        description="Administrative Security Token for privileged SAR operations"
    )
) -> str:
    """
    FastAPI Dependency: Authenticates administrative requests.
    Raises HTTP 401 if header is absent, HTTP 403 if token is invalid.
    """
    if not x_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": "UNAUTHORIZED_ADMIN_ACTION",
                "message": "Missing 'X-API-Key' authentication header.",
                "hint": "Provide 'X-API-Key: kashmir-sar-rescue-key-2026'"
            }
        )
    if x_api_key != ADMIN_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "FORBIDDEN_CREDENTIALS",
                "message": "Invalid SAR admin authentication key."
            }
        )
    return x_api_key


class PaginationParams:
    """Reusable query dependency for pagination."""
    def __init__(
        self,
        skip: int = Query(0, ge=0, description="Records to skip"),
        limit: int = Query(10, ge=1, le=50, description="Records per page")
    ):
        self.skip = skip
        self.limit = limit


# ===========================================================================
# 5. FastAPI Application Initialization & OpenAPI Metadata
# ===========================================================================

app = FastAPI(
    title="Kashmir Mountain Operations & High-Altitude Expeditions API",
    description="""
# 🏔️ Lab 76: FastAPI Architecture & Internal Engine

Welcome to the **Kashmir Mountain Operations API**, built with **FastAPI**, **Starlette**, and **Pydantic v2**.

### 🌟 Core Architectural Highlights:
* **ASGI Engine**: Built on Starlette and served via Uvicorn for asynchronous I/O performance.
* **Pydantic v2 Validation**: Strict schema enforcement, type coercion, and auto-generated error trees.
* **OpenAPI 3.0 & Swagger UI**: Automatic documentation generated live from type signatures.
* **Dependency Injection**: Composable, type-safe security and pagination dependencies.
* **Real-time Telemetry**: Starlette `StreamingResponse` for live mountain telemetry pings.

---
*Engineer*: **Danish Nazir** | *Track*: **MLOps & Cloud DevOps (APR26)**
""",
    version="1.0.0",
    terms_of_service="https://github.com/Danish20699/fastapi",
    contact={
        "name": "Danish Nazir — Cloud & MLOps Engineer",
        "url": "https://github.com/Danish20699",
        "email": "danishnazir20699@gmail.com",
    },
    license_info={
        "name": "MIT License",
        "url": "https://opensource.org/licenses/MIT",
    },
    openapi_tags=[
        {
            "name": "System & Telemetry",
            "description": "API status, health probes, and live real-time mountain sensor streams.",
        },
        {
            "name": "Expeditions",
            "description": "Full CRUD operations for Himalayan trekking and mountain rescue missions.",
        },
        {
            "name": "Administrative",
            "description": "Privileged endpoints guarded by FastAPI Dependency Injection.",
        },
    ]
)

# Cross-Origin Resource Sharing (CORS) Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ===========================================================================
# 6. Route Handlers: System & Telemetry Endpoints
# ===========================================================================

@app.get("/", tags=["System & Telemetry"], summary="API Root & Ecosystem Index")
async def root(request: Request) -> Dict[str, Any]:
    """Provides platform discovery URLs, documentation links, and engine metadata."""
    base_url = str(request.base_url).rstrip("/")
    return {
        "engine": "FastAPI 0.110+ (Starlette ASGI + Pydantic v2)",
        "service": "Kashmir Mountain Operations & Expeditions Hub",
        "lab": "Lab 76 — FastAPI Architecture & Internal Engine",
        "engineer": "Danish Nazir (@Danish20699)",
        "endpoints": {
            "interactive_swagger_ui": f"{base_url}/docs",
            "interactive_redoc_ui": f"{base_url}/redoc",
            "openapi_json_schema": f"{base_url}/openapi.json",
            "health_check": f"{base_url}/health",
            "expeditions_collection": f"{base_url}/api/v1/expeditions",
            "live_gondola_stream": f"{base_url}/api/v1/telemetry/gondola-stream"
        },
        "status": "OPERATIONAL_ONLINE",
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }


@app.get("/health", tags=["System & Telemetry"], summary="Kubernetes & Cloud Health Probe")
async def health_check() -> Dict[str, str]:
    """Lightweight health probe endpoint for Docker and Kubernetes liveness checks."""
    return {
        "status": "healthy",
        "uptime": "nominal",
        "database": "in_memory_synced",
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }


@app.get(
    "/api/v1/telemetry/gondola-stream",
    tags=["System & Telemetry"],
    summary="Real-Time Gulmarg Gondola Phase-2 Cable Car Telemetry (SSE)"
)
async def gondola_telemetry_stream():
    """
    Demonstrates Starlette's asynchronous `StreamingResponse` for Server-Sent Events (SSE).
    Simulates live GPS altitude, wind speed, and cable tension on Apharwat Peak (3,980m).
    """
    async def event_generator():
        altitudes = [2690, 2950, 3200, 3550, 3800, 3980]
        for tick, alt in enumerate(altitudes, start=1):
            await asyncio.sleep(0.5)
            payload = {
                "event": "GONDOLA_PHASE2_PING",
                "tick": tick,
                "cable_car_id": "CAR-042",
                "altitude_meters": alt,
                "wind_speed_kmh": round(24.5 + (tick * 2.1), 1),
                "cable_tension_kilonewtons": round(142.0 + (tick * 0.8), 2),
                "status": "NOMINAL_ASCENT" if alt < 3980 else "SUMMIT_DOCK_REACHED"
            }
            yield f"event: telemetry\ndata: {JSONResponse(content=payload).body.decode('utf-8')}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive"
        }
    )


# ===========================================================================
# 7. Route Handlers: Expeditions CRUD
# ===========================================================================

@app.get(
    "/api/v1/expeditions",
    response_model=List[TrekExpeditionResponse],
    tags=["Expeditions"],
    summary="List Expeditions with Filtering & Pagination"
)
async def list_expeditions(
    pagination: PaginationParams = Depends(),
    difficulty: Optional[DifficultyLevel] = Query(
        None,
        description="Filter expeditions by alpine technical difficulty"
    ),
    q: Optional[str] = Query(
        None,
        min_length=2,
        max_length=50,
        description="Case-insensitive text search in title or basecamp"
    )
) -> List[Dict[str, Any]]:
    """
    Retrieve Himalayan expeditions with composable pagination and filter parameters.
    Demonstrates FastAPI's query parameter parsing, type conversion, and dependency injection.
    """
    results = list(EXPEDITIONS_DB.values())

    if difficulty:
        results = [e for e in results if e["difficulty"] == difficulty]

    if q:
        query_lower = q.lower()
        results = [
            e for e in results
            if query_lower in e["name"].lower() or query_lower in e["base_camp"].lower()
        ]

    # Apply pagination via dependency attributes
    return results[pagination.skip : pagination.skip + pagination.limit]


@app.get(
    "/api/v1/expeditions/{expedition_id}",
    response_model=TrekExpeditionResponse,
    tags=["Expeditions"],
    summary="Retrieve Single Expedition by Identifier"
)
async def get_expedition(
    expedition_id: str = Path(
        ...,
        pattern=r"^TREK-[0-9]{3}$",
        description="Strict format: TREK- followed by exactly 3 digits",
        examples=["TREK-001"]
    )
) -> Dict[str, Any]:
    """
    Fetch a single expedition by unique ID.
    Demonstrates FastAPI's path parameter regex validation and HTTP 404 handling.
    """
    if expedition_id not in EXPEDITIONS_DB:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": "EXPEDITION_NOT_FOUND",
                "message": f"No mountain expedition registered with ID '{expedition_id}'.",
                "available_expeditions": list(EXPEDITIONS_DB.keys())
            }
        )
    return EXPEDITIONS_DB[expedition_id]


@app.post(
    "/api/v1/expeditions",
    response_model=TrekExpeditionResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Expeditions"],
    summary="Register New Mountain Expedition (Pydantic Validation)"
)
async def create_expedition(
    payload: TrekExpeditionCreate
) -> Dict[str, Any]:
    """
    Register a new mountain expedition.
    Demonstrates Pydantic v2 automatic body parsing, cross-field validation, and HTTP 201 status.
    """
    # Generate sequential unique identifier
    existing_nums = [
        int(k.split("-")[1]) for k in EXPEDITIONS_DB.keys() if k.startswith("TREK-")
    ]
    next_num = max(existing_nums, default=0) + 1
    new_id = f"TREK-{next_num:03d}"

    record = payload.model_dump()
    record.update({
        "id": new_id,
        "status": ExpeditionStatus.SCHEDULED,
        "registered_participants": 0,
        "created_at": datetime.utcnow().isoformat() + "Z"
    })

    EXPEDITIONS_DB[new_id] = record
    return record


@app.put(
    "/api/v1/expeditions/{expedition_id}",
    response_model=TrekExpeditionResponse,
    tags=["Expeditions"],
    summary="Full Replacement of Expedition Record"
)
async def update_expedition(
    expedition_id: str = Path(..., pattern=r"^TREK-[0-9]{3}$"),
    payload: TrekExpeditionCreate = ...
) -> Dict[str, Any]:
    """
    Idempotent full update of an existing expedition resource.
    """
    if expedition_id not in EXPEDITIONS_DB:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Expedition '{expedition_id}' does not exist for replacement."
        )

    existing = EXPEDITIONS_DB[expedition_id]
    updated = payload.model_dump()
    updated.update({
        "id": expedition_id,
        "status": existing["status"],
        "registered_participants": existing["registered_participants"],
        "created_at": existing["created_at"]
    })

    EXPEDITIONS_DB[expedition_id] = updated
    return updated


@app.patch(
    "/api/v1/expeditions/{expedition_id}/status",
    response_model=TrekExpeditionResponse,
    tags=["Expeditions"],
    summary="Partial State Transition (Status Update)"
)
async def update_expedition_status(
    expedition_id: str = Path(..., pattern=r"^TREK-[0-9]{3}$"),
    update: ExpeditionStatusUpdate = ...
) -> Dict[str, Any]:
    """
    Partially modifies the operational lifecycle status of an expedition.
    """
    if expedition_id not in EXPEDITIONS_DB:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Expedition '{expedition_id}' not found."
        )

    record = EXPEDITIONS_DB[expedition_id]
    record["status"] = update.status
    return record


@app.delete(
    "/api/v1/expeditions/{expedition_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Administrative"],
    summary="Delete Expedition Record (Admin Key Required)"
)
async def delete_expedition(
    expedition_id: str = Path(..., pattern=r"^TREK-[0-9]{3}$"),
    _: str = Depends(verify_sar_admin_key)
):
    """
    Privileged Administrative Endpoint: Deletes an expedition.
    Demonstrates header validation and security enforcement via `Depends()`.
    Returns HTTP 204 No Content upon success.
    """
    if expedition_id not in EXPEDITIONS_DB:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Cannot delete non-existent expedition '{expedition_id}'."
        )

    del EXPEDITIONS_DB[expedition_id]
    return None


# ===========================================================================
# 8. Server Execution Block
# ===========================================================================

if __name__ == "__main__":
    import uvicorn
    print("\n" + "=" * 78)
    print("🏔️  KASHMIR HIGH-ALTITUDE MOUNTAIN OPERATIONS API (FASTAPI ENGINE)")
    print("=" * 78)
    print("📍 Interactive Swagger UI : http://127.0.0.1:8000/docs")
    print("📖 Interactive ReDoc UI   : http://127.0.0.1:8000/redoc")
    print("📜 Raw OpenAPI 3.0 Schema : http://127.0.0.1:8000/openapi.json")
    print("🚀 Telemetry Live Stream  : http://127.0.0.1:8000/api/v1/telemetry/gondola-stream")
    print("=" * 78 + "\n")
    uvicorn.run("fastapi_intro_lab:app", host="127.0.0.1", port=8000, reload=True)
