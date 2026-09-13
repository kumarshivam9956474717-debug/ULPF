from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.processing_run import ProcessingRun
from app.schemas.processing_run import ProcessingRunResponse

router = APIRouter()


@router.get(
    "/{run_id}",
    response_model=ProcessingRunResponse,
    summary="Get processing run execution metrics",
    description="Retrieves operational batch telemetry and counts for a processing run."
)
def get_processing_run(
    run_id: str,
    db: Session = Depends(get_db)
) -> ProcessingRun:
    run = db.query(ProcessingRun).filter(ProcessingRun.run_id == run_id).first()
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Processing run '{run_id}' not found."
        )
    return run
