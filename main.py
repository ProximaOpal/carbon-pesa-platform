# =======================================================================
# CARBON PESA — Python Backend (main.py)
# FastAPI server: receives state POSTs from the JS frontend,
# serves the latest state to n8n / AI Workflow Coordinator.
#
# Run locally:
#   pip install fastapi uvicorn
#   uvicorn main:app --reload --port 8000
#
# Deploy on Render (matches frontend URL):
#   Start command: uvicorn main:app --host 0.0.0.0 --port $PORT
# =======================================================================

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional  # BUG FIX: use typing module for 3.8 compat

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
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
        "with the n8n AI Workflow Coordinator. The frontend POSTs its "
        "CarbonPesaState on every meaningful interaction; n8n GETs it to "
        "gain situational awareness before executing AI workflows."
    ),
    version="2.0.0",
)

# ── CORS — allow the frontend origin (Render + localhost dev) ────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://proxima-opal-platform-1.onrender.com",   # production frontend
        "http://localhost:3000",               # local dev
        "http://localhost:5500",               # VS Code Live Server
        "http://127.0.0.1:5500",
        "null",                               # file:// opened locally
    ],
    allow_origin_regex=r"https://.*\.onrender\.com",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── In-Memory Cache ──────────────────────────────────────────────────────
# Single source of truth — replaced atomically on every POST.
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

# ── Pydantic schema (loose — accepts any extra fields the JS sends) ──────
class MapContext(BaseModel):
    lat: float = -0.5023
    lng: float = 35.4156
    zoom: int = 15

class CarbonPesaState(BaseModel):
    currentPage: str = "Unknown"
    currentSlideIndex: int = Field(0)  # No range cap — AI/frontend may suggest any index
    currentSlideHeading: str = "MISSION"
    searchOpen: bool = False
    navMenuOpen: bool = False
    activeView: str = "audit"
    activeFarmId: Optional[int] = 1
    mapContext: MapContext = MapContext()
    activeLayers: List[str] = ["satellite", "NDVI"]  # BUG FIX: list[str] is 3.9+ only
    lastAgentIntent: Optional[str] = None
    lastAgentPayload: Optional[Any] = None
    updatedAt: Optional[str] = None
    _pending_agent_action: dict | None = None

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

    # allow extra fields without rejecting the request
    model_config = {"extra": "allow"}

# ── Routes ───────────────────────────────────────────────────────────────

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
    """
    **GET /api/state** — used by n8n's 'Fetch Internal App State' node.

    Returns the most recently POSTed CarbonPesaState so the AI Workflow
    Coordinator knows exactly which page, farm, slide, and map region the
    operator is looking at before executing any workflow.

    Fixes the n8n 'Resource Not Found' 404 error.
    """
    return JSONResponse(content=latest_app_state)


@app.post("/api/update-state", tags=["state"], status_code=200)
async def update_state(request: Request) -> Dict[str, Any]:
    """
    **POST /api/update-state** — called by the JavaScript state-manager.

    Accepts the full CarbonPesaState JSON body (debounced 500ms on the
    frontend) and stores it in the in-memory cache.  Responds immediately
    so map-pan latency is unaffected.

    The endpoint is intentionally permissive: unknown keys are preserved
    so future JS-side additions do not require backend changes.
    """
    global latest_app_state, state_receive_count

    try:
        body: Dict[str, Any] = await request.json()
    except Exception as exc:
        log.warning("Malformed JSON in POST /api/update-state: %s", exc)
        raise HTTPException(status_code=422, detail="Invalid JSON body")

    # Stamp server-side receipt time alongside the client timestamp
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
    """
    **DELETE /api/state/reset** — resets the cache to defaults.
    Useful for testing / CI without restarting the server.
    """
    global latest_app_state, state_receive_count
    latest_app_state = dict(_DEFAULT_STATE)
    latest_app_state["updatedAt"] = datetime.now(timezone.utc).isoformat()
    state_receive_count = 0
    log.info("State cache reset to defaults.")
    return {"status": "reset"}


@app.get("/api/state/meta", tags=["state"])
def get_state_meta() -> Dict[str, Any]:
    """
    **GET /api/state/meta** — lightweight diagnostic endpoint.
    Returns counts and timestamps without the full state blob.
    """
    return {
        "totalUpdatesReceived": state_receive_count,
        "lastUpdatedAt": latest_app_state.get("updatedAt"),
        "serverNow": datetime.now(timezone.utc).isoformat(),
        "currentPage": latest_app_state.get("currentPage"),
        "activeView": latest_app_state.get("activeView"),
    }
