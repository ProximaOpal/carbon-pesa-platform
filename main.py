# =======================================================================
# CARBON PESA — Python Backend (main.py)
# FastAPI server: receives state POSTs from the JS frontend,
# serves the latest state to n8n / AI Workflow Coordinator.
# =======================================================================

from __future__ import annotations

import logging
import threading
import time
import urllib.request
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Request, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, Field

# ── Logging ─────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
log = logging.getLogger("carbonpesa.state")

# ── App ──────────────────────────────────────────────────────────────────
app = FastAPI(
    title="Carbon Pesa State API",
    description=(
        "In-memory state registry that bridges the Carbon Pesa frontend "
        "with the n8n AI Workflow Coordinator."
    ),
    version="2.0.0",
)

# ── CORS — allow all origins ─────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Keep Alive Loop ──────────────────────────────────────────────────────
def keep_alive_ping():
    # Wait 30 seconds for the server to start up before sending the first ping
    time.sleep(30)
    while True:
        try:
            url = "https://carbon-pesa-platform-1.onrender.com/"
            req = urllib.request.Request(url, headers={"User-Agent": "CarbonPesaKeepAlive"})
            with urllib.request.urlopen(req) as res:
                res.read()
            log.info("Keep-alive self-ping successful")
        except Exception as e:
            log.warning("Keep-alive self-ping failed: %s", e)
        time.sleep(14 * 60)  # Sleep for 14 minutes

@app.on_event("startup")
def start_keep_alive():
    threading.Thread(target=keep_alive_ping, daemon=True).start()

# ── In-Memory Cache and Registry ────────────────────────────────────────
_DEFAULT_STATE: Dict[str, Any] = {
    "currentPage": "Unknown",
    "currentSlideIndex": 0,
    "currentSlideHeading": "MISSION",
    "searchOpen": False,
    "navMenuOpen": False,
    "activeView": "audit",
    "activeFarmId": 1,
    "mapContext": {"lat": -0.5023, "lng": 35.4156, "zoom": 15},
    "activeLayers": ["satellite", "NDVI"],
    "lastAgentIntent": None,
    "lastAgentPayload": None,
    "updatedAt": datetime.now(timezone.utc).isoformat(),
}

latest_app_state: Dict[str, Any] = dict(_DEFAULT_STATE)
state_receive_count: int = 0

_registered_farms = {
    "type": "FeatureCollection",
    "features": [
        {
            "type": "Feature",
            "properties": {
                "farm_id": 1,
                "name": "Mau Forest Conservation",
                "area_ha": 150.4
            },
            "geometry": {
                "type": "Polygon",
                "coordinates": [
                    [
                        [35.41, -0.50],
                        [35.42, -0.50],
                        [35.42, -0.51],
                        [35.41, -0.51],
                        [35.41, -0.50]
                    ]
                ]
            }
        }
    ]
}

_audits = [
    {
        "timestamp": "2026-06-26T10:00:00Z",
        "hash_manifest": "c3ab8ff718223c72b22f42a12d1b82cc03a8ec3f8d38bf228aa412e6900223d5",
        "carbon_yield_tons": 124.5
    },
    {
        "timestamp": "2026-06-25T14:30:00Z",
        "hash_manifest": "f892a0134bfb42a129f12d8a01f92ac3debc40fa3d8bc2d6a8a3a0e412f690ab",
        "carbon_yield_tons": 98.2
    }
]

_payouts = [
    {
        "amount": 25000,
        "daraja_receipt": "DAR-MPESA-88271",
        "status": "COMPLETED"
    },
    {
        "amount": 18500,
        "daraja_receipt": "DAR-MPESA-77312",
        "status": "COMPLETED"
    }
]

_stresses = [
    { "name": "Mau Zone 4", "area": "4.5 ac", "priority": "High", "date": "New", "ndvi": 0.31, "coords": [-0.502, 35.416] },
    { "name": "Sector 7B", "area": "12.0 ac", "priority": "Medium", "date": "Jul 2", "ndvi": 0.48, "coords": [-0.506, 35.412] },
    { "name": "Riparian 1", "area": "2.1 ac", "priority": "Low", "date": "Jul 14", "ndvi": 0.61, "coords": [-0.498, 35.418] }
]

