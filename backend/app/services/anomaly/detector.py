from typing import Any, Dict, List, Tuple
import numpy as np
from sklearn.ensemble import IsolationForest

from app.core.config import settings


class IsolationForestDetector:
    """
    Offline unsupervised anomaly detection baseline using Scikit-learn IsolationForest.
    Generates deterministic anomaly scores and structured, explainable indicator signals.
    """

    MODEL_NAME = "isolation_forest_baseline"
    MODEL_VERSION = "1.0.0"

    def __init__(
        self,
        contamination: float = settings.ULPF_ANOMALY_CONTAMINATION,
        random_state: int = settings.ULPF_ANOMALY_RANDOM_STATE
    ):
        self.contamination = contamination
        self.random_state = random_state
        self.model: IsolationForest = IsolationForest(
            contamination=self.contamination,
            random_state=self.random_state,
            n_estimators=100,
            n_jobs=1
        )
        self.is_trained: bool = False
        self.training_records_count: int = 0

    def fit(self, X: np.ndarray) -> None:
        """Trains the Isolation Forest model on feature matrix X."""
        if X.shape[0] < settings.ULPF_ANOMALY_MIN_TRAIN_RECORDS:
            raise ValueError(
                f"Insufficient training records: {X.shape[0]} records provided, "
                f"minimum required is {settings.ULPF_ANOMALY_MIN_TRAIN_RECORDS}."
            )
        self.model.fit(X)
        self.is_trained = True
        self.training_records_count = X.shape[0]

    def predict(
        self,
        X: np.ndarray,
        feature_summaries: List[Dict[str, Any]]
    ) -> Tuple[np.ndarray, np.ndarray, List[Dict[str, Any]]]:
        """
        Calculates anomaly scores, binary flags, and deterministic explanations.

        Returns:
            Tuple[scores: np.ndarray, is_anomalies: np.ndarray, explanations: List[Dict]]
        """
        if not self.is_trained:
            raise RuntimeError("Anomaly detector must be trained before predicting.")

        if X.shape[0] == 0:
            return np.array([]), np.array([]), []

        # Decision function: lower values mean more abnormal
        raw_scores = self.model.decision_function(X)
        # Predictions: -1 for anomaly, 1 for inlier
        raw_preds = self.model.predict(X)

        # Normalize score into [0, 1] range where 1.0 is highest anomaly probability
        # In IsolationForest, decision_function typically lies in [-0.5, 0.5]
        norm_scores = 0.5 - (raw_scores * 0.5)
        norm_scores = np.clip(norm_scores, 0.0, 1.0)

        is_anomalies = (raw_preds == -1)

        explanations = []
        for idx in range(X.shape[0]):
            summary = feature_summaries[idx]
            reasons = []

            # 1. Rare / unusual destination port
            if not summary.get("is_well_known_port") and summary.get("dst_port_freq_ratio", 1.0) < 0.08:
                reasons.append(f"Rare destination port ({summary.get('destination_port')})")

            # 2. Unusual source frequency
            if summary.get("src_freq_ratio", 0.0) > 0.35:
                reasons.append("Unusually high source connection frequency (potential flood/burst)")
            elif summary.get("src_freq_ratio", 1.0) < 0.02:
                reasons.append("Infrequent source communication pattern")

            # 3. Security severity
            sev = (summary.get("severity") or "").lower()
            if sev in ("high", "critical"):
                reasons.append(f"High-severity security indicator ({sev})")

            # 4. Perimeter block/drop action
            act = (summary.get("action") or "").lower()
            if act in ("block", "drop", "deny", "reject"):
                reasons.append("Perimeter firewall block or drop event")

            if len(reasons) >= 2:
                reasons.insert(0, "Multiple anomaly indicators detected")

            if not reasons and is_anomalies[idx]:
                reasons.append("Multivariate feature space isolation outlier")

            explanations.append({"reasons": reasons})

        return norm_scores, is_anomalies, explanations
