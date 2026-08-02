from datetime import datetime, timezone
import logging
import time

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from database import engine
from schemas.system_status import HealthResponse


logger = logging.getLogger(__name__)
router = APIRouter(tags=["health"])


@router.get("/api/health", response_model=HealthResponse, summary="Check FastAPI and PostgreSQL health")
def health():
    started = time.perf_counter()
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1")).scalar_one()
        query_ms = round((time.perf_counter() - started) * 1000, 3)
        payload = {
            "status": "healthy",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "fastapi": {"status": "healthy"},
            "postgresql": {"status": "healthy", "query_ms": query_ms, "error": None},
        }
        return JSONResponse(status_code=200, content=payload)
    except SQLAlchemyError as exc:
        logger.error("Health check failed error_code=DATABASE_UNAVAILABLE exception_type=%s", type(exc).__name__)
    except Exception as exc:
        logger.error("Health check failed error_code=DATABASE_UNAVAILABLE exception_type=%s", type(exc).__name__)
    payload = {
        "status": "degraded",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "fastapi": {"status": "healthy"},
        "postgresql": {"status": "unavailable", "query_ms": None, "error": "database_unavailable"},
    }
    return JSONResponse(status_code=503, content=payload)