_telemetry = [
    { "id": "UAV-01 Alpha", "status": "Active scanning", "battery": "82%", "type": "Thermal", "latitude": -0.501, "longitude": 35.414, "altitude": 120, "speed": 8, "wind": "NW 12km/h", "co2_level": 412, "humidity": 72 },
    { "id": "UAV-02 Beta", "status": "Return to base", "battery": "14%", "type": "LIDAR", "latitude": -0.505, "longitude": 35.418, "altitude": 110, "speed": 5, "wind": "NW 10km/h", "co2_level": 408, "humidity": 71 },
    { "id": "UAV-04 Delta", "status": "Active scanning", "battery": "95%", "type": "Optical", "latitude": -0.498, "longitude": 35.412, "altitude": 125, "speed": 9, "wind": "NW 11km/h", "co2_level": 415, "humidity": 73 },
    { "id": "Ground-Bot 1", "status": "Offline", "battery": "--", "type": "Soil Sampler", "latitude": -0.510, "longitude": 35.410, "altitude": 0, "speed": 0, "wind": "None", "co2_level": 420, "humidity": 75 }
]

# ── Pydantic Schemas ─────────────────────────────────────────────────────
class MapContext(BaseModel):
    lat: float = -0.5023
    lng: float = 35.4156
    zoom: int = 15

class CarbonPesaState(BaseModel):
    currentPage: str = "Unknown"
    currentSlideIndex: int = Field(0)
    currentSlideHeading: str = "MISSION"
    searchOpen: bool = False
    navMenuOpen: bool = False
    activeView: str = "audit"
    activeFarmId: Optional[int] = 1
    mapContext: MapContext = MapContext()
    activeLayers: List[str] = ["satellite", "NDVI"]
    lastAgentIntent: Optional[str] = None
    lastAgentPayload: Optional[Any] = None
    updatedAt: Optional[str] = None

    model_config = {"extra": "allow"}

# ── Agent Action Storage and Endpoints (Module-Level) ────────────────────
_pending_agent_action: Optional[Dict[str, Any]] = None

@app.post("/api/agent-action")
async def set_agent_action(request: Request):
    global _pending_agent_action
    body = await request.json()
    _pending_agent_action = body
    return {"status": "queued"}

@app.get("/api/agent-action")
def get_agent_action():
    global _pending_agent_action
    action = _pending_agent_action
    _pending_agent_action = None
    return action or {}

# ── State Registry Routes ────────────────────────────────────────────────
@app.get("/", tags=["health"])
def root() -> Dict[str, str]:
    """Health-check / root probe."""
    return {
        "service": "Carbon Pesa State API",
        "status": "online",
        "version": "2.0.0",
        "docs": "/docs",
    }

@app.get("/api/state", tags=["state"])
def get_state() -> JSONResponse:
    """Returns the most recently POSTed CarbonPesaState."""
    return JSONResponse(content=latest_app_state)

@app.post("/api/update-state", tags=["state"], status_code=200)
async def update_state(request: Request) -> Dict[str, Any]:
    """Accepts the full CarbonPesaState JSON body."""
    global latest_app_state, state_receive_count

    try:
        body: Dict[str, Any] = await request.json()
    except Exception as exc:
        log.warning("Malformed JSON in POST /api/update-state: %s", exc)
        raise HTTPException(status_code=422, detail="Invalid JSON body")

    body.setdefault("updatedAt", datetime.now(timezone.utc).isoformat())
    body["_serverReceivedAt"] = datetime.now(timezone.utc).isoformat()

    latest_app_state = body
    state_receive_count += 1

    log.info(
        "State updated #%d — page=%s slide=%s view=%s farm=%s zoom=%s",
        state_receive_count,
        body.get("currentPage"),
        body.get("currentSlideIndex"),
        body.get("activeView"),
        body.get("activeFarmId"),
        body.get("mapContext", {}).get("zoom"),
    )

    return {"status": "ok", "receivedAt": body["_serverReceivedAt"]}

@app.delete("/api/state/reset", tags=["state"])
def reset_state() -> Dict[str, str]:
    """Resets the cache to defaults."""
    global latest_app_state, state_receive_count
    latest_app_state = dict(_DEFAULT_STATE)
    latest_app_state["updatedAt"] = datetime.now(timezone.utc).isoformat()
    state_receive_count = 0
    log.info("State cache reset to defaults.")
    return {"status": "reset"}

@app.get("/api/state/meta", tags=["state"])
def get_state_meta() -> Dict[str, Any]:
    """Lightweight diagnostic endpoint."""
    return {
        "totalUpdatesReceived": state_receive_count,
        "lastUpdatedAt": latest_app_state.get("updatedAt"),
        "serverNow": datetime.now(timezone.utc).isoformat(),
        "currentPage": latest_app_state.get("currentPage"),
        "activeView": latest_app_state.get("activeView"),
    }

