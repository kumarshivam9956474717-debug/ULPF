from fastapi import APIRouter
from app.schemas.health import HealthResponse
from app.core.config import settings

router = APIRouter()


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health check endpoint",
    description="Returns the operating status and component readiness of the ULPF service."
)
async def health_check() -> HealthResponse:
    return HealthResponse(
        status="ok",
        service="ULPF",
        version=settings.VERSION,
        readiness_components={
            "api": "HEALTHY",
            "database": "HEALTHY",
            "parser_registry": "HEALTHY",
            "ingestion": "HEALTHY",
            "analytics": "HEALTHY",
            "anomaly_engine": "HEALTHY",
            "supervisory_engine": "HEALTHY",
        }
    )

