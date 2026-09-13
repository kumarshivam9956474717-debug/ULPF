import re
from typing import List, Optional, Tuple
from app.services.normalization.mapper import FIELD_ALIASES
from app.services.onboarding.models import FieldCandidate, SuggestedMapping, ConfidenceLevel
from app.services.onboarding.confidence import ConfidenceScorer

# Canonical target fields in the Universal Event Schema (UES)
CANONICAL_UES_FIELDS = {
    "source_ip": "ip",
    "destination_ip": "ip",
    "source_port": "port",
    "destination_port": "port",
    "protocol": "protocol",
    "timestamp": "timestamp",
    "action": "action",
    "outcome": "outcome",
    "severity": "severity",
    "event_type": "string",
    "category": "string",
    "subcategory": "string",
    "username": "username",
    "user_id": "string",
    "authentication_method": "string",
    "hostname": "string",
    "device_id": "string",
    "vendor": "string",
    "product": "string",
    "threat_name": "string",
    "threat_id": "string",
    "signature_id": "string",
    "rule_id": "string",
    "interface": "string",
    "direction": "string",
    "zone": "string",
    "message": "string",
}

CAMEL_TO_SNAKE = re.compile(r"(?<!^)(?=[A-Z])")


def to_snake_case(name: str) -> str:
    """Converts camelCase or PascalCase to snake_case."""
    return CAMEL_TO_SNAKE.sub("_", name).lower()


class FieldMapper:
    """
    Evaluates candidate field tokens against the Universal Event Schema
    using alias dictionaries, normalized keys, and data-type hints.
    """

    @classmethod
    def suggest_mappings(cls, candidates: List[FieldCandidate]) -> List[SuggestedMapping]:
        """
        Generates deterministic mapping recommendations for a list of candidate fields.
        """
        suggestions: List[SuggestedMapping] = []
        assigned_targets = set()

        for cand in candidates:
            mapping = cls.map_candidate(cand, assigned_targets)
            if not mapping.is_custom:
                assigned_targets.add(mapping.target_field)
            suggestions.append(mapping)

        return suggestions

    @classmethod
    def map_candidate(cls, cand: FieldCandidate, assigned_targets: Optional[set] = None) -> SuggestedMapping:
        if assigned_targets is None:
            assigned_targets = set()

        raw_key = cand.source_field.strip()
        clean_key = raw_key.lower().replace("-", "_").replace(" ", "_")
        snake_key = to_snake_case(raw_key).replace("-", "_").replace(" ", "_")

        has_exact = False
        has_normalized = False
        has_datatype = False
        has_pattern = False
        target_field = ""
        method = "custom"

        # 1. Direct match in FIELD_ALIASES
        if clean_key in FIELD_ALIASES:
            target_field = FIELD_ALIASES[clean_key]
            has_exact = True
            method = "exact_alias"
        elif snake_key in FIELD_ALIASES:
            target_field = FIELD_ALIASES[snake_key]
            has_normalized = True
            method = "normalized_alias"
        else:
            # 2. Heuristic normalization (strip prefixes like c_, s_, src_, dst_)
            stripped = re.sub(r"^(c_|s_|src_|dst_|client_|server_)", "", snake_key)
            if stripped in FIELD_ALIASES:
                target_field = FIELD_ALIASES[stripped]
                # If original key had dst or server prefix, ensure target reflects destination
                if any(p in snake_key for p in ("dst", "destination", "server", "cs")):
                    if target_field == "source_ip":
                        target_field = "destination_ip"
                    elif target_field == "source_port":
                        target_field = "destination_port"
                has_normalized = True
                method = "normalized_alias"
            elif snake_key in CANONICAL_UES_FIELDS:
                target_field = snake_key
                has_exact = True
                method = "exact_alias"

        # 3. Data-type compatibility check & disambiguation
        if target_field:
            expected_type = CANONICAL_UES_FIELDS.get(target_field, "string")
            if cand.inferred_type == expected_type:
                has_datatype = True
            elif expected_type == "string":
                has_datatype = True
            has_pattern = True
        else:
            # 4. Infer target field purely from strong data types if name didn't match
            if cand.inferred_type == "ip":
                if any(k in snake_key for k in ("dst", "destination", "server", "to")):
                    target_field = "destination_ip"
                elif any(k in snake_key for k in ("src", "source", "client", "from")):
                    target_field = "source_ip"
                elif "source_ip" in assigned_targets and "destination_ip" not in assigned_targets:
                    target_field = "destination_ip"
                elif "source_ip" not in assigned_targets:
                    target_field = "source_ip"
                else:
                    target_field = "destination_ip"
                has_datatype = True
                method = "datatype_inference"
            elif cand.inferred_type == "port":
                if any(k in snake_key for k in ("dst", "destination", "server", "to", "dpt")):
                    target_field = "destination_port"
                elif any(k in snake_key for k in ("src", "source", "client", "from", "spt")):
                    target_field = "source_port"
                elif "destination_port" not in assigned_targets:
                    target_field = "destination_port"
                elif "source_port" not in assigned_targets:
                    target_field = "source_port"
                else:
                    target_field = "destination_port"
                has_datatype = True
                method = "datatype_inference"
            elif cand.inferred_type == "timestamp":
                target_field = "timestamp"
                has_datatype = True
                method = "datatype_inference"
            elif cand.inferred_type == "protocol":
                target_field = "protocol"
                has_datatype = True
                method = "datatype_inference"
            elif cand.inferred_type == "action":
                target_field = "action"
                has_datatype = True
                method = "datatype_inference"
            elif cand.inferred_type == "severity":
                target_field = "severity"
                has_datatype = True
                method = "datatype_inference"

        # 5. Prevent duplicate canonical assignments: if target already assigned, mark as custom
        if target_field and target_field in assigned_targets:
            target_field = f"custom_{clean_key}"
            return SuggestedMapping(
                source_field=raw_key,
                target_field=target_field,
                confidence=0.35,
                confidence_level=ConfidenceLevel.LOW,
                method="custom_field",
                is_custom=True,
                transform="none"
            )

        # 5. Fallback: If still unmapped, mark as custom field preserving raw key
        if not target_field:
            return SuggestedMapping(
                source_field=raw_key,
                target_field=f"custom_{clean_key}",
                confidence=0.30,
                confidence_level=ConfidenceLevel.LOW,
                method="custom_field",
                is_custom=True,
                transform="none"
            )

        # 6. Calculate deterministic score
        score, level = ConfidenceScorer.calculate_confidence(
            has_exact_alias=has_exact,
            has_normalized_alias=has_normalized,
            has_datatype_match=has_datatype,
            has_pattern_match=has_pattern,
            occurrence_rate=cand.occurrence_rate
        )

        return SuggestedMapping(
            source_field=raw_key,
            target_field=target_field,
            confidence=score,
            confidence_level=level,
            method=method,
            is_custom=False,
            transform="none"
        )
