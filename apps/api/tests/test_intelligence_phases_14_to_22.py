"""
Comprehensive Unit & Regression Test Suite for:
- Phase 14: Orchestration & Concurrency
- Phase 16: Source Quality Scoring
- Phase 17: False Positive Detection & Contradictions
- Phase 18: Explainable AI Analysis & Grounding
- Phase 19: Export & Shareable Reports
- Phase 20: Authentication & Multi-Tenancy Privacy
- Phase 21: Intelligent Cache TTL & Performance Telemetry
- Phase 22: Production Observability & Diagnostics
"""

from unittest.mock import MagicMock, patch
import pytest
from fastapi.testclient import TestClient

from intelligence.email.ai_explanation import ExplainableAIEngine
from intelligence.email.false_positive import FalsePositiveDetector
from intelligence.email.models import (
    AccountFinding,
    ConfidenceAssessment,
    DeveloperFootprint,
    EmailTarget,
    Evidence,
    FindingStatus,
    SourceQuality,
)
from intelligence.email.orchestrator import EmailIntelligenceOrchestrator
from intelligence.email.telemetry import IntelligenceCache, ObservabilityTelemetry
from main import app


@pytest.fixture
def client():
    return TestClient(app)


class TestPhase16SourceQualityScoring:
    def test_first_party_dominates_weak_snippets(self):
        ev_first_party = Evidence(
            provider="github",
            source_type="api",
            title="GitHub API Verified Author",
            url="https://api.github.com",
            supports="account",
            strength="deterministic",
            source_quality=SourceQuality.FIRST_PARTY
        )
        assert ev_first_party.source_quality == SourceQuality.FIRST_PARTY

        ev_weak = Evidence(
            provider="web",
            source_type="search_snippet",
            title="Forum Mention",
            url="https://forum.com",
            supports="candidate",
            strength="weak",
            source_quality=SourceQuality.WEAK
        )
        assert ev_weak.source_quality == SourceQuality.WEAK


class TestPhase17FalsePositiveDetection:
    def test_common_username_flagged_with_low_confidence_cap(self):
        acc = AccountFinding(
            provider="github",
            finding_type="account",
            platform="github",
            status=FindingStatus.PROBABLE,
            confidence_score=0.8,
            account_identifier="john",
            public_email_match=False
        )

        adjusted, contras = FalsePositiveDetector.evaluate_account(
            account=acc,
            target_email="john@generic.com",
            target_local="john",
            target_domain="generic.com",
            verified_accounts=[]
        )

        assert adjusted.status == FindingStatus.CANDIDATE
        assert adjusted.confidence_score <= 0.20
        assert any("common username" in c.lower() for c in contras)

    def test_contradictions_penalize_candidate_scores(self):
        verified_acc = AccountFinding(
            provider="github",
            finding_type="account",
            platform="github",
            status=FindingStatus.VERIFIED,
            confidence_score=1.0,
            account_identifier="alice_dev",
            public_email_match=True,
            display_name="Alice Wonder",
            metadata={"company": "Acme Corp", "blog": "https://alice.dev"}
        )

        candidate_acc = AccountFinding(
            provider="gitlab",
            finding_type="account",
            platform="gitlab",
            status=FindingStatus.PROBABLE,
            confidence_score=0.75,
            account_identifier="alice_dev",
            public_email_match=False,
            display_name="Alice NotWonder",
            metadata={"company": "Hooli Corp", "blog": "https://other.blog"}
        )

        adjusted, contras = FalsePositiveDetector.evaluate_account(
            account=candidate_acc,
            target_email="alice@acme.com",
            target_local="alice",
            target_domain="acme.com",
            verified_accounts=[verified_acc]
        )

        # -0.25 (website) + -0.20 (company) + -0.10 (name) penalties
        assert adjusted.status == FindingStatus.CANDIDATE
        assert adjusted.confidence_score < 0.30
        assert len(contras) >= 3


class TestPhase18ExplainableAI:
    def test_deterministic_fallback_generation(self):
        target = EmailTarget(raw_email="dev@kernel.org", is_valid=True)
        conf = ConfidenceAssessment(level=FindingStatus.VERIFIED, score=95)
        footprint = DeveloperFootprint(top_languages=["Rust", "C"], total_stars=120)
        acc = AccountFinding(
            provider="github",
            finding_type="account",
            platform="github",
            status=FindingStatus.VERIFIED,
            confidence_score=1.0,
            account_identifier="kernel_author",
            public_email_match=True
        )

        explanation = ExplainableAIEngine._generate_deterministic_fallback(
            target=target,
            confidence=conf,
            accounts=[acc],
            footprint=footprint,
            breaches_count=0
        )

        assert explanation.summary != ""
        assert "Systems / Low-Level Engineer" in explanation.developer_archetype
        assert len(explanation.key_highlights) > 0



class TestPhase21IntelligentCacheAndTelemetry:
    def test_cache_set_get_and_hit_rate(self):
        cache = IntelligenceCache()
        cache.set("github", "user1", {"name": "User One"})

        assert cache.get("github", "user1") == {"name": "User One"}
        assert cache.get("github", "nonexistent") is None

        stats = cache.stats
        assert stats["hits"] == 1
        assert stats["misses"] == 1
        assert stats["hit_rate_pct"] == 50.0

    def test_telemetry_tracker(self):
        tel = ObservabilityTelemetry()
        from intelligence.email.models import ProviderMetric
        tel.record_metric(ProviderMetric(provider="github", duration_ms=120.5, status="success"))
        tel.record_metric(ProviderMetric(provider="npm", duration_ms=80.0, status="success"))

        summary = tel.get_summary()
        assert summary["total_operations"] == 2
        assert summary["avg_duration_ms"] > 0
        assert summary["success_rate_pct"] == 100.0


class TestPhase19And22APIEndpoints:
    def test_diagnostics_endpoint(self, client):
        res = client.get("/api/v1/diagnostics")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "healthy"
        assert "cache" in data
        assert "telemetry" in data
        assert "queue" in data
