from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator, Optional

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from backend.config.settings import settings
from backend.models.database_models import Base

_engine: Optional[Engine] = None
_SessionLocal: Optional[sessionmaker[Session]] = None


def get_engine() -> Optional[Engine]:
    global _engine, _SessionLocal
    if not settings.database_url:
        return None
    if _engine is None:
        _engine = create_engine(settings.database_url, pool_pre_ping=True, future=True)
        _SessionLocal = sessionmaker(bind=_engine, autoflush=False, autocommit=False, future=True)
    return _engine


def database_available() -> bool:
    engine = get_engine()
    if engine is None:
        return False
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


def init_db() -> None:
    engine = get_engine()
    if engine is None:
        return
    Base.metadata.create_all(bind=engine)


@contextmanager
def session_scope() -> Iterator[Session]:
    engine = get_engine()
    if engine is None or _SessionLocal is None:
        raise RuntimeError("DATABASE_URL is not configured")
    session = _SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
