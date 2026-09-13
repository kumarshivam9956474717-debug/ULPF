from typing import List, Optional
from sqlalchemy.orm import Session

from app.models.normalized_event import NormalizedEvent
from app.services.analytics.models import (
    OverviewMetrics,
    TimelinePoint,
    DistributionItem,
    TopItem,
    AnalyticsFilter
)
from app.services.analytics import queries


class AnalyticsService:
    """
    High-level analytics service coordinating SQL-level aggregations
    over the normalized PostgreSQL event repository.
    """

    @staticmethod
    def get_overview(db: Session, filters: Optional[AnalyticsFilter] = None) -> OverviewMetrics:
        return queries.query_overview(db, filters)

    @staticmethod
    def get_timeline(db: Session, filters: Optional[AnalyticsFilter] = None) -> List[TimelinePoint]:
        return queries.query_timeline(db, filters)

    @staticmethod
    def get_vendors(db: Session, filters: Optional[AnalyticsFilter] = None) -> List[DistributionItem]:
        return queries.query_distribution(db, NormalizedEvent.vendor, filters)

    @staticmethod
    def get_severity(db: Session, filters: Optional[AnalyticsFilter] = None) -> List[DistributionItem]:
        return queries.query_distribution(db, NormalizedEvent.severity, filters)

    @staticmethod
    def get_categories(db: Session, filters: Optional[AnalyticsFilter] = None) -> List[DistributionItem]:
        return queries.query_distribution(db, NormalizedEvent.category, filters)

    @staticmethod
    def get_top_source_ips(db: Session, limit: int = 10, filters: Optional[AnalyticsFilter] = None) -> List[TopItem]:
        return queries.query_top_items(db, NormalizedEvent.source_ip, limit, filters)

    @staticmethod
    def get_top_destination_ports(db: Session, limit: int = 10, filters: Optional[AnalyticsFilter] = None) -> List[TopItem]:
        return queries.query_top_items(db, NormalizedEvent.destination_port, limit, filters)

    @staticmethod
    def get_sources(db: Session, filters: Optional[AnalyticsFilter] = None) -> List[DistributionItem]:
        return queries.query_distribution(db, NormalizedEvent.device_type, filters)


analytics_service = AnalyticsService()
