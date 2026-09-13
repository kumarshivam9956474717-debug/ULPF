import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.models.mapping_profile import LogMappingProfile, MappingAuditLog
from app.services.onboarding.models import (
    LogAnalysisResult,
    MappingValidationRequest,
    MappingValidationResult,
    ProfileCreateRequest,
    ProfileUpdateRequest,
    TestProfileRequest,
    MappingRule,
    AuditLogItem
)
from app.services.onboarding.analyzer import LogAnalyzer
from app.services.onboarding.mapper import FieldMapper
from app.services.onboarding.validators import MappingValidator


class OnboardingService:
    """
    Coordinates unknown log analysis, mapping suggestions, human verification,
    profile versioning, testing, and lifecycle audit tracking.
    """

    @staticmethod
    def analyze_logs(sample_logs: List[str]) -> LogAnalysisResult:
        """
        Analyzes sample raw logs, extracts candidate fields, and generates
        UES mapping recommendations with deterministic confidence scoring.
        """
        (
            detected_format,
            conf,
            delim,
            kv_delim,
            has_syslog_header,
            candidates,
            warnings
        ) = LogAnalyzer.analyze_samples(sample_logs)

        suggested_mappings = FieldMapper.suggest_mappings(candidates)

        return LogAnalysisResult(
            detected_format=detected_format,
            format_confidence=conf,
            delimiter=delim,
            kv_delimiter=kv_delim,
            has_syslog_header=has_syslog_header,
            sample_count=len(sample_logs),
            fields=candidates,
            suggested_mappings=suggested_mappings,
            warnings=warnings
        )

    @staticmethod
    def validate_mapping(req: MappingValidationRequest) -> MappingValidationResult:
        """
        Simulates parsing and normalization of sample logs against proposed mapping definitions.
        Does NOT alter persistent storage.
        """
        return MappingValidator.simulate_mapping(
            sample_logs=req.sample_logs,
            source_format=req.source_format,
            delimiter=req.delimiter,
            kv_delimiter=req.kv_delimiter,
            mappings=req.mappings
        )

    @staticmethod
    def create_profile(db: Session, req: ProfileCreateRequest) -> LogMappingProfile:
        """
        Creates a new log mapping profile in DRAFT status and records creation audit.
        """
        # Validate profile name uniqueness
        existing = db.query(LogMappingProfile).filter(LogMappingProfile.name == req.name).first()
        if existing:
            raise ValueError(f"Mapping profile with name '{req.name}' already exists.")

        # Validate rules
        errors, warnings = MappingValidator.validate_rules(req.field_mappings)
        if errors:
            raise ValueError(f"Invalid field mappings: {'; '.join(errors)}")

        now_dt = datetime.now(timezone.utc)
        profile_id = str(uuid.uuid4())

        # Serialize mapping rules to dicts
        mappings_dict = [m.model_dump() for m in req.field_mappings]

        profile = LogMappingProfile(
            id=profile_id,
            name=req.name,
            vendor=req.vendor,
            product=req.product,
            device_type=req.device_type,
            source_format=req.source_format,
            parser_type="configurable",
            configuration=req.configuration,
            field_mappings=mappings_dict,
            version="1.0.0",
            status="DRAFT",
            confidence=req.confidence or 0.85,
            created_by=req.created_by or "system",
            created_at=now_dt,
            updated_at=now_dt
        )
        db.add(profile)

        # Audit record
        audit = MappingAuditLog(
            id=str(uuid.uuid4()),
            profile_id=profile_id,
            action="CREATED",
            version="1.0.0",
            actor=req.created_by or "system",
            summary=f"Profile '{req.name}' created with {len(req.field_mappings)} field mapping rules.",
            timestamp=now_dt
        )
        db.add(audit)
        db.commit()
        db.refresh(profile)

        return profile

    @staticmethod
    def get_profile(db: Session, profile_id: str) -> Optional[LogMappingProfile]:
        return db.query(LogMappingProfile).filter(LogMappingProfile.id == profile_id).first()

    @staticmethod
    def list_profiles(
        db: Session,
        status: Optional[str] = None,
        vendor: Optional[str] = None
    ) -> List[LogMappingProfile]:
        query = db.query(LogMappingProfile)
        if status:
            query = query.filter(LogMappingProfile.status == status.upper())
        if vendor:
            query = query.filter(LogMappingProfile.vendor == vendor)
        return query.order_by(desc(LogMappingProfile.updated_at)).all()

    @staticmethod
    def update_profile(
        db: Session,
        profile_id: str,
        req: ProfileUpdateRequest
    ) -> LogMappingProfile:
        profile = db.query(LogMappingProfile).filter(LogMappingProfile.id == profile_id).first()
        if not profile:
            raise ValueError(f"Mapping profile '{profile_id}' not found.")

        now_dt = datetime.now(timezone.utc)

        if req.field_mappings is not None:
            errors, _ = MappingValidator.validate_rules(req.field_mappings)
            if errors:
                raise ValueError(f"Invalid field mappings: {'; '.join(errors)}")
            profile.field_mappings = [m.model_dump() for m in req.field_mappings]

        if req.vendor is not None:
            profile.vendor = req.vendor
        if req.product is not None:
            profile.product = req.product
        if req.device_type is not None:
            profile.device_type = req.device_type
        if req.source_format is not None:
            profile.source_format = req.source_format
        if req.configuration is not None:
            profile.configuration = req.configuration
        if req.confidence is not None:
            profile.confidence = req.confidence

        old_ver = profile.version
        new_ver = old_ver
        if req.increment_version:
            # Increment minor version (e.g. 1.0.0 -> 1.1.0)
            parts = old_ver.split(".")
            if len(parts) == 3 and parts[1].isdigit():
                new_ver = f"{parts[0]}.{int(parts[1]) + 1}.0"
            else:
                new_ver = f"{old_ver}.1"
            profile.version = new_ver

        profile.updated_at = now_dt

        audit = MappingAuditLog(
            id=str(uuid.uuid4()),
            profile_id=profile.id,
            action="UPDATED",
            version=new_ver,
            actor=req.actor or "system",
            summary=f"Profile updated from version {old_ver} to {new_ver}.",
            timestamp=now_dt
        )
        db.add(audit)
        db.commit()
        db.refresh(profile)

        return profile

    @staticmethod
    def test_profile(db: Session, req: TestProfileRequest) -> MappingValidationResult:
        """
        Tests profile against sample logs and creates an audit record.
        """
        config = req.configuration or {}
        rules: List[MappingRule] = req.field_mappings or []
        profile_id = req.profile_id

        if profile_id:
            prof = db.query(LogMappingProfile).filter(LogMappingProfile.id == profile_id).first()
            if prof:
                config = prof.configuration
                if not rules:
                    rules = [MappingRule(**m) for m in prof.field_mappings]

        res = MappingValidator.simulate_mapping(
            sample_logs=req.sample_logs,
            source_format=config.get("source_format", "key_value"),
            delimiter=config.get("delimiter", " "),
            kv_delimiter=config.get("kv_delimiter", "="),
            mappings=rules
        )

        if profile_id:
            audit = MappingAuditLog(
                id=str(uuid.uuid4()),
                profile_id=profile_id,
                action="TESTED",
                version="test",
                actor="user",
                summary=f"Tested with {len(req.sample_logs)} records. Passed: {res.records_passed}, Failed: {res.records_failed}.",
                timestamp=datetime.now(timezone.utc)
            )
            db.add(audit)
            db.commit()

        return res

    @staticmethod
    def activate_profile(db: Session, profile_id: str, actor: str = "user") -> LogMappingProfile:
        """
        Transitions profile to ACTIVE status and registers it with the parser engine.
        Enforces that profile cannot be activated if field mappings are empty or invalid.
        """
        profile = db.query(LogMappingProfile).filter(LogMappingProfile.id == profile_id).first()
        if not profile:
            raise ValueError(f"Profile '{profile_id}' not found.")

        # Ensure valid mappings exist
        rules = [MappingRule(**m) for m in profile.field_mappings]
        errors, _ = MappingValidator.validate_rules(rules)
        if errors:
            raise ValueError(f"Cannot activate profile with invalid mappings: {'; '.join(errors)}")

        profile.status = "ACTIVE"
        profile.updated_at = datetime.now(timezone.utc)

        audit = MappingAuditLog(
            id=str(uuid.uuid4()),
            profile_id=profile.id,
            action="ACTIVATED",
            version=profile.version,
            actor=actor,
            summary=f"Profile '{profile.name}' activated at version {profile.version}.",
            timestamp=datetime.now(timezone.utc)
        )
        db.add(audit)
        db.commit()
        db.refresh(profile)

        # Register with parser engine
        from app.services.parsers.configurable import register_profile_parser
        register_profile_parser(profile)

        return profile

    @staticmethod
    def disable_profile(db: Session, profile_id: str, actor: str = "user") -> LogMappingProfile:
        profile = db.query(LogMappingProfile).filter(LogMappingProfile.id == profile_id).first()
        if not profile:
            raise ValueError(f"Profile '{profile_id}' not found.")

        profile.status = "DISABLED"
        profile.updated_at = datetime.now(timezone.utc)

        audit = MappingAuditLog(
            id=str(uuid.uuid4()),
            profile_id=profile.id,
            action="DISABLED",
            version=profile.version,
            actor=actor,
            summary=f"Profile '{profile.name}' disabled.",
            timestamp=datetime.now(timezone.utc)
        )
        db.add(audit)
        db.commit()
        db.refresh(profile)

        from app.services.parsers.configurable import unregister_profile_parser
        unregister_profile_parser(profile.name)

        return profile

    @staticmethod
    def get_audit_logs(db: Session, profile_id: str) -> List[AuditLogItem]:
        logs = (
            db.query(MappingAuditLog)
            .filter(MappingAuditLog.profile_id == profile_id)
            .order_by(desc(MappingAuditLog.timestamp))
            .all()
        )
        return [
            AuditLogItem(
                id=l.id,
                action=l.action,
                version=l.version,
                actor=l.actor,
                summary=l.summary,
                timestamp=l.timestamp
            )
            for l in logs
        ]


onboarding_service = OnboardingService()