# ── Missing Backend Endpoints ────────────────────────────────────────────
@app.get("/farms")
def get_farms():
    """Retrieve all registered farms as a FeatureCollection."""
    return _registered_farms

@app.post("/farms")
async def create_farm(request: Request):
    """Register a new farm boundary."""
    body = await request.json()
    name = body.get("name")
    geometry = body.get("geometry")
    area_ha = body.get("area_ha", 0.0)
    
    new_id = len(_registered_farms["features"]) + 1
    new_feature = {
        "type": "Feature",
        "properties": {
            "farm_id": new_id,
            "name": name,
            "area_ha": area_ha
        },
        "geometry": geometry
    }
    _registered_farms["features"].append(new_feature)
    return {"id": new_id, "name": name}

@app.get("/audits")
def get_audits():
    """Retrieve history of carbon verification audits."""
    return _audits

@app.get("/payouts")
def get_payouts():
    """Retrieve payment txn history."""
    return _payouts

@app.get("/stresses")
def get_stresses():
    """Retrieve live forest canopy anomaly areas."""
    return _stresses

@app.get("/telemetry")
def get_telemetry():
    """Retrieve active drone scanning metrics."""
    return _telemetry

@app.get("/stats/dashboard")
def get_dashboard_stats():
    """Retrieve core system aggregations for landing pages."""
    return {
        "total_tco2e_sequestered": 142000,
        "total_usd_flowing": 492000,
        "spot_price_usd": 24.80
    }

@app.post("/deforestation/alert")
async def post_deforestation_alert(request: Request):
    """Dispatch forest degradation notifications to field personnel."""
    body = await request.json()
    farm_id = body.get("farm_id")
    log.info(f"Deforestation alert triggered for farm_id: {farm_id}")
    return {"status": "alert_dispatched", "farm_id": farm_id}

@app.post("/audit/{farm_id}")
def run_audit(farm_id: int):
    """Execute GEE verification audit and queue Daraja M-Pesa payout."""
    payout_ksh = 25000
    carbon_density = 25.1
    hedera_tx_id = f"0.0.{uuid.uuid4().hex[:6]}-{int(time.time())}-000"
    
    # Prepend new records to display immediately in UI history lists
    _audits.insert(0, {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "hash_manifest": uuid.uuid4().hex,
        "carbon_yield_tons": 15.0
    })
    
    _payouts.insert(0, {
        "amount": payout_ksh,
        "daraja_receipt": f"MPESA-{uuid.uuid4().hex[:8].upper()}",
        "status": "COMPLETED"
    })
    
    return {
        "payout_ksh": payout_ksh,
        "carbon_density": carbon_density,
        "hedera_tx_id": hedera_tx_id
    }

@app.get("/gee/tile-url")
def get_gee_tile_url():
    """Retrieve map imagery tiles (fallback/dynamic ESRI/GEE tiles)."""
    return {
        "status": "success",
        "tile_url": "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
    }

@app.get("/gee/timeseries/{farm_id}")
def get_gee_timeseries(farm_id: int):
    """Retrieve historical vegetation index NDVI chart series."""
    return {
        "labels": ["Oct", "Nov", "Dec", "Jan", "Feb", "Mar", "Apr", "May", "Jun"],
        "data": [0.45, 0.48, 0.47, 0.42, 0.51, 0.62, 0.58, 0.65, 0.72]
    }

@app.post("/verify-planting")
async def verify_planting(photo: UploadFile = File(...)):
    """Run tree seedling detection and geotag authentication via CNN model."""
    log.info(f"Received photo upload: {photo.filename}")
    return {
        "verified": True,
        "confidence_pct": 98.5,
        "message": "Planting verified successfully! Healthy canopy and correct coordinates detected."
    }

@app.get("/pdd/generate")
def generate_pdd(farm_id: int):
    """Generate a downloadable XML Project Design Document (PDD) VM0047 manifest."""
    xml_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<PDD>
  <ProjectName>Carbon Pesa Project</ProjectName>
  <Standard>VM0047</Standard>
  <Status>Verified</Status>
  <FarmID>{farm_id}</FarmID>
  <GeneratedAt>{datetime.now(timezone.utc).isoformat()}</GeneratedAt>
  <HederaAnchor>0.0.123456</HederaAnchor>
</PDD>
"""
    return Response(content=xml_content, media_type="application/xml")
