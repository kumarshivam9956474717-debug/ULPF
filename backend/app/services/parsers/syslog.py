import re
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from app.services.parsers.base import BaseParser, ParsedEvent

# RFC 5424 regex: <PRI>VERSION TIMESTAMP HOSTNAME APP-NAME PROCID MSGID STRUCTURED-DATA MSG
RFC5424_RE = re.compile(
    r"^<(?P<pri>\d{1,3})>(?P<version>[1-9]\d{0,1})\s+"
    r"(?P<timestamp>[^\s]+)\s+"
    r"(?P<hostname>[^\s]+)\s+"
    r"(?P<app_name>[^\s]+)\s+"
    r"(?P<procid>[^\s]+)\s+"
    r"(?P<msgid>[^\s]+)\s*"
    r"(?P<structured_data>\[.*?\]|-)?\s*"
    r"(?P<message>.*)$"
)

# RFC 3164 regex: <PRI>MMM DD HH:MM:SS HOSTNAME TAG: MSG
RFC3164_RE = re.compile(
    r"^(?:<(?P<pri>\d{1,3})>)?(?P<timestamp>[A-Z][a-z]{2}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2})\s+"
    r"(?P<hostname>[^\s:]+)\s+"
    r"(?:(?P<tag>[a-zA-Z0-9_\-\.\/]+)(?:\[(?P<pid>\d+)\])?:\s*)?"
    r"(?P<message>.*)$"
)

# Cisco format: %FACILITY-SEVERITY-MNEMONIC: Message
CISCO_RE = re.compile(r"%(?P<facility>[A-Z0-9_\-]+)-(?P<severity>\d)-(?P<mnemonic>[A-Z0-9_\-]+):\s*(?P<msg>.*)")

# Cisco ASA connection pattern: for inside:192.168.1.100/49210 to outside:198.51.100.25/443
CISCO_CONN_RE = re.compile(
    r"for\s+(?:(?P<src_intf>[a-zA-Z0-9_\-]+):)?(?P<src_ip>\d{1,3}(?:\.\d{1,3}){3})(?:\/(?P<src_port>\d+))?"
    r".*?\s+to\s+(?:(?P<dst_intf>[a-zA-Z0-9_\-]+):)?(?P<dst_ip>\d{1,3}(?:\.\d{1,3}){3})(?:\/(?P<dst_port>\d+))?",
    re.IGNORECASE
)

# Common key-value extraction pattern inside syslog messages (Fortinet, Checkpoint, etc.)
KV_RE = re.compile(r'([a-zA-Z0-9_\.\-]+)=(?:"([^"]*)"|([^\s,;]+))')



class SyslogParser(BaseParser):
    parser_id = "syslog_generic"
    parser_version = "1.0.0"
    supported_formats = ["syslog"]

    def can_parse(self, payload: str, metadata: Optional[Dict[str, Any]] = None) -> bool:
        if not payload:
            return False
        p = payload.strip()
        return bool(
            p.startswith("<")
            or RFC5424_RE.match(p)
            or RFC3164_RE.match(p)
            or "%" in p
            or "devname=" in p
            or "devid=" in p
            or ("date=" in p and "time=" in p)
        )


    def parse(self, payload: str, metadata: Optional[Dict[str, Any]] = None) -> ParsedEvent:
        text = payload.strip()
        extracted: Dict[str, Any] = {}
        custom: Dict[str, Any] = {}
        warnings = []
        errors = []

        m5424 = RFC5424_RE.match(text)
        m3164 = RFC3164_RE.match(text)

        if m5424:
            d = m5424.groupdict()
            pri = int(d["pri"]) if d.get("pri") else None
            if pri is not None:
                extracted["facility"] = pri >> 3
                extracted["severity"] = pri & 7
            if d.get("timestamp") and d["timestamp"] != "-":
                extracted["timestamp"] = d["timestamp"]
            if d.get("hostname") and d["hostname"] != "-":
                extracted["hostname"] = d["hostname"]
            if d.get("app_name") and d["app_name"] != "-":
                extracted["process"] = d["app_name"]
            if d.get("procid") and d["procid"] != "-":
                custom["process_id"] = d["procid"]
            if d.get("msgid") and d["msgid"] != "-":
                custom["message_id"] = d["msgid"]
            if d.get("structured_data") and d["structured_data"] != "-":
                custom["structured_data"] = d["structured_data"]

            msg = d.get("message", "").strip()
            extracted["message"] = msg
            self._extract_embedded_content(msg, extracted, custom)

        elif m3164:
            d = m3164.groupdict()
            if d.get("pri"):
                pri = int(d["pri"])
                extracted["facility"] = pri >> 3
                extracted["severity"] = pri & 7
            if d.get("timestamp"):
                extracted["timestamp"] = d["timestamp"]
            if d.get("hostname"):
                extracted["hostname"] = d["hostname"]
            if d.get("tag"):
                extracted["process"] = d["tag"]
            if d.get("pid"):
                custom["process_id"] = d["pid"]

            msg = d.get("message", "").strip()
            extracted["message"] = msg
            self._extract_embedded_content(msg, extracted, custom)

        else:
            # Fallback parsing for unstructured syslog or Cisco direct message
            extracted["message"] = text
            self._extract_embedded_content(text, extracted, custom)
            warnings.append("Syslog did not strictly match RFC 5424 or RFC 3164; parsed using heuristic fallback.")

        return ParsedEvent(
            extracted_fields=extracted,
            parser_id=self.parser_id,
            parser_version=self.parser_version,
            source_format="syslog",
            warnings=warnings,
            errors=errors,
            confidence=0.90 if (m5424 or m3164) else 0.70,
            custom_fields=custom
        )

    def _extract_embedded_content(self, msg: str, extracted: Dict[str, Any], custom: Dict[str, Any]) -> None:
        """Extracts Cisco codes and key-value pairs if present in the message body."""
        # Check Cisco mnemonic
        cisco_match = CISCO_RE.search(msg)
        if cisco_match:
            cd = cisco_match.groupdict()
            custom["cisco_facility"] = cd["facility"]
            extracted["severity"] = int(cd["severity"])
            custom["cisco_mnemonic"] = cd["mnemonic"]
            extracted["rule_id"] = f"%{cd['facility']}-{cd['severity']}-{cd['mnemonic']}"

        # Check Cisco network connection (IPs, Ports, Interfaces)
        conn_match = CISCO_CONN_RE.search(msg)
        if conn_match:
            cnd = conn_match.groupdict()
            if cnd.get("src_ip"):
                extracted["source_ip"] = cnd["src_ip"]
            if cnd.get("src_port"):
                extracted["source_port"] = int(cnd["src_port"])
            if cnd.get("dst_ip"):
                extracted["destination_ip"] = cnd["dst_ip"]
            if cnd.get("dst_port"):
                extracted["destination_port"] = int(cnd["dst_port"])
            if cnd.get("src_intf"):
                custom["src_interface"] = cnd["src_intf"]
            if cnd.get("dst_intf"):
                custom["dst_interface"] = cnd["dst_intf"]


        # Extract embedded key=value pairs (Fortinet, Palo Alto, etc.)
        for match in KV_RE.finditer(msg):
            k = match.group(1)
            v = match.group(2) if match.group(2) is not None else match.group(3)
            # Store in custom fields for normalization mapper to process
            custom[k] = v
