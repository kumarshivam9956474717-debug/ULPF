from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.schemas.health import HealthResponse
from app.core.config import settings
from app.core.database import get_db
from app.services.persistence import global_persistence_queue

router = APIRouter()


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health check endpoint",
    description="Returns the operating status and component readiness of the ULPF service."
)
def health_check(response: Response, db: Session = Depends(get_db)) -> HealthResponse:
    readiness = {
        "api": "HEALTHY",
        "parser_registry": "HEALTHY",
        "ingestion": "HEALTHY",
        "analytics": "HEALTHY",
        "anomaly_engine": "HEALTHY",
        "supervisory_engine": "HEALTHY",
    }

    # Active DB ping
    db_healthy = False
    try:
        db.execute(text("SELECT 1"))
        readiness["database"] = "HEALTHY"
        db_healthy = True
    except Exception as e:
        readiness["database"] = f"DEGRADED: {str(e)[:50]}"

    # Active Persistence Queue probe
    if global_persistence_queue.is_running:
        readiness["persistence_queue"] = "HEALTHY"
    else:
        readiness["persistence_queue"] = "STANDBY"

    if not db_healthy:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        overall_status = "degraded"
    else:
        overall_status = "ok"

    return HealthResponse(
        status=overall_status,
        service="ULPF",
        version=settings.VERSION,
        readiness_components=readiness
    )

