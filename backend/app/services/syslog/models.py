from datetime import datetime, timezone
from typing import Tuple
from pydantic import BaseModel, Field, ConfigDict


class ReceivedSyslogMessage(BaseModel):
    """
    Common internal transport representation for an incoming Syslog event.
    Preserves raw bytes exactly as received on the wire.
    """
    model_config = ConfigDict(arbitrary_types_allowed=True)

    payload: bytes = Field(..., description="Original raw bytes received over socket")
    transport: str = Field(..., description="Transport protocol: udp, tcp, or tls")
    remote_address: str = Field(..., description="Remote sender IP address")
    remote_port: int = Field(..., description="Remote sender port")
    received_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp of socket receipt"
    )
    listener_id: str = Field(..., description="Identifier of the listener, e.g. udp-1514")


def decode_payload_safe(raw_bytes: bytes) -> Tuple[str, str]:
    """
    Decodes raw payload bytes safely without throwing exceptions.
    Attempts strict UTF-8 first; falls back to replacement decoding.

    Returns:
        Tuple[str, str]: (decoded_text, encoding_label)
    """
    try:
        return raw_bytes.decode("utf-8"), "utf-8"
    except UnicodeDecodeError:
        return raw_bytes.decode("utf-8", errors="replace"), "utf-8-replaced"
