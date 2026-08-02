import logging
import os

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from dependencies import get_db
from repositories.system_status_repository import SystemStatusRepository
from schemas.system_status import HeartbeatInput, HeartbeatResponse, SystemStatusResponse
from services.system_status_service import SystemStatusService, validate_heartbeat_thresholds


router = APIRouter(prefix="/api/system", tags=["system"])
logger = logging.getLogger(__name__)


def heartbeat_settings() -> tuple[list[tuple[str, str]], int, int]:
    expected = [
        ("raspberry_pi", os.getenv("EXPECTED_RASPBERRY_PI_ID", "raspberry-pi-01")),
        ("esp32", os.getenv("EXPECTED_ESP32_ID", "esp32-cyberhunter-01")),
    ]
    online = int(os.getenv("HEARTBEAT_ONLINE_THRESHOLD_SECONDS", "30"))
    offline = int(os.getenv("HEARTBEAT_OFFLINE_THRESHOLD_SECONDS", "60"))
    validate_heartbeat_thresholds(online, offline)
    return expected, online, offline


def get_system_status_service(db: Session = Depends(get_db)) -> SystemStatusService:
    return SystemStatusService(SystemStatusRepository(db))


@router.post(
    "/heartbeat",
    response_model=HeartbeatResponse,
    responses={200: {"description": "Updated or idempotent duplicate heartbeat."}, 201: {"description": "First heartbeat created."}, 409: {"description": "Stale or equal sequence with a different payload."}, 500: {"description": "Sanitized internal persistence error."}, 503: {"description": "Database unavailable."}},
    summary="Store a component heartbeat",
    description=(
        "Stores a Raspberry Pi or ESP32 heartbeat using monotonic sequence semantics. "
        "Authentication is not implemented yet; sequence numbers are not authentication."
    ),
)
def post_heartbeat(payload: HeartbeatInput, service: SystemStatusService = Depends(get_system_status_service)):
    # Authentication will be added with the device security design. Sequence is only replay ordering.
    try:
        result = service.heartbeat(payload)
        return JSONResponse(status_code=result.http_status, content=result.response.model_dump(mode="json"))
    except Exception as exc:
        logger.error(
            "Heartbeat endpoint failed error_code=INTERNAL_PERSISTENCE_ERROR exception_type=%s",
            type(exc).__name__,
        )
        response = HeartbeatResponse(
            component_type=payload.component_type,
            component_id=payload.component_id,
            accepted_sequence=payload.sequence,
            result="error",
            last_seen=None,
            error_code="INTERNAL_PERSISTENCE_ERROR",
        )
        return JSONResponse(status_code=500, content=response.model_dump(mode="json"))


@router.get("/status", response_model=SystemStatusResponse, summary="Read expected component status")
def get_system_status(service: SystemStatusService = Depends(get_system_status_service)):
    expected, online, offline = heartbeat_settings()
    return service.status(expected=expected, online_threshold=online, offline_threshold=offline)
