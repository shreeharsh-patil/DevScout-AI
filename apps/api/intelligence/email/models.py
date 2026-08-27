"""
Email Intelligence Data Models.

Provides strongly-typed, normalized Pydantic V2 data models for targets, findings,
evidence items, provider results, and comprehensive intelligence reports.
"""

from __future__ import annotations

import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, ConfigDict, Field, model_validator


def utc_now_iso() -> str:
    """Returns current UTC timestamp in ISO 8601 format."""
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


# ─── 1. Statuses & Enums ───────────────────────────────────────────────────────

class FindingStatus(str, Enum):
    """Standardized finding status & confidence classification across all providers."""
    VERIFIED = "VERIFIED"                # Cryptographic, commit author, or direct profile match
    HIGH_CONFIDENCE = "HIGH_CONFIDENCE"  # Multiple independent verified signals connecting identity
    PROBABLE = "PROBABLE"                # Strong domain or bio correlation without direct email proof
    CANDIDATE = "CANDIDATE"              # Inferred username / syntax hypothesis only
    NO_EVIDENCE = "NO_EVIDENCE"          # Searched but no data found
    UNAVAILABLE = "UNAVAILABLE"          # Provider unconfigured, rate-limited, or uncontactable
    ERROR = "ERROR"                      # Provider execution failure


# Backward-compatible alias for existing imports
ConfidenceLevel = FindingStatus


class ProviderType(str, Enum):
    COMMON = "common"
    CUSTOM = "custom"
    ACADEMIC = "academic"
    DISPOSABLE = "disposable"


class CorrelationType(str, Enum):
    EXACT_EMAIL_MENTION = "exact_email_mention"
    USERNAME_CORRELATION = "username_correlation"
    NAME_CORRELATION = "name_correlation"
    UNRELATED = "unrelated"


# ─── 2. Target Specification ───────────────────────────────────────────────────

class EmailTarget(BaseModel):
    """Normalized email target specification and validation metadata."""
    model_config = ConfigDict(str_strip_whitespace=True, populate_by_name=True, extra="ignore")

    raw_email: str = Field(alias="email")
    normalized_email: str = ""
    local_part: str = ""
    domain: str = ""
    is_valid: bool = Field(default=True, alias="valid")
    provider_type: ProviderType = ProviderType.CUSTOM
    is_disposable: bool = Field(default=False, alias="disposable")
    validation_error: Optional[str] = Field(default=None, alias="error")
    created_at: str = Field(default_factory=utc_now_iso)

    @property
    def email(self) -> str:
        return self.raw_email

    @property
    def valid(self) -> bool:
        return self.is_valid

    @property
    def disposable(self) -> bool:
        return self.is_disposable

    @property
    def error(self) -> Optional[str]:
        return self.validation_error


# Backward-compatible alias
EmailValidationResult = EmailTarget


# ─── 3. Evidence Model ─────────────────────────────────────────────────────────

class Evidence(BaseModel):
    """Verifiable concrete evidence item backing a finding."""
    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    evidence_id: str = Field(default="", alias="source_id")
    provider: str
    source_type: str
    title: str
    url: str
    retrieved_at: str = Field(default_factory=utc_now_iso)
    supports: str
    strength: str = "strong"  # deterministic, strong, moderate, weak
    snippet: str = ""
    raw_data: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="before")
    @classmethod
    def accept_legacy_platform(cls, value):
        if isinstance(value, dict) and not value.get("provider"):
            value = {**value, "provider": value.get("platform", "unknown")}
        return value

    @property
    def source_id(self) -> str:
        return self.evidence_id


# Backward-compatible alias
EvidenceItem = Evidence


# ─── 4. Base Finding Schema (Mandatory 9-Field Contract) ───────────────────────

class BaseFinding(BaseModel):
    """
    Core normalized finding schema across all providers and intelligence types.
    Every finding MUST contain these 9 standardized fields.
    """
    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    provider: str
    finding_type: str
    status: FindingStatus
    confidence_level: FindingStatus
    confidence_score: float = Field(ge=0.0, le=1.0)
    evidence_ids: List[str] = Field(default_factory=list)
    retrieved_at: str = Field(default_factory=utc_now_iso)
    error: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="before")
    @classmethod
    def accept_legacy_confidence_fields(cls, value):
        if not isinstance(value, dict):
            return value
        normalized = dict(value)
        normalized.setdefault("provider", normalized.get("platform", "unknown"))
        normalized.setdefault("status", FindingStatus.NO_EVIDENCE)
        normalized.setdefault("confidence_level", normalized["status"])
        normalized.setdefault("confidence_score", normalized.get("confidence", 0.0))
        return normalized

    @property
    def confidence(self) -> float:
        return self.confidence_score


# ─── 5. Concrete Finding Models ────────────────────────────────────────────────

class AccountFinding(BaseFinding):
    """Account discovery finding on a public registry (GitHub, Gravatar, npm, etc.)."""
    finding_type: str = "account"
    platform: str
    account_identifier: Optional[str] = None
    profile_url: Optional[str] = None
    display_name: Optional[str] = None
    avatar_url: Optional[str] = None
    bio: Optional[str] = None
    method: str = "public_profile_search"
    evidence: List[Evidence] = Field(default_factory=list)


