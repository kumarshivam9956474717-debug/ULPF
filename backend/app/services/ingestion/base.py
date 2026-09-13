import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Union
from pydantic import BaseModel, Field


class IngestionItem(BaseModel):
    """
    Standardized container for raw event ingestion.
    Preserves original bytes, decoding metadata, and verbatim raw string.
    """
    raw_payload: str = Field(..., description="Verbatim unmodified raw string payload")
    encoding: str = Field(default="utf-8", description="Encoding utilized to decode payload")
    payload_hash_sha256: str = Field(..., description="Cryptographic SHA-256 hex digest of payload")
    source_id: Optional[str] = Field(None, description="Identifier of originating log source")
    source_format_hint: Optional[str] = Field(None, description="Optional format hint provided by caller")
    received_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @classmethod
    def from_input(
        cls,
        data: Union[str, bytes, Dict[str, Any]],
        source_id: Optional[str] = None,
        source_format_hint: Optional[str] = None,
        encoding: str = "utf-8"
    ) -> "IngestionItem":
        """
        Constructs an IngestionItem from raw string, bytes, or structured dict
        without mutating or discarding content.
        """
        if isinstance(data, bytes):
            try:
                raw_str = data.decode(encoding)
                enc = encoding
            except UnicodeDecodeError:
                # Fallback to latin-1 to guarantee lossless byte preservation without failure
                raw_str = data.decode("latin-1")
                enc = "latin-1"
        elif isinstance(data, dict):
            raw_str = json.dumps(data)
            enc = "utf-8"
        elif isinstance(data, str):
            raw_str = data
            enc = encoding
        else:
            raw_str = str(data)
            enc = encoding

        payload_bytes = raw_str.encode(enc, errors="replace")
        sha256_hash = hashlib.sha256(payload_bytes).hexdigest()

        return cls(
            raw_payload=raw_str,
            encoding=enc,
            payload_hash_sha256=sha256_hash,
            source_id=source_id,
            source_format_hint=source_format_hint
        )
