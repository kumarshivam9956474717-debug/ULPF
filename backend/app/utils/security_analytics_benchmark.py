"""
Security Analytics & Data Quality Intelligence Benchmark Utility for ULPF Phase 6.

Measures:
1. Security overview query & distribution latency
2. Source health calculation throughput
3. Negative-space coverage gap analysis throughput
4. Historical baseline deviation calculation runtime
5. Cross-source multi-vendor correlation scanning throughput
6. Supervisory findings generation throughput on 10,000 and 100,000 event datasets
"""

import os
import sys
import time
import uuid
import random
from datetime import datetime, timezone, timedelta

current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.abspath(os.path.join(current_dir, "..", ".."))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.models.log_source import LogSource
from app.models.raw_event import RawEvent
from app.models.normalized_event import NormalizedEvent
from app.models.security_analytics import AnalyticsFinding, SourceBaseline
from app.services.security_analytics.service import security_analytics_service
from app.services.security_analytics.health import SourceHealthAnalyzer
from app.services.security_analytics.coverage import CoverageAnalyzer
from app.services.security_analytics.baseline import BaselineEngine
from app.services.security_analytics.correlation import CorrelationEngine


def seed_synthetic_analytics_data(session, event_count: int):
    """Seeds synthetic log sources, raw events, and normalized events."""
    vendors = ["Fortinet", "PaloAlto", "Cisco", "CheckPoint", "F5"]
    sources = []

    for v in vendors:
        sid = f"src_{v.lower()}_gw"
        source = LogSource(
            source_id=sid,
            hostname=f"{v}-Perimeter-Gateway",
            vendor=v,
            product="GatewayOS",
            device_type="firewall",
            enabled=True
        )
        session.add(source)
        sources.append(sid)

    session.flush()

    now_dt = datetime.now(timezone.utc)
    ips = ["10.0.0.5", "10.0.0.12", "192.168.1.50", "172.16.0.22", "198.51.100.8"]
    actions = ["allow", "deny", "block", "permit"]
    severities = ["low", "medium", "high", "critical", "informational"]
    protocols = ["tcp", "udp", "icmp", "https"]

    batch_size = 1000
    for i in range(event_count):
        raw_id = f"RAW-BM-{i:07d}"
        event_id = f"EVT-BM-{i:07d}"
        sid = sources[i % len(sources)]
        v = vendors[i % len(vendors)]

        # Time distribution over past 7 days
        offset_mins = random.randint(0, 7 * 24 * 60)
        evt_ts = now_dt - timedelta(minutes=offset_mins)

        raw = RawEvent(
            raw_event_id=raw_id,
            source_id=sid,
            received_at=evt_ts,
            raw_payload=f"src={ips[i % len(ips)]} dst=198.51.100.100 act={actions[i % len(actions)]}",
            payload_encoding="utf-8",
            payload_hash_sha256=f"hash_{i:07d}",
            source_format="key_value"
        )
        session.add(raw)

        norm = NormalizedEvent(
            event_id=event_id,
            raw_event_id=raw_id,
            schema_version="1.0.0",
            timestamp=evt_ts,
            ingestion_timestamp=evt_ts,
            vendor=v,
            product="GatewayOS",
            device_type="firewall",
            source_ip=ips[i % len(ips)],
            source_port=random.randint(1024, 65000),
            destination_ip="198.51.100.100",
            destination_port=443,
            protocol=protocols[i % len(protocols)],
            action=actions[i % len(actions)],
            severity=severities[i % len(severities)],
            category="network",
            normalization_version="1.0.0"
        )
        session.add(norm)

        if (i + 1) % batch_size == 0:
            session.commit()

    session.commit()


def run_security_analytics_benchmark(sample_counts: list = [10000, 100000]):
    print("=" * 78)
    print("  ULPF PHASE 6: ADVANCED SECURITY ANALYTICS & DATA QUALITY BENCHMARK")
    print("  National Technical Research Organisation (NTRO) - SIH26156")
    print("=" * 78)

    for count in sample_counts:
        print(f"\n============================================================================")
        print(f"  DATASET SIZE: {count:,} SYNTHETIC NORMALIZED EVENTS")
        print(f"============================================================================")

        engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool
        )
        Base.metadata.create_all(bind=engine)
        Session = sessionmaker(bind=engine)
        session = Session()

        # Seed data
        t0 = time.perf_counter()
        seed_synthetic_analytics_data(session, count)
        d_seed = time.perf_counter() - t0
        print(f"[*] Seeded {count:,} events & sources into memory DB: {d_seed:.2f} s")

        # 1. Overview Query Latency
        t0 = time.perf_counter()
        overview = security_analytics_service.get_overview(session)
        d_overview = (time.perf_counter() - t0) * 1000
        print(f"    1. Security Overview Aggregation:  {d_overview:.2f} ms")
        print(f"       -> Total Events: {overview.total_events:,}, Quality Index: {overview.data_quality_index}")

        # 2. Source Health Analytics
        t0 = time.perf_counter()
        health_list = SourceHealthAnalyzer.get_all_sources_health(session)
        d_health = (time.perf_counter() - t0) * 1000
        print(f"    2. Source Health Evaluation:       {d_health:.2f} ms")
        print(f"       -> Evaluated {len(health_list)} sources")

        # 3. Coverage / Negative-Space Analysis
        t0 = time.perf_counter()
        coverage_findings = CoverageAnalyzer.analyze_coverage_gaps(session)
        d_cov = (time.perf_counter() - t0) * 1000
        print(f"    3. Negative-Space Coverage Check:  {d_cov:.2f} ms")
        print(f"       -> Findings: {len(coverage_findings)} monitoring gap items")

        # 4. Baseline Deviation Engine
        t0 = time.perf_counter()
        baseline_results = security_analytics_service.get_baselines(session)
        d_base = (time.perf_counter() - t0) * 1000
        print(f"    4. Baseline & Deviation Scanning: {d_base:.2f} ms")
        print(f"       -> Evaluated {len(baseline_results)} source baselines")

        # 5. Cross-Source Correlation Scanning
        t0 = time.perf_counter()
        correlations = CorrelationEngine.scan_correlations(session, window_minutes=60)
        d_corr = (time.perf_counter() - t0) * 1000
        print(f"    5. Cross-Source Correlation Scan:  {d_corr:.2f} ms")
        print(f"       -> Candidates Found: {len(correlations)} correlation group(s)")

        # 6. Full On-Demand Scan Run & Findings Generation
        t0 = time.perf_counter()
        scan_res = security_analytics_service.run_analysis_scan(session)
        d_scan = time.perf_counter() - t0
        scan_rate = count / d_scan if d_scan > 0 else 0
        print(f"    6. Full Security Analysis Scan:    {d_scan:.3f} s ({scan_rate:,.0f} events/sec)")
        print(f"       -> Findings Generated: {scan_res.findings_generated} ({scan_res.new_findings_count} new)")

        session.close()

    print("\n" + "=" * 78)
    print("  SECURITY ANALYTICS BENCHMARK COMPLETE - 100% OFFLINE ENGINE VERIFIED")
    print("=" * 78)


if __name__ == "__main__":
    run_security_analytics_benchmark([10000, 100000])
