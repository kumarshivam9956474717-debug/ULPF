import ipaddress
from datetime import datetime
from typing import List, Tuple
from app.schemas.universal_event import UniversalEvent, SeverityLevel


class ValidationReport:
    def __init__(self, is_valid: bool, errors: List[str], warnings: List[str]):
        self.is_valid = is_valid
        self.errors = errors
        self.warnings = warnings
        self.status = "valid" if is_valid and not warnings else ("warning" if is_valid else "invalid")


class ValidationService:
    """
    Data quality and schema compliance auditor.
    Distinguishes blocking fatal errors from non-blocking audit warnings.
    """

    @staticmethod
    def validate_event(event: UniversalEvent) -> ValidationReport:
        errors: List[str] = []
        warnings: List[str] = []

        # 1. Mandatory Traceability & Raw Verification (Errors)
        if not event.raw_event_id:
            errors.append("Missing mandatory raw_event_id for forensic traceability.")
        if not event.raw_event:
            errors.append("Missing mandatory verbatim raw_event payload.")

        # 2. IP Address Validation (Warnings/Errors)
        if event.source_ip:
            try:
                ipaddress.ip_address(event.source_ip)
            except ValueError:
                warnings.append(f"Invalid source_ip syntax: '{event.source_ip}'")

        if event.destination_ip:
            try:
                ipaddress.ip_address(event.destination_ip)
            except ValueError:
                warnings.append(f"Invalid destination_ip syntax: '{event.destination_ip}'")

        # 3. Port Range Validation (0 - 65535)
        if event.source_port is not None:
            if not (0 <= event.source_port <= 65535):
                errors.append(f"Source port {event.source_port} out of legal bounds (0-65535).")

        if event.destination_port is not None:
            if not (0 <= event.destination_port <= 65535):
                errors.append(f"Destination port {event.destination_port} out of legal bounds (0-65535).")

        # 4. Timestamp Sanity (Warning)
        if not event.timestamp:
            warnings.append("Event missing originating device timestamp; defaulting to ingestion time.")
        elif event.timestamp.year < 2000 or event.timestamp.year > 2035:
            warnings.append(f"Event timestamp year {event.timestamp.year} appears suspicious or clock skewed.")

        # 5. Severity Assessment
        if event.severity == SeverityLevel.UNKNOWN:
            warnings.append("Severity could not be mapped to known level; classified as UNKNOWN.")

        # 6. Missing Context (Warnings)
        if not event.vendor:
            warnings.append("Device vendor is undefined.")
        if not event.action:
            warnings.append("Perimeter decision action is unspecified.")

        is_valid = len(errors) == 0
        return ValidationReport(is_valid=is_valid, errors=errors, warnings=warnings)
