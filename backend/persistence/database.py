from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator, Optional, Tuple

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from backend.config.settings import settings
from backend.models.database_models import Base
from backend.utils.logging import logger

from sqlalchemy.pool import NullPool

_engine: Optional[Engine] = None
_SessionLocal: Optional[sessionmaker[Session]] = None


class DatabaseConfigurationError(Exception):
    """Raised when DATABASE_URL is missing or invalid."""
    pass


class DatabaseConnectionError(Exception):
    """Raised when connecting to PostgreSQL fails."""
    pass


def reset_engine() -> None:
    """Reset the global engine instance (useful for tests or reconnection)."""
    global _engine, _SessionLocal
    if _engine is not None:
        try:
            _engine.dispose()
        except Exception:
            pass
    _engine = None
    _SessionLocal = None


def get_engine() -> Engine:
    """Get or create the SQLAlchemy engine with pooling and error handling.
    Fails fast with DatabaseConfigurationError if DATABASE_URL is missing.
    """
    global _engine, _SessionLocal
    if _engine is not None:
        return _engine

    db_url = settings.normalized_database_url
    if not db_url:
        raise DatabaseConfigurationError(
            "DATABASE_URL is not configured. Set DATABASE_URL in .env to connect to Supabase PostgreSQL."
        )

    logger.info("[DB] Connecting to PostgreSQL")
    try:
        connect_args = {
            "connect_timeout": getattr(settings, "db_connect_timeout", 10),
            # Keep alive so intermediate routers/NATs don't drop idle TCP connections
            "keepalives": 1,
            "keepalives_idle": 30,
            "keepalives_interval": 10,
            "keepalives_count": 5,
        }

        # Supabase Supavisor Transaction Pooler (port 6543):
        # Supavisor manages connection pooling on the server side and terminates
        # idle client connections after 5 minutes.
        # Using NullPool prevents SQLAlchemy from holding stale idle connections,
        # completely eliminating "server closed the connection unexpectedly" errors.
        is_transaction_pooler = ":6543" in db_url or "pooler.supabase.com" in db_url

        if is_transaction_pooler:
            logger.info("[DB] Supabase transaction pooler (:6543) detected — using NullPool")
            _engine = create_engine(
                db_url,
                poolclass=NullPool,
                connect_args=connect_args,
                future=True,
            )
        else:
            _engine = create_engine(
                db_url,
                pool_size=getattr(settings, "db_pool_size", 10),
                max_overflow=getattr(settings, "db_max_overflow", 15),
                pool_timeout=30,
                pool_recycle=getattr(settings, "db_pool_recycle", 60),
                pool_pre_ping=True,
                connect_args=connect_args,
                future=True,
            )

        _SessionLocal = sessionmaker(bind=_engine, autoflush=False, autocommit=False, expire_on_commit=False, future=True)
        logger.info("[DB] Connection successful")
        return _engine
    except Exception as exc:
        logger.error(f"[DB] Failed to initialize PostgreSQL engine: {type(exc).__name__}")
        raise DatabaseConnectionError(f"Failed to initialize PostgreSQL engine: {type(exc).__name__}") from exc


def database_available() -> bool:
    """Non-throwing check if the database is available and responding to SELECT 1."""
    try:
        engine = get_engine()
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


def check_database_health() -> Tuple[bool, str]:
    """Check database health, returning (is_healthy, status_message) without exposing secrets."""
    if not settings.normalized_database_url:
        return False, "DATABASE_URL is not configured"
    try:
        engine = get_engine()
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.debug("[DB] Connection successful (health check)")
        return True, "healthy"
    except DatabaseConfigurationError as exc:
        return False, str(exc)
    except Exception as exc:
        err_msg = f"Database unreachable: {type(exc).__name__}"
        logger.warning(f"[DB] {err_msg}")
        return False, err_msg


def init_db() -> None:
    """Safely initialize database tables without dropping existing data."""
    if not settings.normalized_database_url:
        logger.warning("[DB] Skipping init_db: DATABASE_URL not set")
        return
    try:
        engine = get_engine()
        logger.info("[DB] Verifying/creating tables in Supabase PostgreSQL")
        Base.metadata.create_all(bind=engine)
        logger.info("[DB] Database tables initialized successfully")
    except Exception as exc:
        logger.error(f"[DB] Error during init_db: {type(exc).__name__}")
        raise


@contextmanager
def session_scope() -> Iterator[Session]:
    """Provide a transactional scope around a series of operations.
    Commits only after successful operations; rolls back and re-raises on exception.
    """
    get_engine()  # Ensure engine is initialized
    if _SessionLocal is None:
        raise DatabaseConfigurationError("Database session factory is not initialized")

    session = _SessionLocal()
    try:
        yield session
        session.commit()
        logger.debug("[DB] Transaction committed")
    except Exception as exc:
        session.rollback()
        logger.error(f"[DB] Transaction failed: {type(exc).__name__}")
        raise
    finally:
        try:
            session.close()
        except Exception:
            pass
