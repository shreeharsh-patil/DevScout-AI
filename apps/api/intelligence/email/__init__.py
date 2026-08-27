"""
Email Intelligence Subsystem.

Exports normalized data models, specialized agents, provider adapters, centralized registry,
and pipeline orchestrators.
"""

from .confidence import ConfidenceEngine
from .correlation import UsernameCorrelationAgent, UsernameCorrelationEngine
from .identity_resolver import IdentityResolverAgent
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
    ProviderHealthReport,
    ProviderHealthStatus,
    ProviderResult,
    ProviderType,
    UsernameCandidate,
    WebMention,
    WebMentionFinding,
    utc_now_iso,
)
from .orchestrator import EmailIntelligenceOrchestrator
from .providers.base import BaseEmailProvider, BaseProvider
from .registry import ProviderRegistry, create_default_registry, default_registry
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
    "ProviderHealthReport",
    # Base / Supporting Models & Enums
    "BaseFinding",
    "FindingStatus",
    "ConfidenceLevel",
    "ProviderHealthStatus",
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
    # Registry & Providers
    "ProviderRegistry",
    "default_registry",
    "create_default_registry",
    "BaseEmailProvider",
    "BaseProvider",
    # Orchestrator & Agents
    "EmailIntelligenceOrchestrator",
    "EmailValidatorAgent",
    "ConfidenceEngine",
    "UsernameCorrelationEngine",
    "UsernameCorrelationAgent",
    "IdentityResolverAgent",
    "EmailIntelligenceReporter",
]
