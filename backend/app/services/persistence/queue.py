import asyncio
import logging
import time
from typing import Any, Dict, List, Optional

from app.core.config import settings
from app.services.persistence.base import PersistenceBackend, PersistenceItem
from app.services.persistence.database_backend import BatchDatabasePersistence

logger = logging.getLogger("ulpf.persistence.queue")


class AsyncPersistenceQueue:
    """
    High-throughput asynchronous persistence queue.
    Decouples ingestion & processing workers from disk I/O and database transactions.
    
    Provides:
    - Bounded in-memory queue with strict backpressure
    - Size-based and time-based (dual trigger) batch commits
    - Controlled drop policy with exact metrics accounting
    - Graceful drain and flush upon shutdown
    """

    def __init__(
        self,
        backend: Optional[PersistenceBackend] = None,
        batch_size: Optional[int] = None,
        flush_interval_ms: Optional[int] = None,
        max_queue_size: Optional[int] = None,
    ):
        self.backend = backend or BatchDatabasePersistence(max_retries=settings.PERSISTENCE_MAX_RETRIES)
        self.batch_size = batch_size or settings.PERSISTENCE_BATCH_SIZE
        self.flush_interval_seconds = (flush_interval_ms or settings.PERSISTENCE_FLUSH_INTERVAL_MS) / 1000.0
        self.max_queue_size = max_queue_size or settings.PERSISTENCE_QUEUE_MAX_SIZE

        self.queue: asyncio.Queue = asyncio.Queue(maxsize=self.max_queue_size)
        self.worker_task: Optional[asyncio.Task] = None
        self.shutdown_event = asyncio.Event()
        self.is_running = False

        # Metrics & Event Accounting
        self.total_enqueued = 0
        self.total_persisted = 0
        self.total_failed = 0
        self.total_dropped = 0
        self.batch_count = 0
        self.latencies_ms: List[float] = []

    async def start(self) -> None:
        """Starts background batch writer worker."""
        if self.is_running:
            return

        current_loop = asyncio.get_running_loop()
        q_loop = getattr(self.queue, "_loop", None)
        if q_loop is not None and q_loop != current_loop:
            # Rebind queue to active loop, preserving any buffered items
            old_items = []
            while not self.queue.empty():
                try:
                    old_items.append(self.queue.get_nowait())
                except Exception:
                    break
            self.queue = asyncio.Queue(maxsize=self.max_queue_size)
            for item in old_items:
                self.queue.put_nowait(item)
            self.shutdown_event = asyncio.Event()

        self.shutdown_event.clear()
        self.is_running = True
        self.worker_task = asyncio.create_task(self._worker_loop())
        logger.info(
            f"PersistenceQueue started: batch_size={self.batch_size}, "
            f"flush_interval={self.flush_interval_seconds * 1000:.0f}ms, max_queue={self.max_queue_size}"
        )

    async def stop(self, drain_timeout: float = 5.0) -> None:
        """Gracefully drains queued events and shuts down worker."""
        if not self.is_running:
            return

        logger.info(f"Draining persistence queue ({self.queue.qsize()} remaining items)...")
        self.shutdown_event.set()

        # Wait for worker loop to drain and terminate cleanly
        if self.worker_task:
            try:
                await asyncio.wait_for(self.worker_task, timeout=drain_timeout)
            except (asyncio.TimeoutError, asyncio.CancelledError):
                self.worker_task.cancel()
                try:
                    await self.worker_task
                except asyncio.CancelledError:
                    pass

        await self.backend.flush()
        await self.backend.close()
        self.is_running = False
        logger.info("PersistenceQueue shutdown complete.")

    def enqueue(self, item: PersistenceItem) -> bool:
        """
        Non-blocking enqueue called by processing workers.
        Returns True if enqueued, False if dropped due to queue saturation.
        """
        try:
            self.queue.put_nowait(item)
            self.total_enqueued += 1
            return True
        except asyncio.QueueFull:
            self.total_dropped += 1
            logger.warning(
                f"Persistence queue full ({self.max_queue_size} items). Controlled drop policy activated."
            )
            return False

    async def enqueue_wait(self, item: PersistenceItem, timeout: float = 1.0) -> bool:
        """
        Blocking enqueue with backpressure timeout.
        """
        try:
            await asyncio.wait_for(self.queue.put(item), timeout=timeout)
            self.total_enqueued += 1
            return True
        except (asyncio.TimeoutError, asyncio.QueueFull):
            self.total_dropped += 1
            logger.warning("Persistence queue backpressure timeout exceeded; event dropped.")
            return False

    async def _worker_loop(self) -> None:
        """Continuous consumer loop gathering and committing batches."""
        current_batch: List[PersistenceItem] = []
        last_flush_time = time.perf_counter()

        while not self.shutdown_event.is_set() or not self.queue.empty():
            try:
                # Wait for next item with timeout based on remaining flush window
                time_since_flush = time.perf_counter() - last_flush_time
                remaining_time = max(0.01, self.flush_interval_seconds - time_since_flush)

                try:
                    item = await asyncio.wait_for(self.queue.get(), timeout=remaining_time)
                    current_batch.append(item)
                    self.queue.task_done()
                except asyncio.TimeoutError:
                    pass

                # Check flush conditions:
                # 1. Batch size threshold reached
                # 2. Flush interval timer expired and batch has items
                # 3. Shutdown initiated and items remain
                now = time.perf_counter()
                size_trigger = len(current_batch) >= self.batch_size
                time_trigger = (now - last_flush_time) >= self.flush_interval_seconds and len(current_batch) > 0
                shutdown_trigger = self.shutdown_event.is_set() and len(current_batch) > 0

                if size_trigger or time_trigger or shutdown_trigger:
                    to_flush = current_batch
                    current_batch = []
                    last_flush_time = time.perf_counter()
                    await self._flush_batch(to_flush)

            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.error(f"Error in persistence worker loop: {exc}")
                await asyncio.sleep(0.05)

        # Final flush on exit
        if current_batch:
            await self._flush_batch(current_batch)

    async def _flush_batch(self, batch: List[PersistenceItem]) -> None:
        """Executes atomic batch write through configured persistence backend."""
        if not batch:
            return

        flush_start = time.perf_counter()
        try:
            persisted_count = await self.backend.write_batch(batch)
            self.total_persisted += persisted_count
            self.batch_count += 1
            latency_ms = (time.perf_counter() - flush_start) * 1000.0

            # Retain sliding window of latencies for percentile calculation
            self.latencies_ms.append(latency_ms)
            if len(self.latencies_ms) > 1000:
                self.latencies_ms = self.latencies_ms[-500:]

            logger.debug(
                f"Persisted batch of {len(batch)} items in {latency_ms:.2f}ms "
                f"(Total persisted: {self.total_persisted})"
            )
        except Exception as exc:
            self.total_failed += len(batch)
            logger.error(f"Failed to persist batch of {len(batch)} items: {exc}")

    def get_metrics(self) -> Dict[str, Any]:
        """Returns observable metrics snapshot."""
        avg_lat = round(sum(self.latencies_ms) / len(self.latencies_ms), 2) if self.latencies_ms else 0.0
        avg_batch = round(self.total_persisted / self.batch_count, 1) if self.batch_count > 0 else 0.0

        return {
            "queue_depth": self.queue.qsize(),
            "queue_capacity": self.max_queue_size,
            "total_enqueued": self.total_enqueued,
            "total_persisted": self.total_persisted,
            "total_failed": self.total_failed,
            "total_dropped": self.total_dropped,
            "batch_count": self.batch_count,
            "avg_batch_size": avg_batch,
            "persistence_latency_ms_avg": avg_lat,
            "accounting_balanced": (
                self.total_enqueued == (self.total_persisted + self.total_failed + self.queue.qsize())
            )
        }

    def reset_metrics(self) -> None:
        """Resets counters for clean benchmark runs."""
        self.total_enqueued = 0
        self.total_persisted = 0
        self.total_failed = 0
        self.total_dropped = 0
        self.batch_count = 0
        self.latencies_ms.clear()


# Default singleton instance for application runtime
global_persistence_queue = AsyncPersistenceQueue()
