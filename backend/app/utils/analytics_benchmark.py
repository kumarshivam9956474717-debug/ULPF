"""
Analytics, Columnar Export, and Anomaly Detection Benchmark Utility for ULPF Phase 4B.

Measures:
1. SQL aggregation query performance (overview, timeline, top-items)
2. Apache Parquet columnar export throughput (records/sec, MB/sec, compression)
3. Offline anomaly detection feature extraction throughput and scoring latency
"""

import os
import sys
import time
import uuid
import tempfile
from datetime import datetime, timezone, timedelta
from typing import List

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Setup path if run directly
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.abspath(os.path.join(current_dir, "..", ".."))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.core.database import Base
from app.models.normalized_event import NormalizedEvent
from app.services.analytics.service import AnalyticsService
from app.services.analytics.models import AnalyticsFilter
from app.services.export.parquet_exporter import ParquetExporter
from app.services.anomaly.feature_engineering import FeatureExtractor
from app.services.anomaly.detector import IsolationForestDetector


def generate_synthetic_events(count: int) -> List[NormalizedEvent]:
    """Generates synthetic normalized perimeter security events for benchmarking."""
    base_time = datetime(2026, 9, 10, 8, 0, 0, tzinfo=timezone.utc)
    vendors = ["cisco", "paloalto", "fortinet", "checkpoint", "juniper"]
    actions = ["allowed", "blocked", "dropped", "alerted"]
    severities = ["low", "informational", "medium", "high", "critical"]
    protocols = ["tcp", "udp", "icmp"]

    events = []
    for i in range(count):
        v = vendors[i % len(vendors)]
        e = NormalizedEvent(
            event_id=f"EVT-BENCH-{uuid.uuid4().hex[:12]}",
            raw_event_id=f"RAW-BENCH-{uuid.uuid4().hex[:12]}",
            schema_version="1.0.0",
            timestamp=base_time + timedelta(seconds=i),
            ingestion_timestamp=base_time + timedelta(seconds=i, milliseconds=50),
            vendor=v,
            product=f"{v}_firewall",
            device_type="firewall",
            device_id=f"fw-perimeter-{(i % 8) + 1:02d}",
            hostname=f"gw-edge-{(i % 8) + 1:02d}.local",
            source_ip=f"10.0.{(i % 250)}.{10 + (i % 200)}",
            destination_ip=f"198.51.100.{(i % 100) + 1}",
            source_port=10000 + (i % 50000),
            destination_port=443 if i % 2 == 0 else (80 if i % 3 == 0 else 22),
            protocol=protocols[i % len(protocols)],
            action=actions[i % len(actions)],
            severity=severities[i % len(severities)],
            category="network_traffic",
            message=f"Traffic {actions[i % len(actions)]} from 10.0.{(i % 250)}.{10 + (i % 200)}",
            custom_fields={"flow_id": i, "tcp_flags": "ACK,PSH", "interface": "eth0"},
            tags=["perimeter", "benchmark", v],
            normalization_version="1.0.0"
        )
        events.append(e)
    return events


