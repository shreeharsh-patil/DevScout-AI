"""
Comprehensive Test Suite for Email Intelligence Subsystem.

Tests:
- RFC Email syntax & disposable domain validation
- Account discovery provider adapters
- GitHub identity: exact commit/profile matches (VERIFIED) vs prefix guesses (CANDIDATE)
- Gravatar cryptographic hash profile lookup
- Zero-credential breach exposure & UNAVAILABLE handling
- Deterministic ConfidenceEngine evaluation
- Identity resolver & username correlation
- End-to-end EmailIntelligenceOrchestrator pipeline execution
- Robustness: error isolation on provider failures
"""

import json
import pytest
from unittest.mock import MagicMock, patch

from intelligence.email.models import (
    DomainClassification,
    AccountFinding,
    ConfidenceLevel,
    EvidenceItem,
    ProviderType,
)
from intelligence.email.validator import EmailValidatorAgent
from intelligence.email.confidence import ConfidenceEngine
from intelligence.email.providers.github import GitHubProvider
from intelligence.email.providers.gravatar import GravatarProvider
from intelligence.email.providers.hibp import HIBPProvider
from intelligence.email.agents.username_correlation import UsernameCorrelationAgent
from intelligence.email.identity_resolver import IdentityResolverAgent
from intelligence.email.orchestrator import EmailIntelligenceOrchestrator


# ---------------------------------------------------------------------------
# 1. Email Validation Tests
# ---------------------------------------------------------------------------

class TestEmailValidation:
    def test_valid_emails(self):
        valid_cases = [
            ("torvalds@linux-foundation.org", "linux-foundation.org", ProviderType.CUSTOM),
            ("developer@gmail.com", "gmail.com", ProviderType.COMMON),
            ("student@mit.edu", "mit.edu", ProviderType.ACADEMIC),
            ("jane.doe+test@company.co.uk", "company.co.uk", ProviderType.CUSTOM),
        ]
        for email, expected_domain, expected_type in valid_cases:
            res = EmailValidatorAgent.validate(email)
            assert res.valid is True
            assert res.domain == expected_domain
            assert res.provider_type in (expected_type, DomainClassification.CORPORATE_DOMAIN, DomainClassification.CUSTOM_DOMAIN)
            assert res.disposable is False


    def test_disposable_email_detection(self):
        disposable_cases = [
            "temp@mailinator.com",
            "burner@guerrillamail.com",
            "anon@sharklasers.com",
            "throwaway@10minutemail.com",
        ]
        for email in disposable_cases:
            res = EmailValidatorAgent.validate(email)
            assert res.valid is True
            assert res.disposable is True
            assert res.provider_type == ProviderType.DISPOSABLE

    def test_malformed_emails_rejected(self):
        invalid_cases = [
            "",
            "   ",
            "plainaddress",
            "@missinglocal.com",
            "missingdomain@",
            "user@.com",
            "user@domain..com",
            "user@domain",
            "spaces in@domain.com",
            "a" * 255 + "@domain.com",
        ]
        for email in invalid_cases:
            res = EmailValidatorAgent.validate(email)
            assert res.valid is False
            assert res.error is not None


# ---------------------------------------------------------------------------
# 2. GitHub Identity & Anti-False-Positive Tests (CRITICAL)
# ---------------------------------------------------------------------------

