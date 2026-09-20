import json
import os
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session, joinedload

from app.core.config import settings
from app.models.normalized_event import NormalizedEvent
from app.models.raw_event import RawEvent
from app.services.export.models import ExportMetrics, ExportStatus
from app.services.export.parquet_exporter import ParquetExporter


class ExportService:
    """
    Coordinates chunked extraction of normalized events from the database
    and export into partitioned Parquet or deterministic JSON/NDJSON datasets.
    """

    def __init__(self, export_dir: Optional[str] = None):
        self.export_dir = export_dir or settings.ULPF_PARQUET_EXPORT_DIR
        self.last_export: Optional[ExportMetrics] = None
        self._is_exporting: bool = False

    def export_events(
        self,
        db: Session,
        format: str = "parquet",
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        source_id: Optional[str] = None,
        batch_size: Optional[int] = None
    ) -> ExportMetrics:
        """
        Extracts events in chunked batches and exports them to Parquet or JSON.
        Never loads entire table into memory at once.
        """
        start_perf = time.perf_counter()
        self._is_exporting = True
        actual_batch_size = batch_size or settings.ULPF_EXPORT_BATCH_SIZE
        target_format = (format or "parquet").lower()

        try:
            os.makedirs(self.export_dir, exist_ok=True)

            # Build base query with joinedload to fetch raw_events for SHA-256 hash
            query = db.query(NormalizedEvent).options(joinedload(NormalizedEvent.raw_event))

            # Apply timestamp filters
            if start_time:
                query = query.filter(NormalizedEvent.timestamp >= start_time)
            if end_time:
                query = query.filter(NormalizedEvent.timestamp <= end_time)

            # Optional log source filter via raw_events join
            if source_id:
                query = query.join(
                    RawEvent, NormalizedEvent.raw_event_id == RawEvent.raw_event_id
                ).filter(RawEvent.source_id == source_id)

            total_selected = query.count()

            if total_selected == 0:
                metrics = ExportMetrics(
                    export_format=target_format,
                    records_selected=0,
                    records_exported=0,
                    files_created=0,
                    bytes_written=0,
                    duration_seconds=round(time.perf_counter() - start_perf, 4),
                    failed_records=0,
                    partition_count=0,
                    file_paths=[]
                )
                self.last_export = metrics
                return metrics

            total_exported = 0
            total_files = 0
            total_bytes = 0
            all_paths: List[str] = []
            partitions_set = set()

            offset = 0
            while offset < total_selected:
                batch_records = query.order_by(NormalizedEvent.id).offset(offset).limit(actual_batch_size).all()
                if not batch_records:
                    break

                dicts = [self._event_to_dict(e) for e in batch_records]

                if target_format == "parquet":
                    f_created, b_written, paths, p_count = ParquetExporter.write_partitioned_parquet(
                        records=dicts,
                        base_dir=self.export_dir
                    )
                    total_files += f_created
                    total_bytes += b_written
                    all_paths.extend(paths)
                    for p in paths:
                        partitions_set.add(os.path.dirname(p))
                elif target_format in ("json", "ndjson"):
                    f_created, b_written, paths = self._write_json_batch(
                        records=dicts,
                        base_dir=self.export_dir,
                        is_ndjson=(target_format == "ndjson")
                    )
                    total_files += f_created
                    total_bytes += b_written
                    all_paths.extend(paths)
                    for p in paths:
                        partitions_set.add(os.path.dirname(p))
                else:
                    raise ValueError(f"Unsupported export format '{target_format}'. Supported: parquet, json, ndjson")

                total_exported += len(dicts)
                offset += actual_batch_size

            duration = round(time.perf_counter() - start_perf, 4)

            metrics = ExportMetrics(
                export_format=target_format,
                records_selected=total_selected,
                records_exported=total_exported,
                files_created=total_files,
                bytes_written=total_bytes,
                duration_seconds=duration,
                failed_records=0,
                partition_count=len(partitions_set),
                file_paths=all_paths
            )
            self.last_export = metrics
            return metrics

        finally:
            self._is_exporting = False

    def _write_json_batch(
        self,
        records: List[Dict[str, Any]],
        base_dir: str,
        is_ndjson: bool = False
    ) -> tuple[int, int, List[str]]:
        """Writes batch to deterministic UTF-8 JSON or NDJSON file."""
        if not records:
            return 0, 0, []

        now_dt = datetime.now(timezone.utc)
        part_dir = os.path.join(
            base_dir,
            f"year={now_dt.strftime('%Y')}",
            f"month={now_dt.strftime('%m')}",
            f"day={now_dt.strftime('%d')}"
        )
        os.makedirs(part_dir, exist_ok=True)

        ext = "ndjson" if is_ndjson else "json"
        filename = f"events-{uuid.uuid4().hex[:12]}.{ext}"
        filepath = os.path.join(part_dir, filename)

        with open(filepath, "w", encoding="utf-8") as f:
            if is_ndjson:
                for rec in records:
                    f.write(json.dumps(rec, sort_keys=True) + "\n")
            else:
                json.dump(records, f, indent=2, sort_keys=True)

        size = os.path.getsize(filepath)
        return 1, size, [os.path.abspath(filepath)]

    def get_status(self) -> ExportStatus:
        """Returns the current status and latest export run metrics."""
        return ExportStatus(
            status="exporting" if self._is_exporting else "ready",
            export_directory=os.path.abspath(self.export_dir),
            last_export=self.last_export
        )

    @staticmethod
    def _event_to_dict(e: NormalizedEvent) -> Dict[str, Any]:
        """Maps SQLAlchemy NormalizedEvent into serializable dict with SHA-256 and raw payload."""
        raw_hash = e.raw_event.payload_hash_sha256 if e.raw_event else None
        raw_payload = e.raw_event.raw_payload if e.raw_event else None

        return {
            "event_id": e.event_id,
            "source_event_id": e.source_event_id,
            "raw_event_id": e.raw_event_id,
            "schema_version": e.schema_version,
            "timestamp": e.timestamp.isoformat() if e.timestamp else None,
            "ingestion_timestamp": e.ingestion_timestamp.isoformat() if e.ingestion_timestamp else None,
            "timezone": e.timezone,
            "vendor": e.vendor,
            "product": e.product,
            "device_type": e.device_type,
            "device_id": e.device_id,
            "hostname": e.hostname,
            "source_format": e.source_format,
            "source_ip": e.source_ip,
            "source_port": e.source_port,
            "destination_ip": e.destination_ip,
            "destination_port": e.destination_port,
            "protocol": e.protocol,
            "username": e.username,
            "user_id": e.user_id,
            "authentication_method": e.authentication_method,
            "event_type": e.event_type,
            "action": e.action,
            "outcome": e.outcome,
            "severity": e.severity,
            "category": e.category,
            "subcategory": e.subcategory,
            "interface": e.interface,
            "direction": e.direction,
            "zone": e.zone,
            "threat_name": e.threat_name,
            "threat_id": e.threat_id,
            "signature_id": e.signature_id,
            "rule_id": e.rule_id,
            "message": e.message,
            "tags": e.tags,
            "custom_fields": e.custom_fields,
            "parser_id": e.parser_id,
            "parser_version": e.parser_version,
            "normalization_version": e.normalization_version,
            "payload_hash_sha256": raw_hash,
            "raw_payload": raw_payload,
        }


export_service = ExportService()
