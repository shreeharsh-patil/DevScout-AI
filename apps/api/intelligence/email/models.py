"""
Email Intelligence Data Models.

Defines normalized data structures for evidence items, account findings, developer footprint,
breach records, username candidates, and identity resolution signals.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ConfidenceLevel(str, Enum):
    VERIFIED = "VERIFIED"                # Exact email in public commit/profile/hash evidence
    HIGH_CONFIDENCE = "HIGH_CONFIDENCE"  # Multiple independent strong signals connecting same identity
    PROBABLE = "PROBABLE"                # Strong correlation (domain ownership, bio hint) without direct email
    CANDIDATE = "CANDIDATE"              # Inferred username / weak string similarity only
    NO_EVIDENCE = "NO_EVIDENCE"          # Searched but no public account or data found
    UNAVAILABLE = "UNAVAILABLE"          # Provider unconfigured, rate-limited, or failed


class ProviderType(str, Enum):
    COMMON = "common"
    CUSTOM = "custom"
    ACADEMIC = "academic"
    DISPOSABLE = "disposable"


class EmailValidationResult(BaseModel):
    email: str
    valid: bool
    normalized_email: str
    domain: str
    local_part: str
    provider_type: ProviderType
    disposable: bool
    error: Optional[str] = None


class EvidenceItem(BaseModel):
    source_id: str
    platform: str
    source_type: str
    title: str
    url: str
    retrieved_at: str
    supports: str
    strength: str = "strong"             # deterministic, strong, moderate, weak
    snippet: str = ""
    raw_data: Optional[Dict[str, Any]] = None


class AccountFinding(BaseModel):
    platform: str
    status: ConfidenceLevel
    confidence: float = Field(ge=0.0, le=1.0)
    account_identifier: Optional[str] = None
    profile_url: Optional[str] = None
    display_name: Optional[str] = None
    avatar_url: Optional[str] = None
    bio: Optional[str] = None
    method: str
    evidence: List[EvidenceItem] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = None


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


class CorrelationType(str, Enum):
    EXACT_EMAIL_MENTION = "exact_email_mention"
    USERNAME_CORRELATION = "username_correlation"
    NAME_CORRELATION = "name_correlation"
    UNRELATED = "unrelated"


class WebMentionFinding(BaseModel):
    source_id: str
    url: str
    title: str
    domain: str
    snippet: str
    correlation_type: CorrelationType
    retrieved_at: str


class BreachFinding(BaseModel):
    breach_name: str
    domain: str
    breach_date: Optional[str] = None
    data_classes: List[str] = Field(default_factory=list)
    is_verified: bool = True
    description: Optional[str] = None
    # NOTE: Strictly ZERO sensitive credentials, passwords, or hashes are stored or returned.


class UsernameCandidate(BaseModel):
    username: str
    generation_rule: str
    confidence_level: ConfidenceLevel = ConfidenceLevel.CANDIDATE
    matched_platforms: List[str] = Field(default_factory=list)
    evidence_note: str = "Candidate handle derived from email syntax. Unverified without independent public evidence."


class IdentitySignals(BaseModel):
    possible_name: Optional[str] = None
    possible_usernames: List[str] = Field(default_factory=list)
    developer_profiles: List[Dict[str, str]] = Field(default_factory=list)
    websites: List[str] = Field(default_factory=list)
    organizations: List[str] = Field(default_factory=list)
    locations: List[str] = Field(default_factory=list)
    public_bios: List[str] = Field(default_factory=list)
    avatars: List[str] = Field(default_factory=list)
    ambiguity_note: Optional[str] = None


class ConfidenceAssessment(BaseModel):
    level: ConfidenceLevel
    score: int = Field(ge=0, le=100)
    reasons: List[str] = Field(default_factory=list)
    verified_count: int = 0
    high_confidence_count: int = 0
    probable_count: int = 0
    candidate_count: int = 0
    formula_breakdown: Dict[str, Any] = Field(default_factory=dict)


class EmailIntelligenceResult(BaseModel):
    email: str
    validation: EmailValidationResult
    confidence: ConfidenceAssessment
    account_discovery: List[AccountFinding] = Field(default_factory=list)
    developer_footprint: DeveloperFootprint = Field(default_factory=DeveloperFootprint)
    web_mentions: List[WebMentionFinding] = Field(default_factory=list)
    breaches: List[BreachFinding] = Field(default_factory=list)
    breach_status: str = "checked"       # checked, unavailable, error
    username_candidates: List[UsernameCandidate] = Field(default_factory=list)
    identity_signals: IdentitySignals = Field(default_factory=IdentitySignals)
    sources: List[Dict[str, Any]] = Field(default_factory=list)
    report_markdown: str = ""
    status: str = "completed"
    error: Optional[str] = None
