import asyncio
import hashlib
import logging
import time
import uuid
from typing import Optional

from app.core.config import settings
from app.core.database import SessionLocal
from app.services.ingestion.detector import detect_format
from app.services.normalization.service import NormalizationService
from app.services.parsers.registry import default_parser_registry
from app.services.persistence.base import PersistenceItem
from app.services.persistence.queue import AsyncPersistenceQueue, global_persistence_queue
from app.services.pipeline import PipelineService
from app.services.syslog.metrics import syslog_metrics
from app.services.syslog.models import ReceivedSyslogMessage, decode_payload_safe
from app.services.syslog.source_resolver import source_resolver
from app.services.validation.service import ValidationService

logger = logging.getLogger("ulpf.syslog.worker")


async def syslog_worker_task(
    worker_id: int,
    queue: asyncio.Queue,
    shutdown_event: asyncio.Event,
    persistence_queue: Optional[AsyncPersistenceQueue] = None
) -> None:
    """
    Asynchronous consumer worker: pulls events from bounded queue and
    routes them into the ULPF processing pipeline.
    
    When decoupled persistence is enabled (batch/parquet/streaming),
    workers perform format detection, parsing, normalization, validation,
    and SHA-256 integrity hashing in-memory, then enqueue items to the
    persistence queue without blocking on database transactions.
    """
    p_queue = persistence_queue or global_persistence_queue
    use_decoupled = settings.PERSISTENCE_MODE != "single"

    logger.debug(
        f"Syslog worker #{worker_id} started (decoupled_persistence={use_decoupled})."
    )

    while not shutdown_event.is_set():
        try:
            # Wait for next message with a brief timeout so we can check shutdown_event
            try:
                msg: ReceivedSyslogMessage = await asyncio.wait_for(queue.get(), timeout=0.5)
            except asyncio.TimeoutError:
                continue

            start_time = time.perf_counter()
            syslog_metrics.set_queue_depth(queue.qsize())

            # Decode payload safely
            decoded_text, encoding_status = decode_payload_safe(msg.payload)

            if use_decoupled:
                # =========================================================
                # HIGH-THROUGHPUT DECOUPLED IN-MEMORY PROCESSING
                # =========================================================
                try:
                    # Sync session factory for testing / dynamic database sessions
                    if hasattr(p_queue.backend, "session_factory") and p_queue.backend.session_factory != SessionLocal:
                        p_queue.backend.session_factory = SessionLocal

                    # 1. Resolve source (check memory cache first, lookup DB if uncached)
                    source_id = source_resolver.resolve_source(msg.remote_address, db=None)
                    if source_id is None:
                        try:
                            lookup_db = SessionLocal()
                            source_id = source_resolver.resolve_source(msg.remote_address, db=lookup_db)
                            lookup_db.close()
                        except Exception:
                            pass

                    # 2. Compute SHA-256 raw payload hash immediately (Principle: immutable integrity)
                    raw_bytes = decoded_text.encode("utf-8", errors="replace")
                    payload_hash = hashlib.sha256(raw_bytes).hexdigest()
                    raw_event_id = f"RAW-{uuid.uuid4().hex.upper()}"

                    # 3. Format Detection
                    det = detect_format(decoded_text)
                    detected_format = det.detected_format

                    # 4. Parser Selection & Parsing
                    parser = default_parser_registry.select_parser(
                        detected_format=detected_format,
                        payload=decoded_text
                    )

                    universal_event = None
                    val_status = "valid"
                    val_errors = []
                    val_warnings = []

                    if parser:
                        parsed_event = parser.parse(decoded_text)
                        if parsed_event.errors:
                            val_status = "invalid"
                            val_errors = parsed_event.errors
                        else:
                            # 5. Normalization
                            universal_event = NormalizationService.normalize_event(
                                parsed=parsed_event,
                                raw_event_id=raw_event_id,
                                raw_payload=decoded_text
                            )
                            # 6. Validation
                            val_report = ValidationService.validate_event(universal_event)
                            val_status = val_report.status
                            val_errors = val_report.errors
                            val_warnings = val_report.warnings
                    else:
                        is_unknown = (detected_format.lower() == "unknown")
                        val_status = "unknown_format" if is_unknown else "invalid"
                        if not is_unknown:
                            val_errors = [f"No compatible parser found for format '{detected_format}'"]

                    # 7. Package into PersistenceItem preserving raw data and full traceability
                    p_item = PersistenceItem(
                        raw_event_id=raw_event_id,
                        raw_payload=decoded_text,
                        payload_hash_sha256=payload_hash,
                        received_at=msg.received_at,
                        payload_encoding="utf-8",
                        source_id=source_id,
                        source_format=detected_format,
                        normalized_event=universal_event.model_dump() if universal_event else None,
                        validation_status=val_status,
                        validation_errors=val_errors,
                        validation_warnings=val_warnings
                    )

                    # 8. Asynchronous enqueue onto persistence queue (non-blocking)
                    enqueued = p_queue.enqueue(p_item)
                    latency_ms = (time.perf_counter() - start_time) * 1000.0

                    if enqueued and (val_status in ("valid", "warning", "unknown_format")):
                        syslog_metrics.record_processed(latency_ms)
                    else:
                        syslog_metrics.record_failed()

                except Exception as exc:
                    syslog_metrics.record_failed()
                    logger.error(
                        f"Worker #{worker_id}: In-memory processing error from {msg.remote_address}: {exc}"
                    )
                finally:
                    queue.task_done()
                    syslog_metrics.set_queue_depth(queue.qsize())

            else:
                # =========================================================
                # SYNCHRONOUS SINGLE-EVENT PERSISTENCE (DEVELOPMENT MODE)
                # =========================================================
                db = SessionLocal()
                try:
                    source_id = source_resolver.resolve_source(msg.remote_address, db)
                    res = PipelineService.process_event(
                        raw_payload=decoded_text,
                        db=db,
                        source_id=source_id,
                        source_format_hint=None,
                        run_id=None,
                        commit=True
                    )
                    latency_ms = (time.perf_counter() - start_time) * 1000.0
                    if res.success:
                        syslog_metrics.record_processed(latency_ms)
                    else:
                        syslog_metrics.record_failed()
                except Exception as exc:
                    syslog_metrics.record_failed()
                    logger.error(f"Worker #{worker_id}: Synchronous error from {msg.remote_address}: {exc}")
                    try:
                        db.rollback()
                    except Exception:
                        pass
                finally:
                    db.close()
                    queue.task_done()
                    syslog_metrics.set_queue_depth(queue.qsize())

        except asyncio.CancelledError:
            logger.debug(f"Syslog worker #{worker_id} cancelled.")
            break
        except Exception as outer_exc:
            logger.error(f"Unexpected error in Syslog worker #{worker_id}: {outer_exc}")

    logger.debug(f"Syslog worker #{worker_id} exited.")
