import csv
import io
from typing import Any, Dict, List, Optional
from app.services.parsers.base import BaseParser, ParsedEvent


class CsvParser(BaseParser):
    parser_id = "csv_generic"
    parser_version = "1.0.0"
    supported_formats = ["csv"]

    def can_parse(self, payload: str, metadata: Optional[Dict[str, Any]] = None) -> bool:
        if not payload:
            return False
        first_line = payload.strip().splitlines()[0] if payload.strip() else ""
        return any(d in first_line for d in [",", ";", "\t"])

    def parse(self, payload: str, metadata: Optional[Dict[str, Any]] = None) -> ParsedEvent:
        warnings: List[str] = []
        errors: List[str] = []
        extracted: Dict[str, Any] = {}
        custom: Dict[str, Any] = {}

        lines = [line.strip() for line in payload.strip().splitlines() if line.strip()]
        if not lines:
            errors.append("Empty CSV payload")
            return ParsedEvent(
                extracted_fields={},
                parser_id=self.parser_id,
                parser_version=self.parser_version,
                source_format="csv",
                warnings=warnings,
                errors=errors,
                confidence=0.0,
                custom_fields={}
            )

        # Detect delimiter
        first_line = lines[0]
        delimiter = ","
        for d in [",", ";", "\t"]:
            if d in first_line:
                delimiter = d
                break

        try:
            reader = list(csv.reader(lines, delimiter=delimiter))
        except Exception as exc:
            errors.append(f"CSV parsing failure: {str(exc)}")
            return ParsedEvent(
                extracted_fields={},
                parser_id=self.parser_id,
                parser_version=self.parser_version,
                source_format="csv",
                warnings=warnings,
                errors=errors,
                confidence=0.0,
                custom_fields={"raw_lines": lines}
            )

        if not reader:
            errors.append("No valid CSV rows parsed")
            return ParsedEvent(
                extracted_fields={},
                parser_id=self.parser_id,
                parser_version=self.parser_version,
                source_format="csv",
                warnings=warnings,
                errors=errors,
                confidence=0.0,
                custom_fields={}
            )

        # Determine headers
        if len(reader) >= 2:
            headers = [h.strip() for h in reader[0]]
            data_row = [v.strip() for v in reader[1]]
        else:
            # Single line CSV: check if it looks like header or data
            row = [c.strip() for c in reader[0]]
            # If any value contains IP or digits, treat as data row with default column names
            headers = [f"column_{i+1}" for i in range(len(row))]
            data_row = row
            warnings.append("Single line CSV without header row; assigned synthetic column names.")

        if len(data_row) != len(headers):
            warnings.append(f"Column count mismatch: {len(headers)} headers vs {len(data_row)} values.")

        for i, h in enumerate(headers):
            if i < len(data_row):
                val = data_row[i]
                extracted[h] = val
            else:
                extracted[h] = None

        return ParsedEvent(
            extracted_fields=extracted,
            parser_id=self.parser_id,
            parser_version=self.parser_version,
            source_format="csv",
            warnings=warnings,
            errors=errors,
            confidence=0.85,
            custom_fields=custom
        )
