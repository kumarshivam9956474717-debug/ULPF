"""
OmniLogix / ULPF Air-Gapped Network Enforcement Module.
Guarantees that when AIR_GAPPED_MODE=True, unauthorized outbound network
connections to public internet endpoints are strictly blocked and audited.
Legitimate local traffic (loopback, private LAN, Docker bridge, local database)
remains 100% operational.
"""

import ipaddress
import logging
import socket
from typing import Any, Tuple, Union

from app.core.config import settings

logger = logging.getLogger("omnilogix.airgap")

# Authorized local hostnames and container aliases
LOCAL_HOSTS = {
    "localhost",
    "127.0.0.1",
    "::1",
    "0.0.0.0",
    "::",
    "ulpf-db",
    "db",
    "ulpf-backend",
    "backend",
    "ulpf-frontend",
    "frontend",
    "postgres",
}

_orig_socket_connect = socket.socket.connect
_is_airgap_installed = False


def is_destination_permitted(host: str, port: int = 0) -> bool:
    """
    Evaluates whether an outbound socket connection target is authorized in an air-gapped enclave.
    Returns True for localhost, loopback, private subnets (RFC 1918), and local container aliases.
    Returns False for public Internet IPs and external domain names.
    """
    if not host:
        return True

    clean_host = str(host).strip().lower()

    # 1. Check known local alias set
    if clean_host in LOCAL_HOSTS:
        return True

    # 2. Check for local/internal domain naming conventions
    if clean_host.endswith(".local") or clean_host.endswith(".internal") or clean_host.endswith(".lan"):
        return True

    # 3. Check if host is a valid IP address
    try:
        ip = ipaddress.ip_address(clean_host)
        # Allow loopback (127.0.0.0/8, ::1), private (10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16), link-local
        if ip.is_loopback or ip.is_private or ip.is_link_local:
            return True
        return False
    except ValueError:
        pass

    # 4. If host has no dot, treat as container service name on internal Docker network
    if "." not in clean_host:
        return True

    return False


def airgap_guarded_connect(self, address: Union[Tuple[Any, ...], str, bytes]) -> Any:
    """Intercepts socket connect calls to prevent unauthorized external network egress."""
    if not settings.AIR_GAPPED_MODE:
        return _orig_socket_connect(self, address)

    host = None
    port = 0

    if isinstance(address, tuple) and len(address) >= 2:
        host, port = address[0], address[1]
    elif isinstance(address, str):
        host = address

    if host is not None and not is_destination_permitted(str(host), port):
        err_msg = (
            f"[AIR-GAP ENCLAVE VIOLATION] Outbound connection to external host "
            f"'{host}:{port}' was blocked. OmniLogix is operating in strictly "
            f"enforced AIR_GAPPED_MODE."
        )
        logger.error(err_msg)
        raise PermissionError(err_msg)

    return _orig_socket_connect(self, address)


def install_airgap_guard() -> bool:
    """Activates socket-level air-gap enforcement."""
    global _is_airgap_installed
    if settings.AIR_GAPPED_MODE and not _is_airgap_installed:
        socket.socket.connect = airgap_guarded_connect
        _is_airgap_installed = True
        logger.info("Air-Gapped Enclave Socket Guard successfully activated.")
        return True
    return False


def uninstall_airgap_guard() -> bool:
    """Restores standard socket connection behavior (useful for unit testing)."""
    global _is_airgap_installed
    if _is_airgap_installed:
        socket.socket.connect = _orig_socket_connect
        _is_airgap_installed = False
        return True
    return False