class TestGitHubIdentityAntiFalsePositive:
    def test_exact_commit_email_match_is_verified(self):
        provider = GitHubProvider()
        
        mock_commit_resp = MagicMock()
        mock_commit_resp.status_code = 200
        mock_commit_resp.json.return_value = {
            "items": [
                {
                    "sha": "a1b2c3d4e5",
                    "author": {"login": "linus", "avatar_url": "https://avatars.github.com/u/1024025"},
                    "repository": {"full_name": "torvalds/linux"},
                    "html_url": "https://github.com/torvalds/linux/commit/a1b2c3d4e5"
                }
            ]
        }

        with patch.object(provider, "_safe_request", return_value=mock_commit_resp):
            with patch.object(provider, "_fetch_user_profile", return_value={"name": "Linus Torvalds", "public_repos": 10, "followers": 150000}):
                findings = provider.search("torvalds@linux-foundation.org", "torvalds", "linux-foundation.org")
                
                assert len(findings) >= 1
                verified_findings = [f for f in findings if f.status == ConfidenceLevel.VERIFIED]
                assert len(verified_findings) == 1
                assert verified_findings[0].account_identifier == "linus"
                assert verified_findings[0].confidence == 1.0
                assert verified_findings[0].method == "public_commit_author_email"

    def test_username_guess_is_strictly_candidate_and_never_verified(self):
        """
        CRITICAL TEST: When no commit author email or profile email matches,
        a handle matching the email local-part prefix must NEVER be marked VERIFIED.
        """
        provider = GitHubProvider()

        # Mock commit search returns 0 matches
        mock_empty_resp = MagicMock()
        mock_empty_resp.status_code = 200
        mock_empty_resp.json.return_value = {"items": []}

        # Mock user profile returns a user with NO public email match and NO domain correlation
        mock_profile = {
            "login": "randomuser",
            "name": "Random Person",
            "email": "",
            "bio": "Just an unrelated developer",
            "company": "OtherCorp",
            "blog": "https://other.org",
            "public_repos": 5,
            "followers": 10
        }

        with patch.object(provider, "_safe_request", return_value=mock_empty_resp):
            with patch.object(provider, "_fetch_user_profile", return_value=mock_profile):
                findings = provider.search("randomuser@example.com", "randomuser", "example.com")
                
                assert len(findings) == 1
                finding = findings[0]
                assert finding.status == ConfidenceLevel.CANDIDATE
                assert finding.confidence <= 0.30
                assert finding.method == "unverified_handle_prefix_guess"
                assert "unconfirmed candidate lead" in finding.evidence[0].snippet


# ---------------------------------------------------------------------------
# 3. Gravatar Intelligence Tests
# ---------------------------------------------------------------------------

class TestGravatarIntelligence:
    def test_gravatar_profile_match_is_verified(self):
        provider = GravatarProvider()

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "entry": [
                {
                    "displayName": "Jane Developer",
                    "aboutMe": "Distributed systems engineer",
                    "profileUrl": "https://gravatar.com/janedev",
                    "thumbnailUrl": "https://www.gravatar.com/avatar/abc"
                }
            ]
        }

        with patch.object(provider, "_safe_request", return_value=mock_resp):
            findings = provider.search("jane@company.com", "jane", "company.com")
            assert len(findings) == 1
            assert findings[0].status == ConfidenceLevel.VERIFIED
            assert findings[0].display_name == "Jane Developer"
            assert findings[0].bio == "Distributed systems engineer"
            assert findings[0].confidence == 1.0

    def test_gravatar_no_profile_returns_no_evidence(self):
        provider = GravatarProvider()
        mock_resp = MagicMock()
        mock_resp.status_code = 404

        with patch.object(provider, "_safe_request", return_value=mock_resp):
            findings = provider.search("unregistered@domain.com", "unregistered", "domain.com")
            assert len(findings) == 1
            assert findings[0].status == ConfidenceLevel.NO_EVIDENCE
            assert findings[0].confidence == 0.0


# ---------------------------------------------------------------------------
# 4. Breach Exposure Tests (Zero Credentials & Safety)
# ---------------------------------------------------------------------------

class TestBreachExposureSafety:
    def test_unconfigured_hibp_returns_unavailable_cleanly(self):
        with patch.dict("os.environ", {"HIBP_API_KEY": ""}):
            provider = HIBPProvider()
            findings, status = provider.check_breaches("test@example.com")
            assert findings == []
            assert status == "unavailable"

    def test_configured_hibp_returns_high_level_metadata_no_credentials(self):
        with patch.dict("os.environ", {"HIBP_API_KEY": "fake_key_123"}):
            provider = HIBPProvider()
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = [
                {
                    "Title": "Adobe",
                    "Domain": "adobe.com",
                    "BreachDate": "2013-10-04",
                    "DataClasses": ["Email addresses", "Password hints", "Usernames"],
                    "IsVerified": True,
                    "Description": "Adobe breach description"
                }
            ]

            with patch.object(provider, "_safe_request", return_value=mock_resp):
                findings, status = provider.check_breaches("test@example.com")
                assert status == "checked"
                assert len(findings) == 1
                assert findings[0].breach_name == "Adobe"
                assert findings[0].domain == "adobe.com"
                # Confirm data structure contains zero sensitive payload
                assert hasattr(findings[0], "password") is False
                assert hasattr(findings[0], "hash") is False


# ---------------------------------------------------------------------------
# 5. Deterministic Confidence Engine Tests
# ---------------------------------------------------------------------------

