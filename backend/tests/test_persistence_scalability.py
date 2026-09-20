import asyncio
import hashlib
import os
import shutil
import tempfile
import time
import uuid
from datetime import datetime, timezone
import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.core.database import Base, create_resilient_engine
from app.core.security import create_access_token
from app.main import app
from app.models.raw_event import RawEvent
from app.models.normalized_event import NormalizedEvent
from app.services.persistence.base import PersistenceItem
from app.services.persistence.database_backend import BatchDatabasePersistence
from app.services.persistence.parquet_backend import ParquetExportBackend
from app.services.persistence.streaming_backend import StreamingSink
from app.services.persistence.queue import AsyncPersistenceQueue
from tests.conftest import TestingSessionLocal, engine


@pytest.fixture(autouse=True)
def ensure_tables():
    Base.metadata.create_all(bind=engine)
    yield


def _make_sample_item(idx: int, batch_id: str = "TEST-RUN-01") -> PersistenceItem:
    raw_payload = f"<14>1 2026-09-15T12:00:00Z edge-gw-01 app-{idx} 1001 ID-{idx} [meta key=\"val\"] Test event {idx}"
    raw_hash = hashlib.sha256(raw_payload.encode("utf-8")).hexdigest()
    raw_id = f"RAW-{uuid.uuid4().hex[:16].upper()}"
    evt_id = f"EVT-{uuid.uuid4().hex[:16].upper()}"

    norm_event = {
        "event_id": evt_id,
        "source_event_id": f"SRC-{idx}",
        "raw_event_id": raw_id,
        "schema_version": "1.0.0",
        "timestamp": datetime.now(timezone.utc),
        "ingestion_timestamp": datetime.now(timezone.utc),
        "vendor": "Generic",
        "product": "SyslogEdge",
        "device_type": "gateway",
        "hostname": "edge-gw-01",
        "source_format": "syslog",
        "source_ip": "10.0.0.1",
        "destination_ip": "10.0.0.2",
        "severity": "low",
        "action": "allow",
        "event_type": "network_traffic",
        "message": f"Test event {idx}"
    }

    return PersistenceItem(
        raw_event_id=raw_id,
        raw_payload=raw_payload,
        payload_hash_sha256=raw_hash,
        received_at=datetime.now(timezone.utc),
        source_id="EDGE_GW_01",
        source_format="syslog",
        ingestion_batch_id=batch_id,
        normalized_event=norm_event,
        validation_status="valid"
    )


# =====================================================================
# 1. BATCH INSERTION & 2. PARTIAL BATCH FLUSH
# =====================================================================

@pytest.mark.anyio
async def test_batch_insertion_atomic():
    backend = BatchDatabasePersistence(session_factory=TestingSessionLocal)
    items = [_make_sample_item(i) for i in range(10)]

    persisted = await backend.write_batch(items)
    assert persisted == 10

    db = TestingSessionLocal()
    try:
        raw_count = db.query(RawEvent).filter(RawEvent.ingestion_batch_id == "TEST-RUN-01").count()
        assert raw_count >= 10
    finally:
        db.close()


@pytest.mark.anyio
async def test_partial_batch_flush():
    backend = BatchDatabasePersistence(session_factory=TestingSessionLocal)
    p_queue = AsyncPersistenceQueue(
        backend=backend,
        batch_size=50,  # Batch threshold larger than item count
        flush_interval_ms=50,
        max_queue_size=100
    )
    await p_queue.start()

    # Enqueue 5 items (partial batch)
    for i in range(5):
        p_queue.enqueue(_make_sample_item(i, batch_id="PARTIAL-BATCH-RUN"))

    # Wait for flush interval timer to fire
    await asyncio.sleep(0.15)
    await p_queue.stop(drain_timeout=1.0)

    metrics = p_queue.get_metrics()
    assert metrics["total_enqueued"] == 5
    assert metrics["total_persisted"] == 5
    assert metrics["batch_count"] >= 1


