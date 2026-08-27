"""
Comprehensive Test Suite for Email Intelligence Provider Engine (Phase 2).

Validates:
- BaseEmailProvider contract: is_available, supports, lookup, normalize_result, health_check
- Provider failure isolation (crashes never break pipeline)
- Per-provider timeout and execution timing (execution_time_ms)
- Retry logic with exponential backoff on temporary 5xx failures
- No retries on permanent 4xx client errors
- Rate limit detection (HTTP 429) and health state transition
- ProviderRegistry registration, dynamic discovery, health monitoring, and concurrent execution
- Dynamic pluggable provider integration without changing orchestrator code
"""

import time
from unittest.mock import MagicMock, patch
import pytest
import requests

from intelligence.email.models import (
    AccountFinding,
    EmailTarget,
    Evidence,
    FindingStatus,
    ProviderHealthStatus,
    ProviderResult,
    ProviderType,
    utc_now_iso,
)
from intelligence.email.providers.base import BaseEmailProvider
from intelligence.email.providers.github import GitHubEmailProvider
from intelligence.email.providers.gravatar import GravatarEmailProvider
from intelligence.email.providers.npm import NpmEmailProvider
from intelligence.email.providers.gitlab import GitLabEmailProvider
from intelligence.email.providers.web_search import WebSearchEmailProvider
from intelligence.email.providers.breach import BreachEmailProvider
from intelligence.email.registry import ProviderRegistry, create_default_registry
from intelligence.email.orchestrator import EmailIntelligenceOrchestrator


class MockFailingProvider(BaseEmailProvider):
    provider_name: str = "mock_failing"

    def is_available(self) -> bool:
        return True

    def lookup(self, target: EmailTarget) -> ProviderResult:
        raise RuntimeError("Simulated unhandled third-party service crash!")


class MockSlowProvider(BaseEmailProvider):
    provider_name: str = "mock_slow"

    def __init__(self, delay_s: float = 0.05):
        super().__init__(timeout=1.0)
        self.delay_s = delay_s

    def is_available(self) -> bool:
        return True

    def lookup(self, target: EmailTarget) -> ProviderResult:
        time.sleep(self.delay_s)
        return ProviderResult(
            provider=self.provider_name,
            finding_type="account",
            status=FindingStatus.VERIFIED,
            confidence_level=FindingStatus.VERIFIED,
            confidence_score=1.0,
            retrieved_at=utc_now_iso()
        )


class MockCustomPluginProvider(BaseEmailProvider):
    provider_name: str = "custom_enterprise_directory"

    def is_available(self) -> bool:
        return True

    def lookup(self, target: EmailTarget) -> ProviderResult:
        ev = Evidence(
            evidence_id="custom_dir_01",
            provider=self.provider_name,
            source_type="enterprise_directory",
            title=f"Corporate LDAP Match for {target.normalized_email}",
            url="https://ldap.corp.internal/user",
            supports="enterprise_identity"
        )
        finding = AccountFinding(
            provider=self.provider_name,
            finding_type="account",
            platform="enterprise_ldap",
            status=FindingStatus.VERIFIED,
            confidence_level=FindingStatus.VERIFIED,
            confidence_score=1.0,
            evidence_ids=[ev.evidence_id],
            account_identifier="corp_user",
            display_name="Enterprise Developer",
            evidence=[ev]
        )
        return ProviderResult(
            provider=self.provider_name,
            finding_type="account",
            status=FindingStatus.VERIFIED,
            confidence_level=FindingStatus.VERIFIED,
            confidence_score=1.0,
            evidence_ids=[ev.evidence_id],
            evidence_items=[ev],
            findings=[finding],
            retrieved_at=utc_now_iso()
        )


@pytest.fixture
def sample_target():
    return EmailTarget(
        raw_email="dev.scout@example.com",
        normalized_email="dev.scout@example.com",
        local_part="dev.scout",
        domain="example.com",
        is_valid=True,
        provider_type=ProviderType.CUSTOM
    )


