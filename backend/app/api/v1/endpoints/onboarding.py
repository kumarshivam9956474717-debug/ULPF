from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.onboarding.models import (
    LogAnalysisRequest,
    LogAnalysisResult,
    MappingValidationRequest,
    MappingValidationResult,
    TestProfileRequest,
    ProfileCreateRequest,
    ProfileUpdateRequest,
    ProfileResponse,
    AuditLogItem
)
from app.services.onboarding.service import onboarding_service

router = APIRouter()


@router.post(
    "/analyze",
    response_model=LogAnalysisResult,
    summary="Analyze unknown raw log samples offline",
    description="Inspects sample log payloads, identifies structure/delimiter, infers data types, and recommends UES mappings with deterministic confidence scores."
)
def analyze_unknown_log(payload: LogAnalysisRequest) -> LogAnalysisResult:
    try:
        return onboarding_service.analyze_logs(payload.sample_logs)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Analysis failed: {str(exc)}"
        )


@router.post(
    "/validate-mapping",
    response_model=MappingValidationResult,
    summary="Validate proposed field mapping definition against samples",
    description="Simulates field extraction and UES normalization on sample logs without persisting data to database."
)
def validate_log_mapping(req: MappingValidationRequest) -> MappingValidationResult:
    try:
        return onboarding_service.validate_mapping(req)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Mapping validation failed: {str(exc)}"
        )


@router.post(
    "/test-profile",
    response_model=MappingValidationResult,
    summary="Test profile extraction on sample logs",
    description="Runs validation tests on sample logs using profile configuration and records test audit log."
)
def test_mapping_profile(
    req: TestProfileRequest,
    db: Session = Depends(get_db)
) -> MappingValidationResult:
    try:
        return onboarding_service.test_profile(db=db, req=req)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Profile testing failed: {str(exc)}"
        )


@router.post(
    "/profiles",
    response_model=ProfileResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Save a new log mapping profile in DRAFT status"
)
def create_mapping_profile(
    req: ProfileCreateRequest,
    db: Session = Depends(get_db)
) -> ProfileResponse:
    try:
        profile = onboarding_service.create_profile(db=db, req=req)
        return ProfileResponse(
            id=profile.id,
            name=profile.name,
            vendor=profile.vendor,
            product=profile.product,
            device_type=profile.device_type,
            source_format=profile.source_format,
            parser_type=profile.parser_type,
            configuration=profile.configuration,
            field_mappings=profile.field_mappings,
            version=profile.version,
            status=profile.status,
            confidence=profile.confidence,
            created_by=profile.created_by,
            created_at=profile.created_at,
            updated_at=profile.updated_at
        )
    except ValueError as val_err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(val_err)
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create profile: {str(exc)}"
        )


@router.get(
    "/profiles",
    response_model=List[ProfileResponse],
    summary="List saved log mapping profiles"
)
def list_mapping_profiles(
    status: Optional[str] = Query(None, description="Filter by status (DRAFT, ACTIVE, DISABLED)"),
    vendor: Optional[str] = Query(None, description="Filter by vendor"),
    db: Session = Depends(get_db)
) -> List[ProfileResponse]:
    profiles = onboarding_service.list_profiles(db=db, status=status, vendor=vendor)
    return [
        ProfileResponse(
            id=p.id,
            name=p.name,
            vendor=p.vendor,
            product=p.product,
            device_type=p.device_type,
            source_format=p.source_format,
            parser_type=p.parser_type,
            configuration=p.configuration,
            field_mappings=p.field_mappings,
            version=p.version,
            status=p.status,
            confidence=p.confidence,
            created_by=p.created_by,
            created_at=p.created_at,
            updated_at=p.updated_at
        )
        for p in profiles
    ]


