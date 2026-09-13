import asyncio
import socket
import pytest
from app.services.syslog.tcp_listener import TCPListener
from app.services.syslog.metrics import syslog_metrics
from app.services.syslog.models import ReceivedSyslogMessage

SAMPLE_CISCO = "%ASA-6-302013: Built outbound TCP connection 987654 for inside:192.168.1.100/49210 to outside:198.51.100.25/443"


@pytest.mark.anyio
async def test_tcp_listener_newline_framing():
    syslog_metrics.reset()
    queue = asyncio.Queue(maxsize=100)
    test_port = 19520

    listener = TCPListener(
        host="127.0.0.1",
        port=test_port,
        queue=queue,
        max_bytes=65536,
        connection_limit=10,
        idle_timeout=10
    )
    await listener.start()
    assert listener.is_running is True

    reader, writer = await asyncio.open_connection("127.0.0.1", test_port)
    try:
        # Send two newline-delimited messages
        payload = f"{SAMPLE_CISCO}\nSecond test log message\n".encode("utf-8")
        writer.write(payload)
        await writer.drain()

        msg1: ReceivedSyslogMessage = await asyncio.wait_for(queue.get(), timeout=2.0)
        msg2: ReceivedSyslogMessage = await asyncio.wait_for(queue.get(), timeout=2.0)

        assert msg1.transport == "tcp"
        assert msg1.remote_address == "127.0.0.1"
        assert msg1.payload == SAMPLE_CISCO.encode("utf-8")

        assert msg2.transport == "tcp"
        assert msg2.payload == b"Second test log message"
        assert syslog_metrics.messages_received == 2
    finally:
        writer.close()
        await writer.wait_closed()
        await listener.stop()

    assert listener.is_running is False


@pytest.mark.anyio
async def test_tcp_listener_octet_counted_framing():
    syslog_metrics.reset()
    queue = asyncio.Queue(maxsize=100)
    test_port = 19521

    listener = TCPListener(
        host="127.0.0.1",
        port=test_port,
        queue=queue,
        max_bytes=65536
    )
    await listener.start()

    reader, writer = await asyncio.open_connection("127.0.0.1", test_port)
    try:
        msg_content = b"<134>1 2026-09-10T10:00:00Z host app - - - Octet counted test"
        frame = f"{len(msg_content)} ".encode("ascii") + msg_content

        writer.write(frame)
        await writer.drain()

        msg = await asyncio.wait_for(queue.get(), timeout=2.0)
        assert msg.payload == msg_content
        assert syslog_metrics.messages_received == 1
    finally:
        writer.close()
        await writer.wait_closed()
        await listener.stop()


@pytest.mark.anyio
async def test_tcp_listener_multiple_clients():
    syslog_metrics.reset()
    queue = asyncio.Queue(maxsize=100)
    test_port = 19522

    listener = TCPListener(
        host="127.0.0.1",
        port=test_port,
        queue=queue,
        max_bytes=65536,
        connection_limit=20
    )
    await listener.start()

    # Open 3 clients simultaneously
    clients = []
    for _ in range(3):
        r, w = await asyncio.open_connection("127.0.0.1", test_port)
        clients.append((r, w))

    try:
        for idx, (r, w) in enumerate(clients):
            w.write(f"Message from client {idx}\n".encode("utf-8"))
            await w.drain()

        received_payloads = set()
        for _ in range(3):
            msg = await asyncio.wait_for(queue.get(), timeout=2.0)
            received_payloads.add(msg.payload.decode("utf-8"))

        assert len(received_payloads) == 3
        for idx in range(3):
            assert f"Message from client {idx}" in received_payloads
    finally:
        for r, w in clients:
            w.close()
            await w.wait_closed()
        await listener.stop()


@pytest.mark.anyio
async def test_tcp_oversized_stream_buffer_protection():
    syslog_metrics.reset()
    queue = asyncio.Queue(maxsize=100)
    test_port = 19523
    max_bytes = 200

    listener = TCPListener(
        host="127.0.0.1",
        port=test_port,
        queue=queue,
        max_bytes=max_bytes
    )
    await listener.start()

    reader, writer = await asyncio.open_connection("127.0.0.1", test_port)
    try:
        # Send 300 bytes without newline (exceeding 200 byte limit)
        oversized = b"A" * 300
        writer.write(oversized)
        await writer.drain()

        await asyncio.sleep(0.1)
        assert syslog_metrics.oversized_messages >= 1
        assert queue.empty()

        # Follow up with valid message with newline
        writer.write(b"Recovery valid message\n")
        await writer.drain()

        msg = await asyncio.wait_for(queue.get(), timeout=2.0)
        assert msg.payload == b"Recovery valid message"
    finally:
        writer.close()
        await writer.wait_closed()
        await listener.stop()
