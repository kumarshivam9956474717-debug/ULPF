import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from app.schemas.universal_event import UniversalEvent, SeverityLevel
from app.services.parsers.base import ParsedEvent
from app.services.normalization.mapper import (
    normalize_field_name,
    normalize_action,
    normalize_outcome,
    normalize_severity,
    normalize_port,
    normalize_timestamp,
)


class NormalizationService:
    """
    Universal Event Normalization Service.
    Transforms intermediate ParsedEvent into fully typed UniversalEvent schema.
    """

    @staticmethod
    def normalize_event(
        parsed: ParsedEvent,
        raw_event_id: str,
        raw_payload: str,
        vendor_override: Optional[str] = None,
        product_override: Optional[str] = None,
        device_type_override: Optional[str] = None
    ) -> UniversalEvent:
        """
        Maps extracted attributes into Universal Event Schema logical groups.
        Retains unmapped and vendor-specific data in custom_fields.
        """
        canonical: Dict[str, Any] = {}
        unmapped: Dict[str, Any] = dict(parsed.custom_fields)

        # Merge extracted fields through normalization mapper
        for k, v in parsed.extracted_fields.items():
            norm_key = normalize_field_name(k)
            # If norm_key is an existing UES attribute, map it; otherwise preserve in unmapped
            if norm_key in UniversalEvent.model_fields:
                canonical[norm_key] = v
            else:
                unmapped[k] = v

        # Also promote recognized UES aliases from custom_fields (e.g. key-value syslog fields)
        for k, v in list(unmapped.items()):
            norm_key = normalize_field_name(k)
            if norm_key in UniversalEvent.model_fields and norm_key not in canonical:
                canonical[norm_key] = v
                unmapped.pop(k, None)


        # 1. Identity
        event_id = f"EVT-{uuid.uuid4().hex[:16].upper()}"
        source_event_id = str(canonical.get("source_event_id") or canonical.get("event_id") or "") or None

        # 2. Time
        raw_ts = canonical.get("timestamp")
        parsed_ts = normalize_timestamp(raw_ts)
        ingestion_ts = datetime.now(timezone.utc)
        tz = canonical.get("timezone", "UTC")

        # 3. Source Device
        vendor = vendor_override or canonical.get("vendor")
        product = product_override or canonical.get("product")
        device_type = device_type_override or canonical.get("device_type") or "firewall"
        device_id = canonical.get("device_id")
        hostname = canonical.get("hostname")
        source_format = parsed.source_format

        # 4. Network
        source_ip = canonical.get("source_ip")
        source_port = normalize_port(canonical.get("source_port"))
        destination_ip = canonical.get("destination_ip")
        destination_port = normalize_port(canonical.get("destination_port"))
        protocol = str(canonical.get("protocol")).upper() if canonical.get("protocol") else None

        # 5. User Identity
        username = canonical.get("username")
        user_id = canonical.get("user_id")
        auth_method = canonical.get("authentication_method")

        # 6. Event Taxonomy
        event_type = canonical.get("event_type") or "network_traffic"
        action = normalize_action(canonical.get("action"))
        outcome = normalize_outcome(canonical.get("outcome"))
        severity = normalize_severity(canonical.get("severity"))
        category = canonical.get("category")
        subcategory = canonical.get("subcategory")

        # 7. Network Context
        interface = canonical.get("interface")
        direction = canonical.get("direction")
        zone = canonical.get("zone")

        # 8. Threat / Security
        threat_name = canonical.get("threat_name")
        threat_id = canonical.get("threat_id")
        signature_id = canonical.get("signature_id")
        rule_id = canonical.get("rule_id")

        # 9. Additional & Custom
        message = canonical.get("message")
        tags = canonical.get("tags") if isinstance(canonical.get("tags"), list) else []

        # 10. Traceability & Lineage
        parser_id = parsed.parser_id
        parser_version = parsed.parser_version
        normalization_version = "1.0.0"

        # Build verified UniversalEvent
        return UniversalEvent(
            event_id=event_id,
            source_event_id=source_event_id,
            schema_version="1.0.0",
            timestamp=parsed_ts,
            ingestion_timestamp=ingestion_ts,
            timezone=tz,
            vendor=vendor,
            product=product,
            device_type=device_type,
            device_id=device_id,
            hostname=hostname,
            source_format=source_format,
            source_ip=source_ip,
            source_port=source_port,
            destination_ip=destination_ip,
            destination_port=destination_port,
            protocol=protocol,
            username=username,
            user_id=user_id,
            authentication_method=auth_method,
            event_type=event_type,
            action=action,
            outcome=outcome,
            severity=severity,
            category=category,
            subcategory=subcategory,
            interface=interface,
            direction=direction,
            zone=zone,
            threat_name=threat_name,
            threat_id=threat_id,
            signature_id=signature_id,
            rule_id=rule_id,
            message=message,
            tags=tags,
            custom_fields=unmapped,
            raw_event_id=raw_event_id,
            parser_id=parser_id,
            parser_version=parser_version,
            normalization_version=normalization_version,
            raw_event=raw_payload
        )
