"""
Comprehensive Test Suite for:
- Phase 11: Email Reputation and Risk Signals
- Phase 12: Historical Intelligence Snapshots & Timeline Diff
- Phase 13: Configurable Search Depth Modes (quick, standard, deep)
"""

from unittest.mock import MagicMock, patch
import pytest
from fastapi.testclient import TestClient

from intelligence.email.history import HistoricalSnapshotEngine
from intelligence.email.models import (
    AccountFinding,
    BreachFinding,
    ConfidenceAssessment,
    DeveloperFootprint,
    DeveloperRepository,
    EmailTarget,
    FindingStatus,
    IntelligenceReport,
    ReputationCategory,
)

from intelligence.email.orchestrator import EmailIntelligenceOrchestrator
from intelligence.email.reputation import EmailReputationEngine
from main import app


@pytest.fixture
def client():
    return TestClient(app)


class TestPhase11EmailReputationEngine:
    def test_evaluates_neutral_reputation_and_disposable_exposure(self):
        target_disposable = EmailTarget(
            raw_email="test@tempmail.com",
            normalized_email="test@tempmail.com",
            local_part="test",
            domain="tempmail.com",
            is_valid=True,
            is_disposable=True
        )

        rep = EmailReputationEngine.evaluate(
            target=target_disposable,
            accounts=[],
            footprint=DeveloperFootprint(),
            web_mentions=[],
            breaches=[]
        )

        assert rep.category == ReputationCategory.ELEVATED_EXPOSURE
        assert any(s.signal_name == "disposable_provider" for s in rep.signals)

    def test_evaluates_large_developer_footprint_reputation(self):
        target = EmailTarget(
            raw_email="dev@kernel.org",
            normalized_email="dev@kernel.org",
            local_part="dev",
            domain="kernel.org",
            is_valid=True,
            has_mx_records=True
        )

        acc = AccountFinding(
            provider="github",
            finding_type="account",
            platform="github",
            status=FindingStatus.VERIFIED,
            confidence_score=1.0,
            account_identifier="kerneldev",
            public_email_match=True
        )

        footprint = DeveloperFootprint(
            github_handle="kerneldev",
            total_stars=250,
            repositories=[
                DeveloperRepository(name="kernel-core", full_name="kerneldev/kernel-core", url="https://github.com/kerneldev/kernel-core", stars=250)
            ]
        )

        rep = EmailReputationEngine.evaluate(
            target=target,
            accounts=[acc, acc],
            footprint=footprint,
            web_mentions=[],
            breaches=[]
        )

        assert rep.category == ReputationCategory.HIGH_PUBLIC_EXPOSURE
        assert any(s.signal_name == "extensive_public_developer_footprint" for s in rep.signals)


class TestPhase12HistoricalSnapshotEngine:
    def test_detects_new_account_and_repository_updates(self):
        prev_data = {
            "analysis": {
                "accounts": [
                    {"platform": "github", "account_identifier": "dan_abramov"}
                ],
                "footprint": {
                    "total_stars": 100,
                    "repositories": [{"name": "redux"}]
                },
                "breach_status": "checked",
                "breaches": []
            }
        }

        curr_report = IntelligenceReport(
            target=EmailTarget(raw_email="dan@example.com", is_valid=True),
            confidence=ConfidenceAssessment(level=FindingStatus.VERIFIED, score=95),
            account_discovery=[

                AccountFinding(
                    provider="github",
                    finding_type="account",
                    platform="github",
                    status=FindingStatus.VERIFIED,
                    confidence_score=1.0,
                    account_identifier="dan_abramov"
                ),
                AccountFinding(
                    provider="npm",
                    finding_type="account",
                    platform="npm",
                    status=FindingStatus.VERIFIED,
                    confidence_score=1.0,
                    account_identifier="gaearon"
                )
            ],
            developer_footprint=DeveloperFootprint(
                total_stars=150,
                repositories=[
                    DeveloperRepository(name="redux", full_name="reduxjs/redux", url="https://github.com/reduxjs/redux", stars=100),
                    DeveloperRepository(name="use-sync-external-store", full_name="reactjs/use-sync", url="https://github.com/reactjs/use-sync", stars=50)
                ]
            ),
            breach_status="checked",
            breaches=[
                BreachFinding(
                    provider="hibp",
                    finding_type="breach",
                    status=FindingStatus.VERIFIED,
                    confidence_level=FindingStatus.VERIFIED,
                    confidence_score=1.0,
                    breach_name="Data2026",
                    domain="example.com"
                )
            ]
        )

        comparison = HistoricalSnapshotEngine.compare_snapshots(
            current_report=curr_report,
            previous_data=prev_data,
            previous_job_id="job_old_1",
            previous_created_at="2026-08-01T00:00:00Z"
        )

        assert comparison.has_previous_scan is True
        assert len(comparison.changes) >= 3

        change_types = {c.change_type for c in comparison.changes}
        assert "new_account" in change_types
        assert "github_activity" in change_types
        assert "new_breach" in change_types


class TestPhase13SearchDepthModes:
    def test_quick_depth_restricts_to_fast_providers(self):
        orchestrator = EmailIntelligenceOrchestrator()

        with patch.object(orchestrator.validator, "validate_email") as mock_val:
            mock_val.return_value = EmailTarget(
                raw_email="quick@example.com",
                normalized_email="quick@example.com",
                local_part="quick",
                domain="example.com",
                is_valid=True
            )
            with patch.object(orchestrator.account_discovery, "discover_all") as mock_disc:
                mock_disc.return_value = [
                    AccountFinding(
                        provider="github",
                        finding_type="account",
                        platform="github",
                        status=FindingStatus.VERIFIED,
                        confidence_score=1.0,
                        account_identifier="quickdev"
                    ),
                    AccountFinding(
                        provider="npm",
                        finding_type="account",
                        platform="npm",
                        status=FindingStatus.VERIFIED,
                        confidence_score=1.0,
                        account_identifier="quickpkg"
                    )
                ]

                res = orchestrator.execute("quick@example.com", depth="quick")

                assert res.scope.depth == "quick"
                # Quick mode filters to github & gravatar only
                assert len(res.account_discovery) == 1
                assert res.account_discovery[0].platform == "github"
                # Web search and breach lookup are skipped in quick mode
                assert len(res.web_mentions) == 0
                assert len(res.breaches) == 0
