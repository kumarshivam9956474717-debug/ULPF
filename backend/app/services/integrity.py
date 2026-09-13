import hashlib
from typing import Dict, Any, Union
from app.models.raw_event import RawEvent


def compute_sha256(payload: str, encoding: str = "utf-8") -> str:
    """
    Computes standard SHA-256 hex digest for a raw log payload.
    Supports any custom encoding (defaults to UTF-8).
    """
    if payload is None:
        raise ValueError("Cannot compute hash of None payload.")
    payload_bytes = payload.encode(encoding, errors="replace")
    return hashlib.sha256(payload_bytes).hexdigest()


def verify_payload_integrity(
    raw_payload: str,
    stored_hash: str,
    encoding: str = "utf-8"
) -> Dict[str, Any]:
    """
    Verifies raw payload integrity against an expected SHA-256 hash.
    Returns structured verification output:
    {
        "status": "valid" | "invalid",
        "stored_hash": str,
        "computed_hash": str,
        "is_tampered": bool
    }
    """
    if raw_payload is None or stored_hash is None:
        return {
            "status": "invalid",
            "stored_hash": stored_hash,
            "computed_hash": None,
            "is_tampered": True,
            "error": "Missing payload or hash"
        }

    computed = compute_sha256(raw_payload, encoding=encoding)
    is_valid = computed.lower() == stored_hash.lower()

    return {
        "status": "valid" if is_valid else "invalid",
        "stored_hash": stored_hash,
        "computed_hash": computed,
        "is_tampered": not is_valid
    }


def verify_raw_event_record(raw_event: RawEvent) -> Dict[str, Any]:
    """
    Verifies the integrity of a stored RawEvent database record.
    """
    result = verify_payload_integrity(
        raw_payload=raw_event.raw_payload,
        stored_hash=raw_event.payload_hash_sha256,
        encoding=raw_event.payload_encoding or "utf-8"
    )
    result["raw_event_id"] = raw_event.raw_event_id
    return result
