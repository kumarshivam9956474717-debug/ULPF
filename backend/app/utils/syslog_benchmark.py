"""
ULPF Live Syslog Ingestion Benchmark
Measures UDP and TCP ingestion performance against the local server and pipeline.
"""

import asyncio
import socket
import time
from typing import Dict, Any

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from unittest.mock import patch

from app.core.database import Base, engine as pg_engine, SessionLocal as PGSessionLocal
from app.services.syslog.manager import syslog_manager
from app.services.syslog.metrics import syslog_metrics

# In-memory benchmark database fallback
SQLITE_ENGINE = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)
BenchmarkSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=SQLITE_ENGINE)

SAMPLE_CISCO = (
    "%ASA-6-302013: Built outbound TCP connection 987654 for "
    "inside:192.168.1.100/49210 (192.168.1.100/49210) to "
    "outside:198.51.100.25/443 (198.51.100.25/443)"
)


async def run_benchmark(event_count: int = 1000, protocol: str = "udp", port: int = 1514) -> Dict[str, Any]:
    # Determine database engine
    try:
        with pg_engine.connect():
            bench_engine = pg_engine
            bench_session_factory = PGSessionLocal
            print("[*] Using PostgreSQL database for benchmark.")
    except Exception:
        bench_engine = SQLITE_ENGINE
        bench_session_factory = BenchmarkSessionLocal
        print("[*] PostgreSQL not reachable; using fast in-memory SQLite for benchmark.")

    Base.metadata.create_all(bind=bench_engine)

    with patch("app.services.syslog.worker.SessionLocal", bench_session_factory):
        # Start SyslogManager
        syslog_metrics.reset()
        if not syslog_manager.is_running:
            await syslog_manager.start(
                queue_maxsize=20000,
                num_workers=4,
                udp_enabled=(protocol == "udp"),
                udp_port=port,
                tcp_enabled=(protocol == "tcp"),
                tcp_port=port,
                tls_enabled=False
            )

        # Allow listener to bind
        await asyncio.sleep(0.1)

        print(f"[*] Starting {protocol.upper()} benchmark with {event_count:,} events...")
        payload_bytes = (SAMPLE_CISCO + "\n").encode("utf-8") if protocol == "tcp" else SAMPLE_CISCO.encode("utf-8")

        start_send = time.perf_counter()

        if protocol == "udp":
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            try:
                for _ in range(event_count):
                    sock.sendto(payload_bytes, ("127.0.0.1", port))
            finally:
                sock.close()
        else:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect(("127.0.0.1", port))
            try:
                for _ in range(event_count):
                    sock.sendall(payload_bytes)
            finally:
                sock.close()

        send_duration = time.perf_counter() - start_send

        # Wait for workers to drain the queue
        drain_start = time.perf_counter()
        timeout = 30.0
        while True:
            snap = syslog_metrics.snapshot()
            if snap["messages_processed"] + snap["messages_failed"] >= event_count:
                break
            if time.perf_counter() - drain_start > timeout:
                print("[!] Drain timeout reached.")
                break
            await asyncio.sleep(0.05)

        total_duration = time.perf_counter() - start_send
        final_snap = syslog_metrics.snapshot()

        rate = final_snap["messages_processed"] / total_duration if total_duration > 0 else 0

        results = {
            "event_count": event_count,
            "protocol": protocol,
            "send_duration_sec": round(send_duration, 4),
            "total_duration_sec": round(total_duration, 4),
            "events_per_second": round(rate, 2),
            "messages_received": final_snap["messages_received"],
            "messages_processed": final_snap["messages_processed"],
            "messages_failed": final_snap["messages_failed"],
            "messages_dropped": final_snap["messages_dropped"],
            "oversized_messages": final_snap["oversized_messages"],
            "avg_latency_ms": final_snap["processing_latency_ms_avg"]
        }

        print("=" * 60)
        print(f"BENCHMARK RESULTS ({protocol.upper()} - {event_count:,} events)")
        print(f"Total Time:      {results['total_duration_sec']}s")
        print(f"Throughput:      {results['events_per_second']} events/sec")
        print(f"Processed:       {results['messages_processed']}/{event_count}")
        print(f"Failed:          {results['messages_failed']}")
        print(f"Dropped:         {results['messages_dropped']}")
        print(f"Avg Latency:     {results['avg_latency_ms']} ms")
        print("=" * 60)

        # Stop manager
        await syslog_manager.stop()

        return results



if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="ULPF Syslog Benchmark")
    parser.add_argument("--count", type=int, default=1000, help="Number of events (default: 1000)")
    parser.add_argument("--protocol", choices=["tcp", "udp"], default="tcp", help="Protocol (default: tcp)")
    parser.add_argument("--port", type=int, default=1514, help="Port (default: 1514)")
    args = parser.parse_args()

    asyncio.run(run_benchmark(args.count, args.protocol, args.port))


