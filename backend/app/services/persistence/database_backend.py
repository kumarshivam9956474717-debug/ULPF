import asyncio
import logging
import time
from datetime import datetime, timezone
from typing import List
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import SessionLocal
from app.models.raw_event import RawEvent
from app.models.normalized_event import NormalizedEvent
from app.models.validation_result import ValidationResult
from app.services.persistence.base import PersistenceBackend, PersistenceItem

logger = logging.getLogger("ulpf.persistence.database")


def _parse_dt(val):
    if val is None:
        return None
    if isinstance(val, datetime):
        return val
    if isinstance(val, str):
        try:
            return datetime.fromisoformat(val.replace("Z", "+00:00"))
        except Exception:
            return None
    return None


class BatchDatabasePersistence(PersistenceBackend):
    """
    High-throughput relational persistence backend.
    Commits events in atomic batches to reduce disk fsync calls and I/O bottlenecks.
    """

    def __init__(self, session_factory=None, max_retries: int = 3):
        self.session_factory = session_factory
        self.max_retries = max_retries

    def get_session(self) -> Session:
        if self.session_factory:
            return self.session_factory()
        from app.core.database import SessionLocal
        return SessionLocal()

    async def write_batch(self, items: List[PersistenceItem]) -> int:
        if not items:
            return 0

        # Execute DB blocking calls inside a thread to avoid blocking asyncio loop
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self._write_batch_sync, items)

    def _write_batch_sync(self, items: List[PersistenceItem]) -> int:
        retries = 0
        last_error = None

        while retries <= self.max_retries:
            db = None
            try:
                db = self.get_session()
                raw_models = []
                norm_models = []
                val_models = []

                for item in items:
                    rec_at = _parse_dt(item.received_at) or datetime.now(timezone.utc)
                    # 1. Raw Event Model (Verbatim payload preservation & SHA-256 integrity)
                    raw_models.append(
                        RawEvent(
                            raw_event_id=item.raw_event_id,
                            source_id=item.source_id,
                            received_at=rec_at,
                            raw_payload=item.raw_payload,
                            payload_encoding=item.payload_encoding,
                            payload_hash_sha256=item.payload_hash_sha256,
                            source_format=item.source_format,
                            ingestion_batch_id=item.ingestion_batch_id
                        )
                    )

                    # 2. Normalized Event Model (if parsed successfully)
                    if item.normalized_event:
                        ne = item.normalized_event
                        ev_ts = _parse_dt(ne.get("timestamp"))
                        ing_ts = _parse_dt(ne.get("ingestion_timestamp")) or rec_at

                        norm_models.append(
                            NormalizedEvent(
                                event_id=ne.get("event_id"),
                                source_event_id=ne.get("source_event_id"),
                                raw_event_id=item.raw_event_id,
                                schema_version=ne.get("schema_version", "1.0.0"),
                                timestamp=ev_ts,
                                ingestion_timestamp=ing_ts,
                                timezone=ne.get("timezone", "UTC"),
                                vendor=ne.get("vendor"),
                                product=ne.get("product"),
                                device_type=ne.get("device_type"),
                                device_id=ne.get("device_id"),
                                hostname=ne.get("hostname"),
                                source_format=ne.get("source_format"),
                                source_ip=ne.get("source_ip"),
                                source_port=ne.get("source_port"),
                                destination_ip=ne.get("destination_ip"),
                                destination_port=ne.get("destination_port"),
                                protocol=ne.get("protocol"),
                                username=ne.get("username"),
                                user_id=ne.get("user_id"),
                                authentication_method=ne.get("authentication_method"),
                                event_type=ne.get("event_type"),
                                action=str(ne.get("action")) if ne.get("action") is not None else None,
                                outcome=str(ne.get("outcome")) if ne.get("outcome") is not None else None,
                                severity=str(ne.get("severity")) if ne.get("severity") is not None else "unknown",
                                category=ne.get("category"),
                                subcategory=ne.get("subcategory"),
                                interface=ne.get("interface"),
                                direction=str(ne.get("direction")) if ne.get("direction") is not None else None,
                                zone=ne.get("zone"),
                                threat_name=ne.get("threat_name"),
                                threat_id=ne.get("threat_id"),
                                signature_id=ne.get("signature_id"),
                                rule_id=ne.get("rule_id"),
                                message=ne.get("message"),
                                tags=ne.get("tags"),
                                custom_fields=ne.get("custom_fields"),
                                parser_id=ne.get("parser_id"),
                                parser_version=ne.get("parser_version"),
                                normalization_version=ne.get("normalization_version")
                            )
                        )

                        # 3. Validation Result
                        val_models.append(
                            ValidationResult(
                                normalized_event_id=ne.get("event_id"),
                                run_id=item.ingestion_batch_id,
                                validation_status=item.validation_status,
                                validation_errors=item.validation_errors,
                                validation_warnings=item.validation_warnings,
                                validation_timestamp=rec_at
                            )
                        )

                # Bulk insert in atomic transaction
                db.add_all(raw_models)
                db.flush()

                if norm_models:
                    db.add_all(norm_models)
                    db.flush()

                if val_models:
                    db.add_all(val_models)

                # Single commit for entire batch
                db.commit()
                return len(items)

            except Exception as exc:
                if db:
                    try:
                        db.rollback()
                    except Exception:
                        pass
                last_error = exc
                retries += 1
                logger.warning(
                    f"Batch persistence transaction failed (attempt {retries}/{self.max_retries}): {exc}"
                )
                time.sleep(0.05 * (2 ** (retries - 1)))  # Exponential backoff
            finally:
                if db:
                    db.close()

        logger.error(f"Batch persistence failed after {self.max_retries} retries: {last_error}")
        raise RuntimeError(f"Database batch persistence failed: {last_error}")

    async def flush(self) -> None:
        pass  # In batch DB mode, write_batch is already synchronously committed on transaction

    async def close(self) -> None:
        pass
