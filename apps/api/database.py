"""
DevScout AI – Database configuration and models.

Production targets (all supported):
    - Neon (serverless Postgres)
    - Supabase Postgres
    - Railway Postgres
    - Any standard PostgreSQL >= 14
    - SQLite (for local development and testing)
"""

from __future__ import annotations

import datetime
import os
from typing import Generator

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    create_engine,
    text,
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
    **({"connect_args": {"check_same_thread": False}} if _is_sqlite else {}),
    pool_pre_ping=True,
    **({} if _is_sqlite else {
        "pool_size": int(os.getenv("DB_POOL_SIZE", "5")),
        "max_overflow": int(os.getenv("DB_MAX_OVERFLOW", "10")),
        "pool_timeout": int(os.getenv("DB_POOL_TIMEOUT", "10")),
        "pool_recycle": int(os.getenv("DB_POOL_RECYCLE", "1800")),
        "connect_args": {"connect_timeout": int(os.getenv("DB_CONNECT_TIMEOUT", "10"))},
    }),
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

Base = declarative_base()


def _utc_now():
    return datetime.datetime.now(datetime.timezone.utc)


# ---------------------------------------------------------------------------
# SaaS Models: User, Workspace, WorkspaceMember, Report, UsageLog
# ---------------------------------------------------------------------------

class User(Base):
    """Represents an authenticated user."""
    __tablename__ = "users"

    id = Column(String(64), primary_key=True)  # e.g. usr_123 or UUID
    email = Column(String(255), unique=True, index=True, nullable=False)
    name = Column(String(255), nullable=False)
    avatar_url = Column(String(500), nullable=True)
    role = Column(String(32), nullable=False, default="member")  # owner, admin, member

    created_at = Column(DateTime, nullable=False, default=_utc_now)
    updated_at = Column(DateTime, nullable=False, default=_utc_now, onupdate=_utc_now)


class Workspace(Base):
    """
    Represents an isolated tenant/organization/workspace.
    All research jobs and reports belong to a specific workspace.
    """
    __tablename__ = "workspaces"

    id = Column(String(64), primary_key=True)  # e.g. ws_123 or UUID
    name = Column(String(255), nullable=False)
    slug = Column(String(255), unique=True, index=True, nullable=False)
    owner_id = Column(String(64), ForeignKey("users.id"), nullable=False)

    # Billing & Credit Tiers (ready for Stripe / billing expansion)
    plan_tier = Column(String(32), nullable=False, default="free")  # free, pro, team, enterprise
    monthly_credit_limit = Column(Integer, nullable=False, default=50)
    credits_used = Column(Integer, nullable=False, default=0)

    created_at = Column(DateTime, nullable=False, default=_utc_now)
    updated_at = Column(DateTime, nullable=False, default=_utc_now, onupdate=_utc_now)


class WorkspaceMember(Base):
    """Represents membership and role within a workspace."""
    __tablename__ = "workspace_members"

    id = Column(String(64), primary_key=True)
    workspace_id = Column(String(64), ForeignKey("workspaces.id"), index=True, nullable=False)
    user_id = Column(String(64), ForeignKey("users.id"), index=True, nullable=False)
    role = Column(String(32), nullable=False, default="member")  # owner, admin, member, viewer
    joined_at = Column(DateTime, nullable=False, default=_utc_now)

    __table_args__ = (
        Index("ix_workspace_user", "workspace_id", "user_id", unique=True),
    )