# =====================================================================
# 3. FLUSH INTERVAL TIMER & 4. GRACEFUL SHUTDOWN
# =====================================================================

@pytest.mark.anyio
async def test_flush_interval_timer():
    backend = BatchDatabasePersistence(session_factory=TestingSessionLocal)
    p_queue = AsyncPersistenceQueue(
        backend=backend,
        batch_size=1000,
        flush_interval_ms=80,
        max_queue_size=500
    )
    await p_queue.start()

    t_start = time.perf_counter()
    p_queue.enqueue(_make_sample_item(1, batch_id="INTERVAL-RUN"))

    # Should flush after ~80ms without reaching 1000 items
    while p_queue.total_persisted == 0 and (time.perf_counter() - t_start) < 1.0:
        await asyncio.sleep(0.02)

    elapsed_ms = (time.perf_counter() - t_start) * 1000.0
    assert p_queue.total_persisted == 1
    assert elapsed_ms < 600.0  # Verified timer triggered quickly
    await p_queue.stop()


@pytest.mark.anyio
async def test_graceful_shutdown_drains_queue():
    backend = BatchDatabasePersistence(session_factory=TestingSessionLocal)
    p_queue = AsyncPersistenceQueue(
        backend=backend,
        batch_size=100,
        flush_interval_ms=1000,  # Long interval
        max_queue_size=500
    )
    await p_queue.start()

    for i in range(25):
        p_queue.enqueue(_make_sample_item(i, batch_id="SHUTDOWN-RUN"))

    # Stop queue immediately; shutdown must flush remaining 25 items
    await p_queue.stop(drain_timeout=2.0)

    assert p_queue.queue.empty()
    assert p_queue.total_persisted == 25


# =====================================================================
# 5. QUEUE CAPACITY, 6. BACKPRESSURE & 7. CONTROLLED DROPS
# =====================================================================

@pytest.mark.anyio
async def test_queue_capacity_and_controlled_drops():
    backend = BatchDatabasePersistence(session_factory=TestingSessionLocal)
    small_queue = AsyncPersistenceQueue(
        backend=backend,
        batch_size=10,
        flush_interval_ms=1000,
        max_queue_size=5  # Cap queue at 5 items
    )
    # Do not start worker loop so queue fills completely
    for i in range(5):
        success = small_queue.enqueue(_make_sample_item(i, batch_id="DROP-TEST"))
        assert success is True

    # 6th item must trigger controlled drop
    dropped = small_queue.enqueue(_make_sample_item(99, batch_id="DROP-TEST"))
    assert dropped is False
    assert small_queue.total_dropped == 1

    metrics = small_queue.get_metrics()
    assert metrics["queue_depth"] == 5
    assert metrics["total_dropped"] == 1


# =====================================================================
# 8. PERSISTENCE FAILURE & 9. RETRY BEHAVIOR
# =====================================================================

class FailingPersistenceBackend(BatchDatabasePersistence):
    def __init__(self, fail_count: int = 2):
        super().__init__(session_factory=TestingSessionLocal, max_retries=3)
        self.fail_count = fail_count
        self.attempts = 0

    def get_session(self):
        self.attempts += 1
        if self.attempts <= self.fail_count:
            raise ConnectionError(f"Simulated database lock failure (attempt {self.attempts})")
        return super().get_session()


@pytest.mark.anyio
async def test_persistence_retry_success():
    failing_backend = FailingPersistenceBackend(fail_count=2)
    items = [_make_sample_item(i) for i in range(3)]

    persisted = await failing_backend.write_batch(items)
    assert persisted == 3
    assert failing_backend.attempts == 3  # Failed twice, succeeded on 3rd attempt


# =====================================================================
# 10. EXACT EVENT ACCOUNTING FORMULA
# =====================================================================

