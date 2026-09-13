from collections import Counter
from typing import Any, Dict, List, Tuple
import numpy as np

from app.models.normalized_event import NormalizedEvent

WELL_KNOWN_PORTS = {20, 21, 22, 23, 25, 53, 80, 110, 123, 143, 389, 443, 445, 465, 587, 636, 993, 995, 3389, 8080, 8443}

SEVERITY_SCORES = {
    "informational": 1.0,
    "low": 2.0,
    "medium": 3.0,
    "high": 4.0,
    "critical": 5.0,
    "unknown": 0.0,
}

ACTION_SCORES = {
    "allow": 0.0,
    "permit": 0.0,
    "accept": 0.0,
    "pass": 0.0,
    "deny": 1.0,
    "block": 1.0,
    "drop": 1.0,
    "reject": 1.0,
}

PROTOCOL_SCORES = {
    "tcp": 1.0,
    "udp": 2.0,
    "icmp": 3.0,
}


class FeatureExtractor:
    """
    Transforms normalized events into deterministic numerical feature vectors
    suitable for local statistical and unsupervised anomaly detection.
    """

    FEATURE_NAMES = [
        "src_ip_freq_ratio",
        "dst_ip_freq_ratio",
        "dst_port_freq_ratio",
        "port_normalized",
        "is_well_known_port",
        "is_ephemeral_port",
        "protocol_code",
        "severity_score",
        "action_score",
    ]

    @classmethod
    def extract_features(cls, events: List[NormalizedEvent]) -> Tuple[np.ndarray, List[Dict[str, Any]]]:
        """
        Extracts feature vectors and per-event feature summaries.

        Returns:
            Tuple[X: np.ndarray (N, 9), feature_summaries: List[Dict]]
        """
        if not events:
            return np.empty((0, len(cls.FEATURE_NAMES))), []

        n = len(events)
        src_counts = Counter(e.source_ip for e in events if e.source_ip)
        dst_counts = Counter(e.destination_ip for e in events if e.destination_ip)
        port_counts = Counter(e.destination_port for e in events if e.destination_port is not None)

        rows = []
        summaries = []

        for e in events:
            # 1. Frequency ratios
            src_ratio = (src_counts.get(e.source_ip, 1) / n) if e.source_ip else 0.0
            dst_ratio = (dst_counts.get(e.destination_ip, 1) / n) if e.destination_ip else 0.0
            port_ratio = (port_counts.get(e.destination_port, 1) / n) if e.destination_port is not None else 0.0

            # 2. Port attributes
            port = e.destination_port or 0
            port_norm = min(float(port) / 65535.0, 1.0)
            is_wk = 1.0 if port in WELL_KNOWN_PORTS else 0.0
            is_eph = 1.0 if port > 1024 else 0.0

            # 3. Protocol
            proto = (e.protocol or "").lower()
            proto_code = PROTOCOL_SCORES.get(proto, 0.0)

            # 4. Severity
            sev = (e.severity or "unknown").lower()
            sev_score = SEVERITY_SCORES.get(sev, 0.0)

            # 5. Action
            act = (e.action or "").lower()
            act_score = ACTION_SCORES.get(act, 0.5)

            vec = [
                src_ratio,
                dst_ratio,
                port_ratio,
                port_norm,
                is_wk,
                is_eph,
                proto_code,
                sev_score,
                act_score,
            ]
            rows.append(vec)

            summaries.append({
                "source_ip": e.source_ip,
                "destination_ip": e.destination_ip,
                "destination_port": e.destination_port,
                "src_freq_ratio": round(src_ratio, 4),
                "dst_port_freq_ratio": round(port_ratio, 4),
                "is_well_known_port": bool(is_wk),
                "protocol": e.protocol,
                "severity": e.severity,
                "action": e.action,
            })

        return np.array(rows, dtype=np.float32), summaries
