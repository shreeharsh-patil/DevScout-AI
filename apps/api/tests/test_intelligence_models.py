"""
Comprehensive Test Suite for Intelligence Data Models (Phase 1).

Validates:
- Creation and validation of all normalized models:
  * EmailTarget
  * ProviderResult
  * AccountFinding
  * IdentityFinding
  * Evidence
  * WebMention
  * BreachFinding
  * UsernameCandidate
  * IntelligenceReport
- Strict adherence to the 9-field BaseFinding contract
- All standardized FindingStatus values:
  VERIFIED, HIGH_CONFIDENCE, PROBABLE, CANDIDATE, NO_EVIDENCE, UNAVAILABLE, ERROR
- Full JSON serialization & round-trip deserialization
- Backward-compatibility aliases and properties
"""

import json
import pytest
from pydantic import ValidationError

from intelligence.email.models import (
    AccountFinding,
    BaseFinding,
    BreachFinding,
    ConfidenceAssessment,
    CorrelationType,
    DeveloperFootprint,
    DeveloperRepository,
    EmailTarget,
    Evidence,
    FindingStatus,
    IdentityFinding,
    IntelligenceReport,
    ProviderResult,
    ProviderType,
    UsernameCandidate,
    WebMention,
    utc_now_iso,
)


class TestIntelligenceModelsContract:
    """Validates the 9-field BaseFinding contract on all finding models."""

    def test_standardized_finding_statuses(self):
        expected_statuses = {
            "VERIFIED",
            "HIGH_CONFIDENCE",
            "PROBABLE",
            "CANDIDATE",
            "NO_EVIDENCE",
            "UNAVAILABLE",
            "ERROR",
        }
        actual_statuses = {s.value for s in FindingStatus}
        assert actual_statuses == expected_statuses

    def test_email_target_creation_and_serialization(self):
        target = EmailTarget(
            raw_email="Dev.Scout+test@Company.IO",
            normalized_email="dev.scout+test@company.io",
            local_part="dev.scout+test",
            domain="company.io",
            is_valid=True,
            provider_type=ProviderType.CUSTOM,
            is_disposable=False
        )

        # Attribute and property access
        assert target.email == "Dev.Scout+test@Company.IO"
        assert target.valid is True
        assert target.disposable is False
        assert target.domain == "company.io"
        assert target.created_at is not None

        # Serialization & round-trip
        data = target.model_dump()
        assert data["raw_email"] == "Dev.Scout+test@Company.IO"
        assert data["domain"] == "company.io"

        json_str = target.model_dump_json()
        rehydrated = EmailTarget.model_validate_json(json_str)
        assert rehydrated.normalized_email == target.normalized_email
        assert rehydrated.is_valid is True

    def test_evidence_model(self):
        ev = Evidence(
            evidence_id="src_github_01",
            provider="github",
            source_type="public_commit",
            title="Public Commit author in torvalds/linux",
            url="https://github.com/torvalds/linux/commit/123",
            supports="github_identity",
            strength="deterministic",
            snippet="Commit 123 lists email as author",
            raw_data={"sha": "123"},
            metadata={"repo": "torvalds/linux"}
        )

        assert ev.evidence_id == "src_github_01"
        assert ev.source_id == "src_github_01"  # Backward-compatible alias
        assert ev.provider == "github"
        assert ev.strength == "deterministic"

        # Roundtrip JSON
        json_data = ev.model_dump_json()
        loaded = Evidence.model_validate_json(json_data)
        assert loaded.evidence_id == ev.evidence_id
        assert loaded.metadata["repo"] == "torvalds/linux"

    def test_account_finding_adheres_to_base_contract(self):
        ev = Evidence(
            evidence_id="ev_gh_1",
            provider="github",
            source_type="public_profile",
            title="GitHub Profile",
            url="https://github.com/octocat",
            supports="github_identity"
        )
        finding = AccountFinding(
            provider="github",
            finding_type="account",
            platform="github",
            status=FindingStatus.VERIFIED,
            confidence_level=FindingStatus.VERIFIED,
            confidence_score=1.0,
            evidence_ids=["ev_gh_1"],
            retrieved_at=utc_now_iso(),
            account_identifier="octocat",
            profile_url="https://github.com/octocat",
            display_name="The Octocat",
            avatar_url="https://github.com/octocat.png",
            bio="GitHub mascot and developer",
            method="public_profile_email",
            evidence=[ev],
            metadata={"public_repos": 8}
        )

        # Check 9 mandatory base fields
        assert finding.provider == "github"
        assert finding.finding_type == "account"
        assert finding.status == FindingStatus.VERIFIED
        assert finding.confidence_level == FindingStatus.VERIFIED
        assert finding.confidence_score == 1.0
        assert finding.confidence == 1.0  # Backward-compatible property
        assert finding.evidence_ids == ["ev_gh_1"]
        assert finding.retrieved_at is not None
        assert finding.error is None
        assert finding.metadata["public_repos"] == 8

        # Check Account specific fields
        assert finding.platform == "github"
        assert finding.account_identifier == "octocat"
        assert finding.profile_url == "https://github.com/octocat"

        # Serialization roundtrip
        dump = finding.model_dump()
        assert dump["finding_type"] == "account"
        rebuilt = AccountFinding.model_validate(dump)
        assert rebuilt.account_identifier == "octocat"

    def test_identity_finding_model(self):
        finding = IdentityFinding(
            provider="identity_resolver",
            finding_type="identity",
            status=FindingStatus.PROBABLE,
            confidence_level=FindingStatus.PROBABLE,
            confidence_score=0.75,
            evidence_ids=["ev_1", "ev_2"],
            possible_name="Linus Torvalds",
            possible_usernames=["torvalds", "linus"],
            developer_profiles=[{"platform": "github", "url": "https://github.com/torvalds"}],
            websites=["https://kernel.org"],
            organizations=["Linux Foundation"],
            locations=["Portland, OR"],
            public_bios=["Creator of Linux & Git"],
            avatars=["https://avatars.github.com/u/1024025"],
            metadata={"correlations_count": 2}
        )

        assert finding.provider == "identity_resolver"
        assert finding.possible_name == "Linus Torvalds"
        assert len(finding.possible_usernames) == 2
        assert finding.status == FindingStatus.PROBABLE

        json_str = finding.model_dump_json()
        rebuilt = IdentityFinding.model_validate_json(json_str)
        assert rebuilt.organizations == ["Linux Foundation"]

    def test_web_mention_model(self):
        mention = WebMention(
            provider="web",
            finding_type="web_mention",
            status=FindingStatus.HIGH_CONFIDENCE,
            confidence_level=FindingStatus.HIGH_CONFIDENCE,
            confidence_score=0.85,
            evidence_ids=["web_1"],
            url="https://example.com/team",
            title="Core Engineering Team",
            domain="example.com",
            snippet="Contact our engineer at dev@example.com for inquiries.",
            correlation_type=CorrelationType.EXACT_EMAIL_MENTION
        )

        assert mention.provider == "web"
        assert mention.finding_type == "web_mention"
        assert mention.correlation_type == CorrelationType.EXACT_EMAIL_MENTION
        assert mention.domain == "example.com"

        dump = mention.model_dump()
        assert dump["url"] == "https://example.com/team"

    def test_breach_finding_model(self):
        breach = BreachFinding(
            provider="hibp",
            finding_type="breach",
            status=FindingStatus.VERIFIED,
            confidence_level=FindingStatus.VERIFIED,
            confidence_score=0.90,
            evidence_ids=["hibp_dropbox"],
            breach_name="Dropbox",
            domain="dropbox.com",
            breach_date="2012-07-01",
            data_classes=["Email addresses", "Passwords"],
            is_verified=True,
            description="In 2012, Dropbox suffered a breach."
        )

        assert breach.provider == "hibp"
        assert breach.finding_type == "breach"
        assert breach.breach_name == "Dropbox"
        assert "Email addresses" in breach.data_classes
        # Verify strictly zero sensitive fields exist
        assert hasattr(breach, "plaintext_password") is False
        assert hasattr(breach, "hash") is False

    def test_username_candidate_model(self):
        candidate = UsernameCandidate(
            provider="username_correlation",
            finding_type="username_candidate",
            status=FindingStatus.CANDIDATE,
            confidence_level=FindingStatus.CANDIDATE,
            confidence_score=0.20,
            evidence_ids=[],
            username="john-doe",
            generation_rule="hyphen_separated",
            matched_platforms=["github"],
            evidence_note="Candidate handle derived from syntax."
        )

        assert candidate.status == FindingStatus.CANDIDATE
        assert candidate.username == "john-doe"
        assert candidate.generation_rule == "hyphen_separated"

    def test_provider_result_envelope(self):
        ev = Evidence(
            evidence_id="ev_npm_1",
            provider="npm",
            source_type="package_registry",
            title="npm Package Maintainer",
            url="https://npmjs.com/~developer",
            supports="npm_footprint"
        )
        acc = AccountFinding(
            provider="npm",
            finding_type="account",
            platform="npm",
            status=FindingStatus.VERIFIED,
            confidence_level=FindingStatus.VERIFIED,
            confidence_score=0.95,
            evidence_ids=["ev_npm_1"],
            account_identifier="developer",
            method="npm_registry_maintainer_search",
            evidence=[ev]
        )
        result = ProviderResult(
            provider="npm",
            finding_type="account",
            status=FindingStatus.VERIFIED,
            confidence_level=FindingStatus.VERIFIED,
            confidence_score=0.95,
            evidence_ids=["ev_npm_1"],
            evidence_items=[ev],
            findings=[acc]
        )

        assert result.provider == "npm"
        assert len(result.findings) == 1
        assert len(result.evidence_items) == 1

        json_data = result.model_dump_json()
        rehydrated = ProviderResult.model_validate_json(json_data)
        assert rehydrated.provider == "npm"
        assert len(rehydrated.findings) == 1

    def test_intelligence_report_full_lifecycle_and_serialization(self):
        target = EmailTarget(
            raw_email="founder@company.com",
            normalized_email="founder@company.com",
            local_part="founder",
            domain="company.com",
            is_valid=True,
            provider_type=ProviderType.CUSTOM
        )

        confidence = ConfidenceAssessment(
            level=FindingStatus.VERIFIED,
            score=85,
            reasons=["Exact email found in public commit history."],
            verified_count=1,
            high_confidence_count=0,
            probable_count=0,
            candidate_count=1
        )

        report = IntelligenceReport(
            target=target,
            confidence=confidence,
            account_discovery=[],
            developer_footprint=DeveloperFootprint(
                has_footprint=True,
                github_handle="founder",
                repositories=[
                    DeveloperRepository(
                        name="core-engine",
                        full_name="company/core-engine",
                        url="https://github.com/company/core-engine",
                        stars=120,
                        language="Rust"
                    )
                ],
                top_languages=["Rust", "TypeScript"]
            ),
            web_mentions=[],
            breaches=[],
            username_candidates=[],
            identity_signals=IdentityFinding(
                provider="identity_resolver",
                finding_type="identity",
                status=FindingStatus.VERIFIED,
                confidence_level=FindingStatus.VERIFIED,
                confidence_score=1.0,
                possible_name="Founder Person"
            ),
            report_markdown="# Email Intelligence Report",
            status="completed"
        )

        # Properties
        assert report.email == "founder@company.com"
        assert report.validation.valid is True
        assert report.confidence.score == 85
        assert report.developer_footprint.top_languages == ["Rust", "TypeScript"]

        # Full serialization & roundtrip
        json_output = report.model_dump_json(indent=2)
        parsed = json.loads(json_output)
        assert parsed["target"]["domain"] == "company.com"
        assert parsed["confidence"]["score"] == 85

        rehydrated = IntelligenceReport.model_validate_json(json_output)
        assert rehydrated.email == "founder@company.com"
        assert len(rehydrated.developer_footprint.repositories) == 1
        assert rehydrated.developer_footprint.repositories[0].stars == 120
