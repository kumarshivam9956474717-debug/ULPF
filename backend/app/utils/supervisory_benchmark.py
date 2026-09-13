"""
ULPF Phase 7 Supervisory Intelligence Performance Benchmark Utility.

Measures actual performance of:
1. Multi-dimensional 8-capability assessment generation latency
2. Intelligent alert sample prioritization throughput
3. Peer benchmarking computation speed
4. Execution-gap and negative-space finding generation speed
"""

import time
import sys
import os
from datetime import datetime, timezone

# Add backend directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from app.services.supervisory.capability_engine import CapabilityEngine
from app.services.supervisory.execution_gaps import ExecutionGapEngine
from app.services.supervisory.negative_space import SupervisoryNegativeSpaceEngine
from app.services.supervisory.prioritization_engine import PrioritizationEngine
from app.services.supervisory.peer_benchmarking import PeerBenchmarkingEngine


def run_supervisory_benchmark():
    print("=" * 70)
    print("ULPF PHASE 7 SUPERVISORY INTELLIGENCE BENCHMARK")
    print("=" * 70)

    # Generate synthetic event & case dataset across 5 entities
    num_entities = 5
    num_events_per_entity = 2000
    total_events = num_entities * num_events_per_entity

    print(f"[*] Generating synthetic telemetry: {num_entities} entities, {total_events} total events...")

    events_by_entity = {}
    for i in range(num_entities):
        eid = f"CSE-ENTITY-0{i+1}"
        e_list = []
        for j in range(num_events_per_entity):
            sev = "CRITICAL" if j % 50 == 0 else ("HIGH" if j % 10 == 0 else "MEDIUM")
            e_list.append({
                "id": f"evt-{i}-{j}",
                "event_id": f"evt-{i}-{j}",
                "raw_event_id": f"raw-{i}-{j}",
                "severity": sev,
                "vendor": "Cisco" if j % 2 == 0 else "Palo Alto",
                "category": "firewall" if j % 3 == 0 else "authentication",
                "event_type": "SESSION_DROP",
                "signature_id": f"SIG-100{j % 10}",
                "timestamp": datetime.now(timezone.utc),
                "closure_time_seconds": 5.0 if j % 100 == 0 else 350.0,
                "escalated": False if sev == "CRITICAL" else True,
            })
        events_by_entity[eid] = e_list

    cap_engine = CapabilityEngine()
    gap_engine = ExecutionGapEngine()
    neg_engine = SupervisoryNegativeSpaceEngine()
    prioritization_engine = PrioritizationEngine()
    peer_engine = PeerBenchmarkingEngine()

    # Benchmark 1: 8-Capability Dimension Evaluation
    print("\n--- 1. 8-Capability Dimension Evaluation ---")
    start_t = time.perf_counter()
    sample_metrics = {"total_events": 2000, "high_severity_count": 200, "unmapped_ratio": 0.05}
    for _ in range(100):
        _ = cap_engine.evaluate_all(sample_metrics, {}, {}, {}, {})
    eval_time = (time.perf_counter() - start_t) / 100.0 * 1000.0
    print(f"[OK] 8-Capability Dimension Scan: {eval_time:.3f} ms / entity")

    # Benchmark 2: Execution-Gap & Negative-Space Finding Generation
    print("\n--- 2. Execution-Gap & Negative-Space Finding Generation ---")
    start_t = time.perf_counter()
    total_findings = 0
    for eid, evts in events_by_entity.items():
        gaps = gap_engine.detect_execution_gaps(eid, evts, [{"status": "CLOSED", "closure_time_seconds": 4.0}])
        negs = neg_engine.analyze_negative_space(eid, [{"hostname": "fw-01", "enabled": False}], evts)
        total_findings += len(gaps) + len(negs)
    gap_time = (time.perf_counter() - start_t) * 1000.0
    print(f"[OK] Finding Generation Latency: {gap_time:.2f} ms across {num_entities} entities ({total_findings} total findings generated)")

    # Benchmark 3: Alert Sample Prioritization
    print("\n--- 3. Alert Sample Prioritization Engine ---")
    start_t = time.perf_counter()
    sampled_count = 0
    for eid, evts in events_by_entity.items():
        samples = prioritization_engine.sample_and_prioritize(eid, evts, limit=50)
        sampled_count += len(samples)
    prioritization_time = time.perf_counter() - start_t
    throughput = total_events / prioritization_time
    print(f"[OK] Prioritized {total_events} events into {sampled_count} review samples in {prioritization_time:.4f} sec")
    print(f"[OK] Prioritization Throughput: {throughput:,.0f} events/sec")

    # Benchmark 4: Peer Benchmarking
    print("\n--- 4. Peer Benchmarking Matrix Computation ---")
    start_t = time.perf_counter()
    peer_data = [{"anomaly_rate": 0.04, "investigation_rate": 0.80, "data_quality_score": 96.0}] * 20
    for _ in range(500):
        _ = peer_engine.compute_peer_benchmarking("CSE-ALPHA-01", peer_data[0], peer_data)
    peer_time = (time.perf_counter() - start_t) / 500.0 * 1000.0
    print(f"[OK] Peer Benchmarking Latency: {peer_time:.3f} ms / entity across 20 peers")

    print("\n" + "=" * 70)
    print("PHASE 7 BENCHMARK COMPLETE — ALL SYSTEMS HIGH-THROUGHPUT OFFLINE")
    print("=" * 70)


if __name__ == "__main__":
    run_supervisory_benchmark()