class IdentityFinding(BaseFinding):
    """Synthesized cross-platform identity signals and metadata."""
    finding_type: str = "identity"
    possible_name: Optional[str] = None
    possible_usernames: List[str] = Field(default_factory=list)
    developer_profiles: List[Dict[str, str]] = Field(default_factory=list)
    websites: List[str] = Field(default_factory=list)
    organizations: List[str] = Field(default_factory=list)
    locations: List[str] = Field(default_factory=list)
    public_bios: List[str] = Field(default_factory=list)
    avatars: List[str] = Field(default_factory=list)
    ambiguity_note: Optional[str] = None


# Backward-compatible alias
IdentitySignals = IdentityFinding


class WebMention(BaseFinding):
    """Public web mention or citation finding."""
    finding_type: str = "web_mention"
    url: str
    title: str
    domain: str
    snippet: str
    correlation_type: CorrelationType = CorrelationType.EXACT_EMAIL_MENTION
    source_id: str = ""


# Backward-compatible alias
WebMentionFinding = WebMention


class BreachFinding(BaseFinding):
    """High-level security breach disclosure event. Strictly ZERO credentials."""
    finding_type: str = "breach"
    breach_name: str
    domain: str
    breach_date: Optional[str] = None
    data_classes: List[str] = Field(default_factory=list)
    is_verified: bool = True
    description: Optional[str] = None


class UsernameCandidate(BaseFinding):
    """Candidate username hypothesis derived from syntax rules. Strictly CANDIDATE."""
    finding_type: str = "username_candidate"
    username: str
    generation_rule: str
    matched_platforms: List[str] = Field(default_factory=list)
    evidence_note: str = (
        "Candidate handle derived from email syntax. Unverified without independent public evidence."
    )


# ─── 6. Provider Result Envelope ───────────────────────────────────────────────

class ProviderResult(BaseModel):
    """Normalized response envelope returned by every provider adapter."""
    model_config = ConfigDict(extra="ignore")

    provider: str
    finding_type: str
    status: FindingStatus
    confidence_level: FindingStatus
    confidence_score: float = Field(ge=0.0, le=1.0)
    evidence_ids: List[str] = Field(default_factory=list)
    evidence_items: List[Evidence] = Field(default_factory=list)
    findings: List[Union[AccountFinding, IdentityFinding, WebMention, BreachFinding, UsernameCandidate]] = Field(
        default_factory=list
    )
    retrieved_at: str = Field(default_factory=utc_now_iso)
    error: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


# ─── 7. Developer Footprint Model ──────────────────────────────────────────────

class DeveloperRepository(BaseModel):
    name: str
    full_name: str
    url: str
    description: Optional[str] = None
    stars: int = 0
    forks: int = 0
    language: Optional[str] = None
    updated_at: Optional[str] = None


class DeveloperFootprint(BaseModel):
    has_footprint: bool = False
    github_handle: Optional[str] = None
    gitlab_handle: Optional[str] = None
    npm_maintainer: Optional[str] = None
    repositories: List[DeveloperRepository] = Field(default_factory=list)
    top_languages: List[str] = Field(default_factory=list)
    npm_packages: List[Dict[str, Any]] = Field(default_factory=list)
    organizations: List[str] = Field(default_factory=list)
    contributions_summary: Optional[str] = None
    public_technical_mentions: List[Dict[str, Any]] = Field(default_factory=list)


# ─── 8. Assessment & Final Intelligence Report ────────────────────────────────

class ConfidenceAssessment(BaseModel):
    level: FindingStatus
    score: int = Field(ge=0, le=100)
    reasons: List[str] = Field(default_factory=list)
    verified_count: int = 0
    high_confidence_count: int = 0
    probable_count: int = 0
    candidate_count: int = 0
    formula_breakdown: Dict[str, Any] = Field(default_factory=dict)


class IntelligenceReport(BaseModel):
    """
    Standardized, strongly typed intelligence report container.
    """
    model_config = ConfigDict(extra="ignore")

    target: EmailTarget
    confidence: ConfidenceAssessment
    account_discovery: List[AccountFinding] = Field(default_factory=list)
    developer_footprint: DeveloperFootprint = Field(default_factory=DeveloperFootprint)
    web_mentions: List[WebMention] = Field(default_factory=list)
    breaches: List[BreachFinding] = Field(default_factory=list)
    breach_status: str = "checked"  # checked, unavailable, error
    username_candidates: List[UsernameCandidate] = Field(default_factory=list)
    identity_signals: IdentityFinding = Field(
        default_factory=lambda: IdentityFinding(
            provider="identity_resolver",
            finding_type="identity",
            status=FindingStatus.NO_EVIDENCE,
            confidence_level=FindingStatus.NO_EVIDENCE,
            confidence_score=0.0
        )
    )
    evidence_pool: List[Evidence] = Field(default_factory=list)
    sources: List[Dict[str, Any]] = Field(default_factory=list)
    report_markdown: str = ""
    status: str = "completed"
    error: Optional[str] = None

    # Backward-compatible properties
    @property
    def email(self) -> str:
        return self.target.normalized_email or self.target.raw_email

    @property
    def validation(self) -> EmailTarget:
        return self.target


# Backward-compatible alias
EmailIntelligenceResult = IntelligenceReport
