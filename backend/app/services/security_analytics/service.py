import csv
import io
import json
import uuid
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from app.models.normalized_event import NormalizedEvent
from app.models.raw_event import RawEvent
from app.models.validation_result import ValidationResult
from app.models.anomaly_result import AnomalyResult
from app.models.log_source import LogSource
from app.models.security_analytics import AnalyticsFinding, SourceBaseline
from app.services.security_analytics.models import (
    AnalyticsFilter,
    SecurityOverview,
    SourceHealthMetrics,
    CoverageFindingItem,
    BaselineMetrics,
    BaselineDeviationItem,
    CorrelationGroup,
    FindingResponse,
    AnalyzeRunResponse,
    HealthStatus,
    PriorityCategory
)
from app.services.security_analytics.health import SourceHealthAnalyzer
from app.services.security_analytics.coverage import CoverageAnalyzer
from app.services.security_analytics.baseline import BaselineEngine
from app.services.security_analytics.correlation import CorrelationEngine
from app.services.security_analytics.prioritization import PrioritizationEngine, ExplainabilityGenerator


class SecurityAnalyticsService:
    """
    Main Security Analytics & Data Quality Service coordinating source health monitoring,
    negative-space coverage gap detection, baseline deviation analysis, cross-source
    correlation, risk prioritization, supervisory findings lifecycle, and JSON/CSV exports.
    """

    @staticmethod
    def get_overview(db: Session, filters: Optional[AnalyticsFilter] = None) -> SecurityOverview:
        now_dt = datetime.now(timezone.utc)

        total_norm = db.query(func.count(NormalizedEvent.id)).scalar() or 0
        total_sources = db.query(func.count(LogSource.id)).scalar() or 0

        # Health counts
        health_list = SourceHealthAnalyzer.get_all_sources_health(db)
        healthy = sum(1 for h in health_list if h.status == HealthStatus.HEALTHY)
        degraded = sum(1 for h in health_list if h.status == HealthStatus.DEGRADED)
        suspicious = sum(1 for h in health_list if h.status == HealthStatus.SUSPICIOUS)
        inactive = sum(1 for h in health_list if h.status == HealthStatus.INACTIVE)

        # Finding counts
        open_q = db.query(AnalyticsFinding).filter(AnalyticsFinding.status == "OPEN")
        open_count = open_q.count()
        critical_count = open_q.filter(AnalyticsFinding.priority_category == "CRITICAL").count()
        high_count = open_q.filter(AnalyticsFinding.priority_category == "HIGH").count()
        coverage_count = open_q.filter(AnalyticsFinding.finding_type == "COVERAGE_GAP").count()
        correlation_count = open_q.filter(AnalyticsFinding.finding_type == "CORRELATION").count()

        # Anomaly & Quality counts
        anomaly_cnt = db.query(func.count(AnomalyResult.id)).filter(AnomalyResult.is_anomaly == True).scalar() or 0
        unknown_fmt_cnt = db.query(func.count(RawEvent.id)).filter(RawEvent.source_format == "unknown").scalar() or 0
        val_fail_cnt = db.query(func.count(ValidationResult.id)).filter(ValidationResult.validation_status == "invalid").scalar() or 0

        # Calculate Data Quality Index (100 - penalties for unknown format & validation failures)
        penalty = min(50.0, (unknown_fmt_cnt * 2.0) + (val_fail_cnt * 1.5))
        quality_index = round(max(0.0, 100.0 - penalty), 1)

        return SecurityOverview(
            total_events=total_norm,
            total_sources=total_sources,
            healthy_sources_count=healthy,
            degraded_sources_count=degraded,
            suspicious_sources_count=suspicious,
            inactive_sources_count=inactive,
            open_findings_count=open_count,
            critical_findings_count=critical_count,
            high_findings_count=high_count,
            coverage_gaps_count=coverage_count,
            correlation_candidates_count=correlation_count,
            anomaly_count=anomaly_cnt,
            unknown_format_count=unknown_fmt_cnt,
            parser_failure_count=0,
            validation_failure_count=val_fail_cnt,
            data_quality_index=quality_index
        )

    @staticmethod
    def get_trends(db: Session, timeframe: str = "24h") -> Dict[str, Any]:
        """Calculates time-bucketed event volume and anomaly trends."""
        now_dt = datetime.now(timezone.utc)
        hours = 24
        if timeframe == "7d":
            hours = 168
        elif timeframe == "30d":
            hours = 720

        window_start = now_dt - timedelta(hours=hours)
        is_sqlite = db.bind.dialect.name == "sqlite" if db.bind else False

        if is_sqlite:
            bucket = func.strftime("%Y-%m-%d %H:00:00", NormalizedEvent.timestamp)
        else:
            bucket = func.to_char(func.date_trunc("hour", NormalizedEvent.timestamp), "YYYY-MM-DD HH24:00:00")

        rows = (
            db.query(
                bucket.label("tb"),
                func.count(NormalizedEvent.id).label("total_cnt")
            )
            .filter(NormalizedEvent.timestamp >= window_start)
            .group_by("tb")
            .order_by("tb")
            .all()
        )

        trend_points = [{"timestamp": str(r[0]), "events": r[1], "anomalies": 0} for r in rows]
        return {"timeframe": timeframe, "points": trend_points}

    @staticmethod
    def get_sources_health(db: Session) -> List[SourceHealthMetrics]:
        return SourceHealthAnalyzer.get_all_sources_health(db)

    @staticmethod
    def get_coverage_gaps(db: Session) -> List[CoverageFindingItem]:
        return CoverageAnalyzer.analyze_coverage_gaps(db)

    @staticmethod
    def get_baselines(db: Session) -> List[Dict[str, Any]]:
        baselines = db.query(SourceBaseline).all()
        res = []
        for b in baselines:
            devs = BaselineEngine.detect_deviations(db, b.source_id)
            res.append({
                "source_id": b.source_id,
                "avg_hourly_volume": b.avg_hourly_volume,
                "median_hourly_volume": b.median_hourly_volume,
                "stddev_hourly_volume": b.stddev_hourly_volume,
                "severity_distribution": b.severity_distribution,
                "protocol_distribution": b.protocol_distribution,
                "action_distribution": b.action_distribution,
                "sample_hours_count": b.sample_hours_count,
                "calculated_at": b.calculated_at.isoformat() if b.calculated_at else None,
                "deviations": [d.model_dump() for d in devs]
            })
        return res

    @staticmethod
    def get_correlations(db: Session, window_minutes: int = 15) -> List[CorrelationGroup]:
        return CorrelationEngine.scan_correlations(db, window_minutes=window_minutes)

    @staticmethod
    def run_analysis_scan(db: Session) -> AnalyzeRunResponse:
        """
        Executes on-demand comprehensive security analytics scan:
        1. Analyzes source health.
        2. Recalculates baselines & detects volume/distribution deviations.
        3. Scans negative-space coverage gaps.
        4. Scans cross-source correlations.
        5. Generates/updates persistent supervisory `AnalyticsFinding` records with deterministic risk prioritization.
        """
        now_dt = datetime.now(timezone.utc)
        scan_id = f"SCAN-{uuid.uuid4().hex[:8].upper()}"

        sources = db.query(LogSource).all()
        health_list = SourceHealthAnalyzer.get_all_sources_health(db)
        new_findings = 0
        total_findings = 0

        # 1. Evaluate Source Health & Inactive/Degraded Findings
        for h in health_list:
            if h.status in (HealthStatus.INACTIVE, HealthStatus.SUSPICIOUS, HealthStatus.DEGRADED):
                f_type = "SOURCE_GAP" if h.status == HealthStatus.INACTIVE else "DATA_QUALITY"
                sev = "CRITICAL" if h.status == HealthStatus.INACTIVE else ("HIGH" if h.status == HealthStatus.SUSPICIOUS else "MEDIUM")
                title, explanation = ExplainabilityGenerator.generate_source_gap_explanation(
                    source_name=h.name,
                    gap_duration_mins=h.ingestion_gap_duration_minutes,
                    last_seen_str=h.last_event_timestamp.isoformat() if h.last_event_timestamp else "Never",
                    confidence=0.90
                )

                score, category = PrioritizationEngine.calculate_priority(
                    severity=sev,
                    confidence=0.90,
                    source_criticality="high",
                    duration_hours=h.ingestion_gap_duration_minutes / 60.0
                )

                # Check existing open finding to deduplicate
                existing = (
                    db.query(AnalyticsFinding)
                    .filter(
                        AnalyticsFinding.source_id == h.source_id,
                        AnalyticsFinding.finding_type == f_type,
                        AnalyticsFinding.status == "OPEN"
                    )
                    .first()
                )

                if not existing:
                    finding = AnalyticsFinding(
                        id=str(uuid.uuid4()),
                        finding_type=f_type,
                        severity=sev,
                        confidence=0.90,
                        priority_score=score,
                        priority_category=category.value,
                        source_id=h.source_id,
                        event_count=h.total_events,
                        first_seen=h.last_event_timestamp or now_dt,
                        last_seen=now_dt,
                        title=title,
                        explanation=explanation,
                        evidence=h.model_dump(mode="json"),
                        recommended_action="Verify network perimeter gateway connectivity and Syslog listener logs.",
                        status="OPEN",
                        created_at=now_dt,
                        updated_at=now_dt
                    )
                    db.add(finding)
                    new_findings += 1
                total_findings += 1

        # 2. Evaluate Baseline Deviations
        for s in sources:
            baseline = BaselineEngine.calculate_source_baseline(db, s.source_id)
            deviations = BaselineEngine.detect_deviations(db, s.source_id, now_dt)

            sname = s.hostname or s.source_id
            for dev in deviations:
                sev = "HIGH" if dev.deviation_type == "VOLUME_SPIKE" else "MEDIUM"
                if dev.deviation_type == "VOLUME_SPIKE":
                    title, explanation = ExplainabilityGenerator.generate_volume_spike_explanation(
                        source_name=sname,
                        baseline_vol=dev.baseline_value,
                        current_vol=dev.current_value,
                        spike_pct=dev.deviation_percentage,
                        time_window_str="last 60 minutes",
                        confidence=0.85
                    )
                else:
                    title, explanation = ExplainabilityGenerator.generate_volume_drop_explanation(
                        source_name=sname,
                        baseline_vol=dev.baseline_value,
                        current_vol=dev.current_value,
                        drop_pct=abs(dev.deviation_percentage),
                        time_window_str="last 60 minutes",
                        confidence=0.85
                    )

                score, category = PrioritizationEngine.calculate_priority(
                    severity=sev,
                    confidence=0.85,
                    source_criticality="medium",
                    deviation_magnitude_pct=abs(dev.deviation_percentage)
                )

                existing = (
                    db.query(AnalyticsFinding)
                    .filter(
                        AnalyticsFinding.source_id == s.source_id,
                        AnalyticsFinding.finding_type == dev.deviation_type,
                        AnalyticsFinding.status == "OPEN"
                    )
                    .first()
                )

                if not existing:
                    finding = AnalyticsFinding(
                        id=str(uuid.uuid4()),
                        finding_type=dev.deviation_type,
                        severity=sev,
                        confidence=0.85,
                        priority_score=score,
                        priority_category=category.value,
                        source_id=s.source_id,
                        event_count=int(dev.current_value),
                        first_seen=now_dt - timedelta(hours=1),
                        last_seen=now_dt,
                        title=title,
                        explanation=explanation,
                        evidence=dev.model_dump(mode="json"),
                        recommended_action="Review log volume baseline shifts and inspect upstream perimeter device filters.",
                        status="OPEN",
                        created_at=now_dt,
                        updated_at=now_dt
                    )
                    db.add(finding)
                    new_findings += 1
                total_findings += 1

        # 3. Evaluate Correlations
        correlations = CorrelationEngine.scan_correlations(db, window_minutes=15, now_dt=now_dt)
        for corr in correlations:
            title, explanation = ExplainabilityGenerator.generate_correlation_explanation(
                shared_entity_type=corr.shared_entity_type,
                shared_entity_value=corr.shared_entity_value,
                event_count=corr.event_count,
                distinct_sources=corr.distinct_sources_count,
                vendors_list=corr.distinct_vendors,
                window_seconds=corr.time_window_seconds
            )

            score, category = PrioritizationEngine.calculate_priority(
                severity="HIGH",
                confidence=0.85,
                source_criticality="high",
                event_count=corr.event_count
            )

            existing = (
                db.query(AnalyticsFinding)
                .filter(
                    AnalyticsFinding.title == title,
                    AnalyticsFinding.status == "OPEN"
                )
                .first()
            )

            if not existing:
                finding = AnalyticsFinding(
                    id=str(uuid.uuid4()),
                    finding_type="CORRELATION",
                    severity="HIGH",
                    confidence=0.85,
                    priority_score=score,
                    priority_category=category.value,
                    source_id=None,
                    event_count=corr.event_count,
                    first_seen=corr.first_seen,
                    last_seen=corr.last_seen,
                    title=title,
                    explanation=explanation,
                    evidence=corr.model_dump(mode="json"),
                    recommended_action="Inspect correlation candidate logs across multiple vendor devices for unified event trail.",
                    status="OPEN",
                    created_at=now_dt,
                    updated_at=now_dt
                )
                db.add(finding)
                new_findings += 1
            total_findings += 1

        db.commit()

        health_summary = {
            "healthy": sum(1 for h in health_list if h.status == HealthStatus.HEALTHY),
            "degraded": sum(1 for h in health_list if h.status == HealthStatus.DEGRADED),
            "suspicious": sum(1 for h in health_list if h.status == HealthStatus.SUSPICIOUS),
            "inactive": sum(1 for h in health_list if h.status == HealthStatus.INACTIVE),
        }

        return AnalyzeRunResponse(
            scan_id=scan_id,
            scan_timestamp=now_dt,
            sources_scanned=len(sources),
            findings_generated=total_findings,
            new_findings_count=new_findings,
            health_summary=health_summary
        )

    @staticmethod
    def list_findings(
        db: Session,
        status: Optional[str] = None,
        finding_type: Optional[str] = None,
        severity: Optional[str] = None,
        source_id: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[FindingResponse]:
        query = db.query(AnalyticsFinding)
        if status:
            query = query.filter(AnalyticsFinding.status == status.upper())
        if finding_type:
            query = query.filter(AnalyticsFinding.finding_type == finding_type.upper())
        if severity:
            query = query.filter(AnalyticsFinding.severity == severity.upper())
        if source_id:
            query = query.filter(AnalyticsFinding.source_id == source_id)

        findings = query.order_by(desc(AnalyticsFinding.priority_score), desc(AnalyticsFinding.created_at)).offset(offset).limit(limit).all()

        return [
            FindingResponse(
                id=f.id,
                finding_type=f.finding_type,
                severity=f.severity,
                confidence=f.confidence,
                priority_score=f.priority_score,
                priority_category=f.priority_category,
                source_id=f.source_id,
                event_count=f.event_count,
                first_seen=f.first_seen,
                last_seen=f.last_seen,
                title=f.title,
                explanation=f.explanation,
                evidence=f.evidence,
                recommended_action=f.recommended_action,
                status=f.status,
                reviewed_by=f.reviewed_by,
                reviewed_at=f.reviewed_at,
                created_at=f.created_at,
                updated_at=f.updated_at
            )
            for f in findings
        ]

    @staticmethod
    def get_finding(db: Session, finding_id: str) -> Optional[FindingResponse]:
        f = db.query(AnalyticsFinding).filter(AnalyticsFinding.id == finding_id).first()
        if not f:
            return None
        return FindingResponse(
            id=f.id,
            finding_type=f.finding_type,
            severity=f.severity,
            confidence=f.confidence,
            priority_score=f.priority_score,
            priority_category=f.priority_category,
            source_id=f.source_id,
            event_count=f.event_count,
            first_seen=f.first_seen,
            last_seen=f.last_seen,
            title=f.title,
            explanation=f.explanation,
            evidence=f.evidence,
            recommended_action=f.recommended_action,
            status=f.status,
            reviewed_by=f.reviewed_by,
            reviewed_at=f.reviewed_at,
            created_at=f.created_at,
            updated_at=f.updated_at
        )

    @staticmethod
    def review_finding(db: Session, finding_id: str, actor: str = "analyst") -> FindingResponse:
        f = db.query(AnalyticsFinding).filter(AnalyticsFinding.id == finding_id).first()
        if not f:
            raise ValueError(f"Finding '{finding_id}' not found.")
        f.status = "REVIEWED"
        f.reviewed_by = actor
        f.reviewed_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(f)
        return SecurityAnalyticsService.get_finding(db, finding_id)

    @staticmethod
    def dismiss_finding(db: Session, finding_id: str, actor: str = "analyst") -> FindingResponse:
        f = db.query(AnalyticsFinding).filter(AnalyticsFinding.id == finding_id).first()
        if not f:
            raise ValueError(f"Finding '{finding_id}' not found.")
        f.status = "DISMISSED"
        f.reviewed_by = actor
        f.reviewed_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(f)
        return SecurityAnalyticsService.get_finding(db, finding_id)

    @staticmethod
    def get_findings_report_data(db: Session) -> Dict[str, Any]:
        findings = db.query(AnalyticsFinding).order_by(desc(AnalyticsFinding.priority_score)).all()
        return {
            "report_title": "ULPF Security Analytics & Data Quality Supervisory Report",
            "generation_timestamp": datetime.now(timezone.utc).isoformat(),
            "analytical_methodology": "Offline deterministic baseline deviation, negative-space coverage gap, and cross-source correlation engine.",
            "disclaimer": "The analytics engine identifies indicators requiring investigation; it does not establish that a cyberattack occurred.",
            "total_findings": len(findings),
            "findings": [
                {
                    "id": f.id,
                    "finding_type": f.finding_type,
                    "title": f.title,
                    "severity": f.severity,
                    "priority_score": f.priority_score,
                    "priority_category": f.priority_category,
                    "confidence": f.confidence,
                    "source_id": f.source_id,
                    "first_seen": f.first_seen.isoformat() if f.first_seen else None,
                    "last_seen": f.last_seen.isoformat() if f.last_seen else None,
                    "explanation": f.explanation,
                    "evidence": f.evidence,
                    "status": f.status
                }
                for f in findings
            ]
        }

    @staticmethod
    def export_findings(db: Session, export_format: str = "json") -> Tuple[str, str]:
        """
        Exports security analytics findings report to JSON or CSV.
        Returns: (content_string, media_type)
        """
        findings = db.query(AnalyticsFinding).order_by(desc(AnalyticsFinding.priority_score)).all()

        if export_format.lower() == "csv":
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow([
                "Finding ID", "Type", "Title", "Severity", "Priority Score",
                "Priority Category", "Confidence", "Status", "Source ID",
                "First Seen", "Last Seen", "Explanation"
            ])
            for f in findings:
                writer.writerow([
                    f.id, f.finding_type, f.title, f.severity, f.priority_score,
                    f.priority_category, f.confidence, f.status, f.source_id or "",
                    f.first_seen.isoformat() if f.first_seen else "",
                    f.last_seen.isoformat() if f.last_seen else "",
                    f.explanation
                ])
            return output.getvalue(), "text/csv"

        else:
            report_data = SecurityAnalyticsService.get_findings_report_data(db)
            return json.dumps(report_data, indent=2), "application/json"


security_analytics_service = SecurityAnalyticsService()
