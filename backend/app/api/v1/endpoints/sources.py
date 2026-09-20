from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.auth import require_roles
from app.models.user import User
from app.models.log_source import LogSource
from app.schemas.log_source import LogSourceCreate, LogSourceResponse

router = APIRouter()


@router.post(
    "",
    response_model=LogSourceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new perimeter log source",
    description="Registers a new firewall, router, IDPS or proxy source into the registry."
)
def create_log_source(
    payload: LogSourceCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("ADMIN"))
) -> LogSource:
    existing = db.query(LogSource).filter(LogSource.source_id == payload.source_id).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Log source with source_id '{payload.source_id}' already exists."
        )

    log_source = LogSource(
        source_id=payload.source_id,
        vendor=payload.vendor,
        product=payload.product,
        device_type=payload.device_type,
        hostname=payload.hostname,
        source_format=payload.source_format,
        description=payload.description,
        enabled=payload.enabled,
    )
    db.add(log_source)
    db.commit()
    db.refresh(log_source)
    return log_source


@router.get(
    "",
    response_model=List[LogSourceResponse],
    summary="List registered log sources",
    description="Returns all perimeter device sources currently registered."
)
def list_log_sources(
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("ADMIN", "OPERATOR", "ANALYST", "VIEWER"))
) -> List[LogSource]:
    return db.query(LogSource).order_by(LogSource.created_at.desc()).all()
