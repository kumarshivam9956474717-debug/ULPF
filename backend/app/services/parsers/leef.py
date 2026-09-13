import re
from typing import Any, Dict, List, Optional
from app.services.parsers.base import BaseParser, ParsedEvent

LEEF_EXT_RE = re.compile(r'([a-zA-Z0-9_\.\-]+)=(.*?)(?=\s+[a-zA-Z0-9_\.\-]+=|$)')


class LeefParser(BaseParser):
    parser_id = "leef_generic"
    parser_version = "1.0.0"
    supported_formats = ["leef"]

    def can_parse(self, payload: str, metadata: Optional[Dict[str, Any]] = None) -> bool:
        if not payload:
            return False
        return "LEEF:" in payload

    def parse(self, payload: str, metadata: Optional[Dict[str, Any]] = None) -> ParsedEvent:
        warnings: List[str] = []
        errors: List[str] = []
        extracted: Dict[str, Any] = {}
        custom: Dict[str, Any] = {}

        text = payload.strip()
        leef_idx = text.find("LEEF:")
        if leef_idx == -1:
            errors.append("Invalid LEEF payload: 'LEEF:' prefix not found.")
            return ParsedEvent(
                extracted_fields={},
                parser_id=self.parser_id,
                parser_version=self.parser_version,
                source_format="leef",
                warnings=warnings,
                errors=errors,
                confidence=0.0,
                custom_fields={}
            )

        if leef_idx > 0:
            custom["syslog_header"] = text[:leef_idx].strip()
            text = text[leef_idx:]

        # Split on pipe: LEEF:Version|Vendor|Product|Version|EventID|attributes
        # Notice LEEF 2.0 can include delimiter delimiter definition, but standard is 5 pipe prefixes + attributes
        parts = text.split("|", 5)
        if len(parts) < 6:
            errors.append(f"Malformed LEEF header: expected at least 5 pipe delimiters, found {len(parts)-1}.")
            return ParsedEvent(
                extracted_fields={"raw_prefix": text},
                parser_id=self.parser_id,
                parser_version=self.parser_version,
                source_format="leef",
                warnings=warnings,
                errors=errors,
                confidence=0.3,
                custom_fields={}
            )

        version = parts[0].replace("LEEF:", "").strip()
        extracted["leef_version"] = version
        extracted["vendor"] = parts[1].strip()
        extracted["product"] = parts[2].strip()
        extracted["device_version"] = parts[3].strip()
        extracted["event_id"] = parts[4].strip()

        attributes = parts[5].strip()
        if attributes:
            # Check delimiter: tab vs whitespace vs default
            matches = LEEF_EXT_RE.findall(attributes)
            for k, v in matches:
                clean_k = k.strip()
                clean_v = v.strip().replace(r"\|", "|").replace(r"\=", "=")
                extracted[clean_k] = clean_v

        return ParsedEvent(
            extracted_fields=extracted,
            parser_id=self.parser_id,
            parser_version=self.parser_version,
            source_format="leef",
            warnings=warnings,
            errors=errors,
            confidence=0.98,
            custom_fields=custom
        )
