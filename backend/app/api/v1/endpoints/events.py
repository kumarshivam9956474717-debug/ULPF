from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import desc
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.normalized_event import NormalizedEvent
from app.schemas.universal_event import UniversalEvent, RawEventTraceabilityResponse
from app.services.integrity import verify_raw_event_record

router = APIRouter()


@router.get(
    "",
    response_model=List[UniversalEvent],
    summary="List normalized universal events",
    description="Fetches a paginated list of normalized events adhering to the Universal Event Schema."
)
def list_normalized_events(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    vendor: Optional[str] = None,
    severity: Optional[str] = None,
    action: Optional[str] = None,
    db: Session = Depends(get_db)
) -> List[UniversalEvent]:
    query = db.query(NormalizedEvent)
    if vendor:
        query = query.filter(NormalizedEvent.vendor == vendor)
    if severity:
        query = query.filter(NormalizedEvent.severity == severity)
    if action:
        query = query.filter(NormalizedEvent.action == action)

    events = query.order_by(desc(NormalizedEvent.timestamp)).offset(offset).limit(limit).all()

    return [
        UniversalEvent(
            event_id=e.event_id,
            source_event_id=e.source_event_id,
            schema_version=e.schema_version,
            timestamp=e.timestamp,
            ingestion_timestamp=e.ingestion_timestamp,
            timezone=e.timezone,
            vendor=e.vendor,
            product=e.product,
            device_type=e.device_type,
            device_id=e.device_id,
            hostname=e.hostname,
            source_format=e.source_format,
            source_ip=e.source_ip,
            source_port=e.source_port,
            destination_ip=e.destination_ip,
            destination_port=e.destination_port,
            protocol=e.protocol,
            username=e.username,
            user_id=e.user_id,
            authentication_method=e.authentication_method,
            event_type=e.event_type,
            action=e.action,
            outcome=e.outcome,
            severity=e.severity,
            category=e.category,
            subcategory=e.subcategory,
            interface=e.interface,
            direction=e.direction,
            zone=e.zone,
            threat_name=e.threat_name,
            threat_id=e.threat_id,
            signature_id=e.signature_id,
            rule_id=e.rule_id,
            message=e.message,
            tags=e.tags or [],
            custom_fields=e.custom_fields or {},
            raw_event_id=e.raw_event_id,
            parser_id=e.parser_id,
            parser_version=e.parser_version,
            normalization_version=e.normalization_version,
            raw_event=e.raw_event.raw_payload if e.raw_event else ""
        )
        for e in events
    ]




@router.get(
    "/{event_id}",
    response_model=UniversalEvent,
    summary="Get normalized universal event by ID",
    description="Fetches an analytics-ready normalized event adhering to Universal Event Schema."
)
def get_normalized_event(
    event_id: str,
    db: Session = Depends(get_db)
) -> UniversalEvent:
    event = db.query(NormalizedEvent).filter(NormalizedEvent.event_id == event_id).first()
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Normalized event '{event_id}' not found."
        )

    # Build UniversalEvent schema object with raw_event from relation if present
    raw_payload = event.raw_event.raw_payload if event.raw_event else ""
    return UniversalEvent(
        event_id=event.event_id,
        source_event_id=event.source_event_id,
        schema_version=event.schema_version,
        timestamp=event.timestamp,
        ingestion_timestamp=event.ingestion_timestamp,
        timezone=event.timezone,
        vendor=event.vendor,
        product=event.product,
        device_type=event.device_type,
        device_id=event.device_id,
        hostname=event.hostname,
        source_format=event.source_format,
        source_ip=event.source_ip,
        source_port=event.source_port,
        destination_ip=event.destination_ip,
        destination_port=event.destination_port,
        protocol=event.protocol,
        username=event.username,
        user_id=event.user_id,
        authentication_method=event.authentication_method,
        event_type=event.event_type,
        action=event.action,
        outcome=event.outcome,
        severity=event.severity,
        category=event.category,
        subcategory=event.subcategory,
        interface=event.interface,
        direction=event.direction,
        zone=event.zone,
        threat_name=event.threat_name,
        threat_id=event.threat_id,
        signature_id=event.signature_id,
        rule_id=event.rule_id,
        message=event.message,
        tags=event.tags or [],
        custom_fields=event.custom_fields or {},
        raw_event_id=event.raw_event_id,
        parser_id=event.parser_id,
        parser_version=event.parser_version,
        normalization_version=event.normalization_version,
        raw_event=raw_payload
    )


@router.get(
    "/{event_id}/raw",
    response_model=RawEventTraceabilityResponse,
    summary="Trace normalized event to original raw log payload",
    description="Answers: 'Show me the original raw event from which this normalized event was generated.' Also performs cryptographic SHA-256 integrity verification."
)
def get_original_raw_event(
    event_id: str,
    db: Session = Depends(get_db)
) -> RawEventTraceabilityResponse:
    event = db.query(NormalizedEvent).filter(NormalizedEvent.event_id == event_id).first()
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Normalized event '{event_id}' not found."
        )

    raw = event.raw_event
    if not raw:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Traceability broken: Raw event pointer '{event.raw_event_id}' does not resolve to an existing record."
        )

    integrity_result = verify_raw_event_record(raw)

    return RawEventTraceabilityResponse(
        event_id=event.event_id,
        raw_event_id=raw.raw_event_id,
        source_id=raw.source_id,
        received_at=raw.received_at,
        raw_payload=raw.raw_payload,
        payload_encoding=raw.payload_encoding,
        payload_hash_sha256=raw.payload_hash_sha256,
        source_format=raw.source_format,
        ingestion_batch_id=raw.ingestion_batch_id,
        created_at=raw.created_at,
        integrity=integrity_result
    )
