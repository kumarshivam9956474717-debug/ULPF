"""
OmniLogix / ULPF Air-Gapped Deployment Verification Test Suite.
Validates that the entire platform operates strictly within an offline air-gapped enclave.
"""

import os
import socket
from pathlib import Path
import pytest
import numpy as np

from app.core.config import settings
from app.core.airgap import (
    is_destination_permitted,
    install_airgap_guard,
    uninstall_airgap_guard,
    LOCAL_HOSTS,
)
from app.services.anomaly.detector import IsolationForestDetector
from app.core.database import SessionLocal
from app.services.pipeline import PipelineService


def test_1_frontend_index_html_has_zero_external_fonts():
    """Verify that frontend/index.html contains zero external Google Fonts or CDN links."""
    # Find frontend index.html relative to backend root
    base_dir = Path(__file__).resolve().parent.parent.parent
    index_html_path = base_dir / "frontend" / "index.html"
    
    assert index_html_path.exists(), f"Expected {index_html_path} to exist"
    content = index_html_path.read_text(encoding="utf-8")

    assert "fonts.googleapis.com" not in content, "Found external Google Fonts API in index.html"
    assert "fonts.gstatic.com" not in content, "Found external Google Fonts GStatic in index.html"
    assert "cdnjs.cloudflare.com" not in content, "Found external CDN in index.html"
    assert "unpkg.com" not in content, "Found unpkg CDN in index.html"
    assert "cdn.jsdelivr.net" not in content, "Found jsdelivr CDN in index.html"


def test_2_frontend_package_json_includes_local_fonts():
    """Verify package.json specifies locally bundled font packages."""
    base_dir = Path(__file__).resolve().parent.parent.parent
    pkg_json_path = base_dir / "frontend" / "package.json"
    
    assert pkg_json_path.exists()
    content = pkg_json_path.read_text(encoding="utf-8")

    assert "@fontsource/inter" in content, "Expected @fontsource/inter in frontend dependencies"
    assert "@fontsource/jetbrains-mono" in content, "Expected @fontsource/jetbrains-mono in frontend dependencies"


def test_3_airgap_destination_filter_logic():
    """Verify that local destinations are permitted and public internet destinations are rejected."""
    # Permitted Local Destinations
    assert is_destination_permitted("127.0.0.1") is True
    assert is_destination_permitted("localhost") is True
    assert is_destination_permitted("::1") is True
    assert is_destination_permitted("0.0.0.0") is True
    assert is_destination_permitted("ulpf-db") is True
    assert is_destination_permitted("ulpf-backend") is True
    assert is_destination_permitted("db") is True
    assert is_destination_permitted("192.168.1.100") is True   # Private RFC1918
    assert is_destination_permitted("10.0.5.1") is True       # Private RFC1918
    assert is_destination_permitted("172.18.0.2") is True     # Docker bridge network

    # Blocked External Destinations
    assert is_destination_permitted("8.8.8.8") is False       # Google DNS
    assert is_destination_permitted("1.1.1.1") is False       # Cloudflare DNS
    assert is_destination_permitted("api.openai.com") is False
    assert is_destination_permitted("huggingface.co") is False
    assert is_destination_permitted("telemetry.example.com") is False
    assert is_destination_permitted("93.184.216.34") is False # Example.com public IP


def test_4_socket_guard_blocks_unauthorized_external_connections():
    """Verify that active socket guard raises PermissionError on public connection attempts."""
    try:
        install_airgap_guard()
        test_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        with pytest.raises(PermissionError) as exc_info:
            # Attempt connection to public IP
            test_sock.connect(("8.8.8.8", 443))
        
        assert "[AIR-GAP ENCLAVE VIOLATION]" in str(exc_info.value)
        test_sock.close()
    finally:
        uninstall_airgap_guard()


def test_5_ml_isolation_forest_executes_completely_offline():
    """Verify ML anomaly engine initializes, trains, and infers without any network dependency."""
    detector = IsolationForestDetector(contamination=0.05, random_state=42)
    assert detector.is_trained is False

    # Generate synthetic feature array
    np.random.seed(42)
    X_train = np.random.randn(100, 6)
    detector.fit(X_train)

    assert detector.is_trained is True
    assert detector.training_records_count == 100

    # Inference check
    X_test = np.random.randn(10, 6)
    scores, flags, explanations = detector.predict(X_test, [{} for _ in range(10)])

    assert len(scores) == 10
    assert len(flags) == 10
    assert len(explanations) == 10


def test_6_local_pipeline_and_database_persistence_offline():
    """Verify end-to-end event ingestion, normalization, and hashing runs offline."""
    db = SessionLocal()
    try:
        raw_log = "<189>date=2026-09-15 time=10:00:00 devname=EdgeFG01 devid=FGT60D3G srcip=192.168.1.50 dstip=10.0.0.1 action=deny msg=\"Airgap validation event\""
        
        result = PipelineService.process_event(
            raw_payload=raw_log,
            db=db,
            source_id="TEST-AIRGAP-01",
            commit=True
        )

        assert result.success is True
        assert result.raw_event_id is not None
        assert result.normalized_event_id is not None
        assert result.detected_format == "syslog"
    finally:
        db.close()
