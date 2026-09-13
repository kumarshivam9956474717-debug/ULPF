from typing import Any, Dict, List, Optional
from collections import Counter
from datetime import datetime, timezone
import uuid

from app.services.onboarding.models import MappingRule, MappingValidationResult
from app.services.onboarding.field_detector import FieldDetector
from app.services.normalization.mapper import (
    normalize_action,
    normalize_outcome,
    normalize_severity,
    normalize_port,
    normalize_timestamp
)
from app.schemas.universal_event import UniversalEvent
from app.services.validation.service import ValidationService


class MappingValidator:
    """
    Validates proposed field mapping rules and simulates normalization
    against sample log records without mutating persistent storage.
    """

    @staticmethod
    def validate_rules(mappings: List[MappingRule]) -> tuple[List[str], List[str]]:
        """
        Validates mapping definitions for conflicting targets or missing critical attributes.
        Returns: (errors, warnings)
        """
        errors = []
        warnings = []

        if not mappings:
            errors.append("At least one field mapping rule is required.")
            return errors, warnings

        target_counts = Counter()
        for rule in mappings:
            if not rule.source_field.strip():
                errors.append("Empty source field name detected.")
            if not rule.is_custom:
                target_counts[rule.target_field] += 1

        for target, count in target_counts.items():
            if count > 1:
                errors.append(f"Duplicate canonical target field assignment: '{target}' mapped {count} times.")

        # Check for core perimeter visibility recommendations
        canonical_targets = {r.target_field for r in mappings if not r.is_custom}
        if "timestamp" not in canonical_targets:
            warnings.append("No 'timestamp' mapping configured; logs will default to ingestion time.")
        if "source_ip" not in canonical_targets and "destination_ip" not in canonical_targets:
            warnings.append("No IP address fields mapped; network perimeter visibility will be degraded.")

        return errors, warnings

    @staticmethod
    def simulate_mapping(
        sample_logs: List[str],
        source_format: str,
        delimiter: Optional[str],
        kv_delimiter: Optional[str],
        mappings: List[MappingRule]
    ) -> MappingValidationResult:
        """
        Simulates parsing and normalization on sample logs.
        """
        errors, warnings = MappingValidator.validate_rules(mappings)
        if errors:
            return MappingValidationResult(
                is_valid=False,
                records_tested=len(sample_logs),
                records_passed=0,
                records_failed=len(sample_logs),
                errors=errors,
                warnings=warnings
            )

        delim = delimiter or " "
        kv_delim = kv_delimiter or "="

        # Build mapping lookup
        canonical_map = {m.source_field: m.target_field for m in mappings if not m.is_custom}
        custom_set = {m.source_field for m in mappings if m.is_custom}

        records_passed = 0
        records_failed = 0
        sample_preview = None
        all_mapped_fields = set()
        all_unmapped_fields = set()
        all_custom_fields = set()

        for idx, log in enumerate(sample_logs):
            clean = log.strip()
            if not clean:
                continue

            # Extract fields based on format
            extracted: Dict[str, Any] = {}
            if source_format in ("key_value", "syslog_kv"):
                extracted = FieldDetector.extract_key_values(clean, delimiter=delim, kv_delimiter=kv_delim)
            elif source_format == "delimited":
                tokens = FieldDetector.extract_delimited_values(clean, delimiter=delim)
                extracted = {f"column_{i+1}": val for i, val in enumerate(tokens)}
            elif source_format == "json":
                import json
                try:
                    data = json.loads(clean)
                    if isinstance(data, dict):
                        extracted = {str(k): str(v) for k, v in data.items()}
                except Exception:
                    pass

            if not extracted:
                records_failed += 1
                errors.append(f"Record {idx + 1}: Unable to extract fields using format '{source_format}'.")
                continue

            # Map to canonical UES attributes & custom fields
            normalized_dict: Dict[str, Any] = {
                "event_id": f"SIM-{uuid.uuid4().hex[:8].upper()}",
                "schema_version": "1.0.0",
                "raw_event_id": "SIM-RAW-001",
                "normalization_version": "1.0.0",
                "raw_event": clean,
                "custom_fields": {},
                "tags": ["onboarding_simulation"]
            }

            for src_k, src_v in extracted.items():
                if src_k in canonical_map:
                    target_k = canonical_map[src_k]
                    all_mapped_fields.add(target_k)

                    # Apply type normalizations matching UES
                    if target_k == "action":
                        norm_act = normalize_action(src_v)
                        normalized_dict[target_k] = norm_act.value if norm_act else None
                    elif target_k == "outcome":
                        norm_out = normalize_outcome(src_v)
                        normalized_dict[target_k] = norm_out.value if norm_out else None
                    elif target_k == "severity":
                        norm_sev = normalize_severity(src_v)
                        normalized_dict[target_k] = norm_sev.value if norm_sev else "unknown"
                    elif target_k in ("source_port", "destination_port"):
                        normalized_dict[target_k] = normalize_port(src_v)
                    elif target_k == "timestamp":
                        normalized_dict[target_k] = normalize_timestamp(src_v)
                    else:
                        normalized_dict[target_k] = src_v
                elif src_k in custom_set or src_k.startswith("custom_"):
                    all_custom_fields.add(src_k)
                    normalized_dict["custom_fields"][src_k] = src_v
                else:
                    all_unmapped_fields.add(src_k)
                    # Lossless guarantee: unmapped fields preserved in custom_fields
                    normalized_dict["custom_fields"][src_k] = src_v

            # Fallback timestamp if missing
            if not normalized_dict.get("timestamp"):
                normalized_dict["timestamp"] = datetime.now(timezone.utc)

            # Validate against UniversalEvent schema
            try:
                ue = UniversalEvent(**normalized_dict)
                val_rep = ValidationService.validate_event(ue)
                if val_rep.is_valid:
                    records_passed += 1
                else:
                    records_failed += 1
                    if val_rep.errors:
                        errors.extend([f"Record {idx + 1}: {e}" for e in val_rep.errors])
                    if val_rep.warnings:
                        warnings.extend([f"Record {idx + 1}: {w}" for w in val_rep.warnings])

                if sample_preview is None:
                    sample_preview = ue.model_dump(mode="json")
            except Exception as exc:
                records_failed += 1
                errors.append(f"Record {idx + 1} validation failed: {str(exc)}")

        total_tested = records_passed + records_failed
        is_valid = (records_failed == 0 and total_tested > 0)

        return MappingValidationResult(
            is_valid=is_valid,
            records_tested=total_tested,
            records_passed=records_passed,
            records_failed=records_failed,
            mapped_fields=sorted(list(all_mapped_fields)),
            unmapped_fields=sorted(list(all_unmapped_fields)),
            custom_fields=sorted(list(all_custom_fields)),
            sample_normalized_preview=sample_preview,
            warnings=warnings,
            errors=errors
        )
