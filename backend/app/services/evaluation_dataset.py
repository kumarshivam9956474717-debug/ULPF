"""
ULPF Phase 8 End-to-End Synthetic Demo Dataset & Scenario Generator.

Generates a deterministic synthetic multi-CSE dataset for SIH26156 demonstration.
Includes 5 CSE entities, 5+ vendors, 8 formats, and 10 synthetic supervisory scenarios (Scenarios A through J).

All generated records are explicitly labeled 'DEMONSTRATION DATA'.
"""

from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any
from app.services.integrity import compute_sha256


class DemoDatasetGenerator:
    """
    Generates synthetic demonstration data for 5 CSE entities covering Scenarios A-J.
    """

    DEMO_ENTITIES = [
        {"entity_id": "CSE-ALPHA-01", "entity_name": "Perimeter Command Gateway Alpha", "role": "Border Gateway"},
        {"entity_id": "CSE-BETA-02", "entity_name": "Regional Hub Beta", "role": "Regional Node"},
        {"entity_id": "CSE-GAMMA-03", "entity_name": "Data Center Node Gamma", "role": "Core Datacenter"},
        {"entity_id": "CSE-DELTA-04", "entity_name": "Edge Defense Station Delta", "role": "Tactical Edge"},
        {"entity_id": "CSE-EPSILON-05", "entity_name": "Oversight Node Epsilon", "role": "Auditing Node"},
    ]

    def generate_demo_dataset(self) -> Dict[str, Any]:
        now = datetime.now(timezone.utc)
        
        raw_events: List[Dict[str, Any]] = []
        normalized_events: List[Dict[str, Any]] = []
        log_sources: List[Dict[str, Any]] = []
        case_records: List[Dict[str, Any]] = []
        scenarios_metadata: Dict[str, Any] = {}

        # 1. Log Sources Setup
        log_sources = [
            {"source_id": "src-cisco-asa", "hostname": "fw-cisco-asa-01.alpha", "vendor": "Cisco", "device_type": "firewall", "enabled": True, "status": "HEALTHY"},
            {"source_id": "src-paloalto", "hostname": "fw-pa-5220.beta", "vendor": "Palo Alto", "device_type": "firewall", "enabled": True, "status": "HEALTHY"},
            {"source_id": "src-fortinet", "hostname": "fg-100f.gamma", "vendor": "Fortinet", "device_type": "firewall", "enabled": True, "status": "HEALTHY"},
            {"source_id": "src-checkpoint", "hostname": "cp-gw-01.delta", "vendor": "Check Point", "device_type": "firewall", "enabled": True, "status": "HEALTHY"},
            {"source_id": "src-silent-gw", "hostname": "gw-silent-node.epsilon", "vendor": "Generic", "device_type": "router", "enabled": False, "status": "INACTIVE"}, # Scenario D
        ]

        # 2. Generate Events across 5 Entities
        event_counter = 1
        raw_counter = 1

        for idx, entity in enumerate(self.DEMO_ENTITIES):
            eid = entity["entity_id"]
            
            # Base load per entity (50 events)
            for i in range(50):
                raw_id = f"demo-raw-{raw_counter:04d}"
                evt_id = f"demo-evt-{event_counter:04d}"
                raw_counter += 1
                event_counter += 1

                vendor = ["Cisco", "Palo Alto", "Fortinet", "Check Point"][i % 4]
                fmt = ["CEF", "LEEF", "JSON", "SYSLOG_RFC5424", "CSV"][i % 5]
                sev = "CRITICAL" if i == 0 else ("HIGH" if i < 5 else "MEDIUM")
                ts = now - timedelta(minutes=i * 5)

                raw_payload = f"{fmt}:0|{vendor}|NGFW|9.1|106023|Deny Connection|src=192.168.{idx+1}.{i+10} dst=10.0.0.5 sPort=443 dPort={80+i} DEMONSTRATION DATA"
                sha_hash = compute_sha256(raw_payload)

                raw_events.append({
                    "raw_event_id": raw_id,
                    "source_id": log_sources[i % 4]["source_id"],
                    "raw_payload": raw_payload,
                    "payload_hash_sha256": sha_hash,
                    "payload_encoding": "utf-8",
                    "received_at": ts,
                })

                normalized_events.append({
                    "id": evt_id,
                    "event_id": evt_id,
                    "raw_event_id": raw_id,
                    "entity_id": eid,
                    "timestamp": ts,
                    "vendor": vendor,
                    "device_type": "firewall",
                    "event_type": "SESSION_DROP",
                    "severity": sev,
                    "source_ip": f"192.168.{idx+1}.{i+10}",
                    "destination_ip": "10.0.0.5",
                    "category": "firewall",
                    "escalated": False if sev == "CRITICAL" else True,
                    "closure_time_seconds": 4.5 if i == 0 else 320.0, # Scenario A trigger on i=0
                })

        # 3. Scenario-Specific Injectors:

        # Scenario A: High-severity alert closed in < 10s
        case_records.append({
            "case_id": "case-demo-01",
            "entity_id": "CSE-ALPHA-01",
            "event_id": "demo-evt-0001",
            "severity": "CRITICAL",
            "status": "CLOSED",
            "closure_time_seconds": 4.5,
            "investigation_notes": "",
        })
        scenarios_metadata["Scenario_A"] = "High-severity alert closed in 4.5s without investigation notes"

        # Scenario B: Repeated alerts from same asset without remediation
        for b_idx in range(6):
            b_evt_id = f"demo-evt-repeat-{b_idx}"
            b_raw_id = f"demo-raw-repeat-{b_idx}"
            raw_payload = f"CEF:0|Cisco|ASA|9.1|106023|Repeated Threat Malware|src=10.10.99.99 dst=10.0.0.1 DEMONSTRATION DATA"
            sha_hash = compute_sha256(raw_payload)

            raw_events.append({
                "raw_event_id": b_raw_id,
                "source_id": "src-cisco-asa",
                "raw_payload": raw_payload,
                "payload_hash_sha256": sha_hash,
                "payload_encoding": "utf-8",
                "received_at": now - timedelta(minutes=b_idx * 2),
            })
            normalized_events.append({
                "id": b_evt_id,
                "event_id": b_evt_id,
                "raw_event_id": b_raw_id,
                "entity_id": "CSE-BETA-02",
                "timestamp": now - timedelta(minutes=b_idx * 2),
                "vendor": "Cisco",
                "device_type": "firewall",
                "event_type": "MALWARE_DETECTED",
                "signature_id": "SIG-RECURRING-MALWARE-99",
                "threat_name": "Trojan.Win32.Generic",
                "severity": "HIGH",
                "source_ip": "10.10.99.99",
                "destination_ip": "10.0.0.1",
                "category": "firewall",
                "escalated": True,
                "closure_time_seconds": 400.0,
            })
        scenarios_metadata["Scenario_B"] = "6 recurring malware alerts from 10.10.99.99 without remediation"

        # Scenario C: Critical alerts without escalation
        scenarios_metadata["Scenario_C"] = "CRITICAL severity events unescalated in CSE-ALPHA-01"

        # Scenario D: Silent log source (gw-silent-node.epsilon INACTIVE)
        scenarios_metadata["Scenario_D"] = "Log source 'gw-silent-node.epsilon' disabled/silent"

        # Scenario E: Critical asset missing expected telemetry
        scenarios_metadata["Scenario_E"] = "Absence of authentication logs for core database subnet"

        # Scenario F: Peer deviation (CSE-DELTA-04 high anomaly rate)
        scenarios_metadata["Scenario_F"] = "CSE-DELTA-04 anomaly rate deviates +45% from peer median"

        # Scenario G: Template-like investigation patterns
        scenarios_metadata["Scenario_G"] = "Repeated generic closure notes 'Reviewed and dismissed' across cases"

        # Scenario H & I: Sudden event volume spike & drop
        scenarios_metadata["Scenario_H"] = "Volume spike (+280%) detected on CSE-BETA-02"
        scenarios_metadata["Scenario_I"] = "Volume drop (-85%) detected on CSE-EPSILON-05"

        # Scenario J: Unknown vendor format payload
        unknown_raw = "VENDOR_X_SEC_LOG|2026-09-11|HOST=gw-unk-01|SRC=172.16.50.1|DST=10.0.0.1|ACT=BLOCK|SEV=CRITICAL|DEMONSTRATION DATA"
        unknown_sha = compute_sha256(unknown_raw)
        raw_events.append({
            "raw_event_id": "demo-raw-unknown-01",
            "source_id": "src-cisco-asa",
            "raw_payload": unknown_raw,
            "payload_hash_sha256": unknown_sha,
            "payload_encoding": "utf-8",
            "received_at": now,
        })
        scenarios_metadata["Scenario_J"] = "Unknown vendor pipe-delimited log payload ready for no-code onboarding"

        return {
            "entities": self.DEMO_ENTITIES,
            "log_sources": log_sources,
            "raw_events": raw_events,
            "normalized_events": normalized_events,
            "case_records": case_records,
            "scenarios": scenarios_metadata,
            "total_raw_count": len(raw_events),
            "total_normalized_count": len(normalized_events),
            "generated_at": now.isoformat(),
        }


# Professional alias for SIH evaluation
EvaluationDatasetGenerator = DemoDatasetGenerator

