import asyncio
import logging
from typing import Any, Callable, Dict, List, Optional
from app.services.persistence.base import PersistenceBackend, PersistenceItem

logger = logging.getLogger("ulpf.persistence.streaming")


class StreamingSink(PersistenceBackend):
    """
    Extensible streaming broker sink abstraction.
    
    Provides an air-gapped, in-process streaming buffer by default, with clean
    extension hooks to connect distributed enterprise message brokers
    (e.g., Apache Kafka, Redpanda, Apache Pulsar) in distributed multi-node deployments.
    """

    def __init__(
        self,
        topic: str = "omnilogix-events",
        external_publisher: Optional[Callable[[List[Dict[str, Any]]], Any]] = None
    ):
        self.topic = topic
        self.external_publisher = external_publisher
        self.buffered_messages: List[Dict[str, Any]] = []
        self.total_streamed = 0

    async def write_batch(self, items: List[PersistenceItem]) -> int:
        if not items:
            return 0

        serialized_events = []
        for item in items:
            ev = {
                "topic": self.topic,
                "raw_event_id": item.raw_event_id,
                "payload_hash_sha256": item.payload_hash_sha256,
                "source_id": item.source_id,
                "received_at": item.received_at.isoformat() if item.received_at else None,
                "validation_status": item.validation_status,
                "normalized_event": item.normalized_event
            }
            serialized_events.append(ev)

        if self.external_publisher:
            # Delegate to custom broker publisher hook if configured
            import inspect
            if inspect.iscoroutinefunction(self.external_publisher):
                await self.external_publisher(serialized_events)
            else:
                loop = asyncio.get_running_loop()
                await loop.run_in_executor(None, self.external_publisher, serialized_events)
        else:
            # In-memory streaming buffer (air-gapped local mode)
            self.buffered_messages.extend(serialized_events)
            # Cap in-memory buffer to prevent unbounded memory growth
            if len(self.buffered_messages) > 10000:
                self.buffered_messages = self.buffered_messages[-5000:]

        self.total_streamed += len(items)
        return len(items)

    async def flush(self) -> None:
        pass

    async def close(self) -> None:
        self.buffered_messages.clear()
