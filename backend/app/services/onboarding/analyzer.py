import json
import re
from typing import Any, Dict, List, Optional, Tuple
from collections import Counter

from app.services.onboarding.field_detector import FieldDetector
from app.services.onboarding.models import FieldCandidate

# Syslog header pattern: <PRI>TIMESTAMP HOSTNAME TAG: or RFC3164
SYSLOG_PREFIX_REGEX = re.compile(
    r"^(?:<\d{1,3}>)?(?:[A-Z][a-z]{2}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2}|\d{4}-\d{2}-\d{2}T[^\s]+)\s+([^\s:]+)(?:\s+[^:]+)?:?\s+(.*)$"
)


class LogAnalyzer:
    """
    Analyzes raw log samples from unknown sources to determine format,
    token delimiters, key-value patterns, and candidate field schemas.
    """

    @staticmethod
    def analyze_samples(samples: List[str]) -> Tuple[str, float, str, str, bool, List[FieldCandidate], List[str]]:
        """
        Analyzes a batch of sample log strings.

        Returns:
            (detected_format, confidence, delimiter, kv_delimiter, has_syslog_header, field_candidates, warnings)
        """
        clean_samples = [s.strip() for s in samples if s and s.strip()]
        if not clean_samples:
            return "unknown", 0.0, " ", "=", False, [], ["No non-empty log samples provided."]

        warnings: List[str] = []

        # 1. Check if JSON formatted
        json_success_count = 0
        json_fields_counter: Counter = Counter()
        json_sample_values: Dict[str, Any] = {}
        for s in clean_samples:
            try:
                data = json.loads(s)
                if isinstance(data, dict):
                    json_success_count += 1
                    for k, v in data.items():
                        json_fields_counter[k] += 1
                        if k not in json_sample_values:
                            json_sample_values[k] = v
            except Exception:
                pass

        if json_success_count == len(clean_samples) and json_success_count > 0:
            candidates = []
            for field_name, count in json_fields_counter.items():
                val = json_sample_values.get(field_name)
                inf_type = FieldDetector.infer_type(field_name, val)
                candidates.append(
                    FieldCandidate(
                        source_field=field_name,
                        sample_value=str(val) if val is not None else None,
                        inferred_type=inf_type,
                        occurrence_rate=round(count / len(clean_samples), 2)
                    )
                )
            return "json", 0.98, " ", "=", False, candidates, warnings

        # 1.5. Check if XML formatted
        xml_success_count = 0
        xml_fields_counter: Counter = Counter()
        xml_sample_values: Dict[str, str] = {}
        for s in clean_samples:
            if s.startswith("<") and s.endswith(">"):
                try:
                    import xml.etree.ElementTree as ET
                    root = ET.fromstring(s)
                    xml_success_count += 1
                    for child in root:
                        tag = child.tag
                        txt = (child.text or "").strip()
                        xml_fields_counter[tag] += 1
                        if tag not in xml_sample_values:
                            xml_sample_values[tag] = txt
                except Exception:
                    pass

        if xml_success_count == len(clean_samples) and xml_success_count > 0:
            candidates = []
            for tag_name, count in xml_fields_counter.items():
                val = xml_sample_values.get(tag_name)
                inf_type = FieldDetector.infer_type(tag_name, val)
                candidates.append(
                    FieldCandidate(
                        source_field=tag_name,
                        sample_value=val,
                        inferred_type=inf_type,
                        occurrence_rate=round(count / len(clean_samples), 2)
                    )
                )
            return "xml", 0.95, " ", "=", False, candidates, warnings

        # 2. Check for Syslog Envelope Prefix
        has_syslog_header = False
        payloads_to_analyze = []
        for s in clean_samples:
            match = SYSLOG_PREFIX_REGEX.match(s)
            if match:
                has_syslog_header = True
                payloads_to_analyze.append(match.group(2))
            else:
                payloads_to_analyze.append(s)

        # 3. Check for Key-Value Patterns (key=value or key:value)
        kv_equal_counts = []
        kv_colon_counts = []
        sample_kv_equal_maps = []
        sample_kv_colon_maps = []

        for p in payloads_to_analyze:
            kv_eq = FieldDetector.extract_key_values(p, delimiter=" ", kv_delimiter="=")
            kv_equal_counts.append(len(kv_eq))
            sample_kv_equal_maps.append(kv_eq)

            kv_col = FieldDetector.extract_key_values(p, delimiter=" ", kv_delimiter=":")
            kv_colon_counts.append(len(kv_col))
            sample_kv_colon_maps.append(kv_col)

        avg_eq = sum(kv_equal_counts) / len(kv_equal_counts)
        avg_col = sum(kv_colon_counts) / len(kv_colon_counts)

        # Require at least 2 distinct key-value pairs on average
        if avg_eq >= 2.0 and avg_eq >= avg_col:
            detected_fmt = "syslog_kv" if has_syslog_header else "key_value"
            conf = min(0.95, 0.70 + (0.05 * min(5, len(clean_samples))))
            field_counter: Counter = Counter()
            sample_vals: Dict[str, str] = {}

            for m in sample_kv_equal_maps:
                for k, v in m.items():
                    field_counter[k] += 1
                    if k not in sample_vals:
                        sample_vals[k] = v

            candidates = []
            for k, count in field_counter.items():
                val = sample_vals.get(k)
                inf_type = FieldDetector.infer_type(k, val)
                candidates.append(
                    FieldCandidate(
                        source_field=k,
                        sample_value=val,
                        inferred_type=inf_type,
                        occurrence_rate=round(count / len(clean_samples), 2)
                    )
                )

            return detected_fmt, conf, " ", "=", has_syslog_header, candidates, warnings

        if avg_col >= 2.0:
            detected_fmt = "syslog_kv" if has_syslog_header else "key_value"
            conf = min(0.92, 0.65 + (0.05 * min(5, len(clean_samples))))
            field_counter = Counter()
            sample_vals = {}

            for m in sample_kv_colon_maps:
                for k, v in m.items():
                    field_counter[k] += 1
                    if k not in sample_vals:
                        sample_vals[k] = v

            candidates = []
            for k, count in field_counter.items():
                val = sample_vals.get(k)
                inf_type = FieldDetector.infer_type(k, val)
                candidates.append(
                    FieldCandidate(
                        source_field=k,
                        sample_value=val,
                        inferred_type=inf_type,
                        occurrence_rate=round(count / len(clean_samples), 2)
                    )
                )

            return detected_fmt, conf, " ", ":", has_syslog_header, candidates, warnings

        # 4. Check for Delimited Lines (pipe, comma, tab, semicolon)
        delimiters = ["|", ",", "\t", ";"]
        best_delim = None
        best_token_count = 0
        best_consistency = 0.0

        for d in delimiters:
            counts = [len(p.split(d)) for p in payloads_to_analyze]
            if counts and counts[0] >= 3:
                # Check consistency
                if all(c == counts[0] for c in counts):
                    best_delim = d
                    best_token_count = counts[0]
                    best_consistency = 1.0
                    break

        if best_delim and best_consistency == 1.0:
            conf = min(0.90, 0.65 + (0.05 * min(5, len(clean_samples))))
            # Generate column candidate field names
            sample_tokens = payloads_to_analyze[0].split(best_delim)
            candidates = []
            for idx, token in enumerate(sample_tokens):
                fn = f"column_{idx + 1}"
                inf_type = FieldDetector.infer_type(fn, token)
                candidates.append(
                    FieldCandidate(
                        source_field=fn,
                        sample_value=token.strip(),
                        inferred_type=inf_type,
                        occurrence_rate=1.0
                    )
                )
            return "delimited", conf, best_delim, "=", has_syslog_header, candidates, warnings

        # 5. Unknown or Unstructured
        warnings.append("Unable to infer structured delimiter or key-value pattern across provided samples.")
        return "unknown", 0.30, " ", "=", has_syslog_header, [], warnings
