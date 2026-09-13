from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.anomaly.models import (
    TrainingResult,
    ScanResult,
    AnomalyScoreItem,
    AnomalyStatistics
)
from app.services.anomaly.service import anomaly_service

router = APIRouter()


class TrainRequest(BaseModel):
    limit: Optional[int] = Query(5000, ge=20, le=50000, description="Max training records")


class ScanRequest(BaseModel):
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    limit: Optional[int] = 5000
    persist: Optional[bool] = True


@router.post("/train", response_model=TrainingResult, summary="Train offline Isolation Forest anomaly baseline")
def train_anomaly_model(
    req: TrainRequest = TrainRequest(),
    db: Session = Depends(get_db)
):
    """
    Fits the offline unsupervised Isolation Forest baseline on normalized database events.
    Fails safely if fewer than the minimum required records exist.
    """
    try:
        return anomaly_service.train_baseline(db, limit=req.limit or 5000)
    except ValueError as val_err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(val_err)
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Model training failed: {str(exc)}"
        )


@router.post("/scan", response_model=ScanResult, summary="Scan normalized events for statistical anomalies")
def scan_events_for_anomalies(
    req: ScanRequest = ScanRequest(),
    db: Session = Depends(get_db)
):
    """
    Evaluates events with the anomaly baseline, computes normalized anomaly scores,
    generates deterministic explanations, and persists results.
    """
    try:
        return anomaly_service.scan_events(
            db=db,
            start_time=req.start_time,
            end_time=req.end_time,
            limit=req.limit or 5000,
            persist=req.persist if req.persist is not None else True
        )
    except ValueError as val_err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(val_err)
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Anomaly scan failed: {str(exc)}"
        )


@router.get("/results", response_model=List[AnomalyScoreItem], summary="List detected anomaly records")
def get_anomaly_results(
    is_anomaly_only: bool = Query(True, description="Filter for flagged anomalies only"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """Retrieves persisted anomaly scoring records and structured explanations."""
    return anomaly_service.get_results(
        db=db,
        is_anomaly_only=is_anomaly_only,
        limit=limit,
        offset=offset
    )


@router.get("/results/{event_id}", response_model=AnomalyScoreItem, summary="Get anomaly evaluation for an event")
def get_anomaly_for_event(
    event_id: str,
    db: Session = Depends(get_db)
):
    """Retrieves anomaly score and explanation for a specific normalized event."""
    result = anomaly_service.get_result_by_event_id(db, event_id)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No anomaly record found for event '{event_id}'."
        )
    return result


@router.get("/statistics", response_model=AnomalyStatistics, summary="Get anomaly detection metrics")
def get_anomaly_statistics(db: Session = Depends(get_db)):
    """Returns anomaly frequency rate, total scanned, and model metadata."""
    return anomaly_service.get_statistics(db)