def run_benchmark(event_counts: List[int] = [1000, 5000]):
    print("=" * 72)
    print("  ULPF PHASE 4B: COLUMNAR ANALYTICS & ANOMALY DETECTION BENCHMARK")
    print("  National Technical Research Organisation (NTRO) - SIH26156")
    print("=" * 72)

    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)

    for count in event_counts:
        print(f"\n--- [ Benchmark Dataset: {count:,} Events ] ---")
        session = Session()

        # 1. Dataset Generation & Ingestion
        gen_start = time.perf_counter()
        events = generate_synthetic_events(count)
        session.bulk_save_objects(events)
        session.commit()
        gen_dur = time.perf_counter() - gen_start
        print(f"[*] Synthetic Event Population: {gen_dur:.3f}s ({count / gen_dur:,.0f} events/sec)")

        # 2. SQL Analytics Benchmark
        print("\n[*] SQL Analytics Query Performance:")
        filters = AnalyticsFilter()

        # Overview
        t0 = time.perf_counter()
        overview = AnalyticsService.get_overview(session, filters)
        d_overview = (time.perf_counter() - t0) * 1000
        print(f"    - Overview Aggregation:       {d_overview:.2f} ms (Total: {overview.total_events})")

        # Timeline
        t0 = time.perf_counter()
        timeline = AnalyticsService.get_timeline(session, filters)
        d_timeline = (time.perf_counter() - t0) * 1000
        print(f"    - Timeline (Hour Buckets):    {d_timeline:.2f} ms (Buckets: {len(timeline)})")

        # Top IPs
        t0 = time.perf_counter()
        top_ips = AnalyticsService.get_top_source_ips(session, limit=10, filters=filters)
        d_top_ips = (time.perf_counter() - t0) * 1000
        print(f"    - Top Source IPs (Limit 10):  {d_top_ips:.2f} ms (Top: {top_ips[0].item if top_ips else 'N/A'})")

        # Top Ports
        t0 = time.perf_counter()
        top_ports = AnalyticsService.get_top_destination_ports(session, limit=10, filters=filters)
        d_top_ports = (time.perf_counter() - t0) * 1000
        print(f"    - Top Dest Ports (Limit 10):  {d_top_ports:.2f} ms")

        # Vendor Distribution
        t0 = time.perf_counter()
        vendors = AnalyticsService.get_vendors(session, filters)
        d_vendors = (time.perf_counter() - t0) * 1000
        print(f"    - Vendor Distribution:        {d_vendors:.2f} ms (Unique: {len(vendors)})")

        # 3. Apache Parquet Columnar Export Benchmark
        print("\n[*] Apache Parquet Columnar Export Performance:")
        dict_records = [
            {
                "event_id": e.event_id,
                "raw_event_id": e.raw_event_id,
                "schema_version": e.schema_version,
                "timestamp": e.timestamp.isoformat() if e.timestamp else None,
                "ingestion_timestamp": e.ingestion_timestamp.isoformat() if e.ingestion_timestamp else None,
                "vendor": e.vendor,
                "product": e.product,
                "device_type": e.device_type,
                "source_ip": e.source_ip,
                "destination_ip": e.destination_ip,
                "source_port": e.source_port,
                "destination_port": e.destination_port,
                "protocol": e.protocol,
                "action": e.action,
                "severity": e.severity,
                "category": e.category,
                "message": e.message,
                "custom_fields": e.custom_fields,
                "tags": e.tags
            }
            for e in events
        ]

        with tempfile.TemporaryDirectory() as tmp_dir:
            t0 = time.perf_counter()
            files_created, bytes_written, paths, partitions = ParquetExporter.write_partitioned_parquet(
                records=dict_records,
                base_dir=tmp_dir
            )
            d_export = time.perf_counter() - t0
            mb_written = bytes_written / (1024 * 1024)
            rate_events = count / d_export
            rate_mb = mb_written / d_export if d_export > 0 else 0

            print(f"    - Total Parquet Files:        {files_created} file(s) across {partitions} partition(s)")
            print(f"    - Data Size Written:          {mb_written:.2f} MB ({bytes_written:,} bytes)")
            print(f"    - Parquet Export Duration:    {d_export:.3f} s")
            print(f"    - Export Throughput:          {rate_events:,.0f} records/sec ({rate_mb:.2f} MB/sec)")

        # 4. Offline Anomaly Detection Benchmark
        print("\n[*] Offline Anomaly Detection (Isolation Forest) Benchmark:")
        # Feature Extraction
        t0 = time.perf_counter()
        X, summaries = FeatureExtractor.extract_features(events)
        d_fe = time.perf_counter() - t0
        print(f"    - Feature Extraction (9 dims):{d_fe:.3f} s ({count / d_fe:,.0f} records/sec)")

        # Training Isolation Forest
        t0 = time.perf_counter()
        detector = IsolationForestDetector(contamination=0.05, random_state=42)
        detector.fit(X)
        d_train = time.perf_counter() - t0
        print(f"    - Model Training Duration:    {d_train:.3f} s")

        # Inference / Scoring + Explanation
        t0 = time.perf_counter()
        scores, is_anom, explanations = detector.predict(X, summaries)
        d_infer = time.perf_counter() - t0
        anom_count = int(is_anom.sum())
        print(f"    - Anomaly Inference & Explain:{d_infer:.3f} s ({count / d_infer:,.0f} records/sec)")
        print(f"    - Anomalies Flagged:          {anom_count} / {count} ({anom_count / count * 100:.2f}%)")

        session.close()

    print("\n" + "=" * 72)
    print("  BENCHMARK COMPLETE - AIR-GAPPED ANALYTICS ENGINE VERIFIED")
    print("=" * 72)


if __name__ == "__main__":
    run_benchmark([1000, 5000])
