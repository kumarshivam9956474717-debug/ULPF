import re
import ipaddress
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
import dateutil.parser

# Common networking & security vocabulary sets
PROTOCOLS = {"tcp", "udp", "icmp", "gre", "esp", "ah", "igmp", "sctp", "tls", "http", "https", "dns", "ssh", "snmp", "ntp", "ftp"}
ACTIONS = {"allow", "allowed", "permit", "permitted", "pass", "accept", "accepted", "block", "blocked", "deny", "denied", "drop", "dropped", "reject", "rejected", "alert", "reset"}
SEVERITIES = {"emergency", "alert", "critical", "crit", "error", "err", "warning", "warn", "notice", "medium", "high", "low", "informational", "info", "debug"}

MAC_REGEX = re.compile(r"^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$")
URL_REGEX = re.compile(r"^https?://[^\s]+$")
IPV4_REGEX = re.compile(r"^(\d{1,3}\.){3}\d{1,3}$")


class FieldDetector:
    """
    Infers data types, detects networking entities (IPs, ports, protocols, timestamps),
    and validates field values extracted from unknown log payloads.
    """

    @staticmethod
    def infer_type(field_name: str, value: Any) -> str:
        """
        Determines the semantic data type of an extracted value using
        value patterns and field name hints.
        """
        if value is None or value == "":
            return "string"

        str_val = str(value).strip()
        str_val_clean = str_val.strip("\"'").strip()
        fn_lower = field_name.lower().replace("-", "_").replace(" ", "_")

        # 1. IP Address
        if IPV4_REGEX.match(str_val_clean):
            try:
                ipaddress.IPv4Address(str_val_clean)
                return "ip"
            except ValueError:
                pass
        try:
            if ":" in str_val_clean and len(str_val_clean) > 2:
                ipaddress.IPv6Address(str_val_clean)
                return "ip"
        except ValueError:
            pass

        # 2. Port (0 - 65535)
        if str_val_clean.isdigit():
            val_int = int(str_val_clean)
            if 0 <= val_int <= 65535:
                # Strong indication if field name hints port or value is well known
                if any(k in fn_lower for k in ("port", "pt", "spt", "dpt", "dport", "sport")):
                    return "port"
                elif val_int in {80, 443, 22, 53, 123, 514, 8080, 8443, 3389, 21, 25}:
                    return "port"

        # 3. Protocol
        val_lower = str_val_clean.lower()
        if val_lower in PROTOCOLS or (fn_lower in ("proto", "protocol", "transport") and len(val_lower) <= 6):
            return "protocol"

        # 4. Action
        if val_lower in ACTIONS or fn_lower in ("act", "action", "decision", "disposition"):
            return "action"

        # 5. Severity
        if val_lower in SEVERITIES or fn_lower in ("sev", "severity", "level", "priority"):
            return "severity"

        # 6. MAC Address
        if MAC_REGEX.match(str_val_clean):
            return "mac"

        # 7. URL
        if URL_REGEX.match(str_val_clean):
            return "url"

        # 8. Timestamp
        if len(str_val_clean) >= 8:
            # Check ISO or RFC timestamp pattern
            if any(char in str_val_clean for char in ("-", "/", "T", ":")):
                try:
                    dt = dateutil.parser.parse(str_val_clean)
                    if dt.year >= 2000:
                        return "timestamp"
                except Exception:
                    pass

        # 9. Numeric integers or floats
        if str_val_clean.isdigit():
            return "integer"
        try:
            float(str_val_clean)
            return "float"
        except ValueError:
            pass

        # 10. Hostname heuristic
        if any(k in fn_lower for k in ("host", "hostname", "shost", "dhost", "devname", "device_name", "dvchost")):
            return "hostname"

        # 11. Interface heuristic
        if any(k in fn_lower for k in ("interface", "iface", "in_if", "out_if", "in_interface", "out_interface")):
            return "interface"

        # 12. Username heuristic
        if any(k in fn_lower for k in ("user", "usr", "username", "account", "actor")):
            return "username"

        return "string"

    @staticmethod
    def extract_key_values(payload: str, delimiter: str = " ", kv_delimiter: str = "=") -> Dict[str, str]:
        """
        Extracts key-value tokens from a payload string with support for quoted strings.
        Example: src=10.0.0.1 dst=10.0.0.2 msg="Traffic blocked"
        """
        extracted = {}
        # Regex matching key<kv_delimiter>value where value can be quoted or unquoted
        pattern = re.compile(
            r'([a-zA-Z0-9_\-\.]+)' + re.escape(kv_delimiter) + r'("(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|[^\s' + re.escape(delimiter) + r']*)'
        )

        for match in pattern.finditer(payload):
            k = match.group(1).strip()
            v = match.group(2).strip()
            if (v.startswith('"') and v.endswith('"')) or (v.startswith("'") and v.endswith("'")):
                v = v[1:-1]
            extracted[k] = v

        return extracted

    @staticmethod
    def extract_delimited_values(payload: str, delimiter: str) -> List[str]:
        """Splits payload by delimiter handling quotes safely."""
        import csv
        import io
        reader = csv.reader(io.StringIO(payload), delimiter=delimiter)
        try:
            for row in reader:
                return [c.strip() for c in row]
        except Exception:
            return [c.strip() for c in payload.split(delimiter)]
        return []
