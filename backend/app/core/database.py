import logging
from typing import Generator
from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from app.core.config import settings

logger = logging.getLogger("ulpf.database")

Base = declarative_base()

def create_resilient_engine():
    url = settings.DATABASE_URL
    if url.startswith("sqlite"):
        return create_engine(
            url,
            connect_args={"check_same_thread": False},
            pool_pre_ping=True,
            echo=settings.DEBUG,
        )
    
    # PostgreSQL with configurable production connection pooling
    try:
        eng = create_engine(
            url,
            connect_args={},
            pool_pre_ping=True,
            pool_size=settings.DB_POOL_SIZE,
            max_overflow=settings.DB_MAX_OVERFLOW,
            pool_timeout=settings.DB_POOL_TIMEOUT,
            pool_recycle=settings.DB_POOL_RECYCLE,
            echo=settings.DEBUG,
        )
        # Verify connection
        with eng.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info(
            f"PostgreSQL connection verified with pool_size={settings.DB_POOL_SIZE}, max_overflow={settings.DB_MAX_OVERFLOW}"
        )
        return eng
    except Exception as e:
        logger.warning(f"PostgreSQL connection unavailable ({e}). Falling back to local SQLite database.")
        from pathlib import Path
        repo_root = Path(__file__).resolve().parents[3]
        db_path = (repo_root / "demo.db").resolve()
        sqlite_url = f"sqlite:///{db_path.as_posix()}"
        return create_engine(
            sqlite_url,
            connect_args={"check_same_thread": False},
            pool_pre_ping=True,
        )

engine = create_resilient_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    try:
        import app.models  # noqa: F401
        Base.metadata.create_all(bind=engine)
    except Exception as e:
        logger.error(f"Failed to auto-create tables: {e}")

# Auto-create all tables
init_db()


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency yielding a database session per request.
    Closes automatically upon completion.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