class Report(Base):
    """
    Represents a research job execution and its finalized analysis report.
    Enforces tenancy via user_id and workspace_id.
    """
    __tablename__ = "reports"

    job_id = Column(String(64), primary_key=True)
    research_type = Column(String(32), nullable=False)
    query = Column(String(500), nullable=False)
    status = Column(String(20), nullable=False, default="pending")
    stage = Column(String(32), nullable=True, default="pending")
    report_markdown = Column(Text, nullable=True)
    raw_data = Column(Text, nullable=True)
    sources = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)

    # Tenancy & Ownership
    user_id = Column(String(64), ForeignKey("users.id"), index=True, nullable=True)
    workspace_id = Column(String(64), ForeignKey("workspaces.id"), index=True, nullable=True)

    # SaaS Productivity features
    custom_title = Column(String(255), nullable=True)
    is_saved = Column(Boolean, nullable=False, default=False)
    tags = Column(Text, nullable=True)  # JSON array string
    is_archived = Column(Boolean, nullable=False, default=False)

    created_at = Column(DateTime, nullable=False, default=_utc_now)
    updated_at = Column(DateTime, nullable=False, default=_utc_now, onupdate=_utc_now)

    __table_args__ = (
        Index("ix_reports_status", "status"),
        Index("ix_reports_created_at", "created_at"),
        Index("ix_reports_type_status", "research_type", "status"),
        Index("ix_reports_workspace", "workspace_id", "created_at"),
        Index("ix_reports_saved", "workspace_id", "is_saved"),
    )


class UsageLog(Base):
    """
    Tracks credit usage per workspace and user.
    Designed for billing, rate limiting, and analytics.
    """
    __tablename__ = "usage_logs"

    id = Column(String(64), primary_key=True)
    workspace_id = Column(String(64), ForeignKey("workspaces.id"), index=True, nullable=False)
    user_id = Column(String(64), ForeignKey("users.id"), index=True, nullable=False)
    job_id = Column(String(64), ForeignKey("reports.job_id"), nullable=True)
    action = Column(String(64), nullable=False, default="research_query")
    credits_deducted = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime, nullable=False, default=_utc_now)

    __table_args__ = (
        Index("ix_usage_workspace_created", "workspace_id", "created_at"),
    )


# ---------------------------------------------------------------------------
# FastAPI dependency
# ---------------------------------------------------------------------------

def get_db() -> Generator[Session, None, None]:
    """Yield a database session and guarantee cleanup after the request."""
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Dev helper – create tables and migrate columns if needed
# ---------------------------------------------------------------------------

def ensure_tables() -> None:
    """Create all tables that don't yet exist and ensure all columns are present."""
    Base.metadata.create_all(bind=engine)

    if _is_sqlite:
        try:
            with engine.connect() as conn:
                result = conn.execute(text("PRAGMA table_info(reports)"))
                columns = {row[1] for row in result.fetchall()}
                if columns:
                    if "error_message" not in columns:
                        conn.execute(text("ALTER TABLE reports ADD COLUMN error_message TEXT"))
                    if "stage" not in columns:
                        conn.execute(text("ALTER TABLE reports ADD COLUMN stage VARCHAR(32) DEFAULT 'pending'"))
                    if "updated_at" not in columns:
                        conn.execute(text("ALTER TABLE reports ADD COLUMN updated_at TIMESTAMP"))
                    if "sources" not in columns:
                        conn.execute(text("ALTER TABLE reports ADD COLUMN sources TEXT"))
                    if "user_id" not in columns:
                        conn.execute(text("ALTER TABLE reports ADD COLUMN user_id VARCHAR(64)"))
                    if "workspace_id" not in columns:
                        conn.execute(text("ALTER TABLE reports ADD COLUMN workspace_id VARCHAR(64)"))
                    if "custom_title" not in columns:
                        conn.execute(text("ALTER TABLE reports ADD COLUMN custom_title VARCHAR(255)"))
                    if "is_saved" not in columns:
                        conn.execute(text("ALTER TABLE reports ADD COLUMN is_saved BOOLEAN DEFAULT 0"))
                    if "tags" not in columns:
                        conn.execute(text("ALTER TABLE reports ADD COLUMN tags TEXT"))
                    if "is_archived" not in columns:
                        conn.execute(text("ALTER TABLE reports ADD COLUMN is_archived BOOLEAN DEFAULT 0"))
                    conn.commit()
        except Exception:
            raise RuntimeError("Failed to apply local SQLite compatibility migration")
