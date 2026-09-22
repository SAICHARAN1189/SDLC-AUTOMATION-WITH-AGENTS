from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator, Optional, Tuple

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from backend.config.settings import settings
from backend.models.database_models import Base
from backend.utils.logging import logger

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
            # Keep alive so the OS doesn't silently drop idle TCP connections
            "keepalives": 1,
            "keepalives_idle": 30,
            "keepalives_interval": 10,
            "keepalives_count": 5,
        }
        _engine = create_engine(
            db_url,
            pool_size=getattr(settings, "db_pool_size", 10),
            max_overflow=getattr(settings, "db_max_overflow", 15),
            pool_timeout=30,
            # Recycle connections after 3 minutes (below Supabase's ~5 min idle timeout)
            pool_recycle=getattr(settings, "db_pool_recycle", 180),
            # Pre-ping: issue a lightweight SELECT before handing out a pooled connection.
            # This transparently retries on stale connections that Supabase has closed.
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
    Retries once on transient OperationalError (e.g. Supabase closed the connection
    mid-pipeline after pool_pre_ping recycled the engine).
    """
    from sqlalchemy.exc import OperationalError as SAOperationalError

    get_engine()  # Ensure engine is initialized
    if _SessionLocal is None:
        raise DatabaseConfigurationError("Database session factory is not initialized")

    for attempt in range(2):  # 1 retry on transient connection drop
        session = _SessionLocal()
        try:
            yield session
            session.commit()
            logger.debug("[DB] Transaction committed")
            return
        except SAOperationalError as exc:
            session.rollback()
            session.close()
            if attempt == 0 and "server closed the connection" in str(exc).lower():
                logger.warning("[DB] Transient connection drop detected — resetting pool and retrying once.")
                try:
                    get_engine().dispose()
                except Exception:
                    pass
                continue  # retry
            logger.error(f"[DB] Transaction failed after retry: {type(exc).__name__}")
            raise
        except Exception as exc:
            session.rollback()
            logger.error(f"[DB] Transaction failed: {type(exc).__name__}")
            logger.info("[DB] Rollback completed")
            raise
        finally:
            try:
                session.close()
            except Exception:
                pass
        break
