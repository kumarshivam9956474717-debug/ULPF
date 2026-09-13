import asyncio
import logging
import time
from typing import Optional
from app.core.database import SessionLocal
from app.services.pipeline import PipelineService
from app.services.syslog.models import ReceivedSyslogMessage, decode_payload_safe
from app.services.syslog.metrics import syslog_metrics
from app.services.syslog.source_resolver import source_resolver

logger = logging.getLogger("ulpf.syslog.worker")


async def syslog_worker_task(
    worker_id: int,
    queue: asyncio.Queue,
    shutdown_event: asyncio.Event
) -> None:
    """
    Asynchronous consumer worker: pulls events from bounded queue and
    routes them into the existing ULPF PipelineService.
    """
    logger.debug(f"Syslog worker #{worker_id} started.")

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

            # Process inside database session
            db = SessionLocal()
            try:
                # 1. Resolve source from remote IP
                source_id = source_resolver.resolve_source(msg.remote_address, db)

                # 2. Invoke existing ULPF Pipeline
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
                    logger.warning(
                        f"Worker #{worker_id}: pipeline reported non-success for event from {msg.remote_address}: errors={res.errors}, warnings={res.warnings}"
                    )


            except Exception as exc:
                syslog_metrics.record_failed()
                logger.error(f"Worker #{worker_id}: Exception processing event from {msg.remote_address}: {exc}")
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
