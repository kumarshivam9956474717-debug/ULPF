import csv
import io
import json
import re
import xml.etree.ElementTree as ET
from typing import Optional
from pydantic import BaseModel, Field


class DetectionResult(BaseModel):
    detected_format: str = Field(..., description="Detected format (cef, leef, json, syslog, csv, xml, unknown)")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score from 0.0 to 1.0")
    reason: str = Field(..., description="Deterministic heuristic explanation for detection")


# Pre-compiled regex patterns for format detection
CEF_PATTERN = re.compile(r"^CEF:\s*\d+\|", re.IGNORECASE)
LEEF_PATTERN = re.compile(r"^LEEF:\s*[\d\.]+\|", re.IGNORECASE)
RFC5424_PATTERN = re.compile(r"^<\d{1,3}>[1-9]\d{0,1}\s+\d{4}-\d{2}-\d{2}T")
RFC3164_PATTERN = re.compile(r"^<\d{1,3}>[A-Z][a-z]{2}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2}")
CISCO_SYSLOG_PATTERN = re.compile(r"(%[A-Z0-9_\-]+-[0-7]-[A-Z0-9_\-]+:)")
BSD_SYSLOG_PATTERN = re.compile(r"^[A-Z][a-z]{2}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2}\s+[a-zA-Z0-9_\.\-]+")
KEYVALUE_SYSLOG_PATTERN = re.compile(r"(date=\d{4}-\d{2}-\d{2}\s+time=\d{2}:\d{2}:\d{2}|devname=[^\s]+|devid=[^\s]+)")


def detect_format(raw_payload: str) -> DetectionResult:
    """
    Deterministic offline format detection for perimeter network logs.
    Identifies: CEF, LEEF, JSON, Syslog (RFC 5424 / 3164 / Cisco), CSV, XML, or UNKNOWN.
    """
    if not raw_payload or not raw_payload.strip():
        return DetectionResult(
            detected_format="unknown",
            confidence=0.0,
            reason="Payload is empty or whitespace only"
        )

    text = raw_payload.strip()

    # 1. CEF Check
    if CEF_PATTERN.match(text):
        parts = text.split("|")
        if len(parts) >= 8:
            return DetectionResult(
                detected_format="cef",
                confidence=0.99,
                reason="Standard CEF header prefix matching 'CEF:version|vendor|product|...' with 8+ pipe segments."
            )
        return DetectionResult(
            detected_format="cef",
            confidence=0.85,
            reason="Payload starts with CEF header prefix."
        )

    # 2. LEEF Check
    if LEEF_PATTERN.match(text):
        parts = text.split("|")
        if len(parts) >= 5:
            return DetectionResult(
                detected_format="leef",
                confidence=0.99,
                reason="Standard LEEF header prefix matching 'LEEF:version|vendor|product|...'."
            )
        return DetectionResult(
            detected_format="leef",
            confidence=0.85,
            reason="Payload starts with LEEF header prefix."
        )

    # 3. JSON Check
    if (text.startswith("{") and text.endswith("}")) or (text.startswith("[") and text.endswith("]")):
        try:
            parsed = json.loads(text)
            if isinstance(parsed, (dict, list)):
                return DetectionResult(
                    detected_format="json",
                    confidence=0.99,
                    reason="Valid JSON data structure successfully parsed by JSON parser."
                )
        except Exception:
            pass

    # 4. XML Check
    if (text.startswith("<?xml") or (text.startswith("<") and text.endswith(">") and not text.startswith("<0>") and not text.startswith("<1>"))):
        try:
            # Safe parsing without entity expansion
            parser = ET.XMLParser()
            ET.fromstring(text, parser=parser)
            return DetectionResult(
                detected_format="xml",
                confidence=0.95,
                reason="Well-formed XML document root element successfully verified."
            )
        except Exception:
            pass

    # 5. Syslog Check
    if RFC5424_PATTERN.match(text):
        return DetectionResult(
            detected_format="syslog",
            confidence=0.98,
            reason="Matches RFC 5424 structured syslog priority, version, and ISO-8601 timestamp."
        )

    if RFC3164_PATTERN.match(text):
        return DetectionResult(
            detected_format="syslog",
            confidence=0.95,
            reason="Matches RFC 3164 BSD syslog priority and standard MMM DD HH:MM:SS timestamp."
        )

    if text.startswith("<") and ">" in text[:6] and text[1:text.index(">")].isdigit():
        return DetectionResult(
            detected_format="syslog",
            confidence=0.90,
            reason="Begins with standard RFC syslog numerical PRI facility/severity tag."
        )

    if CISCO_SYSLOG_PATTERN.search(text):
        return DetectionResult(
            detected_format="syslog",
            confidence=0.92,
            reason="Contains Cisco/Perimeter mnemonic pattern (%FACILITY-SEV-MNEMONIC:)."
        )

    if BSD_SYSLOG_PATTERN.match(text):
        return DetectionResult(
            detected_format="syslog",
            confidence=0.75,
            reason="Begins with BSD syslog timestamp and reporting hostname without PRI header."
        )

    if KEYVALUE_SYSLOG_PATTERN.search(text):
        return DetectionResult(
            detected_format="syslog",
            confidence=0.88,
            reason="Matches key-value security event syslog pattern (date/time/devname)."
        )


    # 6. CSV Check
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if len(lines) >= 1:
        # Check first line or multiple lines for delimiter consistency
        for delim in [",", ";", "\t"]:
            if delim in lines[0]:
                try:
                    reader = list(csv.reader(lines[:5], delimiter=delim))
                    col_counts = [len(r) for r in reader if r]
                    if col_counts and col_counts[0] >= 3:
                        # If all rows have identical column count >= 3
                        if all(c == col_counts[0] for c in col_counts):
                            # Ensure it doesn't look like key-value syslog (e.g., 'src=1.1.1.1 dst=2.2.2.2')
                            if not all("=" in col for col in reader[0]):
                                return DetectionResult(
                                    detected_format="csv",
                                    confidence=0.85,
                                    reason=f"Delimited tabular record with consistent {col_counts[0]} columns using '{delim}' delimiter."
                                )
                except Exception:
                    pass

    # 7. Default Unknown
    return DetectionResult(
        detected_format="unknown",
        confidence=0.10,
        reason="Does not match known signatures for CEF, LEEF, JSON, Syslog, CSV, or XML."
    )