@router.get(
    "/profiles/{profile_id}",
    response_model=ProfileResponse,
    summary="Get log mapping profile by ID"
)
def get_mapping_profile(
    profile_id: str,
    db: Session = Depends(get_db)
) -> ProfileResponse:
    profile = onboarding_service.get_profile(db=db, profile_id=profile_id)
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Profile '{profile_id}' not found."
        )

    audit_logs = onboarding_service.get_audit_logs(db=db, profile_id=profile_id)

    return ProfileResponse(
        id=profile.id,
        name=profile.name,
        vendor=profile.vendor,
        product=profile.product,
        device_type=profile.device_type,
        source_format=profile.source_format,
        parser_type=profile.parser_type,
        configuration=profile.configuration,
        field_mappings=profile.field_mappings,
        version=profile.version,
        status=profile.status,
        confidence=profile.confidence,
        created_by=profile.created_by,
        created_at=profile.created_at,
        updated_at=profile.updated_at,
        audit_logs=audit_logs
    )


@router.put(
    "/profiles/{profile_id}",
    response_model=ProfileResponse,
    summary="Update mapping profile configuration and increment version"
)
def update_mapping_profile(
    profile_id: str,
    req: ProfileUpdateRequest,
    db: Session = Depends(get_db)
) -> ProfileResponse:
    try:
        profile = onboarding_service.update_profile(db=db, profile_id=profile_id, req=req)
        return ProfileResponse(
            id=profile.id,
            name=profile.name,
            vendor=profile.vendor,
            product=profile.product,
            device_type=profile.device_type,
            source_format=profile.source_format,
            parser_type=profile.parser_type,
            configuration=profile.configuration,
            field_mappings=profile.field_mappings,
            version=profile.version,
            status=profile.status,
            confidence=profile.confidence,
            created_by=profile.created_by,
            created_at=profile.created_at,
            updated_at=profile.updated_at
        )
    except ValueError as val_err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(val_err)
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update profile: {str(exc)}"
        )


@router.post(
    "/profiles/{profile_id}/activate",
    response_model=ProfileResponse,
    summary="Activate profile to process future matching logs automatically"
)
def activate_mapping_profile(
    profile_id: str,
    actor: str = Query("user"),
    db: Session = Depends(get_db)
) -> ProfileResponse:
    try:
        profile = onboarding_service.activate_profile(db=db, profile_id=profile_id, actor=actor)
        return ProfileResponse(
            id=profile.id,
            name=profile.name,
            vendor=profile.vendor,
            product=profile.product,
            device_type=profile.device_type,
            source_format=profile.source_format,
            parser_type=profile.parser_type,
            configuration=profile.configuration,
            field_mappings=profile.field_mappings,
            version=profile.version,
            status=profile.status,
            confidence=profile.confidence,
            created_by=profile.created_by,
            created_at=profile.created_at,
            updated_at=profile.updated_at
        )
    except ValueError as val_err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(val_err)
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to activate profile: {str(exc)}"
        )


@router.post(
    "/profiles/{profile_id}/disable",
    response_model=ProfileResponse,
    summary="Disable an active mapping profile"
)
def disable_mapping_profile(
    profile_id: str,
    actor: str = Query("user"),
    db: Session = Depends(get_db)
) -> ProfileResponse:
    try:
        profile = onboarding_service.disable_profile(db=db, profile_id=profile_id, actor=actor)
        return ProfileResponse(
            id=profile.id,
            name=profile.name,
            vendor=profile.vendor,
            product=profile.product,
            device_type=profile.device_type,
            source_format=profile.source_format,
            parser_type=profile.parser_type,
            configuration=profile.configuration,
            field_mappings=profile.field_mappings,
            version=profile.version,
            status=profile.status,
            confidence=profile.confidence,
            created_by=profile.created_by,
            created_at=profile.created_at,
            updated_at=profile.updated_at
        )
    except ValueError as val_err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(val_err)
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to disable profile: {str(exc)}"
        )


@router.get(
    "/profiles/{profile_id}/versions",
    response_model=List[AuditLogItem],
    summary="Get audit history and version evolution for a profile"
)
def get_profile_version_history(
    profile_id: str,
    db: Session = Depends(get_db)
) -> List[AuditLogItem]:
    return onboarding_service.get_audit_logs(db=db, profile_id=profile_id)
