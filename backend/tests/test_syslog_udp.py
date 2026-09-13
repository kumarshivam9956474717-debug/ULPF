import asyncio
import socket
import pytest
from app.services.syslog.udp_listener import UDPListener
from app.services.syslog.metrics import syslog_metrics
from app.services.syslog.models import ReceivedSyslogMessage

SAMPLE_RFC5424 = (
    "<165>1 2026-09-10T09:40:00.123Z perimeter-edge-gw.local edge-guard 49152 ID47 "
    "[exampleSDID@32473 iut=\"3\" eventSource=\"EdgeFilter\"] Port probe dropped"
)


@pytest.mark.anyio
async def test_udp_listener_lifecycle_and_reception():
    syslog_metrics.reset()
    queue = asyncio.Queue(maxsize=100)
    test_port = 19514

    listener = UDPListener(
        host="127.0.0.1",
        port=test_port,
        queue=queue,
        max_bytes=65536
    )

    await listener.start()
    assert listener.is_running is True

    # Send a valid UDP datagram
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.sendto(SAMPLE_RFC5424.encode("utf-8"), ("127.0.0.1", test_port))
        # Receive from queue
        msg: ReceivedSyslogMessage = await asyncio.wait_for(queue.get(), timeout=2.0)

        assert msg.transport == "udp"
        assert msg.remote_address == "127.0.0.1"
        assert msg.payload == SAMPLE_RFC5424.encode("utf-8")
        assert msg.listener_id == f"udp-{test_port}"
        assert syslog_metrics.messages_received == 1
    finally:
        sock.close()
        await listener.stop()

    assert listener.is_running is False


@pytest.mark.anyio
async def test_udp_oversized_packet_rejection():
    syslog_metrics.reset()
    queue = asyncio.Queue(maxsize=100)
    test_port = 19515
    max_bytes = 256  # small threshold for test

    listener = UDPListener(
        host="127.0.0.1",
        port=test_port,
        queue=queue,
        max_bytes=max_bytes
    )
    await listener.start()

    oversized_data = b"<13>1 " + (b"X" * 300)

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.sendto(oversized_data, ("127.0.0.1", test_port))
        # Allow event loop to process
        await asyncio.sleep(0.1)

        # Queue should be empty because packet was rejected
        assert queue.empty()
        assert syslog_metrics.oversized_messages == 1
        assert syslog_metrics.messages_received == 0
    finally:
        sock.close()
        await listener.stop()


@pytest.mark.anyio
async def test_udp_continues_after_bad_packet():
    syslog_metrics.reset()
    queue = asyncio.Queue(maxsize=100)
    test_port = 19516

    listener = UDPListener(
        host="127.0.0.1",
        port=test_port,
        queue=queue,
        max_bytes=65536
    )
    await listener.start()

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # Send raw non-utf8 corrupted bytes
        sock.sendto(b"\xff\xfe\x00\x00CORRUPTED_BYTES", ("127.0.0.1", test_port))
        # Send normal message right after
        sock.sendto(b"Valid log message", ("127.0.0.1", test_port))

        msg1 = await asyncio.wait_for(queue.get(), timeout=2.0)
        msg2 = await asyncio.wait_for(queue.get(), timeout=2.0)

        assert b"CORRUPTED_BYTES" in msg1.payload
        assert msg2.payload == b"Valid log message"
        assert syslog_metrics.messages_received == 2
    finally:
        sock.close()
        await listener.stop()
