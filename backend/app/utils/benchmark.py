import argparse
import sys
import time
import tracemalloc
from typing import List
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.services.pipeline import PipelineService

# In-memory benchmark database
TEST_ENGINE = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
BenchmarkSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=TEST_ENGINE)

SAMPLE_EVENTS = [
    # Syslog
    "<166>Sep 10 09:30:00 asa-01 %ASA-6-302013: Built inbound TCP connection 9812 for outside:198.51.100.25/54321 to dmz:10.0.1.10/443",
    # JSON
    '{"timestamp": "2026-09-10T09:30:00Z", "src_ip": "192.168.1.50", "dst_ip": "10.0.0.1", "src_port": 50123, "dst_port": 443, "proto": "TCP", "action": "allow", "vendor": "Fortinet"}',
    # CEF
    "CEF:0|Check Point|VPN-1 & FireWall-1|R80.40|drop|Drop Security Rule|High|src=198.51.100.77 dst=10.0.1.25 spt=55412 dpt=3389 proto=TCP act=drop",
    # LEEF
    "LEEF:1.0|IBM|QRadar|5.4|IntrusionAlert|src=198.51.100.40\tdst=10.0.0.12\tsrcPort=39120\tdstPort=445\tproto=TCP\taction=block\tseverity=8",
    # CSV
    "2026-09-10T09:30:00Z,Juniper,router,10.0.1.5,49152,198.51.100.1,80,TCP,permit,informational,bgp_peer,Pass",
]


def run_benchmark(event_count: int = 1000, batch_size: int = 100):
    print(f"\n==================================================")
    print(f"  ULPF Ingestion & Normalization Engine Benchmark")
    print(f"  Target events: {event_count:,}")
    print(f"==================================================")

    # Initialize schema in memory
    Base.metadata.create_all(bind=TEST_ENGINE)
    db = BenchmarkSessionLocal()

    # Generate test corpus
    corpus: List[str] = [SAMPLE_EVENTS[i % len(SAMPLE_EVENTS)] for i in range(event_count)]

    tracemalloc.start()
    start_time = time.perf_counter()

    success_count = 0
    failed_count = 0

    # Process in chunks
    for i in range(0, event_count, batch_size):
        chunk = corpus[i : i + batch_size]
        res = PipelineService.process_batch(chunk, db=db, source_id="benchmark-emitter")
        success_count += res.total_normalized
        failed_count += res.total_failed

    elapsed = time.perf_counter() - start_time
    current_mem, peak_mem = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    events_per_sec = event_count / elapsed if elapsed > 0 else 0
    success_rate = (success_count / event_count) * 100.0 if event_count > 0 else 0.0

    print(f"\nResults:")
    print(f"  Total Processed:     {event_count:,} events")
    print(f"  Success:             {success_count:,} ({success_rate:.1f}%)")
    print(f"  Failed:              {failed_count:,}")
    print(f"  Total Time:          {elapsed:.3f} seconds")
    print(f"  Throughput:          {events_per_sec:,.1f} events/sec")
    print(f"  Peak Memory Used:    {peak_mem / (1024 * 1024):.2f} MB")
    print(f"==================================================\n")

    db.close()
    Base.metadata.drop_all(bind=TEST_ENGINE)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ULPF Pipeline Throughput Benchmark")
    parser.add_argument("--count", type=int, default=1000, help="Number of events to benchmark (1000, 10000, 100000)")
    parser.add_argument("--batch-size", type=int, default=200, help="Batch size per transaction")
    args = parser.parse_args()

    run_benchmark(event_count=args.count, batch_size=args.batch_size)
