import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional, Set
from app.services.syslog.models import ReceivedSyslogMessage
from app.services.syslog.metrics import syslog_metrics

logger = logging.getLogger("ulpf.syslog.tcp")


class TCPListener:
    """
    Asynchronous TCP Syslog listener with framing support:
    - Newline-delimited framing (RFC 3164 / RFC 5424 over stream)
    - Octet-counted framing (RFC 6587: <length> <message>)
    Enforces connection limits, read timeouts, and message size limits.
    """

    def __init__(
        self,
        host: str,
        port: int,
        queue: asyncio.Queue,
        max_bytes: int = 65536,
        connection_limit: int = 100,
        idle_timeout: int = 60,
        listener_id: Optional[str] = None,
        ssl_context=None
    ):
        self.host = host
        self.port = port
        self.queue = queue
        self.max_bytes = max_bytes
        self.connection_limit = connection_limit
        self.idle_timeout = idle_timeout
        self.listener_id = listener_id or f"tcp-{port}"
        self.ssl_context = ssl_context
        self.server: Optional[asyncio.Server] = None
        self.is_running: bool = False
        self._active_tasks: Set[asyncio.Task] = set()

    async def start(self) -> None:
        if self.is_running:
            return
        self.server = await asyncio.start_server(
            self._handle_client,
            host=self.host,
            port=self.port,
            ssl=self.ssl_context
        )
        self.is_running = True
        proto = "TLS" if self.ssl_context else "TCP"
        logger.info(f"{proto} Syslog listener successfully bound to {self.host}:{self.port}")

    async def stop(self) -> None:
        if not self.is_running:
            return
        if self.server:
            self.server.close()
            await self.server.wait_closed()

        # Cancel any ongoing client handlers
        for task in list(self._active_tasks):
            if not task.done():
                task.cancel()
        if self._active_tasks:
            await asyncio.gather(*self._active_tasks, return_exceptions=True)

        self.is_running = False
        proto = "TLS" if self.ssl_context else "TCP"
        logger.info(f"{proto} Syslog listener on {self.host}:{self.port} stopped.")

    def _handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        task = asyncio.create_task(self._process_client_stream(reader, writer))
        self._active_tasks.add(task)
        task.add_done_callback(self._active_tasks.discard)

    async def _process_client_stream(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        peer = writer.get_extra_info("peername")
        remote_ip = peer[0] if peer else "unknown"
        remote_port = peer[1] if peer else 0

        # Check connection limit
        if syslog_metrics.active_tcp_connections >= self.connection_limit:
            logger.warning(
                f"Rejecting incoming TCP connection from {remote_ip}:{remote_port} - "
                f"connection limit ({self.connection_limit}) reached."
            )
            writer.close()
            await writer.wait_closed()
            return

        syslog_metrics.increment_connections()
        transport_name = "tls" if self.ssl_context else "tcp"
        logger.debug(f"New {transport_name.upper()} client connected from {remote_ip}:{remote_port}")

        buffer = bytearray()

        try:
            while self.is_running and not reader.at_eof():
                try:
                    chunk = await asyncio.wait_for(reader.read(4096), timeout=self.idle_timeout)
                except asyncio.TimeoutError:
                    logger.debug(f"Client {remote_ip}:{remote_port} idle timeout ({self.idle_timeout}s) exceeded. Closing.")
                    break

                if not chunk:
                    break

                buffer.extend(chunk)

                # Process all complete frames currently in buffer
                while buffer:
                    # Check for RFC 6587 octet-counted framing: starts with digits then space
                    octet_handled, consumed = self._try_parse_octet_frame(buffer, remote_ip, remote_port, transport_name)
                    if octet_handled:
                        buffer = buffer[consumed:]
                        continue

                    # Otherwise, check for newline-delimited framing: ends with \n
                    newline_index = buffer.find(b"\n")
                    if newline_index != -1:
                        raw_frame = bytes(buffer[:newline_index]).rstrip(b"\r")
                        buffer = buffer[newline_index + 1:]
                        if raw_frame:
                            self._enqueue_message(raw_frame, remote_ip, remote_port, transport_name)
                        continue

                    # Check if buffer without delimiter has exceeded max size
                    if len(buffer) > self.max_bytes:
                        logger.warning(
                            f"TCP stream from {remote_ip}:{remote_port} exceeded max message bytes "
                            f"({len(buffer)} > {self.max_bytes}) without frame delimiter. Discarding buffer to protect memory."
                        )
                        syslog_metrics.record_oversized()
                        buffer.clear()
                    break

        except asyncio.CancelledError:
            pass
        except Exception as exc:
            logger.warning(f"Error handling {transport_name.upper()} client {remote_ip}:{remote_port}: {exc}")
            syslog_metrics.record_malformed()
        finally:
            syslog_metrics.decrement_connections()
            try:
                writer.close()
                await writer.wait_closed()
            except Exception:
                pass
            logger.debug(f"Client {remote_ip}:{remote_port} disconnected.")

    def _try_parse_octet_frame(
        self,
        buffer: bytearray,
        remote_ip: str,
        remote_port: int,
        transport_name: str
    ) -> tuple[bool, int]:
        """
        Attempts to parse RFC 6587 octet-counted frame (<length> <message>).
        Returns (handled: bool, bytes_consumed: int).
        """
        # Look for space in the first 10 bytes
        space_idx = buffer[:10].find(b" ")
        if space_idx > 0:
            prefix = buffer[:space_idx]
            if prefix.isdigit():
                msg_len = int(prefix)
                total_frame_len = space_idx + 1 + msg_len

                if msg_len > self.max_bytes:
                    logger.warning(
                        f"Octet-counted frame declared length {msg_len} exceeds max limit {self.max_bytes}. Rejecting."
                    )
                    syslog_metrics.record_oversized()
                    # Skip the length prefix + space
                    return True, space_idx + 1

                if len(buffer) >= total_frame_len:
                    msg_bytes = bytes(buffer[space_idx + 1:total_frame_len])
                    self._enqueue_message(msg_bytes, remote_ip, remote_port, transport_name)
                    return True, total_frame_len
                else:
                    # Incomplete frame, wait for more data
                    return False, 0
        return False, 0

    def _enqueue_message(self, data: bytes, remote_ip: str, remote_port: int, transport_name: str) -> None:
        if len(data) > self.max_bytes:
            logger.warning(
                f"Rejected oversized {transport_name.upper()} frame from {remote_ip}:{remote_port} "
                f"({len(data)} bytes > limit of {self.max_bytes} bytes). Lossless guarantee enforced."
            )
            syslog_metrics.record_oversized()
            return

        if not data:
            return

        syslog_metrics.record_received(1)

        msg = ReceivedSyslogMessage(
            payload=data,
            transport=transport_name,
            remote_address=remote_ip,
            remote_port=remote_port,
            received_at=datetime.now(timezone.utc),
            listener_id=self.listener_id
        )

        try:
            self.queue.put_nowait(msg)
            syslog_metrics.set_queue_depth(self.queue.qsize())
        except asyncio.QueueFull:
            logger.error(
                f"Syslog queue full ({self.queue.maxsize} events). Dropping {transport_name.upper()} message "
                f"from {remote_ip}:{remote_port} due to backpressure."
            )
            syslog_metrics.record_dropped(1)
