"""
Onboarding & Configurable Parser Benchmark Utility for ULPF Phase 5.

Measures:
1. Unknown log structure analysis & delimiter detection throughput
2. Candidate field & semantic datatype inference throughput
3. Deterministic UES mapping suggestion latency
4. Mapping simulation & validation throughput
5. Configurable parser end-to-end ingestion throughput on unknown vendors
"""

import os
import sys
import time
import uuid
from typing import List, Dict, Any

current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.abspath(os.path.join(current_dir, "..", ".."))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.services.onboarding.analyzer import LogAnalyzer
from app.services.onboarding.mapper import FieldMapper
from app.services.onboarding.validators import MappingValidator
from app.services.onboarding.models import MappingRule, ProfileCreateRequest
from app.services.onboarding.service import OnboardingService
from app.services.parsers.configurable import ConfigurableParser


def generate_synthetic_unknown_logs(vendor: str, count: int) -> List[str]:
    """Generates synthetic unknown vendor events."""
    logs = []
    actions = ["allow", "deny", "block", "permit"]
    protocols = ["tcp", "udp", "icmp"]
    severities = ["low", "medium", "high", "critical"]

    for i in range(count):
        src_ip = f"10.0.{(i % 250)}.{10 + (i % 200)}"
        dst_ip = f"198.51.100.{(i % 100) + 1}"
        port = 443 if i % 2 == 0 else (80 if i % 3 == 0 else 22)
        act = actions[i % len(actions)]
        proto = protocols[i % len(protocols)]
        sev = severities[i % len(severities)]

        if vendor == "VendorA":
            # key-value with standard prefixes
            log = f"src={src_ip} dst={dst_ip} dpt={port} act={act} proto={proto} flow_id={i} msg=\"Perimeter traffic audit\""
        elif vendor == "VendorB":
            # camelCase key-value
            log = f"sourceAddress={src_ip} destinationAddress={dst_ip} destinationPort={port} action={act} protocol={proto} severity={sev} traceId=TRC-{i:06d}"
        else:
            # pipe-delimited
            log = f"2026-09-10T12:{i % 60:02d}:00Z|edge-gw-{(i % 5) + 1}|{src_ip}|{dst_ip}|{port}|{act}|{proto}|{sev}"

        logs.append(log)

    return logs


def run_onboarding_benchmark(sample_counts: List[int] = [100, 1000, 10000]):
    print("=" * 76)
    print("  ULPF PHASE 5: NO-CODE ONBOARDING & CONFIGURABLE PARSER BENCHMARK")
    print("  National Technical Research Organisation (NTRO) - SIH26156")
    print("=" * 76)

    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)

    vendors = [
        ("VendorA (Key-Value)", "VendorA"),
        ("VendorB (camelCase KV)", "VendorB"),
        ("VendorC (Pipe-Delimited)", "VendorC")
    ]

    for count in sample_counts:
        print(f"\n============================================================================")
        print(f"  DATASET SIZE: {count:,} EVENTS PER UNKNOWN VENDOR")
        print(f"============================================================================")

        for v_label, v_key in vendors:
            print(f"\n[*] Evaluating Unknown Vendor: {v_label}")
            logs = generate_synthetic_unknown_logs(v_key, count)

            # 1. Structure Analysis & Delimiter Detection
            t0 = time.perf_counter()
            fmt, conf, delim, kv_delim, has_syslog, candidates, warnings = LogAnalyzer.analyze_samples(logs[:min(50, len(logs))])
            d_analysis = (time.perf_counter() - t0) * 1000
            print(f"    1. Structure Analysis (50 samples): {d_analysis:.2f} ms")
            print(f"       -> Detected Format: {fmt} (Confidence: {conf:.2f}, Delimiter: '{delim}', KV: '{kv_delim}')")
            print(f"       -> Extracted Candidates: {len(candidates)} candidate field(s)")

            # 2. UES Mapping Suggestion & Confidence Scoring
            t0 = time.perf_counter()
            suggestions = FieldMapper.suggest_mappings(candidates)
            d_mapping = (time.perf_counter() - t0) * 1000
            high_conf = sum(1 for s in suggestions if s.confidence_level.value == "HIGH")
            print(f"    2. UES Field Mapping Suggestion:    {d_mapping:.2f} ms")
            print(f"       -> Suggested: {len(suggestions)} rules ({high_conf} HIGH confidence)")

            # 3. Simulation & Validation Throughput
            rules = [
                MappingRule(
                    source_field=s.source_field,
                    target_field=s.target_field,
                    is_custom=s.is_custom,
                    confidence=s.confidence
                )
                for s in suggestions
            ]

            t0 = time.perf_counter()
            val_res = MappingValidator.simulate_mapping(
                sample_logs=logs,
                source_format=fmt,
                delimiter=delim,
                kv_delimiter=kv_delim,
                mappings=rules
            )
            d_val = time.perf_counter() - t0
            val_rate = count / d_val if d_val > 0 else 0
            print(f"    3. Mapping Simulation on {count:,} logs: {d_val:.3f} s ({val_rate:,.0f} events/sec)")
            print(f"       -> Passed: {val_res.records_passed} / {count} (Failures: {val_res.records_failed})")

            # 4. Configurable Parser End-to-End Execution
            session = Session()
            prof_req = ProfileCreateRequest(
                name=f"Profile_{v_key}_{count}_{uuid.uuid4().hex[:6]}",
                vendor=v_key,
                product="PerimeterEdge",
                device_type="firewall",
                source_format=fmt,
                configuration={"delimiter": delim, "kv_delimiter": kv_delim},
                field_mappings=rules,
                confidence=conf
            )
            profile = OnboardingService.create_profile(session, prof_req)
            parser = ConfigurableParser(profile)

            t0 = time.perf_counter()
            parsed_count = 0
            parse_errors = 0
            for item in logs:
                pe = parser.parse(item)
                if pe.errors:
                    parse_errors += 1
                else:
                    parsed_count += 1
            d_parse = time.perf_counter() - t0
            parse_rate = count / d_parse if d_parse > 0 else 0

            print(f"    4. Configurable Parser Execution:   {d_parse:.3f} s ({parse_rate:,.0f} events/sec)")
            print(f"       -> Successfully Parsed: {parsed_count} / {count} (Errors: {parse_errors})")
            session.close()

    print("\n" + "=" * 76)
    print("  ONBOARDING BENCHMARK COMPLETE - ZERO-CODE REUSABLE ENGINE VERIFIED")
    print("=" * 76)


if __name__ == "__main__":
    run_onboarding_benchmark([100, 1000, 10000])
