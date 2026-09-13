import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional, Tuple
from app.services.syslog.models import ReceivedSyslogMessage
from app.services.syslog.metrics import syslog_metrics

logger = logging.getLogger("ulpf.syslog.udp")


class SyslogUDPProtocol(asyncio.DatagramProtocol):
    """
    Asynchronous UDP protocol for receiving Syslog datagrams.
    Enforces packet size limits and enqueues messages without blocking socket I/O.
    """

    def __init__(self, queue: asyncio.Queue, max_bytes: int, listener_id: str):
        self.queue = queue
        self.max_bytes = max_bytes
        self.listener_id = listener_id
        self.transport: Optional[asyncio.DatagramTransport] = None

    def connection_made(self, transport: asyncio.DatagramTransport) -> None:
        self.transport = transport
        logger.info(f"UDP Syslog listener started on {self.listener_id}")

    def datagram_received(self, data: bytes, addr: Tuple[str, int]) -> None:
        remote_ip, remote_port = addr[0], addr[1]
        payload_len = len(data)

        # 1. Enforce size limit
        if payload_len > self.max_bytes:
            logger.warning(
                f"Rejected oversized UDP Syslog packet from {remote_ip}:{remote_port} "
                f"({payload_len} bytes > limit of {self.max_bytes} bytes). Lossless guarantee enforced."
            )
            syslog_metrics.record_oversized()
            return

        if payload_len == 0:
            return

        syslog_metrics.record_received(1)

        # 2. Package into common transport model
        message = ReceivedSyslogMessage(
            payload=data,
            transport="udp",
            remote_address=remote_ip,
            remote_port=remote_port,
            received_at=datetime.now(timezone.utc),
            listener_id=self.listener_id
        )

        # 3. Enqueue with backpressure handling
        try:
            self.queue.put_nowait(message)
            syslog_metrics.set_queue_depth(self.queue.qsize())
        except asyncio.QueueFull:
            logger.error(
                f"Syslog queue full ({self.queue.maxsize} events). Dropping UDP packet from {remote_ip}:{remote_port} due to backpressure."
            )
            syslog_metrics.record_dropped(1)

    def error_received(self, exc: Exception) -> None:
        logger.warning(f"UDP listener {self.listener_id} error: {exc}")
        syslog_metrics.record_malformed()

    def connection_lost(self, exc: Optional[Exception]) -> None:
        if exc:
            logger.warning(f"UDP listener {self.listener_id} closed with error: {exc}")
        else:
            logger.info(f"UDP listener {self.listener_id} closed gracefully.")


class UDPListener:
    """
    Manages the lifecycle of an asyncio UDP Syslog server.
    """

    def __init__(self, host: str, port: int, queue: asyncio.Queue, max_bytes: int):
        self.host = host
        self.port = port
        self.queue = queue
        self.max_bytes = max_bytes
        self.listener_id = f"udp-{port}"
        self.transport: Optional[asyncio.DatagramTransport] = None
        self.protocol: Optional[SyslogUDPProtocol] = None
        self.is_running: bool = False

    async def start(self) -> None:
        if self.is_running:
            return
        loop = asyncio.get_running_loop()
        self.transport, self.protocol = await loop.create_datagram_endpoint(
            lambda: SyslogUDPProtocol(self.queue, self.max_bytes, self.listener_id),
            local_addr=(self.host, self.port)
        )
        self.is_running = True
        logger.info(f"UDP Syslog listener successfully bound to {self.host}:{self.port}")

    async def stop(self) -> None:
        if not self.is_running:
            return
        if self.transport and not self.transport.is_closing():
            self.transport.close()
        self.is_running = False
        logger.info(f"UDP Syslog listener on {self.host}:{self.port} stopped.")
