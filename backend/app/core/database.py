import logging
from typing import Generator
from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from app.core.config import settings

logger = logging.getLogger("ulpf.database")

Base = declarative_base()

def get_sqlite_url() -> str:
    import os
    import tempfile
    from pathlib import Path

    env_path = os.getenv("SQLITE_DB_PATH")
    if env_path:
        return f"sqlite:///{Path(env_path).resolve().as_posix()}"

    candidates = [
        Path.cwd() / "demo.db",
        Path(__file__).resolve().parent.parent.parent / "demo.db",
    ]
    try:
        candidates.append(Path(__file__).resolve().parents[3] / "demo.db")
    except IndexError:
        pass

    for candidate in candidates:
        try:
            parent_dir = candidate.parent
            if parent_dir.exists():
                probe = parent_dir / ".db_write_probe"
                probe.touch()
                probe.unlink()
                return f"sqlite:///{candidate.resolve().as_posix()}"
        except Exception:
            continue

    temp_db = (Path(tempfile.gettempdir()) / "ulpf_demo.db").resolve()
    return f"sqlite:///{temp_db.as_posix()}"


def create_resilient_engine():
    url = settings.DATABASE_URL
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)

    if url.startswith("sqlite"):
        return create_engine(
            url,
            connect_args={"check_same_thread": False, "timeout": 60},
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
        sqlite_url = get_sqlite_url()
        return create_engine(
            sqlite_url,
            connect_args={"check_same_thread": False, "timeout": 60},
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

