import asyncio
import logging
from typing import Dict, Any, List, Optional

from app.core.config import settings
from app.services.persistence.queue import global_persistence_queue
from app.services.syslog.metrics import syslog_metrics
from app.services.syslog.udp_listener import UDPListener
from app.services.syslog.tcp_listener import TCPListener
from app.services.syslog.tls_listener import TLSListener
from app.services.syslog.worker import syslog_worker_task

logger = logging.getLogger("ulpf.syslog.manager")


class SyslogManager:
    """
    Coordinates lifecycle of all Syslog transport listeners (UDP, TCP, TLS),
    the asynchronous worker pool, and decoupled persistence.
    """

    def __init__(self):
        self.queue: Optional[asyncio.Queue] = None
        self.shutdown_event = asyncio.Event()
        self.udp_listener: Optional[UDPListener] = None
        self.tcp_listener: Optional[TCPListener] = None
        self.tls_listener: Optional[TLSListener] = None
        self.worker_tasks: List[asyncio.Task] = []
        self.is_running: bool = False

    async def start(
        self,
        queue_maxsize: Optional[int] = None,
        num_workers: Optional[int] = None,
        udp_enabled: Optional[bool] = None,
        udp_host: Optional[str] = None,
        udp_port: Optional[int] = None,
        tcp_enabled: Optional[bool] = None,
        tcp_host: Optional[str] = None,
        tcp_port: Optional[int] = None,
        tls_enabled: Optional[bool] = None,
        tls_host: Optional[str] = None,
        tls_port: Optional[int] = None,
        tls_certfile: Optional[str] = None,
        tls_keyfile: Optional[str] = None,
        tls_cafile: Optional[str] = None,
    ) -> None:
        if self.is_running:
            logger.info("SyslogManager already running.")
            return

        q_size = queue_maxsize or settings.SYSLOG_QUEUE_MAXSIZE
        workers_count = num_workers or settings.SYSLOG_WORKERS

        self.queue = asyncio.Queue(maxsize=q_size)
        self.shutdown_event = asyncio.Event()
        self.worker_tasks.clear()

        # 0. Start decoupled persistence queue
        if settings.PERSISTENCE_MODE != "single":
            if hasattr(global_persistence_queue.backend, "session_factory"):
                from app.services.syslog.worker import SessionLocal as WorkerSessionLocal
                global_persistence_queue.backend.session_factory = WorkerSessionLocal
            await global_persistence_queue.start()

        # 1. Start worker pool
        for wid in range(1, workers_count + 1):
            task = asyncio.create_task(
                syslog_worker_task(wid, self.queue, self.shutdown_event, global_persistence_queue)
            )
            self.worker_tasks.append(task)
        logger.info(f"Started {workers_count} Syslog processing workers.")

        # 2. Start UDP Listener if enabled
        u_enabled = settings.SYSLOG_UDP_ENABLED if udp_enabled is None else udp_enabled
        if u_enabled:
            u_host = udp_host or settings.SYSLOG_UDP_HOST
            u_port = udp_port or settings.SYSLOG_UDP_PORT
            try:
                self.udp_listener = UDPListener(
                    host=u_host,
                    port=u_port,
                    queue=self.queue,
                    max_bytes=settings.SYSLOG_MAX_MESSAGE_BYTES
                )
                await self.udp_listener.start()
            except Exception as exc:
                logger.error(f"Failed to start UDP Syslog listener on {u_host}:{u_port}: {exc}")

        # 3. Start TCP Listener if enabled
        t_enabled = settings.SYSLOG_TCP_ENABLED if tcp_enabled is None else tcp_enabled
        if t_enabled:
            t_host = tcp_host or settings.SYSLOG_TCP_HOST
            t_port = tcp_port or settings.SYSLOG_TCP_PORT
            try:
                self.tcp_listener = TCPListener(
                    host=t_host,
                    port=t_port,
                    queue=self.queue,
                    max_bytes=settings.SYSLOG_MAX_MESSAGE_BYTES,
                    connection_limit=settings.SYSLOG_TCP_CONNECTION_LIMIT,
                    idle_timeout=settings.SYSLOG_TCP_IDLE_TIMEOUT_SECONDS
                )
                await self.tcp_listener.start()
            except Exception as exc:
                logger.error(f"Failed to start TCP Syslog listener on {t_host}:{t_port}: {exc}")

        # 4. Start TLS Listener if enabled
        s_enabled = settings.SYSLOG_TLS_ENABLED if tls_enabled is None else tls_enabled
        if s_enabled:
            s_host = tls_host or settings.SYSLOG_TLS_HOST
            s_port = tls_port or settings.SYSLOG_TLS_PORT
            cert = tls_certfile or settings.SYSLOG_TLS_CERTFILE
            key = tls_keyfile or settings.SYSLOG_TLS_KEYFILE
            ca = tls_cafile or settings.SYSLOG_TLS_CAFILE
            try:
                self.tls_listener = TLSListener(
                    host=s_host,
                    port=s_port,
                    queue=self.queue,
                    certfile=cert,
                    keyfile=key,
                    cafile=ca,
                    max_bytes=settings.SYSLOG_MAX_MESSAGE_BYTES,
                    connection_limit=settings.SYSLOG_TCP_CONNECTION_LIMIT,
                    idle_timeout=settings.SYSLOG_TCP_IDLE_TIMEOUT_SECONDS
                )
                await self.tls_listener.start()
            except Exception as exc:
                logger.error(f"Failed to start TLS Syslog listener on {s_host}:{s_port}: {exc}")

        self.is_running = True
        logger.info("SyslogManager started successfully.")

    async def stop(self, drain_timeout: float = 3.0) -> None:
        if not self.is_running:
            return

        logger.info("Initiating graceful shutdown of SyslogManager...")

        # 1. Stop listeners to prevent new incoming messages
        if self.udp_listener:
            await self.udp_listener.stop()
            self.udp_listener = None

        if self.tcp_listener:
            await self.tcp_listener.stop()
            self.tcp_listener = None

        if self.tls_listener:
            await self.tls_listener.stop()
            self.tls_listener = None

        # 2. Allow queued events to drain up to drain_timeout
        if self.queue and not self.queue.empty():
            logger.info(f"Draining remaining {self.queue.qsize()} queued Syslog events...")
            try:
                await asyncio.wait_for(self.queue.join(), timeout=drain_timeout)
            except asyncio.TimeoutError:
                logger.warning(f"Syslog queue drain timed out after {drain_timeout}s.")

        # 3. Stop workers
        self.shutdown_event.set()
        for task in self.worker_tasks:
            if not task.done():
                task.cancel()

        if self.worker_tasks:
            await asyncio.gather(*self.worker_tasks, return_exceptions=True)
            self.worker_tasks.clear()

        # 4. Stop decoupled persistence queue if running
        if settings.PERSISTENCE_MODE != "single" and global_persistence_queue.is_running:
            await global_persistence_queue.stop(drain_timeout=drain_timeout)

        self.is_running = False
        logger.info("SyslogManager shutdown complete.")

    def get_status(self) -> Dict[str, Any]:
        """
        Returns snapshot of listeners, worker pool, runtime metrics, and persistence status.
        """
        metrics_snap = syslog_metrics.snapshot()
        q_depth = self.queue.qsize() if self.queue else 0
        q_max = self.queue.maxsize if self.queue else settings.SYSLOG_QUEUE_MAXSIZE
        persistence_snap = global_persistence_queue.get_metrics() if global_persistence_queue else {}

        return {
            "manager_running": self.is_running,
            "persistence_mode": settings.PERSISTENCE_MODE,
            "udp": {
                "enabled": settings.SYSLOG_UDP_ENABLED,
                "running": self.udp_listener.is_running if self.udp_listener else False,
                "host": self.udp_listener.host if self.udp_listener else settings.SYSLOG_UDP_HOST,
                "port": self.udp_listener.port if self.udp_listener else settings.SYSLOG_UDP_PORT,
            },
            "tcp": {
                "enabled": settings.SYSLOG_TCP_ENABLED,
                "running": self.tcp_listener.is_running if self.tcp_listener else False,
                "host": self.tcp_listener.host if self.tcp_listener else settings.SYSLOG_TCP_HOST,
                "port": self.tcp_listener.port if self.tcp_listener else settings.SYSLOG_TCP_PORT,
            },
            "tls": {
                "enabled": settings.SYSLOG_TLS_ENABLED,
                "running": self.tls_listener.is_running if self.tls_listener else False,
                "host": self.tls_listener.host if self.tls_listener else settings.SYSLOG_TLS_HOST,
                "port": self.tls_listener.port if self.tls_listener else settings.SYSLOG_TLS_PORT,
            },
            "queue": {
                "depth": q_depth,
                "maxsize": q_max,
                "workers": len(self.worker_tasks),
            },
            "metrics": metrics_snap,
            "persistence": persistence_snap
        }


# Singleton manager instance
syslog_manager = SyslogManager()