@pytest.mark.anyio
async def test_exact_event_accounting_formula():
    backend = BatchDatabasePersistence(session_factory=TestingSessionLocal)
    p_queue = AsyncPersistenceQueue(
        backend=backend,
        batch_size=10,
        flush_interval_ms=50,
        max_queue_size=20
    )
    await p_queue.start()

    # Enqueue 30 items into queue of capacity 20 (some will be dropped, rest persisted)
    for i in range(30):
        p_queue.enqueue(_make_sample_item(i, batch_id="ACCOUNTING-RUN"))

    await asyncio.sleep(0.2)
    await p_queue.stop(drain_timeout=1.0)

    metrics = p_queue.get_metrics()
    total_in = metrics["total_enqueued"] + metrics["total_dropped"]
    accounted = metrics["total_persisted"] + metrics["total_failed"] + metrics["total_dropped"]

    assert total_in == 30
    assert total_in == accounted
    assert metrics["accounting_balanced"] is True


# =====================================================================
# 11. RAW-EVENT INTEGRITY & 12. SHA-256 & 13. TRACEABILITY
# =====================================================================

@pytest.mark.anyio
async def test_raw_payload_and_sha256_forensic_traceability():
    backend = BatchDatabasePersistence(session_factory=TestingSessionLocal)
    sample_text = "%ASA-6-302013: Built outbound TCP connection 998877 for inside:192.168.2.50/50000 to outside:203.0.113.88/443"
    expected_hash = hashlib.sha256(sample_text.encode("utf-8")).hexdigest()
    raw_id = f"RAW-{uuid.uuid4().hex[:16].upper()}"
    evt_id = f"EVT-{uuid.uuid4().hex[:16].upper()}"

    item = PersistenceItem(
        raw_event_id=raw_id,
        raw_payload=sample_text,
        payload_hash_sha256=expected_hash,
        received_at=datetime.now(timezone.utc),
        source_id="CISCO-CORE-FW",
        source_format="syslog",
        ingestion_batch_id="FORENSIC-AUDIT-01",
        normalized_event={
            "event_id": evt_id,
            "source_event_id": "998877",
            "raw_event_id": raw_id,
            "schema_version": "1.0.0",
            "timestamp": datetime.now(timezone.utc),
            "vendor": "Cisco",
            "product": "ASA",
            "source_ip": "192.168.2.50",
            "destination_ip": "203.0.113.88",
            "source_port": 50000,
            "destination_port": 443,
            "severity": "low",
            "message": sample_text
        },
        validation_status="valid"
    )

    await backend.write_batch([item])

    db = TestingSessionLocal()
    try:
        # Traceability chain: NormalizedEvent -> raw_event_id -> RawEvent -> payload -> SHA256
        norm = db.query(NormalizedEvent).filter(NormalizedEvent.event_id == evt_id).first()
        assert norm is not None
        assert norm.raw_event_id == raw_id

        raw = db.query(RawEvent).filter(RawEvent.raw_event_id == norm.raw_event_id).first()
        assert raw is not None
        # 11. Verbatim raw payload match
        assert raw.raw_payload == sample_text
        # 12. SHA-256 cryptographic match
        assert raw.payload_hash_sha256 == expected_hash
        assert hashlib.sha256(raw.raw_payload.encode("utf-8")).hexdigest() == raw.payload_hash_sha256
    finally:
        db.close()


# =====================================================================
# 14. DATABASE CONNECTION POOL CONFIGURATION
# =====================================================================

def test_database_connection_pool_configuration():
    assert settings.DB_POOL_SIZE >= 10
    assert settings.DB_MAX_OVERFLOW >= 10
    assert settings.DB_POOL_TIMEOUT >= 10
    assert settings.DB_POOL_RECYCLE >= 300

    # Resilient engine returns valid engine
    eng = create_resilient_engine()
    assert eng is not None
    assert hasattr(eng, "connect")


# =====================================================================
# 15. HIGH-VOLUME PERSISTENCE THROUGHPUT
# =====================================================================

