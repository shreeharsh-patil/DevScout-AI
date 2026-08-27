"""
Email Intelligence Subsystem.

Exports normalized data models, specialized agents, provider adapters, and pipeline orchestrators.
"""

from .confidence import ConfidenceEngine
from .models import (
    AccountFinding,
    BaseFinding,
    BreachFinding,
    ConfidenceAssessment,
    ConfidenceLevel,
    CorrelationType,
    DeveloperFootprint,
    DeveloperRepository,
    EmailIntelligenceResult,
    EmailTarget,
    EmailValidationResult,
    Evidence,
    EvidenceItem,
    FindingStatus,
    IdentityFinding,
    IdentitySignals,
    IntelligenceReport,
    ProviderResult,
    ProviderType,
    UsernameCandidate,
    WebMention,
    WebMentionFinding,
    utc_now_iso,
)
from .orchestrator import EmailIntelligenceOrchestrator
from .reporter import EmailIntelligenceReporter
from .validator import EmailValidatorAgent

__all__ = [
    # Core Models
    "EmailTarget",
    "ProviderResult",
    "AccountFinding",
    "IdentityFinding",
    "Evidence",
    "WebMention",
    "BreachFinding",
    "UsernameCandidate",
    "IntelligenceReport",
    # Base / Supporting Models & Enums
    "BaseFinding",
    "FindingStatus",
    "ConfidenceLevel",
    "ProviderType",
    "CorrelationType",
    "DeveloperFootprint",
    "DeveloperRepository",
    "ConfidenceAssessment",
    "utc_now_iso",
    # Aliases
    "EmailValidationResult",
    "EvidenceItem",
    "IdentitySignals",
    "WebMentionFinding",
    "EmailIntelligenceResult",
    # Orchestrator & Agents
    "EmailIntelligenceOrchestrator",
    "EmailValidatorAgent",
    "ConfidenceEngine",
    "EmailIntelligenceReporter",
]