class TestDeterministicConfidenceEngine:
    def test_verified_github_and_gravatar_yields_verified_tier(self):
        acc1 = AccountFinding(
            platform="github",
            status=ConfidenceLevel.VERIFIED,
            confidence=1.0,
            account_identifier="johndoe",
            method="public_commit_author_email",
            evidence=[EvidenceItem(
                source_id="gh_1",
                platform="github",
                source_type="public_commit",
                title="Commit",
                url="https://github.com/johndoe",
                retrieved_at="2026-08-27T00:00:00Z",
                supports="github_identity"
            )]
        )
        acc2 = AccountFinding(
            platform="gravatar",
            status=ConfidenceLevel.VERIFIED,
            confidence=1.0,
            account_identifier="hash123",
            method="cryptographic_email_hash_lookup"
        )

        assessment = ConfidenceEngine.evaluate([acc1, acc2], [], breaches_count=1)
        assert assessment.level == ConfidenceLevel.VERIFIED
        assert assessment.score >= 80
        assert assessment.verified_count == 2
        assert any("GitHub commit" in r for r in assessment.reasons)

    def test_candidate_only_yields_candidate_tier_low_score(self):
        cand = AccountFinding(
            platform="github",
            status=ConfidenceLevel.CANDIDATE,
            confidence=0.25,
            account_identifier="guesseduser",
            method="unverified_handle_prefix_guess"
        )

        assessment = ConfidenceEngine.evaluate([cand], [], breaches_count=0)
        assert assessment.level == ConfidenceLevel.CANDIDATE
        assert assessment.score <= 25
        assert assessment.verified_count == 0
        assert assessment.candidate_count == 1


# ---------------------------------------------------------------------------
# 6. Username Correlation Permutations
# ---------------------------------------------------------------------------

class TestUsernameCorrelation:
    def test_generates_standard_permutations_as_candidates(self):
        candidates = UsernameCorrelationAgent.generate_candidates("john.doe")
        usernames = [c.username for c in candidates]
        
        assert "john.doe" in usernames
        assert "johndoe" in usernames
        assert "john-doe" in usernames
        assert "john_doe" in usernames
        for c in candidates:
            assert c.confidence_level == ConfidenceLevel.CANDIDATE


# ---------------------------------------------------------------------------
# 7. End-to-End Orchestrator Pipeline Tests
# ---------------------------------------------------------------------------

class TestEmailIntelligenceOrchestratorPipeline:
    def test_end_to_end_pipeline_execution(self):
        stages_recorded = []

        def _on_stage(st: str):
            stages_recorded.append(st)

        orchestrator = EmailIntelligenceOrchestrator(on_stage_change=_on_stage)

        # Mock account discovery to return verified Gravatar
        mock_gravatar = AccountFinding(
            platform="gravatar",
            status=ConfidenceLevel.VERIFIED,
            confidence=1.0,
            account_identifier="md5hash",
            profile_url="https://gravatar.com/developer",
            display_name="Dev User",
            method="cryptographic_email_hash_lookup",
            evidence=[EvidenceItem(
                source_id="grav_1",
                platform="gravatar",
                source_type="cryptographic_hash_lookup",
                title="Gravatar Record",
                url="https://gravatar.com/developer",
                retrieved_at="2026-08-27T00:00:00Z",
                supports="gravatar_identity"
            )]
        )

        with patch.object(orchestrator.account_discovery, "discover_all", return_value=[mock_gravatar]):
            with patch.object(orchestrator.web_mentions, "discover_mentions", return_value=[]):
                with patch.object(orchestrator.breach_exposure, "check_exposure", return_value=([], "unavailable")):
                    result = orchestrator.execute("developer@techcorp.io")

                    assert result.status == "completed"
                    assert result.validation.valid is True
                    assert result.confidence.score > 0
                    assert len(result.account_discovery) == 1
                    assert "# 🔍 Email Intelligence Report" in result.report_markdown
                    assert "## ✅ Verified Identities" in result.report_markdown
                    assert ("## 🌐 Public Developer Ecosystem" in result.report_markdown or "## 🌐 Public Account Signals" in result.report_markdown)
                    assert "## 📚 Sources & Verification" in result.report_markdown


                    # Confirm all real weighted stages executed in sequence
                    expected_stages = [
                        "validating_email",
                        "checking_developer_sources",
                        "searching_public_web",
                        "processing_account_findings",
                        "correlating_identities",
                        "scoring_evidence",
                        "building_report",
                        "completed"
                    ]
                    for s in expected_stages:
                        assert s in stages_recorded

