from app.services.onboarding.models import ConfidenceLevel


class ConfidenceScorer:
    """
    Computes transparent, deterministic heuristic confidence scores [0.0, 1.0]
    for suggested field mappings.
    """

    # Scoring weights for mapping evidence
    WEIGHT_EXACT_ALIAS = 0.40
    WEIGHT_NORMALIZED_ALIAS = 0.25
    WEIGHT_DATATYPE_MATCH = 0.15
    WEIGHT_PATTERN_MATCH = 0.10
    WEIGHT_STRUCTURAL_CONSISTENCY = 0.10

    # Categorization thresholds
    THRESHOLD_HIGH = 0.85
    THRESHOLD_MEDIUM = 0.60

    @classmethod
    def calculate_confidence(
        cls,
        has_exact_alias: bool,
        has_normalized_alias: bool,
        has_datatype_match: bool,
        has_pattern_match: bool,
        occurrence_rate: float = 1.0
    ) -> tuple[float, ConfidenceLevel]:
        """
        Calculates a bounded heuristic score and categorization level.
        """
        score = 0.0

        if has_exact_alias:
            score += cls.WEIGHT_EXACT_ALIAS + cls.WEIGHT_NORMALIZED_ALIAS
        elif has_normalized_alias:
            score += cls.WEIGHT_NORMALIZED_ALIAS

        if has_datatype_match:
            score += cls.WEIGHT_DATATYPE_MATCH

        if has_pattern_match:
            score += cls.WEIGHT_PATTERN_MATCH

        # Structural consistency factor based on sample presence
        score += cls.WEIGHT_STRUCTURAL_CONSISTENCY * min(1.0, max(0.0, occurrence_rate))

        # Clamp between 0.0 and 1.0
        clamped = max(0.0, min(1.0, round(score, 2)))

        if clamped >= cls.THRESHOLD_HIGH:
            level = ConfidenceLevel.HIGH
        elif clamped >= cls.THRESHOLD_MEDIUM:
            level = ConfidenceLevel.MEDIUM
        else:
            level = ConfidenceLevel.LOW

        return clamped, level
