import uuid
from typing import Any, Dict, Optional, Union
from sqlalchemy.orm import Session
from app.models.raw_event import RawEvent
from app.services.ingestion.base import IngestionItem


class IngestionService:
    """
    Ingestion engine responsible for lossless ingestion and cryptographic raw persistence.
    Guarantees raw payloads are stored verbatim without modification.
    """

    @staticmethod
    def ingest_payload(
        data: Union[str, bytes, Dict[str, Any]],
        db: Session,
        source_id: Optional[str] = None,
        source_format_hint: Optional[str] = None,
        ingestion_batch_id: Optional[str] = None,
        encoding: str = "utf-8"
    ) -> RawEvent:
        """
        Processes incoming payload, creates IngestionItem, and persists RawEvent record.
        """
        item = IngestionItem.from_input(
            data=data,
            source_id=source_id,
            source_format_hint=source_format_hint,
            encoding=encoding
        )

        raw_event_id = f"RAW-{uuid.uuid4().hex[:16].upper()}"

        raw_event = RawEvent(
            raw_event_id=raw_event_id,
            source_id=item.source_id,
            received_at=item.received_at,
            raw_payload=item.raw_payload,
            payload_encoding=item.encoding,
            payload_hash_sha256=item.payload_hash_sha256,
            source_format=item.source_format_hint,
            ingestion_batch_id=ingestion_batch_id
        )

        db.add(raw_event)
        db.flush()  # Stage in transaction without committing outer boundary
        return raw_event
