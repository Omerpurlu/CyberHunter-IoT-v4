import logging

from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import JSONResponse
from sqlalchemy.exc import (
    OperationalError,
    SQLAlchemyError,
    TimeoutError as SQLAlchemyTimeoutError,
)
from sqlalchemy.orm import Session

from dependencies import get_db
from repositories.security_event_repository import SecurityEventRepository
from schemas.security_event import (
    Esp32AssessmentRead,
    PersistenceResult,
    SecurityEventInput,
    SecurityEventListResponse,
    SecurityEventRead,
)
from services.security_event_service import SecurityEventService


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/security-events", tags=["security-events"])

EXAMPLE_EVENT_ID = "evt-20260722T131306Z-a7c9f2"
OPENAPI_RESPONSES = {
    201: {
        "model": PersistenceResult,
        "description": "A new security event and assessment were created.",
        "content": {
            "application/json": {
                "example": {
                    "success": True,
                    "event_id": EXAMPLE_EVENT_ID,
                    "status": "created",
                    "duplicate": False,
                    "retryable": False,
                }
            }
        },
    },
    200: {
        "model": PersistenceResult,
        "description": "Duplicate event; idempotent success.",
        "content": {
            "application/json": {
                "example": {
                    "success": True,
                    "event_id": EXAMPLE_EVENT_ID,
                    "status": "duplicate",
                    "duplicate": True,
                    "retryable": False,
                }
            }
        },
    },
    409: {
        "model": PersistenceResult,
        "description": "The event ID or assessment already has a different payload.",
        "content": {
            "application/json": {
                "examples": {
                    "event_conflict": {
                        "summary": "Event payload conflict",
                        "value": {
                            "success": False,
                            "event_id": EXAMPLE_EVENT_ID,
                            "status": "conflict",
                            "error_code": "EVENT_ID_CONFLICT",
                            "duplicate": False,
                            "retryable": False,
                        },
                    },
                    "assessment_conflict": {
                        "summary": "Assessment payload conflict",
                        "value": {
                            "success": False,
                            "event_id": EXAMPLE_EVENT_ID,
                            "status": "conflict",
                            "error_code": "ASSESSMENT_CONFLICT",
                            "duplicate": False,
                            "retryable": False,
                        },
                    },
                }
            }
        },
    },
    422: {
        "description": (
            "FastAPI request validation error, or a PersistenceResult with "
            "VALIDATION_ERROR or INTEGRITY_ERROR."
        ),
        "content": {
            "application/json": {
                "examples": {
                    "request_validation": {
                        "summary": "FastAPI request validation error",
                        "value": {
                            "detail": [
                                {
                                    "loc": ["body", "timestamp"],
                                    "msg": "Input should have timezone info",
                                    "type": "timezone_aware",
                                }
                            ]
                        },
                    },
                    "service_validation": {
                        "summary": "Service validation error",
                        "value": {
                            "success": False,
                            "event_id": EXAMPLE_EVENT_ID,
                            "status": "rejected",
                            "error_code": "VALIDATION_ERROR",
                            "duplicate": False,
                            "retryable": False,
                        },
                    },
                    "integrity_error": {
                        "summary": "Database integrity error",
                        "value": {
                            "success": False,
                            "event_id": EXAMPLE_EVENT_ID,
                            "status": "rejected",
                            "error_code": "INTEGRITY_ERROR",
                            "duplicate": False,
                            "retryable": False,
                        },
                    },
                }
            }
        },
    },
    500: {
        "model": PersistenceResult,
        "description": "Database error or internal persistence error.",
        "content": {
            "application/json": {
                "example": {
                    "success": False,
                    "event_id": EXAMPLE_EVENT_ID,
                    "status": "error",
                    "error_code": "INTERNAL_PERSISTENCE_ERROR",
                    "duplicate": False,
                    "retryable": False,
                }
            }
        },
    },
    503: {
        "model": PersistenceResult,
        "description": "PostgreSQL is unavailable or the operation timed out.",
        "content": {
            "application/json": {
                "example": {
                    "success": False,
                    "event_id": EXAMPLE_EVENT_ID,
                    "status": "temporarily_unavailable",
                    "error_code": "DATABASE_UNAVAILABLE",
                    "duplicate": False,
                    "retryable": True,
                }
            }
        },
    },
}

ENDPOINT_DESCRIPTION = """
Stores a security event that has already been validated by the Raspberry Pi
Bridge. AES, I²C, CRC, frame, and ESP32 validation are outside this endpoint's
responsibility.

- A new event and assessment return `201`.
- The same event and payload return `200` with `status="duplicate"`.
- The same `event_id` with a different payload returns `409`.
- Temporary PostgreSQL failures return `503` with `retryable=true`.

Do not expose this endpoint to the public internet without production
authentication. The authentication mechanism will be agreed with the Bridge
team.
"""


