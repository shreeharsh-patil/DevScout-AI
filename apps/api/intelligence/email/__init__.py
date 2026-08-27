"""
Email Intelligence Module.
"""

from .confidence import ConfidenceEngine
from .models import (
    AccountFinding,
    ConfidenceAssessment,
    ConfidenceLevel,
    DeveloperFootprint,
    EmailIntelligenceResult,
    EmailValidationResult,
    EvidenceItem,
    IdentitySignals,
    UsernameCandidate,
    WebMentionFinding,
)
from .orchestrator import EmailIntelligenceOrchestrator
from .reporter import EmailIntelligenceReporter
from .validator import EmailValidatorAgent

__all__ = [
    "EmailIntelligenceOrchestrator",
    "EmailValidatorAgent",
    "ConfidenceEngine",
    "EmailIntelligenceReporter",
    "EmailIntelligenceResult",
    "EmailValidationResult",
    "ConfidenceAssessment",
    "ConfidenceLevel",
    "AccountFinding",
    "DeveloperFootprint",
    "EvidenceItem",
    "IdentitySignals",
    "UsernameCandidate",
    "WebMentionFinding",
]
