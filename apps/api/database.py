"""
DevScout AI – Database configuration and models.

DATABASE_URL
    Set via the DATABASE_URL environment variable.
    Falls back to sqlite for local development only.

Production targets (all supported):
    - Neon (serverless Postgres)
    - Supabase Postgres
    - Railway Postgres
    - Any standard PostgreSQL ≥ 14

Example connection strings:
    sqlite:///./devscout.db                         # local dev (default)
    postgresql://user:pass@host:5432/devscout        # PostgreSQL
    postgresql+psycopg://user:pass@host/db           # explicit driver
"""

from __future__ import annotations

import datetime
import os
from typing import Generator

from sqlalchemy import (
    Column,
    DateTime,
    Index,
    String,
    Text,
    create_engine,
    event,
)
from sqlalchemy.orm import Session, declarative_base, sessionmaker

# ---------------------------------------------------------------------------
# Database URL
# ---------------------------------------------------------------------------

DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./devscout.db")

# ---------------------------------------------------------------------------
# Engine – configure differently for SQLite vs PostgreSQL
# ---------------------------------------------------------------------------

_is_sqlite = DATABASE_URL.startswith("sqlite")

engine = create_engine(
    DATABASE_URL,
    # SQLite needs check_same_thread=False for multi-threaded FastAPI.
    # PostgreSQL does not accept this kwarg, so we conditionally pass it.
    **({"connect_args": {"check_same_thread": False}} if _is_sqlite else {}),
    # Pool settings that work for both backends.
    pool_pre_ping=True,          # verify connections before use
    **({} if _is_sqlite else {"pool_size": 5, "max_overflow": 10}),
)

# Enable WAL mode for SQLite (better concurrent read performance).
if _is_sqlite:

    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_connection, _connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class Report(Base):
    __tablename__ = "reports"

    job_id = Column(String(64), primary_key=True)
    research_type = Column(String(32), nullable=False)
    query = Column(String(500), nullable=False)
    status = Column(String(20), nullable=False, default="pending")
    report_markdown = Column(Text, nullable=True)
    raw_data = Column(Text, nullable=True)

    # New fields
    error_message = Column(Text, nullable=True)
    stage = Column(String(32), nullable=True, default="pending")

    created_at = Column(
        DateTime, nullable=False, default=datetime.datetime.utcnow,
    )
    updated_at = Column(
        DateTime, nullable=False, default=datetime.datetime.utcnow,
        onupdate=datetime.datetime.utcnow,
    )

    __table_args__ = (
        Index("ix_reports_status", "status"),
        Index("ix_reports_created_at", "created_at"),
        Index("ix_reports_type_status", "research_type", "status"),
    )


# ---------------------------------------------------------------------------
# FastAPI dependency
# ---------------------------------------------------------------------------

def get_db() -> Generator[Session, None, None]:
    """Yield a database session and guarantee cleanup after the request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Dev helper – create tables if they don't exist.
# Only call this for local dev / tests.  In production, use Alembic.
# ---------------------------------------------------------------------------

def ensure_tables() -> None:
    """Create all tables that don't yet exist (dev convenience only)."""
    Base.metadata.create_all(bind=engine)
