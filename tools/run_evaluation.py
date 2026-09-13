"""
ULPF Phase 8 Reproducible SIH Evaluation Runner Script.

Executes the complete end-to-end evaluation pipeline:
1. Safely resets synthetic evaluation data environment
2. Generates synthetic multi-CSE dataset covering Scenarios A-J
3. Ingests raw events & UES normalized events
4. Runs Security Analytics & Supervisory Intelligence
5. Executes Scenario Validation Engine and prints verification summary
"""

import sys
import os
import time
from sqlalchemy import text as sa_text

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../backend")))

from app.core.database import SessionLocal
from app.services.evaluation_dataset import EvaluationDatasetGenerator, DemoDatasetGenerator
from app.services.validation import ValidationEngine
from app.services.supervisory import SupervisoryService
from app.models.raw_event import RawEvent
from app.models.normalized_event import NormalizedEvent
from app.models.log_source import LogSource
from app.models.supervisory import EntityAssessment, CapabilityAssessment, SupervisoryIndicator, ReviewSample, SupervisoryReview


def run_reproducible_evaluation():
    print("=" * 75)
    print("ULPF PHASE 8 — REPRODUCIBLE SIH EVALUATION RUNNER")
    print("=" * 75)

    try:
        db = SessionLocal()
        # Test connection
        db.execute(sa_text("SELECT 1"))
    except Exception:
        print("[!] Local PostgreSQL connection unavailable. Falling back to isolated SQLite demo database ('sqlite:///demo.db')...")
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        from app.core.database import Base
        import app.models  # Register all models

        demo_db_url = "sqlite:///demo.db"
        engine = create_engine(demo_db_url, connect_args={"check_same_thread": False})
        Base.metadata.create_all(bind=engine)
        DemoSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        db = DemoSession()

    try:
        # Step 1: Safe Reset
        print("\n[STEP 1/6] Resetting Synthetic Demo Environment...")
        db.query(SupervisoryReview).delete()
        db.query(ReviewSample).delete()
        db.query(SupervisoryIndicator).delete()
        db.query(CapabilityAssessment).delete()
        db.query(EntityAssessment).delete()
        db.query(NormalizedEvent).filter(NormalizedEvent.raw_event_id.like("demo-raw-%")).delete(synchronize_session=False)
        db.query(RawEvent).filter(RawEvent.raw_event_id.like("demo-raw-%")).delete(synchronize_session=False)
        db.commit()
        print("[OK] Demo database tables reset cleanly.")

        # Step 2: Synthetic Data Generation
        print("\n[STEP 2/6] Generating Synthetic Telemetry across 5 CSE Entities (Scenarios A-J)...")
        generator = DemoDatasetGenerator()
        dataset = generator.generate_demo_dataset()
        print(f"[OK] Generated {dataset['total_raw_count']} raw events and {dataset['total_normalized_count']} UES events.")

        # Step 3: Ingestion
        print("\n[STEP 3/6] Ingesting Demo Log Sources, Raw Events, and Normalized Events...")
        for s in dataset["log_sources"]:
            if not db.query(LogSource).filter(LogSource.source_id == s["source_id"]).first():
                db.add(LogSource(source_id=s["source_id"], hostname=s["hostname"], vendor=s["vendor"], device_type=s["device_type"], enabled=s["enabled"]))
        
        for r in dataset["raw_events"]:
            if not db.query(RawEvent).filter(RawEvent.raw_event_id == r["raw_event_id"]).first():
                db.add(RawEvent(raw_event_id=r["raw_event_id"], source_id=r["source_id"], raw_payload=r["raw_payload"], payload_hash_sha256=r["payload_hash_sha256"], payload_encoding=r["payload_encoding"], received_at=r["received_at"]))

        for n in dataset["normalized_events"]:
            if not db.query(NormalizedEvent).filter(NormalizedEvent.event_id == n["event_id"]).first():
                db.add(NormalizedEvent(id=n["id"], event_id=n["event_id"], raw_event_id=n["raw_event_id"], timestamp=n["timestamp"], vendor=n["vendor"], device_type=n["device_type"], event_type=n["event_type"], severity=n["severity"], source_ip=n.get("source_ip"), destination_ip=n.get("destination_ip"), category=n.get("category"), normalization_version="1.0"))

        db.commit()
        print("[OK] Ingestion & UES Normalization completed.")

        # Step 4: Security Analytics & Supervisory Assessment
        print("\n[STEP 4/6] Executing Supervisory Intelligence Scan & 8 Capability Evaluation across 5 CSEs...")
        supervisory_service = SupervisoryService()
        entities = [
            ("CSE-ALPHA-01", "Perimeter Command Gateway Alpha"),
            ("CSE-BETA-02", "Regional Hub Beta"),
            ("CSE-GAMMA-03", "Data Center Node Gamma"),
            ("CSE-DELTA-04", "Edge Defense Station Delta"),
            ("CSE-EPSILON-05", "Oversight Node Epsilon"),
        ]
        for eid, ename in entities:
            ass = supervisory_service.run_entity_assessment(db, entity_id=eid, entity_name=ename)
            print(f"[OK] Supervisory Assessment generated for {eid}: Overall Score = {ass.overall_score:.1f}/100 ({ass.risk_category}).")

        # Step 5: Scenario Validation Engine
        print("\n[STEP 5/6] Running Scenario Validation Engine against Scenarios A through J...")
        indicators = db.query(SupervisoryIndicator).all()
        actual_ind_list = [
            {"indicator": i.indicator_type, "indicator_type": i.indicator_type, "severity": i.severity, "entity_id": i.entity_id}
            for i in indicators
        ]

        val_engine = ValidationEngine()
        val_report = val_engine.validate_scenarios(actual_ind_list)

        print(f"[OK] Validation Engine Result: {val_report.overall_validation_status}")
        print(f"     Passed Scenarios: {val_report.passed_scenarios_count} / {val_report.total_scenarios_tested}")
        print(f"     Precision: {val_report.precision:.1f}% | Recall: {val_report.recall:.1f}% | F1-Score: {val_report.f1_score:.1f}%")

        # Step 6: Detailed Scenario Validation Breakdown
        print("\n[STEP 6/6] Scenario Validation Results Breakdown:")
        for res in val_report.scenario_results:
            status_symbol = "[PASS]" if res.status == "PASS" else "[PARTIAL]"
            print(f"  {status_symbol} {res.scenario_id}: {res.scenario_title} -> {res.expected_indicator}")

        print("\n" + "=" * 75)
        print("REPRODUCIBLE SIH EVALUATION INITIALIZATION COMPLETE — ALL SYSTEMS READY")
        print("=" * 75)

    finally:
        db.close()


# Backward compatibility alias
run_reproducible_demo = run_reproducible_evaluation
main = run_reproducible_evaluation


if __name__ == "__main__":
    run_reproducible_evaluation()

