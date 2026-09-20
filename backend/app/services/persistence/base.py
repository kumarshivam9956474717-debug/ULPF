import abc
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


@dataclass
class PersistenceItem:
    """
    Decoupled representation of an ingested and processed log event.
    Preserves raw data, cryptographic hash, normalized attributes, and validation results.
    """
    raw_event_id: str
    raw_payload: str
    payload_hash_sha256: str
    received_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    payload_encoding: str = "utf-8"
    source_id: Optional[str] = None
    source_format: Optional[str] = None
    ingestion_batch_id: Optional[str] = None

    # Normalized fields (if parsing and normalization succeeded)
    normalized_event: Optional[Dict[str, Any]] = None

    # Validation results (if validated)
    validation_status: str = "valid"
    validation_errors: List[str] = field(default_factory=list)
    validation_warnings: List[str] = field(default_factory=list)

    # Telemetry
    enqueued_at: float = field(default_factory=time.perf_counter)


class PersistenceBackend(abc.ABC):
    """
    Abstract persistence backend interface.
    Decouples in-memory parsing/normalization from physical storage engines.
    """

    @abc.abstractmethod
    async def write_batch(self, items: List[PersistenceItem]) -> int:
        """
        Persists a batch of items atomically.
        Returns count of successfully persisted items.
        """
        pass

    @abc.abstractmethod
    async def flush(self) -> None:
        """Flushes any internal buffers to durable storage."""
        pass

    @abc.abstractmethod
    async def close(self) -> None:
        """Releases connections and resources."""
        pass
