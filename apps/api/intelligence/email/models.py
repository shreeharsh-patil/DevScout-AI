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


class DomainClassification(str, Enum):
    CONSUMER_PROVIDER = "consumer_provider"
    CUSTOM_DOMAIN = "custom_domain"
    CORPORATE_DOMAIN = "corporate_domain"
    EDUCATION_DOMAIN = "education_domain"
    GOVERNMENT_DOMAIN = "government_domain"
    DISPOSABLE = "disposable"
    UNKNOWN = "unknown"
    # Legacy alias values
    COMMON = "consumer_provider"
    CUSTOM = "custom_domain"
    ACADEMIC = "education_domain"


# Backward-compatible alias
ProviderType = DomainClassification


class CorrelationType(str, Enum):
    EXACT_EMAIL_MENTION = "exact_email_mention"
    USERNAME_CORRELATION = "username_correlation"
    NAME_CORRELATION = "name_correlation"
    UNRELATED = "unrelated"


class ProviderHealthStatus(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    RATE_LIMITED = "rate_limited"
    UNAVAILABLE = "unavailable"
    FAILED = "failed"


class ProviderHealthReport(BaseModel):
    """Health check status and telemetry for a provider."""
    model_config = ConfigDict(extra="ignore")

    provider_name: str
    status: ProviderHealthStatus
    is_available: bool
    rate_limited: bool = False
    rate_limit_reset_at: Optional[str] = None
    last_error: Optional[str] = None
    last_execution_time_ms: Optional[float] = None
    details: Dict[str, Any] = Field(default_factory=dict)
    checked_at: str = Field(default_factory=utc_now_iso)


# ─── 2. Target Specification ───────────────────────────────────────────────────

class EmailTarget(BaseModel):
    """Normalized email target specification and domain intelligence metadata."""
    model_config = ConfigDict(str_strip_whitespace=True, populate_by_name=True, extra="ignore")

    raw_email: str = Field(alias="email")
    normalized_email: str = ""
    local_part: str = ""
    domain: str = ""
    is_valid: bool = Field(default=True, alias="valid")
    domain_classification: DomainClassification = DomainClassification.CUSTOM_DOMAIN
    provider_type: DomainClassification = Field(default=DomainClassification.CUSTOM_DOMAIN)
    is_disposable: bool = Field(default=False, alias="disposable")
    is_role_account: bool = False
    role_type: Optional[str] = None
    is_custom_domain: bool = False
    has_mx_records: bool = False
    mx_records: List[str] = Field(default_factory=list)
    mx_host: Optional[str] = None
    mx_status: str = "uncertain"  # valid, unreachable, uncertain, none
    website_url: Optional[str] = None
    website_title: Optional[str] = None
    is_website_active: bool = False
    organization_name: Optional[str] = None
    domain_age_years: Optional[float] = None
    domain_created_at: Optional[str] = None
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


class SourceQuality(str, Enum):
    """Hierarchical source quality classification (Phase 16)."""
    FIRST_PARTY = "first_party"                   # Official registry API (GitHub API, npm API, PyPI API)
    DIRECT_PUBLIC_EVIDENCE = "direct_evidence"    # Public commit author, cryptographic hash, verified bio link
    SECONDARY = "secondary"                       # Reputable indexed technical web pages, documentation
    WEAK = "weak"                                 # Search engine snippet, forum discussion
    UNVERIFIED = "unverified"                     # Unconfirmed handle hypothesis / candidate guess


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
    source_quality: SourceQuality = SourceQuality.SECONDARY
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


class WebMentionCategory(str, Enum):
    """Categorized public web mention classifications."""
    EXACT_EMAIL_MENTION = "exact_email_mention"
    DEVELOPER_PROFILE_MENTION = "developer_profile_mention"
    ORGANIZATION_MENTION = "organization_mention"
    PERSONAL_WEBSITE_MENTION = "personal_website_mention"
    DOCUMENT_MENTION = "document_mention"
    FORUM_MENTION = "forum_mention"
    UNRELATED_RESULT = "unrelated_result"


# ─── 5. Concrete Finding Models ────────────────────────────────────────────────

class AccountFinding(BaseFinding):
    """Account discovery finding on a public registry (GitHub, GitLab, npm, PyPI, Crates, Gravatar, etc.)."""
    finding_type: str = "account"
    platform: str
    account_identifier: Optional[str] = None
    profile_url: Optional[str] = None
    display_name: Optional[str] = None
    avatar_url: Optional[str] = None
    bio: Optional[str] = None
    method: str = "public_profile_search"
    public_email_match: bool = False
    username_match: bool = False
    website_match: bool = False
    ecosystem_category: str = "general"
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
    mention_category: WebMentionCategory = WebMentionCategory.EXACT_EMAIL_MENTION
    source_id: str = ""
    is_exact_match: bool = False
    canonical_url: str = ""


# Backward-compatible alias
WebMentionFinding = WebMention


class BreachFinding(BaseFinding):
    """High-level security breach disclosure event. Strictly ZERO credentials."""
    finding_type: str = "breach"
    breach_name: str
    domain: str
    breach_date: Optional[str] = None
    added_date: Optional[str] = None
    data_classes: List[str] = Field(default_factory=list)
    is_verified: bool = True
    is_retired: bool = False
    is_spam_list: bool = False
    severity: str = "LOW"  # LOW, MEDIUM, HIGH, CRITICAL
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


class EvidenceCategory(str, Enum):
    """Specific category of evidence establishing identity correlation."""
    EXACT_EMAIL = "exact_email"                    # Direct cryptographic or commit author email match
    NAME_EVIDENCE = "name_evidence"                # Display name match
    USERNAME_EVIDENCE = "username_evidence"        # Handle prefix / username similarity
    ORGANIZATION_EVIDENCE = "organization_evidence"# Company or org affiliation match
    WEAK_CORRELATION = "weak_correlation"          # Bio keywords, location, or blog domain link


class GitHubCommitRecord(BaseModel):
    """Detailed public commit record associated with the target email."""
    model_config = ConfigDict(extra="ignore")

    sha: str
    repo_name: str
    repo_url: str
    author_name: str
    author_email: str
    commit_date: Optional[str] = None
    commit_message: Optional[str] = None
    commit_url: Optional[str] = None


class GitHubOrganization(BaseModel):
    """Public GitHub organization affiliation."""
    model_config = ConfigDict(extra="ignore")

    login: str
    name: Optional[str] = None
    url: str
    avatar_url: Optional[str] = None
    description: Optional[str] = None


class GitHubEvidenceGraphNode(BaseModel):
    """Node in the GitHub developer identity evidence graph."""
    model_config = ConfigDict(extra="ignore")

    id: str
    label: str
    node_type: str  # target_email, github_user, commit, repository, organization, domain, website
    value: str
    category: EvidenceCategory
    confidence: float = 1.0
    metadata: Dict[str, Any] = Field(default_factory=dict)


class GitHubEvidenceGraphEdge(BaseModel):
    """Edge representing a relationship between evidence nodes."""
    model_config = ConfigDict(extra="ignore")

    source: str
    target: str
    relationship: str  # authored_commit, owns_profile, member_of, domain_match, username_match, name_match, links_to
    strength: str = "strong"  # deterministic, strong, moderate, weak
    weight: float = 1.0
    description: str


class GitHubEvidenceGraph(BaseModel):
    """Structured graph representation of connected public identity signals."""
    model_config = ConfigDict(extra="ignore")

    nodes: List[GitHubEvidenceGraphNode] = Field(default_factory=list)
    edges: List[GitHubEvidenceGraphEdge] = Field(default_factory=list)
    summary: str = ""
    verification_tier: FindingStatus = FindingStatus.NO_EVIDENCE
    confidence_score: float = 0.0
    exact_email_matches: int = 0
    correlated_signals_count: int = 0


# ─── 7. Developer Footprint Model ──────────────────────────────────────────────

class DeveloperRepository(BaseModel):
    name: str
    full_name: str
    url: str
    description: Optional[str] = None
    stars: int = 0
    forks: int = 0
    language: Optional[str] = None
    topics: List[str] = Field(default_factory=list)
    updated_at: Optional[str] = None


class DeveloperFootprint(BaseModel):
    has_footprint: bool = False
    github_handle: Optional[str] = None
    gitlab_handle: Optional[str] = None
    npm_maintainer: Optional[str] = None
    repositories: List[DeveloperRepository] = Field(default_factory=list)
    top_languages: List[str] = Field(default_factory=list)
    language_breakdown: Dict[str, int] = Field(default_factory=dict)
    total_stars: int = 0
    total_forks: int = 0
    npm_packages: List[Dict[str, Any]] = Field(default_factory=list)
    organizations: List[str] = Field(default_factory=list)
    github_organizations: List[GitHubOrganization] = Field(default_factory=list)
    github_commits: List[GitHubCommitRecord] = Field(default_factory=list)
    evidence_graph: Optional[GitHubEvidenceGraph] = None
    bio: Optional[str] = None
    location: Optional[str] = None
    website_url: Optional[str] = None
    twitter_username: Optional[str] = None
    account_created_at: Optional[str] = None
    account_age_years: Optional[float] = None
    recent_activity_date: Optional[str] = None
    contributions_summary: Optional[str] = None
    public_technical_mentions: List[Dict[str, Any]] = Field(default_factory=list)



class IdentityCluster(BaseModel):
    """Deterministic cluster of public accounts correlated by concrete evidence links."""
    model_config = ConfigDict(extra="ignore")

    cluster_id: str
    cluster_name: str
    status: FindingStatus = FindingStatus.CANDIDATE
    confidence_score: float = 0.0
    accounts: List[AccountFinding] = Field(default_factory=list)
    shared_signals: List[str] = Field(default_factory=list)
    correlation_reasons: List[str] = Field(default_factory=list)
    ambiguity_warning: Optional[str] = None


class EvidenceGraphNode(BaseModel):
    """Interactive node in the complete Email Intelligence Evidence Graph."""
    model_config = ConfigDict(extra="ignore")

    id: str
    label: str
    node_type: str  # email, person, username, account, domain, website, organization, repository, package, breach, source
    status: str = "verified"  # verified, probable, candidate, info
    confidence: float = 1.0
    value: str = ""
    sources: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class EvidenceGraphEdge(BaseModel):
    """Interactive edge representing a relationship between intelligence entities."""
    model_config = ConfigDict(extra="ignore")

    source: str
    target: str
    relationship: str  # verified_email, mentions, owns, links_to, member_of, same_username, published_on, evidence_for, possible_match
    strength: str = "deterministic"  # deterministic, strong, moderate, weak
    weight: float = 1.0
    description: str


class EvidenceGraph(BaseModel):
    """Complete interactive graph of public developer identity and footprint evidence."""
    model_config = ConfigDict(extra="ignore")

    nodes: List[EvidenceGraphNode] = Field(default_factory=list)
    edges: List[EvidenceGraphEdge] = Field(default_factory=list)
    summary: str = ""
    verification_tier: FindingStatus = FindingStatus.NO_EVIDENCE
    confidence_score: float = 0.0
    total_nodes: int = 0
    total_edges: int = 0


# ─── 8. Assessment & Final Intelligence Report ────────────────────────────────

class ConfidenceAssessment(BaseModel):
    level: FindingStatus
    score: int = Field(ge=0, le=100)
    reasons: List[str] = Field(default_factory=list)
    supporting_signals: List[str] = Field(default_factory=list)
    contradicting_signals: List[str] = Field(default_factory=list)
    evidence_count: int = 0
    independent_source_count: int = 0
    verified_count: int = 0
    high_confidence_count: int = 0
    probable_count: int = 0
    candidate_count: int = 0
    formula_breakdown: Dict[str, Any] = Field(default_factory=dict)



class ReputationCategory(str, Enum):
    """Neutral reputation classification based on technical attributes."""
    NORMAL = "normal"
    LIMITED_PUBLIC_FOOTPRINT = "limited_public_footprint"
    ELEVATED_EXPOSURE = "elevated_exposure"
    HIGH_PUBLIC_EXPOSURE = "high_public_exposure"
    UNCERTAIN = "uncertain"


class ReputationSignal(BaseModel):
    """Neutral technical reputation signal."""
    model_config = ConfigDict(extra="ignore")

    signal_name: str
    severity: str = "info"  # info, low, medium, elevated
    description: str


class EmailReputationAssessment(BaseModel):
    """Non-invasive technical reputation and exposure assessment."""
    model_config = ConfigDict(extra="ignore")

    category: ReputationCategory = ReputationCategory.NORMAL
    signals: List[ReputationSignal] = Field(default_factory=list)
    impersonation_risk: str = "low"  # low, medium, elevated
    summary: str = ""


class SnapshotDeltaItem(BaseModel):
    """Specific change detected between historical research snapshots."""
    model_config = ConfigDict(extra="ignore")

    change_type: str  # new_account, disappeared_source, new_breach, github_activity, profile_updated, new_web_mention, domain_changed
    field_name: str
    old_value: Optional[Any] = None
    new_value: Optional[Any] = None
    description: str
    timestamp: str = Field(default_factory=utc_now_iso)


class HistoricalSnapshotComparison(BaseModel):
    """Delta analysis between previous and current investigation snapshots."""
    model_config = ConfigDict(extra="ignore")

    has_previous_scan: bool = False
    previous_scan_date: Optional[str] = None
    previous_job_id: Optional[str] = None
    changes: List[SnapshotDeltaItem] = Field(default_factory=list)
    summary: str = ""


class InvestigationScope(BaseModel):
    """Configured search depth and scope definition."""
    model_config = ConfigDict(extra="ignore")

    depth: str = "standard"  # quick, standard, deep
    estimated_coverage: str = ""
    enabled_providers: List[str] = Field(default_factory=list)
    depth_rationale: str = ""


class AIExplanation(BaseModel):
    """Structured, bounded LLM intelligence synthesis (Phase 18)."""
    model_config = ConfigDict(extra="ignore")

    summary: str
    key_highlights: List[str] = Field(default_factory=list)
    developer_archetype: str = "General Developer / Technical Contributor"
    uncertainty_notes: List[str] = Field(default_factory=list)
    generated_at: str = Field(default_factory=utc_now_iso)


class ProviderMetric(BaseModel):
    """Performance telemetry record per provider (Phase 21 & 22)."""
    model_config = ConfigDict(extra="ignore")

    provider: str
    duration_ms: float
    status: str  # success, error, rate_limited, timeout, cache_hit
    cache_hit: bool = False
    records_count: int = 0


class RedactionOptions(BaseModel):
    """Client redaction preferences for export and sharing (Phase 19)."""
    model_config = ConfigDict(extra="ignore")

    hide_target_email: bool = False
    hide_breach_info: bool = False
    hide_candidate_identities: bool = False
    hide_raw_evidence: bool = False


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
    identity_clusters: List[IdentityCluster] = Field(default_factory=list)
    evidence_graph: Optional[EvidenceGraph] = None
    reputation: EmailReputationAssessment = Field(default_factory=EmailReputationAssessment)
    historical_comparison: Optional[HistoricalSnapshotComparison] = None
    scope: InvestigationScope = Field(default_factory=InvestigationScope)
    ai_explanation: Optional[AIExplanation] = None
    provider_metrics: List[ProviderMetric] = Field(default_factory=list)
    is_shareable: bool = False
    share_token: Optional[str] = None
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



