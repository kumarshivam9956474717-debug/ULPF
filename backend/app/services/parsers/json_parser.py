import json
from typing import Any, Dict, Optional
from app.services.parsers.base import BaseParser, ParsedEvent


class JsonParser(BaseParser):
    parser_id = "json_generic"
    parser_version = "1.0.0"
    supported_formats = ["json"]

    def can_parse(self, payload: str, metadata: Optional[Dict[str, Any]] = None) -> bool:
        if not payload:
            return False
        p = payload.strip()
        return (p.startswith("{") and p.endswith("}")) or (p.startswith("[") and p.endswith("]"))

    def parse(self, payload: str, metadata: Optional[Dict[str, Any]] = None) -> ParsedEvent:
        warnings = []
        errors = []
        custom: Dict[str, Any] = {}
        extracted: Dict[str, Any] = {}

        try:
            data = json.loads(payload.strip())
        except Exception as exc:
            errors.append(f"Failed to parse JSON: {str(exc)}")
            return ParsedEvent(
                extracted_fields={},
                parser_id=self.parser_id,
                parser_version=self.parser_version,
                source_format="json",
                warnings=warnings,
                errors=errors,
                confidence=0.0,
                custom_fields={}
            )

        if isinstance(data, list):
            # If payload is a list with one object
            if len(data) == 1 and isinstance(data[0], dict):
                data = data[0]
            else:
                data = {"batch_records": data}

        if not isinstance(data, dict):
            errors.append("JSON payload is not an object or supported list")
            return ParsedEvent(
                extracted_fields={},
                parser_id=self.parser_id,
                parser_version=self.parser_version,
                source_format="json",
                warnings=warnings,
                errors=errors,
                confidence=0.0,
                custom_fields={"raw_value": data}
            )

        # Flatten or copy attributes into custom_fields and extracted_fields
        for k, v in data.items():
            if isinstance(v, (str, int, float, bool)) or v is None:
                extracted[k] = v
            else:
                # Retain nested structures safely in custom_fields
                custom[k] = v

        return ParsedEvent(
            extracted_fields=extracted,
            parser_id=self.parser_id,
            parser_version=self.parser_version,
            source_format="json",
            warnings=warnings,
            errors=errors,
            confidence=0.99,
            custom_fields=custom
        )