def get_security_event_service(
    db: Session = Depends(get_db),
) -> SecurityEventService:
    repository = SecurityEventRepository(db)
    return SecurityEventService(repository)


def get_security_event_repository(
    db: Session = Depends(get_db),
) -> SecurityEventRepository:
    return SecurityEventRepository(db)


@router.get(
    "",
    response_model=SecurityEventListResponse,
    summary="List CyberHunter security events",
)
def list_security_events(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    repository: SecurityEventRepository = Depends(
        get_security_event_repository
    ),
) -> SecurityEventListResponse | JSONResponse:
    try:
        rows = repository.list_security_events(limit=limit, offset=offset)
        items = []
        for event, assessment in rows:
            assessment_response = None
            if assessment is not None:
                assessment_response = Esp32AssessmentRead(
                    device_id=assessment.device_id,
                    risk_score=assessment.esp32_risk_score,
                    decision=assessment.esp32_decision,
                    processed=assessment.esp32_processed,
                    assessed_at=assessment.assessed_at,
                    received_at=assessment.received_at,
                )
            items.append(
                SecurityEventRead(
                    event_id=event.event_id,
                    event_timestamp=event.event_timestamp,
                    source_ip=str(event.source_ip),
                    destination_port=event.destination_port,
                    protocol=event.protocol,
                    event_type=event.event_type,
                    command=event.command,
                    tactic=event.tactic,
                    input_risk_score=event.input_risk_score,
                    received_at=event.received_at,
                    assessment=assessment_response,
                )
            )
        return SecurityEventListResponse(
            items=items,
            limit=limit,
            offset=offset,
            count=len(items),
        )
    except (OperationalError, SQLAlchemyTimeoutError) as exc:
        logger.error(
            "Security event read failed layer=endpoint "
            "error_code=DATABASE_UNAVAILABLE exception_type=%s",
            type(exc).__name__,
        )
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "detail": "Security event data is temporarily unavailable."
            },
        )
    except SQLAlchemyError as exc:
        logger.error(
            "Security event read failed layer=endpoint "
            "error_code=DATABASE_ERROR exception_type=%s",
            type(exc).__name__,
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "Security event data could not be read."},
        )
    except Exception as exc:
        logger.error(
            "Security event read failed layer=endpoint "
            "error_code=INTERNAL_READ_ERROR exception_type=%s",
            type(exc).__name__,
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "Security event data could not be read."},
        )


def persistence_http_status(result: PersistenceResult) -> int:
    if result.status == "created" and result.success:
        return status.HTTP_201_CREATED
    if result.status == "duplicate" and result.success:
        return status.HTTP_200_OK

    error_statuses = {
        "VALIDATION_ERROR": status.HTTP_422_UNPROCESSABLE_CONTENT,
        "INTEGRITY_ERROR": status.HTTP_422_UNPROCESSABLE_CONTENT,
        "EVENT_ID_CONFLICT": status.HTTP_409_CONFLICT,
        "ASSESSMENT_CONFLICT": status.HTTP_409_CONFLICT,
        "DATABASE_UNAVAILABLE": status.HTTP_503_SERVICE_UNAVAILABLE,
        "DATABASE_TIMEOUT": status.HTTP_503_SERVICE_UNAVAILABLE,
        "DATABASE_ERROR": status.HTTP_500_INTERNAL_SERVER_ERROR,
        "INTERNAL_PERSISTENCE_ERROR": status.HTTP_500_INTERNAL_SERVER_ERROR,
    }
    return error_statuses.get(
        result.error_code,
        status.HTTP_500_INTERNAL_SERVER_ERROR,
    )


@router.post(
    "",
    response_model=PersistenceResult,
    status_code=status.HTTP_201_CREATED,
    summary="Store a validated CyberHunter security event",
    description=ENDPOINT_DESCRIPTION,
    responses=OPENAPI_RESPONSES,
)
def create_security_event(
    payload: SecurityEventInput,
    service: SecurityEventService = Depends(get_security_event_service),
):
    # Do not expose this unauthenticated ingestion endpoint to the public
    # internet. Bridge authentication will be defined with the Bridge team.
    try:
        result = service.persist(payload)
    except Exception as exc:
        logger.error(
            "Security event endpoint failed "
            "layer=%s event_id=%s error_code=%s exception_type=%s",
            "endpoint",
            payload.event_id,
            "INTERNAL_PERSISTENCE_ERROR",
            type(exc).__name__,
        )
        result = PersistenceResult(
            success=False,
            event_id=payload.event_id,
            status="error",
            error_code="INTERNAL_PERSISTENCE_ERROR",
        )

    return JSONResponse(
        status_code=persistence_http_status(result),
        content=result.model_dump(mode="json", exclude_none=True),
    )
