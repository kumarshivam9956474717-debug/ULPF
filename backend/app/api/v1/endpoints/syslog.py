from fastapi import APIRouter, HTTPException, status
from typing import Dict, Any
from app.core.config import settings
from app.services.syslog.manager import syslog_manager
from app.services.syslog.metrics import syslog_metrics

router = APIRouter()


@router.get("/status", response_model=Dict[str, Any], summary="Get live Syslog listener and queue status")
async def get_syslog_status():
    """
    Returns operational status of the live Syslog transport listeners (UDP, TCP, TLS),
    queue depth, active connections, and throughput metrics.
    """
    return syslog_manager.get_status()


@router.post("/start", response_model=Dict[str, Any], summary="Start Syslog listeners and worker pool")
async def start_syslog_service():
    """
    Administratively start the Syslog listeners and worker pool if enabled in settings.
    """
    if not settings.SYSLOG_ALLOW_API_CONTROL:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Syslog API runtime control is disabled by server configuration."
        )

    if syslog_manager.is_running:
        return {"message": "Syslog service is already running.", "status": syslog_manager.get_status()}

    await syslog_manager.start()
    return {"message": "Syslog service started successfully.", "status": syslog_manager.get_status()}


@router.post("/stop", response_model=Dict[str, Any], summary="Stop Syslog listeners and worker pool")
async def stop_syslog_service():
    """
    Administratively perform graceful shutdown of Syslog listeners and worker pool.
    """
    if not settings.SYSLOG_ALLOW_API_CONTROL:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Syslog API runtime control is disabled by server configuration."
        )

    if not syslog_manager.is_running:
        return {"message": "Syslog service is already stopped.", "status": syslog_manager.get_status()}

    await syslog_manager.stop()
    return {"message": "Syslog service stopped successfully.", "status": syslog_manager.get_status()}


@router.post("/metrics/reset", response_model=Dict[str, Any], summary="Reset Syslog telemetry metrics")
async def reset_syslog_metrics():
    """
    Resets the operational counters and throughput metrics (for benchmark/testing runs).
    """
    if not settings.SYSLOG_ALLOW_API_CONTROL:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Syslog API runtime control is disabled by server configuration."
        )

    syslog_metrics.reset()
    return {"message": "Syslog metrics reset successfully.", "metrics": syslog_metrics.snapshot()}