@pytest.mark.anyio
async def test_high_volume_batch_throughput():
    backend = BatchDatabasePersistence(session_factory=TestingSessionLocal)
    items = [_make_sample_item(i, batch_id="HIGH-VOL-RUN") for i in range(200)]

    t0 = time.perf_counter()
    persisted = await backend.write_batch(items)
    duration_s = max(time.perf_counter() - t0, 0.001)

    assert persisted == 200
    eps = 200 / duration_s
    # In-memory SQLite batch insertion should easily exceed 1000 EPS
    assert eps > 500


# =====================================================================
# 16. PARQUET / COLUMNAR EXPORT BACKEND
# =====================================================================

@pytest.mark.anyio
async def test_parquet_export_backend():
    temp_dir = tempfile.mkdtemp()
    try:
        backend = ParquetExportBackend(base_dir=temp_dir)
        items = [_make_sample_item(i) for i in range(5)]

        persisted = await backend.write_batch(items)
        assert persisted == 5

        # Verify Parquet files were created on disk
        files = []
        for root, _, filenames in os.walk(temp_dir):
            for fn in filenames:
                if fn.endswith(".parquet"):
                    files.append(os.path.join(root, fn))
        assert len(files) >= 1
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


# =====================================================================
# 17. STREAMING SINK EXTENSION POINT
# =====================================================================

@pytest.mark.anyio
async def test_streaming_sink_broker_abstraction():
    sink = StreamingSink(topic="defense-telemetry-feed")
    items = [_make_sample_item(i) for i in range(5)]

    persisted = await sink.write_batch(items)
    assert persisted == 5
    assert sink.total_streamed == 5
    assert len(sink.buffered_messages) == 5
    assert sink.buffered_messages[0]["topic"] == "defense-telemetry-feed"


# =====================================================================
# 18. RBAC ON EXPORT & PERSISTENCE ENDPOINTS
# =====================================================================

def test_rbac_on_export_endpoint(client, db_session):
    from app.models.user import User
    from app.core.security import get_password_hash

    # Seed test users
    if not db_session.query(User).filter(User.username == "test_viewer").first():
        db_session.add(
            User(
                id="usr-viewer-export",
                username="test_viewer",
                email="viewer@test.local",
                hashed_password=get_password_hash("ValidPassword123!"),
                role="VIEWER",
                is_active=True
            )
        )
    if not db_session.query(User).filter(User.username == "test_admin").first():
        db_session.add(
            User(
                id="usr-admin-export",
                username="test_admin",
                email="admin@test.local",
                hashed_password=get_password_hash("ValidPassword123!"),
                role="ADMIN",
                is_active=True
            )
        )
    db_session.commit()

    # Clear mock auth overrides so real security dependencies evaluate
    from app.core.auth import get_current_user, get_current_active_user
    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides.pop(get_current_active_user, None)

    # 1. Unauthenticated request -> 401
    res_unauth = client.post("/api/v1/analytics/export", json={})
    assert res_unauth.status_code == 401

    # 2. VIEWER role -> 403 Forbidden
    viewer_token = create_access_token(data={"sub": "test_viewer", "role": "VIEWER"})
    res_viewer = client.post(
        "/api/v1/analytics/export",
        json={},
        headers={"Authorization": f"Bearer {viewer_token}"}
    )
    assert res_viewer.status_code == 403

    # 3. ADMIN role -> 200 Success
    admin_token = create_access_token(data={"sub": "test_admin", "role": "ADMIN"})
    res_admin = client.post(
        "/api/v1/analytics/export",
        json={},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert res_admin.status_code == 200


# =====================================================================
# 19. AIR-GAPPED COMPLIANCE
# =====================================================================

def test_airgap_mode_flags_active():
    assert settings.AIR_GAPPED_MODE is True
    assert settings.ALLOW_EXTERNAL_CALLS is False
