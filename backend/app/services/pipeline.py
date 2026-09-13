import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.models.raw_event import RawEvent
from app.models.normalized_event import NormalizedEvent
from app.models.validation_result import ValidationResult
from app.models.processing_run import ProcessingRun
from app.schemas.universal_event import UniversalEvent
from app.services.ingestion.service import IngestionService
from app.services.ingestion.detector import detect_format
from app.services.parsers.registry import default_parser_registry
from app.services.normalization.service import NormalizationService
from app.services.validation.service import ValidationService


class SingleEventResult(BaseModel):
    success: bool
    raw_event_id: str
    normalized_event_id: Optional[str] = None
    detected_format: str
    parser_id: Optional[str] = None
    parser_version: Optional[str] = None
    validation_status: str
    onboarding_available: bool = False
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    normalized_event: Optional[Dict[str, Any]] = None


class BatchProcessingResult(BaseModel):
    processing_run_id: str
    total_received: int
    total_parsed: int
    total_normalized: int
    total_failed: int
    processing_time_ms: int
    format_statistics: Dict[str, int] = Field(default_factory=dict)
    parser_statistics: Dict[str, int] = Field(default_factory=dict)
    events: List[SingleEventResult] = Field(default_factory=list)


class PipelineService:
    """
    End-to-end log processing pipeline coordinating:
    Ingestion -> Format Detection -> Parsing -> Normalization -> Validation -> Persistence.
    """

    @staticmethod
    def process_event(
        raw_payload: Union[str, bytes, Dict[str, Any]],
        db: Session,
        source_id: Optional[str] = None,
        source_format_hint: Optional[str] = None,
        run_id: Optional[str] = None,
        commit: bool = True
    ) -> SingleEventResult:
        """
        Executes the full pipeline for a single log event.
        Guarantees lossless raw persistence even if parsing or validation fails.
        """
        errors: List[str] = []
        warnings: List[str] = []

        # 1. Ingestion & Lossless Raw Persistence
        raw_event = IngestionService.ingest_payload(
            data=raw_payload,
            db=db,
            source_id=source_id,
            source_format_hint=source_format_hint,
            ingestion_batch_id=run_id
        )

        raw_text = raw_event.raw_payload

        # 2. Format Detection
        if source_format_hint:
            detected_format = source_format_hint.lower()
        else:
            det_result = detect_format(raw_text)
            detected_format = det_result.detected_format

        # 3. Parser Selection
        parser = default_parser_registry.select_parser(
            detected_format=detected_format,
            payload=raw_text,
            parser_id_hint=None
        )

        if not parser:
            is_unknown = (detected_format.lower() == "unknown")
            errors.append(f"No compatible parser found for detected format '{detected_format}'.")
            if commit:
                db.commit()
            return SingleEventResult(
                success=False,
                raw_event_id=raw_event.raw_event_id,
                detected_format=detected_format,
                validation_status="unknown_format" if is_unknown else "invalid",
                onboarding_available=is_unknown,
                errors=errors,
                warnings=warnings
            )

        # 4. Parsing
        parsed_event = parser.parse(raw_text)
        if parsed_event.warnings:
            warnings.extend(parsed_event.warnings)
        if parsed_event.errors:
            errors.extend(parsed_event.errors)

        if errors:
            # Parsing fatal error: Raw event remains safely persisted in DB!
            if commit:
                db.commit()
            return SingleEventResult(
                success=False,
                raw_event_id=raw_event.raw_event_id,
                detected_format=detected_format,
                parser_id=parser.parser_id,
                parser_version=parser.parser_version,
                validation_status="invalid",
                errors=errors,
                warnings=warnings
            )

        # 5. Universal Normalization
        try:
            universal_event = NormalizationService.normalize_event(
                parsed=parsed_event,
                raw_event_id=raw_event.raw_event_id,
                raw_payload=raw_text
            )
        except Exception as norm_exc:
            errors.append(f"Normalization failed: {str(norm_exc)}")
            if commit:
                db.commit()
            return SingleEventResult(
                success=False,
                raw_event_id=raw_event.raw_event_id,
                detected_format=detected_format,
                parser_id=parser.parser_id,
                parser_version=parser.parser_version,
                validation_status="invalid",
                errors=errors,
                warnings=warnings
            )

        # 6. Validation
        val_report = ValidationService.validate_event(universal_event)
        if val_report.errors:
            errors.extend(val_report.errors)
        if val_report.warnings:
            warnings.extend(val_report.warnings)

        # 7. Persistence of Normalized Event & Validation Result
        norm_model = NormalizedEvent(
            event_id=universal_event.event_id,
            source_event_id=universal_event.source_event_id,
            raw_event_id=raw_event.raw_event_id,
            schema_version=universal_event.schema_version,
            timestamp=universal_event.timestamp,
            ingestion_timestamp=universal_event.ingestion_timestamp,
            timezone=universal_event.timezone,
            vendor=universal_event.vendor,
            product=universal_event.product,
            device_type=universal_event.device_type,
            device_id=universal_event.device_id,
            hostname=universal_event.hostname,
            source_format=universal_event.source_format,
            source_ip=universal_event.source_ip,
            source_port=universal_event.source_port,
            destination_ip=universal_event.destination_ip,
            destination_port=universal_event.destination_port,
            protocol=universal_event.protocol,
            username=universal_event.username,
            user_id=universal_event.user_id,
            authentication_method=universal_event.authentication_method,
            event_type=universal_event.event_type,
            action=str(universal_event.action.value if hasattr(universal_event.action, "value") else universal_event.action) if universal_event.action else None,
            outcome=str(universal_event.outcome.value if hasattr(universal_event.outcome, "value") else universal_event.outcome) if universal_event.outcome else None,
            severity=str(universal_event.severity.value if hasattr(universal_event.severity, "value") else universal_event.severity) if universal_event.severity else "unknown",
            category=universal_event.category,
            subcategory=universal_event.subcategory,
            interface=universal_event.interface,
            direction=str(universal_event.direction.value if hasattr(universal_event.direction, "value") else universal_event.direction) if universal_event.direction else None,
            zone=universal_event.zone,
            threat_name=universal_event.threat_name,
            threat_id=universal_event.threat_id,
            signature_id=universal_event.signature_id,
            rule_id=universal_event.rule_id,
            message=universal_event.message,
            tags=universal_event.tags,
            custom_fields=universal_event.custom_fields,
            parser_id=universal_event.parser_id,
            parser_version=universal_event.parser_version,
            normalization_version=universal_event.normalization_version
        )
        db.add(norm_model)
        db.flush()

        val_model = ValidationResult(
            normalized_event_id=norm_model.event_id,
            run_id=run_id,
            validation_status=val_report.status,
            validation_errors=val_report.errors,
            validation_warnings=val_report.warnings,
            validation_timestamp=datetime.now(timezone.utc)
        )
        db.add(val_model)

        if commit:
            db.commit()

        return SingleEventResult(
            success=val_report.is_valid,
            raw_event_id=raw_event.raw_event_id,
            normalized_event_id=norm_model.event_id,
            detected_format=detected_format,
            parser_id=parser.parser_id,
            parser_version=parser.parser_version,
            validation_status=val_report.status,
            errors=errors,
            warnings=warnings,
            normalized_event=universal_event.model_dump(mode="json")
        )

    @staticmethod
    def process_batch(
        events: List[Union[str, Dict[str, Any]]],
        db: Session,
        source_id: Optional[str] = None
    ) -> BatchProcessingResult:
        """
        Executes bounded batch processing, maintaining ProcessingRun telemetry.
        """
        start_time = time.perf_counter()
        started_at = datetime.now(timezone.utc)
        run_id = f"RUN-{uuid.uuid4().hex[:12].upper()}"

        run_record = ProcessingRun(
            run_id=run_id,
            source_id=source_id,
            started_at=started_at,
            status="started",
            records_received=len(events),
            records_parsed=0,
            records_normalized=0,
            records_failed=0,
            processing_time_ms=0
        )
        db.add(run_record)
        db.commit()

        format_stats: Dict[str, int] = {}
        parser_stats: Dict[str, int] = {}
        event_results: List[SingleEventResult] = []

        success_count = 0
        failed_count = 0

        for item in events:
            res = PipelineService.process_event(
                raw_payload=item,
                db=db,
                source_id=source_id,
                run_id=run_id,
                commit=False
            )
            event_results.append(res)

            # Update format stats
            fmt = res.detected_format
            format_stats[fmt] = format_stats.get(fmt, 0) + 1

            # Update parser stats
            if res.parser_id:
                parser_stats[res.parser_id] = parser_stats.get(res.parser_id, 0) + 1

            if res.success:
                success_count += 1
            else:
                failed_count += 1

        db.commit()

        duration_ms = int((time.perf_counter() - start_time) * 1000)

        # Finalize processing run
        run_record.completed_at = datetime.now(timezone.utc)
        run_record.status = "completed" if failed_count == 0 else ("failed" if success_count == 0 else "completed_with_errors")
        run_record.records_parsed = success_count + failed_count
        run_record.records_normalized = success_count
        run_record.records_failed = failed_count
        run_record.processing_time_ms = duration_ms
        if failed_count > 0:
            run_record.error_summary = f"{failed_count} events failed parsing/validation out of {len(events)} total."

        db.commit()

        return BatchProcessingResult(
            processing_run_id=run_id,
            total_received=len(events),
            total_parsed=success_count + failed_count,
            total_normalized=success_count,
            total_failed=failed_count,
            processing_time_ms=duration_ms,
            format_statistics=format_stats,
            parser_statistics=parser_stats,
            events=event_results
        )
