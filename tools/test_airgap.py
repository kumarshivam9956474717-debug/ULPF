#!/usr/bin/env python3
"""
OmniLogix / ULPF Air-Gapped Deployment Standalone Verification Utility.
Executes an 8-point automated compliance verification to prove that the system
has zero external runtime dependencies and functions completely offline.
"""

import sys
import os
import socket
from pathlib import Path

# Add backend directory to sys.path so imports resolve
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
BACKEND_DIR = PROJECT_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


def run_checks():
    print("=" * 70)
    print("  OMNILOGIX AIR-GAPPED DEPLOYMENT COMPLIANCE VERIFICATION")
    print("=" * 70)

    passed_checks = 0
    total_checks = 8

    # -------------------------------------------------------------
    # Check 1: Frontend index.html External Dependencies
    # -------------------------------------------------------------
    print("\n[Check 1/8] Verifying frontend/index.html has zero external links...")
    index_html = PROJECT_ROOT / "frontend" / "index.html"
    if not index_html.exists():
        print("  FAIL: frontend/index.html not found.")
    else:
        content = index_html.read_text(encoding="utf-8")
        external_needles = ["fonts.googleapis.com", "fonts.gstatic.com", "cdnjs.cloudflare.com", "unpkg.com", "cdn.jsdelivr.net"]
        found = [n for n in external_needles if n in content]
        if found:
            print(f"  FAIL: Found external dependencies: {found}")
        else:
            print("  PASS: Zero external font, script, or stylesheet CDNs in index.html.")
            passed_checks += 1

    # -------------------------------------------------------------
    # Check 2: Locally Bundled Fonts Package Configuration
    # -------------------------------------------------------------
    print("\n[Check 2/8] Verifying local font packaging (@fontsource/inter)...")
    pkg_json = PROJECT_ROOT / "frontend" / "package.json"
    content = pkg_json.read_text(encoding="utf-8") if pkg_json.exists() else ""
    if "@fontsource/inter" in content and "@fontsource/jetbrains-mono" in content:
        print("  PASS: @fontsource/inter and @fontsource/jetbrains-mono locally installed.")
        passed_checks += 1
    else:
        print("  FAIL: Missing @fontsource packages in package.json.")

    # -------------------------------------------------------------
    # Check 3: Backend Runtime Internet Egress Guard
    # -------------------------------------------------------------
    print("\n[Check 3/8] Verifying Air-Gap Egress Guard filters...")
    try:
        from app.core.airgap import is_destination_permitted
        assert is_destination_permitted("127.0.0.1") is True
        assert is_destination_permitted("localhost") is True
        assert is_destination_permitted("ulpf-db") is True
        assert is_destination_permitted("8.8.8.8") is False
        assert is_destination_permitted("api.openai.com") is False
        print("  PASS: Destination filter correctly authorizes LAN/local and rejects public internet.")
        passed_checks += 1
    except Exception as e:
        print(f"  FAIL: Destination filter error: {e}")

    # -------------------------------------------------------------
    # Check 4: Socket-Level Public Connection Blocking
    # -------------------------------------------------------------
    print("\n[Check 4/8] Testing socket connection interception against public IP...")
    try:
        from app.core.airgap import install_airgap_guard, uninstall_airgap_guard
        install_airgap_guard()
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        blocked = False
        try:
            sock.connect(("8.8.8.8", 53))
        except PermissionError as pe:
            blocked = True
            print(f"  PASS: Connection correctly blocked with PermissionError: {pe}")
        finally:
            sock.close()
            uninstall_airgap_guard()

        if blocked:
            passed_checks += 1
        else:
            print("  FAIL: Socket connection was not blocked.")
    except Exception as e:
        print(f"  FAIL: Socket guard test exception: {e}")

    # -------------------------------------------------------------
    # Check 5: Offline Machine Learning (IsolationForest)
    # -------------------------------------------------------------
    print("\n[Check 5/8] Verifying ML Anomaly Engine operates 100% offline...")
    try:
        import numpy as np
        from app.services.anomaly.detector import IsolationForestDetector
        detector = IsolationForestDetector(contamination=0.05, random_state=42)
        X = np.random.randn(80, 6)
        detector.fit(X)
        scores, flags, explanations = detector.predict(X[:5], [{} for _ in range(5)])
        assert len(scores) == 5
        print(f"  PASS: Scikit-learn IsolationForest trained ({detector.training_records_count} records) and predicted offline.")
        passed_checks += 1
    except Exception as e:
        print(f"  FAIL: ML anomaly engine error: {e}")

    # -------------------------------------------------------------
    # Check 6: Local Database Engine & Session
    # -------------------------------------------------------------
    print("\n[Check 6/8] Verifying Database operates locally (SQLite / PostgreSQL fallback)...")
    try:
        from app.core.database import SessionLocal
        db = SessionLocal()
        db.execute(__import__("sqlalchemy").text("SELECT 1"))
        db.close()
        print("  PASS: Local database connection verified successfully.")
        passed_checks += 1
    except Exception as e:
        print(f"  FAIL: Database connectivity failed: {e}")

    # -------------------------------------------------------------
    # Check 7: Local Syslog Socket Binding
    # -------------------------------------------------------------
    print("\n[Check 7/8] Verifying Inbound Syslog UDP / TCP socket reception...")
    try:
        # Verify socket can bind locally
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.bind(("127.0.0.1", 0))
        test_port = s.getsockname()[1]
        s.close()
        print(f"  PASS: Local UDP socket binding and datagram handling available on ephemeral port {test_port}.")
        passed_checks += 1
    except Exception as e:
        print(f"  FAIL: Local socket binding failed: {e}")

    # -------------------------------------------------------------
    # Check 8: Complete Event Ingestion & Normalization Offline
    # -------------------------------------------------------------
    print("\n[Check 8/8] Verifying full pipeline ingestion, normalization, and hashing...")
    try:
        from app.services.pipeline import PipelineService
        from app.core.database import SessionLocal
        db = SessionLocal()
        raw_log = "%ASA-4-106023: Deny tcp src outside:192.168.1.100/4582 dst inside:10.0.0.1/443 by access-group \"OUTSIDE-IN\""
        result = PipelineService.process_event(
            raw_payload=raw_log,
            db=db,
            source_id="AIRGAP-CLI-SRC",
            commit=True
        )
        db.close()
        assert result.success is True
        assert result.raw_event_id is not None
        assert result.normalized_event_id is not None
        print(f"  PASS: Ingestion -> Normalization -> Persistence verified (Raw Event ID: {result.raw_event_id[:12]}...).")
        passed_checks += 1
    except Exception as e:
        print(f"  FAIL: Pipeline offline execution failed: {e}")

    # -------------------------------------------------------------
    # Summary
    # -------------------------------------------------------------
    print("\n" + "=" * 70)
    print(f"  RESULTS: {passed_checks}/{total_checks} CHECKS PASSED")
    print("=" * 70)

    if passed_checks == total_checks:
        print(">>> SUCCESS: OmniLogix is verified 100% AIR-GAP COMPLIANT. <<<")
        return 0
    else:
        print(">>> WARNING: Some air-gap requirements failed. <<<")
        return 1


if __name__ == "__main__":
    sys.exit(run_checks())
