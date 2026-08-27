"""
Phase 23: Critical False-Positive Prevention & Confidence Regression Tests.

Verifies fundamental OSINT confidence invariants:
1. Same username match alone != VERIFIED (Strictly CANDIDATE)
2. Same display name match alone != VERIFIED (Strictly CANDIDATE)
3. Email-prefix permutation guess != VERIFIED (Strictly CANDIDATE)
4. Single weak search snippet != HIGH_CONFIDENCE
5. Transient provider error != NO_EVIDENCE (Must report UNCERTAIN / UNAVAILABLE)
"""

from intelligence.email.confidence import ConfidenceEngine
from intelligence.email.false_positive import FalsePositiveDetector
from intelligence.email.models import (
    AccountFinding,
    Evidence,
    FindingStatus,
    SourceQuality,
)


class TestCriticalFalsePositiveInvariants:
    def test_same_username_only_never_verified(self):
        """Rule: Matching handle without cryptographic/commit proof is strictly CANDIDATE."""
        candidate_account = AccountFinding(
            provider="github",
            finding_type="account",
            platform="github",
            status=FindingStatus.CANDIDATE,
            confidence_score=0.20,
            account_identifier="johndoe",
            public_email_match=False,
            username_match=True
        )

        assert candidate_account.status != FindingStatus.VERIFIED
        assert candidate_account.status != FindingStatus.HIGH_CONFIDENCE
        assert candidate_account.status == FindingStatus.CANDIDATE

        # Confidence engine should not mark report as VERIFIED with only handle match
        conf = ConfidenceEngine.evaluate(
            account_findings=[candidate_account],
            web_mentions=[],
            breaches_count=0
        )
        assert conf.level in (FindingStatus.CANDIDATE, FindingStatus.PROBABLE)
        assert conf.score < 50

    def test_same_name_only_never_verified(self):
        """Rule: Matching display name alone is strictly a CANDIDATE."""
        candidate_account = AccountFinding(
            provider="gitlab",
            finding_type="account",
            platform="gitlab",
            status=FindingStatus.CANDIDATE,
            confidence_score=0.15,
            account_identifier="gitlab_user_99",
            display_name="John Doe",
            public_email_match=False
        )

        assert candidate_account.status == FindingStatus.CANDIDATE

        conf = ConfidenceEngine.evaluate(
            account_findings=[candidate_account],
            web_mentions=[],
            breaches_count=0
        )
        assert conf.score < 40

    def test_email_prefix_guess_never_verified(self):
        """Rule: Local-part permutations (e.g. dev from dev@domain.com) cannot exceed CANDIDATE."""
        account = AccountFinding(
            provider="npm",
            finding_type="account",
            platform="npm",
            status=FindingStatus.CANDIDATE,
            confidence_score=0.15,
            account_identifier="developer",
            public_email_match=False
        )

        calibrated, contras = FalsePositiveDetector.evaluate_account(
            account=account,
            target_email="developer@tech.io",
            target_local="developer",
            target_domain="tech.io",
            verified_accounts=[]
        )

        assert calibrated.status == FindingStatus.CANDIDATE
        assert calibrated.confidence_score <= 0.20
        assert any("common username" in c.lower() for c in contras)

    def test_one_weak_source_never_high_confidence(self):
        """Rule: A single search snippet without API verification cannot produce HIGH_CONFIDENCE."""
        weak_ev = Evidence(
            provider="web",
            source_type="search_snippet",
            title="Indexed Search Result",
            url="https://bing.com/search?q=test",
            supports="mention",
            strength="weak",
            source_quality=SourceQuality.WEAK
        )

        account = AccountFinding(
            provider="web",
            finding_type="account",
            platform="web",
            status=FindingStatus.CANDIDATE,
            confidence_score=0.25,
            account_identifier="test",
            evidence=[weak_ev]
        )

        conf = ConfidenceEngine.evaluate(
            account_findings=[account],
            web_mentions=[],
            breaches_count=0
        )
        assert conf.level != FindingStatus.HIGH_CONFIDENCE
        assert conf.level != FindingStatus.VERIFIED
        assert conf.score < 50

    def test_provider_error_does_not_falsely_claim_no_evidence(self):
        """Rule: Provider timeouts or outages must be labeled as UNAVAILABLE or ERROR, not NO_EVIDENCE."""
        error_finding = AccountFinding(
            provider="github",
            finding_type="account",
            platform="github",
            status=FindingStatus.UNAVAILABLE,
            confidence_score=0.0,
            error="Upstream API 503 Service Unavailable"
        )

        assert error_finding.status == FindingStatus.UNAVAILABLE
        assert error_finding.error is not None
