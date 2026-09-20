import asyncio
import logging
from typing import List

from app.core.config import settings
from app.services.export.parquet_exporter import ParquetExporter
from app.services.persistence.base import PersistenceBackend, PersistenceItem

logger = logging.getLogger("ulpf.persistence.parquet")


class ParquetExportBackend(PersistenceBackend):
    """
    Columnar data-lake persistence backend.
    Streams normalized events directly to timestamp-partitioned Snappy Parquet files,
    bypassing database write contention for high-volume data-lake archival.
    """

    def __init__(self, base_dir: str = None):
        self.base_dir = base_dir or settings.ULPF_PARQUET_EXPORT_DIR

    async def write_batch(self, items: List[PersistenceItem]) -> int:
        if not items:
            return 0

        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self._write_batch_sync, items)

    def _write_batch_sync(self, items: List[PersistenceItem]) -> int:
        records = []
        for item in items:
            rec = {
                "raw_event_id": item.raw_event_id,
                "raw_payload": item.raw_payload,
                "payload_hash_sha256": item.payload_hash_sha256,
                "source_id": item.source_id,
                "source_format": item.source_format,
                "received_at": item.received_at.isoformat() if item.received_at else None,
                "validation_status": item.validation_status
            }
            if item.normalized_event:
                rec.update(item.normalized_event)
            records.append(rec)

        files_created, bytes_written, paths, p_count = ParquetExporter.write_partitioned_parquet(
            records=records,
            base_dir=self.base_dir
        )
        logger.debug(
            f"ParquetExportBackend wrote {len(items)} items to {files_created} files ({bytes_written} bytes)"
        )
        return len(items)

    async def flush(self) -> None:
        pass

    async def close(self) -> None:
        pass
