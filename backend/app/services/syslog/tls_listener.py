import asyncio
import logging
import os
import ssl
from typing import Optional
from app.services.syslog.tcp_listener import TCPListener

logger = logging.getLogger("ulpf.syslog.tls")


def create_syslog_ssl_context(
    certfile: Optional[str],
    keyfile: Optional[str],
    cafile: Optional[str] = None,
    require_client_cert: bool = False
) -> ssl.SSLContext:
    """
    Constructs a hardened SSLContext for enterprise TLS Syslog.
    Enforces minimum TLS 1.2 and secure cipher suites.
    """
    if not certfile or not keyfile:
        raise ValueError("TLS Syslog requires both certfile and keyfile to be configured.")

    if not os.path.exists(certfile):
        raise FileNotFoundError(f"TLS certificate file not found: {certfile}")
    if not os.path.exists(keyfile):
        raise FileNotFoundError(f"TLS private key file not found: {keyfile}")

    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    # Enforce TLS 1.2 minimum
    context.minimum_version = ssl.TLSVersion.TLSv1_2

    # Load server certificate and private key
    context.load_cert_chain(certfile=certfile, keyfile=keyfile)

    # Optional CA verification for mutual TLS (mTLS)
    if cafile:
        if not os.path.exists(cafile):
            raise FileNotFoundError(f"TLS CA certificate file not found: {cafile}")
        context.load_verify_locations(cafile=cafile)
        if require_client_cert:
            context.verify_mode = ssl.CERT_REQUIRED
        else:
            context.verify_mode = ssl.CERT_OPTIONAL
    else:
        context.verify_mode = ssl.CERT_NONE

    return context


class TLSListener(TCPListener):
    """
    Specialized TLS Syslog Listener extending TCPListener with SSLContext.
    """

    def __init__(
        self,
        host: str,
        port: int,
        queue: asyncio.Queue,
        certfile: Optional[str],
        keyfile: Optional[str],
        cafile: Optional[str] = None,
        max_bytes: int = 65536,
        connection_limit: int = 100,
        idle_timeout: int = 60,
        listener_id: Optional[str] = None
    ):
        self.certfile = certfile
        self.keyfile = keyfile
        self.cafile = cafile

        ssl_ctx = None
        if certfile and keyfile:
            ssl_ctx = create_syslog_ssl_context(certfile, keyfile, cafile)

        super().__init__(
            host=host,
            port=port,
            queue=queue,
            max_bytes=max_bytes,
            connection_limit=connection_limit,
            idle_timeout=idle_timeout,
            listener_id=listener_id or f"tls-{port}",
            ssl_context=ssl_ctx
        )
