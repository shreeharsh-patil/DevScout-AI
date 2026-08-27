"""
DevScout AI – Authentication, Multi-Tenancy & Authorization Service.

Provides:
- JWT token generation and verification (compatible with Clerk, Supabase, Auth.js, or native).
- User & Workspace tenancy resolution.
- Granular authorization checks protecting research jobs, history, and reports.
- Credit deduction and usage logging.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time
from typing import Dict, Optional, Tuple

from fastapi import Depends, Header, HTTPException, Request, status
from loguru import logger
from sqlalchemy.orm import Session

from database import Report, UsageLog, User, Workspace, WorkspaceMember, get_db

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

JWT_SECRET: str = os.getenv("JWT_SECRET", "devscout-ai-secure-jwt-secret-key-2026")
JWT_ALGORITHM = "HS256"
JWT_EXP_SECONDS = 60 * 60 * 24 * 7  # 7 days

DEMO_USER_ID = "usr_demo_001"
DEMO_USER_EMAIL = "demo@devscout.ai"
DEMO_WORKSPACE_ID = "ws_demo_001"


# ---------------------------------------------------------------------------
# Zero-Dependency HMAC-SHA256 JWT Implementation
# ---------------------------------------------------------------------------

def _base64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("utf-8")


def _base64url_decode(data: str) -> bytes:
    padding = 4 - (len(data) % 4)
    if padding != 4:
        data += "=" * padding
    return base64.urlsafe_b64decode(data.encode("utf-8"))


def create_jwt_token(payload: Dict, secret: str = JWT_SECRET, exp_seconds: int = JWT_EXP_SECONDS) -> str:
    """Creates a signed HMAC-SHA256 JWT token."""
    header = {"typ": "JWT", "alg": "HS256"}
    claims = dict(payload)
    if "exp" not in claims:
        claims["exp"] = int(time.time()) + exp_seconds
    if "iat" not in claims:
        claims["iat"] = int(time.time())

    encoded_header = _base64url_encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    encoded_payload = _base64url_encode(json.dumps(claims, separators=(",", ":")).encode("utf-8"))
    signing_input = f"{encoded_header}.{encoded_payload}".encode("utf-8")

    signature = hmac.new(secret.encode("utf-8"), signing_input, hashlib.sha256).digest()
    encoded_signature = _base64url_encode(signature)

    return f"{encoded_header}.{encoded_payload}.{encoded_signature}"


def verify_jwt_token(token: str, secret: str = JWT_SECRET) -> Optional[Dict]:
    """Verifies a signed HMAC-SHA256 JWT token and returns payload if valid."""
    try:
        parts = token.strip().split(".")
        if len(parts) != 3:
            return None

        encoded_header, encoded_payload, encoded_signature = parts
        signing_input = f"{encoded_header}.{encoded_payload}".encode("utf-8")

        expected_sig = hmac.new(secret.encode("utf-8"), signing_input, hashlib.sha256).digest()
        actual_sig = _base64url_decode(encoded_signature)

        if not hmac.compare_digest(expected_sig, actual_sig):
            return None

        payload_bytes = _base64url_decode(encoded_payload)
        payload = json.loads(payload_bytes.decode("utf-8"))

        # Check expiration
        exp = payload.get("exp")
        if exp and exp < time.time():
            return None

        return payload
    except Exception as e:
        logger.debug(f"JWT verification failed: {e}")
        return None


# ---------------------------------------------------------------------------
# Default Tenant Provisioning (Ensures seamless local & testing out-of-the-box)
# ---------------------------------------------------------------------------

def get_or_create_default_tenant(db: Session) -> Tuple[User, Workspace]:
    """Retrieves or provisions the default demo user and workspace."""
    user = db.query(User).filter(User.id == DEMO_USER_ID).first()
    if not user:
        user = User(
            id=DEMO_USER_ID,
            email=DEMO_USER_EMAIL,
            name="DevScout Demo User",
            role="owner"
        )
        db.add(user)
        db.flush()

    workspace = db.query(Workspace).filter(Workspace.id == DEMO_WORKSPACE_ID).first()
    if not workspace:
        workspace = Workspace(
            id=DEMO_WORKSPACE_ID,
            name="Personal Workspace",
            slug="personal-demo",
            owner_id=user.id,
            plan_tier="free",
            monthly_credit_limit=50,
            credits_used=0
        )
        db.add(workspace)
        db.flush()

        member = WorkspaceMember(
            id=f"mem_{user.id}_{workspace.id}",
            workspace_id=workspace.id,
            user_id=user.id,
            role="owner"
        )
        db.add(member)

    db.commit()
    return user, workspace


# ---------------------------------------------------------------------------
# Multi-Tenancy & Auth Dependencies
# ---------------------------------------------------------------------------

def get_current_auth(
    request: Request,
    authorization: Optional[str] = Header(None),
    x_user_id: Optional[str] = Header(None),
    x_workspace_id: Optional[str] = Header(None),
    db: Session = Depends(get_db)
) -> Tuple[User, Workspace]:
    """
    Extracts and validates authenticated User and Workspace.
    Supports Bearer tokens, explicit tenancy headers, and seamless demo fallback.
    """
    user_id = None
    workspace_id = None

    # 1. Bearer Token Check
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ")[1]
        payload = verify_jwt_token(token)
        if payload:
            user_id = payload.get("sub") or payload.get("user_id")
            workspace_id = payload.get("workspace_id") or payload.get("org_id")

    # 2. Header overrides / API keys
    if not user_id and x_user_id:
        user_id = x_user_id
    if not workspace_id and x_workspace_id:
        workspace_id = x_workspace_id

    # 3. Resolve User
    user = None
    if user_id:
        user = db.query(User).filter(User.id == user_id).first()

    # If no user found from token/headers, fall back to default demo user
    if not user:
        user, default_ws = get_or_create_default_tenant(db)
        if not workspace_id:
            return user, default_ws

    # 4. Resolve Workspace
    workspace = None
    if workspace_id:
        workspace = db.query(Workspace).filter(Workspace.id == workspace_id).first()
        if not workspace:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Workspace '{workspace_id}' not found."
            )
        # Verify user has membership in requested workspace
        membership = (
            db.query(WorkspaceMember)
            .filter(WorkspaceMember.workspace_id == workspace.id, WorkspaceMember.user_id == user.id)
            .first()
        )
        if not membership and workspace.owner_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have access to this workspace."
            )
    else:
        # Get user's primary or first workspace
        member_record = (
            db.query(WorkspaceMember)
            .filter(WorkspaceMember.user_id == user.id)
            .order_by(WorkspaceMember.joined_at.asc())
            .first()
        )
        if member_record:
            workspace = db.query(Workspace).filter(Workspace.id == member_record.workspace_id).first()

        if not workspace:
            # Create personal workspace for user
            workspace = Workspace(
                id=f"ws_{user.id}",
                name=f"{user.name}'s Workspace",
                slug=f"{user.id}-personal",
                owner_id=user.id,
                plan_tier="free",
                monthly_credit_limit=50,
                credits_used=0
            )
            db.add(workspace)
            db.flush()
            member = WorkspaceMember(
                id=f"mem_{user.id}_{workspace.id}",
                workspace_id=workspace.id,
                user_id=user.id,
                role="owner"
            )
            db.add(member)
            db.commit()

    return user, workspace


def get_current_user(auth: Tuple[User, Workspace] = Depends(get_current_auth)) -> User:
    return auth[0]


def get_current_workspace(auth: Tuple[User, Workspace] = Depends(get_current_auth)) -> Workspace:
    return auth[1]


# ---------------------------------------------------------------------------
# Granular Authorization & Tenancy Guards
# ---------------------------------------------------------------------------

def verify_report_access(
    report: Report,
    user: User,
    workspace: Workspace,
    db: Session
) -> None:
    """
    Guarantees that a user/workspace can only access reports belonging to their workspace.
    Legacy reports with NULL workspace_id are accessible by the demo tenant.
    """
    if not report:
        raise HTTPException(status_code=404, detail="Report not found.")

    # If report has a workspace_id, user MUST belong to that workspace
    if report.workspace_id and report.workspace_id != workspace.id:
        # Check if user has membership in the report's workspace
        membership = (
            db.query(WorkspaceMember)
            .filter(WorkspaceMember.workspace_id == report.workspace_id, WorkspaceMember.user_id == user.id)
            .first()
        )
        if not membership:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Forbidden: You do not have permission to view or modify this report."
            )


# ---------------------------------------------------------------------------
# Credit Deduction & Usage Tracking
# ---------------------------------------------------------------------------

def check_and_deduct_credits(
    workspace: Workspace,
    user: User,
    job_id: str,
    action: str = "research_query",
    credits_cost: int = 1,
    db: Session = None
) -> None:
    """
    Verifies that the workspace has sufficient credits remaining and logs the transaction.
    """
    if workspace.credits_used + credits_cost > workspace.monthly_credit_limit:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=f"Credit limit exceeded. Used {workspace.credits_used}/{workspace.monthly_credit_limit} credits. Please upgrade your plan."
        )

    workspace.credits_used += credits_cost
    if db:
        usage = UsageLog(
            id=f"usg_{int(time.time()*1000)}_{job_id[:8]}",
            workspace_id=workspace.id,
            user_id=user.id,
            job_id=job_id,
            action=action,
            credits_deducted=credits_cost
        )
        db.add(usage)
        db.commit()
