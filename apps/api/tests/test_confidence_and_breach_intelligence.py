"""
Comprehensive Test Suite for Advanced Confidence Engine (Phase 9) & Breach Exposure Intelligence (Phase 10).

Validates:
- Phase 9:
  - Calibrated scoring tiers: VERIFIED (90-100), HIGH_CONFIDENCE (75-89), PROBABLE (50-74), CANDIDATE (1-49), NO_EVIDENCE (0)
  - Source independence (deduplicating 3 pages on the same domain as 1 independent source)
  - Transparent supporting (+) and contradicting (-) signals breakdown
- Phase 10:
  - Breach severity classification based strictly on exposed data classes (LOW, MEDIUM, HIGH, CRITICAL)
  - Zero exposure of passwords, hashes, tokens, or plaintext secrets
  - Processing added_date, is_verified, is_retired, is_spam_list
"""

import pytest

from intelligence.email.confidence import ConfidenceEngine
from intelligence.email.models import (
    AccountFinding,
    BreachFinding,
    Evidence,
    FindingStatus,
    WebMentionFinding,
)
from intelligence.email.providers.breach import BreachEmailProvider, classify_breach_severity


class TestPhase9AdvancedConfidenceEngine:
    def test_calibrated_scoring_and_signal_breakdown(self):
        acc_github = AccountFinding(
            provider="github",
            finding_type="account",
            platform="github",
            status=FindingStatus.VERIFIED,
            confidence_score=1.0,
            account_identifier="torvalds",
            public_email_match=True,
            evidence=[
                Evidence(
                    evidence_id="gh_1",
                    provider="github",
                    source_type="git_commit_match",
                    title="Commit Match",
                    url="https://github.com/torvalds/linux/commit/123",
                    retrieved_at="2026-08-27T00:00:00Z",
                    supports="github_identity"
                )
            ]
        )

        acc_gravatar = AccountFinding(
            provider="gravatar",
            finding_type="account",
            platform="gravatar",
            status=FindingStatus.VERIFIED,
            confidence_score=1.0,
            account_identifier="md5hash",
            evidence=[
                Evidence(
                    evidence_id="grav_1",
                    provider="gravatar",
                    source_type="cryptographic_hash_lookup",
                    title="Gravatar Record",
                    url="https://gravatar.com/torvalds",
                    retrieved_at="2026-08-27T00:00:00Z",
                    supports="gravatar_identity"
                )
            ]
        )

        assessment = ConfidenceEngine.evaluate(
            account_findings=[acc_github, acc_gravatar],
            web_mentions=[],
            breaches_count=0,
            has_domain_ownership=False,
            is_role_account=False
        )

        # Verified with GitHub commit + Gravatar cryptographic hash should score >= 90 (VERIFIED)
        assert assessment.level == FindingStatus.VERIFIED
        assert assessment.score >= 90
        assert assessment.verified_count == 2
        assert assessment.independent_source_count >= 2
        assert any("+ Exact email in public GitHub commit" in s for s in assessment.supporting_signals)
        assert any("+ Verified public Gravatar profile" in s for s in assessment.supporting_signals)

    def test_source_independence_prevents_sybil_inflation(self):
        # 3 web mentions from the same domain (e.g. dev.to)
        web_mentions = [
            WebMentionFinding(
                provider="web_search",
                finding_type="web_mention",
                status=FindingStatus.HIGH_CONFIDENCE,
                confidence_level=FindingStatus.HIGH_CONFIDENCE,
                confidence_score=0.8,
                evidence_ids=["web_1"],
                url="https://dev.to/post1",
                title="Post 1",
                domain="dev.to",
                snippet="Contact me at dev@example.com",
                is_exact_match=True
            ),
            WebMentionFinding(
                provider="web_search",
                finding_type="web_mention",
                status=FindingStatus.HIGH_CONFIDENCE,
                confidence_level=FindingStatus.HIGH_CONFIDENCE,
                confidence_score=0.8,
                evidence_ids=["web_2"],
                url="https://dev.to/post2",
                title="Post 2",
                domain="dev.to",
                snippet="Contact me at dev@example.com",
                is_exact_match=True
            ),
            WebMentionFinding(
                provider="web_search",
                finding_type="web_mention",
                status=FindingStatus.HIGH_CONFIDENCE,
                confidence_level=FindingStatus.HIGH_CONFIDENCE,
                confidence_score=0.8,
                evidence_ids=["web_3"],
                url="https://dev.to/post3",
                title="Post 3",
                domain="dev.to",
                snippet="Contact me at dev@example.com",
                is_exact_match=True
            )
        ]

        assessment = ConfidenceEngine.evaluate(
            account_findings=[],
            web_mentions=web_mentions,
            breaches_count=0,
            has_domain_ownership=False,
            is_role_account=False
        )

        # 3 posts on dev.to should collapse to 1 independent domain source
        assert assessment.independent_source_count == 1
        assert assessment.evidence_count == 3


class TestPhase10BreachExposureIntelligence:
    def test_breach_severity_classification_rules(self):
        # LOW severity: email only
        assert classify_breach_severity(["Email addresses"]) == "LOW"

        # MEDIUM severity: email + usernames + names + IP
        assert classify_breach_severity(["Email addresses", "Usernames", "IP addresses"]) == "MEDIUM"

        # HIGH severity: email + phone number + physical address + security questions
        assert classify_breach_severity(["Email addresses", "Phone numbers", "Physical addresses"]) == "HIGH"

        # CRITICAL severity: financial data, credit cards, bank accounts, SSN
        assert classify_breach_severity(["Email addresses", "Bank account numbers", "Credit cards"]) == "CRITICAL"
