import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy import func, desc
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.normalized_event import NormalizedEvent
from app.models.anomaly_result import AnomalyResult
from app.services.anomaly.models import (
    TrainingResult,
    ScanResult,
    AnomalyScoreItem,
    AnomalyStatistics
)
from app.services.anomaly.feature_engineering import FeatureExtractor
from app.services.anomaly.detector import IsolationForestDetector


class AnomalyService:
    """
    Coordinates offline anomaly detection baseline training, event scoring,
    and persistent traceability linking.
    """

    def __init__(self):
        self.detector = IsolationForestDetector()

    def train_baseline(self, db: Session, limit: int = 10000) -> TrainingResult:
        """
        Trains the local Isolation Forest detector using historical normalized events.
        """
        start_perf = time.perf_counter()

        events = (
            db.query(NormalizedEvent)
            .order_by(desc(NormalizedEvent.timestamp))
            .limit(limit)
            .all()
        )

        if len(events) < settings.ULPF_ANOMALY_MIN_TRAIN_RECORDS:
            raise ValueError(
                f"Insufficient training data: {len(events)} events found in database, "
                f"minimum of {settings.ULPF_ANOMALY_MIN_TRAIN_RECORDS} required to establish baseline."
            )

        X, _ = FeatureExtractor.extract_features(events)
        self.detector.fit(X)

        duration = round(time.perf_counter() - start_perf, 4)

        return TrainingResult(
            model_name=self.detector.MODEL_NAME,
            model_version=self.detector.MODEL_VERSION,
            records_trained=len(events),
            duration_seconds=duration,
            status="trained",
            parameters={
                "contamination": self.detector.contamination,
                "random_state": self.detector.random_state,
                "features": FeatureExtractor.FEATURE_NAMES
            }
        )

    def scan_events(
        self,
        db: Session,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 5000,
        persist: bool = True
    ) -> ScanResult:
        """
        Extracts features from un-scored or selected normalized events, computes
        anomaly scores, and optionally persists AnomalyResult records.
        """
        start_perf = time.perf_counter()

        # Ensure model is trained
        if not self.detector.is_trained:
            self.train_baseline(db, limit=limit)

        query = db.query(NormalizedEvent)
        if start_time:
            query = query.filter(NormalizedEvent.timestamp >= start_time)
        if end_time:
            query = query.filter(NormalizedEvent.timestamp <= end_time)

        events = query.order_by(desc(NormalizedEvent.timestamp)).limit(limit).all()

        if not events:
            return ScanResult(
                records_scanned=0,
                anomalies_detected=0,
                normal_detected=0,
                duration_seconds=round(time.perf_counter() - start_perf, 4),
                status="empty"
            )

        X, summaries = FeatureExtractor.extract_features(events)
        scores, is_anomalies, explanations = self.detector.predict(X, summaries)

        anomaly_count = int(is_anomalies.sum())
        normal_count = len(events) - anomaly_count

        if persist:
            now_dt = datetime.now(timezone.utc)
            for idx, e in enumerate(events):
                # Delete existing anomaly result for this event if re-scanning
                db.query(AnomalyResult).filter(AnomalyResult.event_id == e.event_id).delete()

                res_model = AnomalyResult(
                    event_id=e.event_id,
                    model_name=self.detector.MODEL_NAME,
                    model_version=self.detector.MODEL_VERSION,
                    anomaly_score=float(scores[idx]),
                    is_anomaly=bool(is_anomalies[idx]),
                    feature_summary=summaries[idx],
                    explanation=explanations[idx],
                    detected_at=now_dt
                )
                db.add(res_model)

            db.commit()

        duration = round(time.perf_counter() - start_perf, 4)

        return ScanResult(
            records_scanned=len(events),
            anomalies_detected=anomaly_count,
            normal_detected=normal_count,
            duration_seconds=duration,
            status="completed"
        )

    def get_results(
        self,
        db: Session,
        is_anomaly_only: bool = True,
        limit: int = 50,
        offset: int = 0
    ) -> List[AnomalyScoreItem]:
        """Queries persisted anomaly detection records."""
        query = db.query(AnomalyResult)
        if is_anomaly_only:
            query = query.filter(AnomalyResult.is_anomaly == True)

        rows = query.order_by(desc(AnomalyResult.detected_at)).offset(offset).limit(limit).all()

        return [
            AnomalyScoreItem(
                id=r.id,
                event_id=r.event_id,
                model_name=r.model_name,
                model_version=r.model_version,
                anomaly_score=r.anomaly_score,
                is_anomaly=r.is_anomaly,
                detected_at=r.detected_at,
                feature_summary=r.feature_summary,
                explanation=r.explanation
            )
            for r in rows
        ]

    def get_result_by_event_id(self, db: Session, event_id: str) -> Optional[AnomalyScoreItem]:
        """Retrieves anomaly evaluation for a specific event."""
        r = db.query(AnomalyResult).filter(AnomalyResult.event_id == event_id).first()
        if not r:
            return None
        return AnomalyScoreItem(
            id=r.id,
            event_id=r.event_id,
            model_name=r.model_name,
            model_version=r.model_version,
            anomaly_score=r.anomaly_score,
            is_anomaly=r.is_anomaly,
            detected_at=r.detected_at,
            feature_summary=r.feature_summary,
            explanation=r.explanation
        )

    def get_statistics(self, db: Session) -> AnomalyStatistics:
        """Returns aggregated telemetry on scanned events and anomaly frequency."""
        total_scanned = db.query(func.count(AnomalyResult.id)).scalar() or 0
        total_anomalies = (
            db.query(func.count(AnomalyResult.id))
            .filter(AnomalyResult.is_anomaly == True)
            .scalar() or 0
        )
        rate = round((total_anomalies / total_scanned * 100), 2) if total_scanned > 0 else 0.0

        return AnomalyStatistics(
            total_scanned=total_scanned,
            total_anomalies=total_anomalies,
            anomaly_rate=rate,
            model_name=self.detector.MODEL_NAME,
            model_version=self.detector.MODEL_VERSION,
            is_model_trained=self.detector.is_trained
        )


anomaly_service = AnomalyService()
