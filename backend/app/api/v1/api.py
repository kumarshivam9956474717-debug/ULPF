from fastapi import APIRouter
from app.api.v1.endpoints import (
    health,
    auth,
    sources,
    parsers,
    events,
    runs,
    ingest,
    syslog,
    analytics,
    anomaly,
    onboarding,
    security_analytics,
    supervisory,
    demo,
)

api_router = APIRouter()
api_router.include_router(health.router, tags=["System Health"])
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication & Access Control"])
api_router.include_router(demo.router, prefix="/demo", tags=["SIH Demonstration Mode"])
api_router.include_router(ingest.router, tags=["Ingestion & Parsing"])
api_router.include_router(onboarding.router, prefix="/onboarding", tags=["No-Code Log Onboarding"])
api_router.include_router(syslog.router, prefix="/syslog", tags=["Live Syslog Listener"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["Analytics & Parquet Export"])
api_router.include_router(security_analytics.router, prefix="/security-analytics", tags=["Security Analytics & Data Quality"])
api_router.include_router(supervisory.router, prefix="/supervisory", tags=["Supervisory Intelligence"])
api_router.include_router(anomaly.router, prefix="/anomaly", tags=["Offline Anomaly Detection"])
api_router.include_router(sources.router, prefix="/sources", tags=["Log Sources"])
api_router.include_router(parsers.router, prefix="/parsers", tags=["Parsers"])
api_router.include_router(events.router, prefix="/events", tags=["Universal Events"])
api_router.include_router(runs.router, prefix="/processing-runs", tags=["Processing Runs"])




