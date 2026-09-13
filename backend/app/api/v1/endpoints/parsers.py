from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.parser import Parser, ParserVersion
from app.schemas.parser import ParserCreate, ParserResponse

router = APIRouter()


@router.post(
    "",
    response_model=ParserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a modular parser",
    description="Registers a new vendor parser module into the parser registry."
)
def create_parser(
    payload: ParserCreate,
    db: Session = Depends(get_db)
) -> Parser:
    existing = db.query(Parser).filter(Parser.parser_id == payload.parser_id).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Parser with parser_id '{payload.parser_id}' already exists."
        )

    parser = Parser(
        parser_id=payload.parser_id,
        name=payload.name,
        vendor=payload.vendor,
        product=payload.product,
        device_type=payload.device_type,
        supported_formats=payload.supported_formats,
        description=payload.description,
        enabled=payload.enabled,
    )
    db.add(parser)
    db.flush()

    if payload.initial_version:
        ver = ParserVersion(
            parser_id=parser.parser_id,
            version=payload.initial_version.version,
            checksum=payload.initial_version.checksum,
            configuration=payload.initial_version.configuration or {},
            active=payload.initial_version.active,
        )
        db.add(ver)

    db.commit()
    db.refresh(parser)
    return parser


@router.get(
    "",
    response_model=List[ParserResponse],
    summary="List all modular parsers",
    description="Returns all registered parser plugins and their associated versions."
)
def list_parsers(
    db: Session = Depends(get_db)
) -> List[Parser]:
    return db.query(Parser).order_by(Parser.created_at.desc()).all()
