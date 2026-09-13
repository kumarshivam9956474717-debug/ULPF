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
    
    # Try PostgreSQL first
    try:
        eng = create_engine(
            url,
            connect_args={},
            pool_pre_ping=True,
            pool_size=10,
            max_overflow=20,
            echo=settings.DEBUG,
        )
        # Verify connection
        with eng.connect() as conn:
            conn.execute(text("SELECT 1"))
        return eng
    except Exception as e:
        logger.warning(f"PostgreSQL connection unavailable ({e}). Falling back to local SQLite demo database.")
        sqlite_url = "sqlite:///./demo.db"
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

