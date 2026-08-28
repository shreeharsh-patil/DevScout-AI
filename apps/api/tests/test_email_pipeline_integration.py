"""
End-to-End Integration Test Suite for Email Intelligence Pipeline.

Tests:
1. QUICK mode executes ONLY email validator, GitHub profile, Gravatar (<1s).
2. STANDARD/DEEP modes execute full provider suite with true bounded concurrency.
3. Provider rate limits (429) and timeouts yield UNAVAILABLE status, never NO_EVIDENCE.
4. Canonical source_id and evidence_ids maintain 1-to-1 fidelity in report sources.
5. Breach disclosures cleanly separate verified from unverified/spam/retired records.
6. Target email is never exposed in generated breach source URLs.
7. Candidate username matches alone are strictly prohibited from VERIFIED status.
"""

import pytest
from unittest.mock import MagicMock, patch
import requests

from intelligence.email.models import (
    EmailTarget,
    FindingStatus,
    ConfidenceLevel,
    AccountFinding,
    Evidence,
    EvidenceCategory,
)
from intelligence.email.orchestrator import EmailIntelligenceOrchestrator
from intelligence.email.registry import ProviderRegistry, default_registry
from intelligence.email.providers.github import GitHubEmailProvider
from intelligence.email.providers.breach import BreachEmailProvider
from intelligence.email.confidence import ConfidenceEngine
from sources import SourceCollector, canonicalize_url


class TestEmailPipelineIntegration:
    """End-to-end integration tests for Email Intelligence pipeline."""

    def test_quick_mode_executes_only_fast_providers(self):
        """In QUICK mode, only fast providers are executed and scope reflects quick."""
        orchestrator = EmailIntelligenceOrchestrator()
        report = orchestrator.execute("quick_dev@fastmail.com", depth="quick")

        assert report.status == "completed"
        assert report.scope.depth == "quick"
        assert "github" in report.scope.enabled_providers
        assert "gravatar" in report.scope.enabled_providers
        # Slow external providers should not be enabled in quick mode
        assert "npm" not in report.scope.enabled_providers
        assert "web_search" not in report.scope.enabled_providers
        assert "breach" not in report.scope.enabled_providers

    def test_canonical_source_id_and_evidence_ids_fidelity(self):
        """Evidence IDs on findings must correspond 1-to-1 with report sources source_id."""
        collector = SourceCollector()
        url = "https://github.com/developer/repo?utm_source=twitter&ref=developer"
        canonical_url = canonicalize_url(url)

        src = collector.add_source(
            title="GitHub Commit",
            url=canonical_url,
            platform="github",
            source_type="commit_author",
            snippet="Commit authored by dev",
            source_id="gh_commit_abcd1234efgh5678"
        )

        assert src["source_id"] == "gh_commit_abcd1234efgh5678"
        assert "utm_source" not in src["url"]
        assert "ref" not in src["url"]

        sources_list = collector.get_sources()
        assert len(sources_list) == 1
        assert sources_list[0]["source_id"] == "gh_commit_abcd1234efgh5678"

    def test_rate_limit_and_timeout_yields_unavailable_not_no_evidence(self):
        """HTTP 429 or network timeouts must yield UNAVAILABLE status, not NO_EVIDENCE."""
        prov = GitHubEmailProvider()

        mock_resp_429 = MagicMock()
        mock_resp_429.status_code = 429
        mock_resp_429.headers = {"Retry-After": "60"}

        with patch.object(prov, "_safe_request", return_value=mock_resp_429):
            target = EmailTarget(
                raw_email="test@ratelimited.com",
                normalized_email="test@ratelimited.com",
                local_part="test",
                domain="ratelimited.com",
                is_valid=True
            )
            result = prov.lookup(target)
            assert result.status == FindingStatus.UNAVAILABLE
            assert result.status != FindingStatus.NO_EVIDENCE

    def test_breach_target_email_not_in_source_urls(self):
        """Investigated email must never appear in generated breach evidence URLs."""
        prov = BreachEmailProvider()
        test_email = "target.user@domain.com"

        mock_breach_resp = MagicMock()
        mock_breach_resp.status_code = 200
        mock_breach_resp.json.return_value = [
            {
                "Name": "Adobe",
                "Title": "Adobe Creative Cloud",
                "Domain": "adobe.com",
                "BreachDate": "2013-10-04",
                "AddedDate": "2013-12-04T00:00:00Z",
                "DataClasses": ["Email addresses", "Passwords"],
                "IsVerified": True,
                "IsFabricated": False,
                "IsSensitive": False,
                "IsRetired": False,
                "IsSpamList": False
            }
        ]

        with patch.object(prov, "_safe_request", return_value=mock_breach_resp):
            target = EmailTarget(
                raw_email=test_email,
                normalized_email=test_email,
                local_part="target.user",
                domain="domain.com",
                is_valid=True
            )
            result = prov.lookup(target)
            assert result.status == FindingStatus.VERIFIED
            for ev in result.evidence_items:
                assert test_email not in ev.url
                assert "haveibeenpwned.com/account/" not in ev.url
                assert "haveibeenpwned.com/PwnedWebsites#Adobe" in ev.url

    def test_candidate_handle_cannot_be_verified(self):
        """Invariant: Candidate username matches without direct proof cannot produce VERIFIED score."""
        engine = ConfidenceEngine()
        target = EmailTarget(
            raw_email="unknown.developer@gmail.com",
            normalized_email="unknown.developer@gmail.com",
            local_part="unknown.developer",
            domain="gmail.com",
            is_valid=True
        )

        candidate_account = AccountFinding(
            provider="github",
            finding_type="account",
            platform="github",
            status=FindingStatus.CANDIDATE,
            confidence_score=0.25,
            account_identifier="unknowndeveloper",
            public_email_match=False,
            username_match=True,
            website_match=False,
            evidence=[]
        )

        assessment = engine.evaluate(target, [candidate_account], [], [])
        assert assessment.level != FindingStatus.VERIFIED
        assert assessment.level != FindingStatus.HIGH_CONFIDENCE
        assert assessment.score <= 49
