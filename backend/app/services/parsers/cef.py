import re
from typing import Any, Dict, List, Optional
from app.services.parsers.base import BaseParser, ParsedEvent

# Key-value pattern handling unescaped space vs escaped characters in CEF extension
CEF_EXT_RE = re.compile(r'([a-zA-Z0-9_\.\-]+)=(.*?)(?=\s+[a-zA-Z0-9_\.\-]+=|$)')


class CefParser(BaseParser):
    parser_id = "cef_generic"
    parser_version = "1.0.0"
    supported_formats = ["cef"]

    def can_parse(self, payload: str, metadata: Optional[Dict[str, Any]] = None) -> bool:
        if not payload:
            return False
        return "CEF:" in payload

    def parse(self, payload: str, metadata: Optional[Dict[str, Any]] = None) -> ParsedEvent:
        warnings: List[str] = []
        errors: List[str] = []
        extracted: Dict[str, Any] = {}
        custom: Dict[str, Any] = {}

        text = payload.strip()
        # Find start of CEF header if preceded by syslog header
        cef_idx = text.find("CEF:")
        if cef_idx == -1:
            errors.append("Invalid CEF payload: 'CEF:' prefix not found.")
            return ParsedEvent(
                extracted_fields={},
                parser_id=self.parser_id,
                parser_version=self.parser_version,
                source_format="cef",
                warnings=warnings,
                errors=errors,
                confidence=0.0,
                custom_fields={}
            )

        if cef_idx > 0:
            syslog_prefix = text[:cef_idx].strip()
            custom["syslog_header"] = syslog_prefix
            text = text[cef_idx:]

        # Split on unescaped pipe
        # CEF format: CEF:Version|Device Vendor|Device Product|Device Version|Signature ID|Name|Severity|Extension
        # We can split on pipe, considering up to 8 parts
        parts = text.split("|", 7)
        if len(parts) < 8:
            # Check if there are 7 parts without extension
            if len(parts) == 7:
                parts.append("")
                warnings.append("CEF payload missing extension section.")
            else:
                errors.append(f"Malformed CEF header: expected 7 pipe delimiters, found {len(parts)-1}.")
                return ParsedEvent(
                    extracted_fields={"raw_prefix": text},
                    parser_id=self.parser_id,
                    parser_version=self.parser_version,
                    source_format="cef",
                    warnings=warnings,
                    errors=errors,
                    confidence=0.3,
                    custom_fields={}
                )

        version_part = parts[0]
        version = version_part.replace("CEF:", "").strip()
        extracted["cef_version"] = version
        extracted["vendor"] = parts[1].strip()
        extracted["product"] = parts[2].strip()
        extracted["device_version"] = parts[3].strip()
        extracted["signature_id"] = parts[4].strip()
        extracted["event_name"] = parts[5].strip()
        extracted["severity"] = parts[6].strip()

        extension = parts[7].strip()
        if extension:
            matches = CEF_EXT_RE.findall(extension)
            for k, v in matches:
                clean_k = k.strip()
                clean_v = v.strip().replace(r"\|", "|").replace(r"\=", "=")
                extracted[clean_k] = clean_v

        return ParsedEvent(
            extracted_fields=extracted,
            parser_id=self.parser_id,
            parser_version=self.parser_version,
            source_format="cef",
            warnings=warnings,
            errors=errors,
            confidence=0.98,
            custom_fields=custom
        )
