import json
import logging
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session

from app.models.mapping_profile import LogMappingProfile
from app.services.parsers.base import BaseParser, ParsedEvent
from app.services.onboarding.field_detector import FieldDetector
from app.services.parsers.registry import default_parser_registry

logger = logging.getLogger(__name__)


class ConfigurableParser(BaseParser):
    """
    Reusable, configuration-driven log parser instantiated dynamically
    from a persistent LogMappingProfile. Enables no-code ingestion of unknown
    vendor logs without modifying Python source code.
    """

    def __init__(self, profile: LogMappingProfile):
        self.profile_id = profile.id
        self.profile_name = profile.name
        self.parser_id = f"profile_{profile.name.lower().replace(' ', '_')}"
        self.parser_version = profile.version
        self.source_format = profile.source_format.lower()
        self.supported_formats = [self.source_format]

        self.vendor = profile.vendor
        self.product = profile.product
        self.device_type = profile.device_type

        self.config = profile.configuration or {}
        self.delimiter = self.config.get("delimiter", " ")
        self.kv_delimiter = self.config.get("kv_delimiter", "=")

        # Mapping rules lookup: source_field -> target_field, is_custom
        self.canonical_map: Dict[str, str] = {}
        self.custom_keys: set = set()

        for m in (profile.field_mappings or []):
            src = m.get("source_field", "").strip()
            target = m.get("target_field", "").strip()
            is_cust = m.get("is_custom", False)

            if src:
                if is_cust or target.startswith("custom_"):
                    self.custom_keys.add(src)
                elif target:
                    self.canonical_map[src] = target

    def can_parse(self, payload: str, metadata: Optional[Dict[str, Any]] = None) -> bool:
        if not payload or not isinstance(payload, str):
            return False

        clean = payload.strip()
        if not clean:
            return False

        # If metadata specifies this profile by name or ID
        if metadata:
            if metadata.get("parser_id") == self.parser_id:
                return True
            if metadata.get("profile_id") == self.profile_id:
                return True

        # Format-specific structural validation
        if self.source_format in ("key_value", "syslog_kv"):
            extracted = FieldDetector.extract_key_values(
                clean,
                delimiter=self.delimiter,
                kv_delimiter=self.kv_delimiter
            )
            # Must match at least 2 configured keys or 50% of configured source fields
            if not extracted:
                return False
            matched = set(extracted.keys()) & (set(self.canonical_map.keys()) | self.custom_keys)
            return len(matched) >= 2 or len(matched) >= (len(self.canonical_map) * 0.4)

        elif self.source_format == "delimited":
            tokens = FieldDetector.extract_delimited_values(clean, delimiter=self.delimiter)
            # Check token count matches configured column count
            expected_cols = len(self.canonical_map) + len(self.custom_keys)
            return len(tokens) >= max(2, expected_cols)

        elif self.source_format == "json":
            try:
                data = json.loads(clean)
                if isinstance(data, dict):
                    matched = set(data.keys()) & (set(self.canonical_map.keys()) | self.custom_keys)
                    return len(matched) >= 2
            except Exception:
                return False

        return False

    def parse(self, payload: str, metadata: Optional[Dict[str, Any]] = None) -> ParsedEvent:
        errors = []
        warnings = []
        clean = payload.strip()

        extracted: Dict[str, Any] = {}

        if self.source_format in ("key_value", "syslog_kv"):
            extracted = FieldDetector.extract_key_values(
                clean,
                delimiter=self.delimiter,
                kv_delimiter=self.kv_delimiter
            )
        elif self.source_format == "delimited":
            tokens = FieldDetector.extract_delimited_values(clean, delimiter=self.delimiter)
            extracted = {f"column_{i+1}": val for i, val in enumerate(tokens)}
        elif self.source_format == "json":
            try:
                data = json.loads(clean)
                if isinstance(data, dict):
                    extracted = {str(k): str(v) for k, v in data.items()}
            except Exception as exc:
                errors.append(f"JSON deserialization error in configurable parser: {str(exc)}")

        if not extracted and not errors:
            errors.append(f"Configurable parser '{self.profile_name}' could not extract fields from payload.")

        # Map to canonical attributes & custom fields
        canonical_extracted: Dict[str, Any] = {
            "vendor": self.vendor,
            "product": self.product,
            "device_type": self.device_type,
            "source_format": self.source_format
        }
        custom_fields: Dict[str, Any] = {}

        for src_k, src_v in extracted.items():
            if src_k in self.canonical_map:
                target_k = self.canonical_map[src_k]
                canonical_extracted[target_k] = src_v
            elif src_k in self.custom_keys:
                custom_fields[src_k] = src_v
            else:
                # Lossless guarantee: any unmapped source fields preserved in custom_fields
                custom_fields[src_k] = src_v

        return ParsedEvent(
            extracted_fields=canonical_extracted,
            parser_id=self.parser_id,
            parser_version=self.parser_version,
            source_format=self.source_format,
            warnings=warnings,
            errors=errors,
            confidence=0.95 if not errors else 0.0,
            custom_fields=custom_fields
        )


def register_profile_parser(profile: LogMappingProfile) -> ConfigurableParser:
    """Instantiates a ConfigurableParser for an ACTIVE profile and registers it."""
    parser = ConfigurableParser(profile)
    default_parser_registry.register_parser(parser)
    logger.info(f"Registered configurable parser '{parser.parser_id}' (version {parser.parser_version}).")
    return parser


def unregister_profile_parser(profile_name: str) -> None:
    """Removes a configurable parser from the active registry."""
    parser_id = f"profile_{profile_name.lower().replace(' ', '_')}"
    if parser_id in default_parser_registry._parsers:
        parser = default_parser_registry._parsers.pop(parser_id)
        for fmt, plist in default_parser_registry._format_map.items():
            if parser in plist:
                plist.remove(parser)
        logger.info(f"Unregistered configurable parser '{parser_id}'.")


def load_active_profiles_into_registry(db: Session) -> int:
    """
    Queries all ACTIVE LogMappingProfiles from the database and registers them
    into the default_parser_registry.
    """
    profiles = db.query(LogMappingProfile).filter(LogMappingProfile.status == "ACTIVE").all()
    count = 0
    for p in profiles:
        register_profile_parser(p)
        count += 1
    return count
