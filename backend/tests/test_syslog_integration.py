import asyncio
import socket
import pytest
from sqlalchemy.orm import Session
from unittest.mock import patch

from tests.conftest import TestingSessionLocal, engine
from app.core.database import Base
from app.models.log_source import LogSource
from app.models.raw_event import RawEvent
from app.models.normalized_event import NormalizedEvent
from app.services.syslog.manager import syslog_manager
from app.services.syslog.metrics import syslog_metrics
from app.services.syslog.source_resolver import source_resolver

SAMPLE_CISCO = "%ASA-6-302013: Built outbound TCP connection 987654 for inside:192.168.1.100/49210 to outside:198.51.100.25/443"
SAMPLE_FORTINET = (
    "date=2026-09-10 time=09:30:00 devname=\"FGT-PERIMETER-01\" devid=\"FGT60D1234567890\" "
    "type=\"traffic\" subtype=\"forward\" level=\"notice\" action=\"accept\" "
    "srcip=10.0.1.50 dstip=203.0.113.15 srcport=54321 dstport=80 proto=6 "
    "service=\"HTTP\" app=\"Web.Browsing\" msg=\"Traffic accepted by firewall policy\""
)


@pytest.mark.anyio
async def test_syslog_end_to_end_pipeline_integration():
    Base.metadata.create_all(bind=engine)
    db: Session = TestingSessionLocal()


    # Register LogSource for 127.0.0.1
    existing_source = db.query(LogSource).filter(LogSource.source_id == "TEST_EDGE_FW").first()
    if not existing_source:
        source = LogSource(
            source_id="TEST_EDGE_FW",
            hostname="127.0.0.1",
            vendor="Cisco",
            product="ASA",
            device_type="firewall",
            enabled=True
        )
        db.add(source)
        db.commit()

    source_resolver.clear_cache()
    syslog_metrics.reset()

    udp_test_port = 19550
    tcp_test_port = 19551

    with patch("app.services.syslog.worker.SessionLocal", TestingSessionLocal):
        # Start SyslogManager
        await syslog_manager.start(
            queue_maxsize=500,
            num_workers=2,
            udp_enabled=True,
            udp_port=udp_test_port,
            tcp_enabled=True,
            tcp_port=tcp_test_port,
            tls_enabled=False
        )
        assert syslog_manager.is_running is True

        try:
            # 1. Send UDP packet (Cisco ASA)
            udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            udp_sock.sendto(SAMPLE_CISCO.encode("utf-8"), ("127.0.0.1", udp_test_port))
            udp_sock.close()

            # 2. Send TCP message (Fortinet)
            tcp_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            tcp_sock.connect(("127.0.0.1", tcp_test_port))
            tcp_sock.sendall((SAMPLE_FORTINET + "\n").encode("utf-8"))
            tcp_sock.close()

            # Wait for workers to process events
            for _ in range(30):
                snap = syslog_metrics.snapshot()
                if snap["messages_processed"] >= 2:
                    break
                await asyncio.sleep(0.1)

            assert syslog_metrics.messages_received >= 2
            assert syslog_metrics.messages_processed >= 2

            # Give decoupled batch persistence worker a brief window to flush batch to DB
            await asyncio.sleep(0.25)



            # 3. Verify Database Persistence & Traceability
            # Verify Cisco raw & normalized
            cisco_raw = db.query(RawEvent).filter(RawEvent.raw_payload == SAMPLE_CISCO).first()
            assert cisco_raw is not None
            assert cisco_raw.source_id == "TEST_EDGE_FW"
            assert cisco_raw.payload_hash_sha256 is not None

            cisco_norm = db.query(NormalizedEvent).filter(NormalizedEvent.raw_event_id == cisco_raw.raw_event_id).first()
            assert cisco_norm is not None
            assert cisco_norm.source_ip == "192.168.1.100"
            assert cisco_norm.destination_ip == "198.51.100.25"
            assert cisco_norm.source_port == 49210
            assert cisco_norm.destination_port == 443
            assert cisco_norm.parser_id == "syslog_generic"

            # Verify Fortinet raw & normalized
            forti_raw = db.query(RawEvent).filter(RawEvent.raw_payload == SAMPLE_FORTINET).first()
            assert forti_raw is not None
            forti_norm = db.query(NormalizedEvent).filter(NormalizedEvent.raw_event_id == forti_raw.raw_event_id).first()
            assert forti_norm is not None
            assert forti_norm.source_ip == "10.0.1.50"
            assert forti_norm.destination_ip == "203.0.113.15"

        finally:
            await syslog_manager.stop()
            db.close()

