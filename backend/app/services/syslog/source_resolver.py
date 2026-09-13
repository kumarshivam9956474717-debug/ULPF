import time
from typing import Dict, Optional, Tuple
from sqlalchemy.orm import Session
from app.models.log_source import LogSource


class SourceResolver:
    """
    Associates incoming network remote IP addresses with registered LogSource records.
    Uses an in-memory TTL cache to eliminate database lookups under high EPS.
    """

    def __init__(self, cache_ttl_seconds: int = 60):
        self.cache_ttl = cache_ttl_seconds
        # Mapping: ip_address -> (source_id, expiry_timestamp)
        self._cache: Dict[str, Tuple[Optional[str], float]] = {}

    def resolve_source(self, remote_ip: str, db: Session) -> Optional[str]:
        """
        Looks up the source_id for the given remote IP address.
        Checks cache first; queries database if expired or not found.
        """
        now = time.time()
        if remote_ip in self._cache:
            source_id, expiry = self._cache[remote_ip]
            if now < expiry:
                return source_id

        # Query LogSource table: check hostname matching remote_ip or source_id matching remote_ip
        try:
            source = (
                db.query(LogSource)
                .filter(
                    LogSource.enabled == True,
                    (LogSource.hostname == remote_ip) | (LogSource.source_id == remote_ip)
                )
                .first()
            )
            matched_id = source.source_id if source else None
            self._cache[remote_ip] = (matched_id, now + self.cache_ttl)
            return matched_id
        except Exception:
            # On query error, don't crash ingestion; treat as unknown
            return None

    def clear_cache(self) -> None:
        self._cache.clear()


source_resolver = SourceResolver()