class TestBaseEmailProviderContract:
    def test_provider_health_check_states(self):
        prov = MockSlowProvider()
        health = prov.health_check()
        assert health.provider_name == "mock_slow"
        assert health.status == ProviderHealthStatus.HEALTHY
        assert health.is_available is True

    def test_provider_failure_isolation(self, sample_target):
        prov = MockFailingProvider()
        # execute() should safely catch the exception and return an ERROR ProviderResult
        res = prov.execute(sample_target)
        assert res.status == FindingStatus.ERROR
        assert res.provider == "mock_failing"
        assert "Simulated unhandled" in (res.error or "")
        assert "execution_time_ms" in res.metadata

        # Health status should reflect degraded/failed
        health = prov.health_check()
        assert health.status == ProviderHealthStatus.FAILED
        assert health.last_error is not None

    def test_provider_execution_timing(self, sample_target):
        prov = MockSlowProvider(delay_s=0.03)
        res = prov.execute(sample_target)
        assert res.status == FindingStatus.VERIFIED
        assert "execution_time_ms" in res.metadata
        assert res.metadata["execution_time_ms"] >= 20.0  # at least ~20-30ms

    def test_rate_limit_detection_and_health_update(self, sample_target):
        prov = GitHubEmailProvider()

        mock_resp_429 = MagicMock()
        mock_resp_429.status_code = 429
        mock_resp_429.headers = {"Retry-After": "0"}

        with patch("http_client.get", return_value=mock_resp_429):
            resp = prov._safe_request("https://api.github.com/rate_limit_test")
            assert resp.status_code == 429
            assert prov._rate_limited is True
            health = prov.health_check()
            assert health.status == ProviderHealthStatus.RATE_LIMITED
            assert health.rate_limited is True

    def test_retry_on_500_temporary_failure(self):
        prov = GravatarEmailProvider(max_retries=2)

        mock_resp_500 = MagicMock()
        mock_resp_500.status_code = 500

        mock_resp_200 = MagicMock()
        mock_resp_200.status_code = 200
        mock_resp_200.json.return_value = {"entry": [{"displayName": "Test User"}]}

        # Fails once with 500, then succeeds with 200
        with patch("http_client.get", side_effect=[mock_resp_500, mock_resp_200]) as mock_get:
            resp = prov._safe_request("https://en.gravatar.com/hash.json")
            assert resp.status_code == 200
            assert mock_get.call_count == 2

    def test_no_retry_on_404_client_error(self):
        prov = GitLabEmailProvider(max_retries=2)

        mock_resp_404 = MagicMock()
        mock_resp_404.status_code = 404

        with patch("http_client.get", return_value=mock_resp_404) as mock_get:
            resp = prov._safe_request("https://gitlab.com/api/v4/users?username=unknown")
            assert resp.status_code == 404
            assert mock_get.call_count == 1  # 404 must NOT retry


class TestProviderRegistry:
    def test_registry_registration_and_listing(self):
        registry = ProviderRegistry()
        registry.register(GitHubEmailProvider())
        registry.register(GravatarEmailProvider())

        assert len(registry.list_providers()) == 2
        assert "github" in registry.list_providers()
        assert "gravatar" in registry.list_providers()
        assert registry.get("github") is not None
        assert registry.get("non_existent") is None

    def test_registry_health_checks(self):
        registry = create_default_registry()
        health_reports = registry.health_check_all()

        assert "github" in health_reports
        assert "gravatar" in health_reports
        assert "npm" in health_reports
        assert "gitlab" in health_reports
        assert "web_search" in health_reports
        assert "breach" in health_reports

        for name, report in health_reports.items():
            assert report.provider_name == name
            assert isinstance(report.status, ProviderHealthStatus)

    def test_registry_concurrent_execution_with_isolated_failures(self, sample_target):
        registry = ProviderRegistry()
        registry.register(MockSlowProvider(delay_s=0.02))
        registry.register(MockFailingProvider())
        registry.register(MockCustomPluginProvider())

        start = time.perf_counter()
        results = registry.execute_all(target=sample_target, concurrent=True, max_workers=4)
        elapsed = time.perf_counter() - start

        # Concurrently executed, total time should be close to single slow provider delay
        assert len(results) == 3
        assert results["mock_slow"].status == FindingStatus.VERIFIED
        assert results["mock_failing"].status == FindingStatus.ERROR
        assert results["custom_enterprise_directory"].status == FindingStatus.VERIFIED
        assert elapsed < 0.5  # ran concurrently in < 500ms

    def test_pluggable_provider_integrated_in_orchestrator_without_code_changes(self, sample_target):
        """Validates that a new custom provider plugs into the orchestrator automatically."""
        custom_registry = ProviderRegistry()
        custom_registry.register(MockCustomPluginProvider())

        orchestrator = EmailIntelligenceOrchestrator(registry=custom_registry)
        report = orchestrator.execute("developer@company.org")

        assert report.status == "completed"
        # The custom enterprise finding is collected and present in account_discovery
        assert any(a.provider == "custom_enterprise_directory" for a in report.account_discovery)
        # And sources include the custom provider
        assert any(s.get("platform") == "custom_enterprise_directory" for s in report.sources)
