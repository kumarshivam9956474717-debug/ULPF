from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.auth import require_roles
from app.models.user import User
from app.services.ingestion.detector import detect_format
from app.services.pipeline import PipelineService
from app.schemas.ingest import (
    FormatDetectionRequest,
    FormatDetectionResponse,
    SingleIngestRequest,
    SingleIngestResponse,
    BatchIngestRequest,
    BatchIngestResponse,
)

router = APIRouter()


@router.post(
    "/detect-format",
    response_model=FormatDetectionResponse,
    summary="Detect raw log format offline",
    description="Analyzes a raw log string and returns detected format, confidence score, and heuristic explanation without persisting data."
)
def api_detect_format(
    payload: FormatDetectionRequest,
    _: User = Depends(require_roles("ADMIN", "OPERATOR", "ANALYST"))
) -> FormatDetectionResponse:
    res = detect_format(payload.raw_payload)
    return FormatDetectionResponse(
        detected_format=res.detected_format,
        confidence=res.confidence,
        reason=res.reason
    )


@router.post(
    "/ingest",
    response_model=SingleIngestResponse,
    status_code=status.HTTP_200_OK,
    summary="Ingest, parse, normalize, and persist a single raw log event",
    description="End-to-end processing pipeline for a single log event. Guarantees verbatim raw storage even upon parsing failure."
)
def api_ingest_single(
    payload: SingleIngestRequest,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("ADMIN", "OPERATOR"))
) -> SingleIngestResponse:
    res = PipelineService.process_event(
        raw_payload=payload.raw_payload,
        db=db,
        source_id=payload.source_id,
        source_format_hint=payload.format_hint,
        commit=True
    )
    return SingleIngestResponse(
        success=res.success,
        raw_event_id=res.raw_event_id,
        normalized_event_id=res.normalized_event_id,
        detected_format=res.detected_format,
        parser_id=res.parser_id,
        parser_version=res.parser_version,
        validation_status=res.validation_status,
        onboarding_available=res.onboarding_available,
        errors=res.errors,
        warnings=res.warnings,
        normalized_event=res.normalized_event
    )


@router.post(
    "/ingest/batch",
    response_model=BatchIngestResponse,
    status_code=status.HTTP_200_OK,
    summary="Batch ingest and normalize raw logs",
    description="Bounded batch ingestion updating ProcessingRun operational telemetry and returning batch statistics."
)
def api_ingest_batch(
    payload: BatchIngestRequest,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("ADMIN", "OPERATOR"))
) -> BatchIngestResponse:
    res = PipelineService.process_batch(
        events=payload.events,
        db=db,
        source_id=payload.source_id
    )
    return BatchIngestResponse(
        processing_run_id=res.processing_run_id,
        total_received=res.total_received,
        total_parsed=res.total_parsed,
        total_normalized=res.total_normalized,
        total_failed=res.total_failed,
        processing_time_ms=res.processing_time_ms,
        format_statistics=res.format_statistics,
        parser_statistics=res.parser_statistics
    )
