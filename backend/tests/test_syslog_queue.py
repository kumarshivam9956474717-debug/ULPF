import asyncio
import pytest
from app.services.syslog.models import ReceivedSyslogMessage
from app.services.syslog.metrics import syslog_metrics
from app.services.syslog.udp_listener import UDPListener


@pytest.mark.anyio
async def test_queue_backpressure_drop():
    syslog_metrics.reset()
    # Micro queue of maxsize 2
    queue = asyncio.Queue(maxsize=2)
    test_port = 19540

    listener = UDPListener(
        host="127.0.0.1",
        port=test_port,
        queue=queue,
        max_bytes=65536
    )

    # Pre-fill queue to capacity
    msg1 = ReceivedSyslogMessage(payload=b"1", transport="udp", remote_address="127.0.0.1", remote_port=1000, listener_id="u")
    msg2 = ReceivedSyslogMessage(payload=b"2", transport="udp", remote_address="127.0.0.1", remote_port=1000, listener_id="u")
    queue.put_nowait(msg1)
    queue.put_nowait(msg2)
    assert queue.full()

    # Emulate datagram received while queue is full
    listener.protocol = listener
    from app.services.syslog.udp_listener import SyslogUDPProtocol
    proto = SyslogUDPProtocol(queue, 65536, "udp-test")
    proto.datagram_received(b"overflow packet", ("127.0.0.1", 1000))

    # The overflow packet should be dropped with metrics recorded
    assert syslog_metrics.messages_dropped == 1
    assert syslog_metrics.messages_received == 1  # packet arrived at socket
    assert queue.qsize() == 2  # queue did not exceed bound
