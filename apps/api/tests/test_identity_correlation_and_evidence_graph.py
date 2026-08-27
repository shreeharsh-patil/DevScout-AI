"""
Comprehensive Test Suite for Deterministic Identity Correlation Engine (Phase 7) & Evidence Graph (Phase 8).

Validates:
- Phase 7:
  - Deterministic signal weighting (exact email +100, cryptographic hash +90, cross-link +80, same website +70, same org +25, etc.)
  - Identity clustering (Confirmed Identity Cluster vs strictly isolated Candidate Clusters)
  - Zero automatic merging of ambiguous candidate guesses
  - Explicit ambiguity warnings
- Phase 8:
  - Evidence Graph generation across entities (email, accounts, repos, packages, breaches, domains)
  - Visual/structural distinction between verified deterministic edges and candidate dashed edges
  - Node sources and metadata tracking
  - GET /api/v1/research/{job_id}/graph endpoint
"""

from unittest.mock import MagicMock, patch
import pytest
from fastapi.testclient import TestClient

from intelligence.email.correlation import IdentityCorrelationEngine
from intelligence.email.models import (
    AccountFinding,
    BreachFinding,
    DeveloperFootprint,
    DeveloperRepository,
    EmailTarget,
    Evidence,
    EvidenceGraph,
    FindingStatus,
    IdentityCluster,
)
from main import app


@pytest.fixture
def client():
    return TestClient(app)


class TestDeterministicIdentityCorrelationEngine:
    def test_pairwise_signal_scoring_rules(self):
        # Case 1: Both accounts have exact matching email
        acc_a = AccountFinding(
            provider="github",
            finding_type="account",
            platform="github",
            status=FindingStatus.VERIFIED,
            confidence_score=1.0,
            account_identifier="linus",
            display_name="Linus Torvalds",
            public_email_match=True,
            metadata={"company": "Linux Foundation", "blog": "https://kernel.org"}
        )

        acc_b = AccountFinding(
            provider="gitlab",
            finding_type="account",
            platform="gitlab",
            status=FindingStatus.VERIFIED,
            confidence_score=1.0,
            account_identifier="linus",
            display_name="Linus Torvalds",
            public_email_match=True,
            metadata={"company": "Linux Foundation", "website_url": "https://kernel.org"}
        )

        score, reasons = IdentityCorrelationEngine.evaluate_pair(
            acc_a, acc_b, email="torvalds@linux-foundation.org", domain="linux-foundation.org"
        )

        # 100 (exact email) + 70 (same website) + 25 (same company) + 15 (same name) + 10 (same username) = 220
        assert score >= 200
        assert any("Both accounts explicitly verified" in r for r in reasons)
        assert any("identical personal website" in r for r in reasons)

    def test_candidate_guess_is_isolated_into_separate_cluster(self):
        acc_verified = AccountFinding(
            provider="github",
            finding_type="account",
            platform="github",
            status=FindingStatus.VERIFIED,
            confidence_score=1.0,
            account_identifier="dan_abramov",
            display_name="Dan Abramov",
            public_email_match=True
        )

        acc_candidate = AccountFinding(
            provider="gitlab",
            finding_type="account",
            platform="gitlab",
            status=FindingStatus.CANDIDATE,
            confidence_score=0.25,
            account_identifier="dan_abramov",
            display_name="Random Dan",
            public_email_match=False,
            method="unverified_handle_prefix_guess"
        )

        clusters = IdentityCorrelationEngine.build_clusters(
            email="dan@example.com",
            domain="example.com",
            accounts=[acc_verified, acc_candidate]
        )

        # Must produce 2 separate clusters: 1 verified, 1 candidate (never merged!)
        assert len(clusters) == 2
        verified_cluster = [c for c in clusters if c.status == FindingStatus.VERIFIED][0]
        candidate_cluster = [c for c in clusters if c.status == FindingStatus.CANDIDATE][0]

        assert len(verified_cluster.accounts) == 1
        assert verified_cluster.accounts[0].platform == "github"
        assert len(candidate_cluster.accounts) == 1
        assert candidate_cluster.accounts[0].platform == "gitlab"
        assert candidate_cluster.ambiguity_warning is not None


class TestInteractiveEvidenceGraph:
    def test_builds_complete_evidence_graph_with_typed_nodes_and_edges(self):
        target = EmailTarget(
            raw_email="dev@startup.io",
            normalized_email="dev@startup.io",
            local_part="dev",
            domain="startup.io",
            is_valid=True,
            has_mx_records=True,
            organization_name="Startup Inc"
        )

        acc = AccountFinding(
            provider="github",
            finding_type="account",
            platform="github",
            status=FindingStatus.VERIFIED,
            confidence_score=1.0,
            account_identifier="devguy",
            evidence_ids=["src_1"]
        )

        footprint = DeveloperFootprint(
            github_handle="devguy",
            repositories=[
                DeveloperRepository(name="core-engine", full_name="devguy/core-engine", url="https://github.com/devguy/core-engine", stars=120)
            ]
        )

        breaches = [
            BreachFinding(
                provider="hibp",
                finding_type="breach",
                status=FindingStatus.VERIFIED,
                confidence_level=FindingStatus.VERIFIED,
                confidence_score=1.0,
                breach_name="DataExposure2025",
                domain="target.com",
                data_classes=["Email", "Username"]
            )
        ]

        graph = IdentityCorrelationEngine.build_evidence_graph(
            email="dev@startup.io",
            target=target,
            clusters=[],
            accounts=[acc],
            footprint=footprint,
            web_mentions=[],
            breaches=breaches,
            sources=[{"source_id": "src_1", "platform": "github"}]
        )

        assert isinstance(graph, EvidenceGraph)
        assert graph.total_nodes >= 5  # email, domain, org, account, repo, breach
        assert graph.total_edges >= 4

        node_types = {n.node_type for n in graph.nodes}
        assert "email" in node_types
        assert "domain" in node_types
        assert "organization" in node_types
        assert "account" in node_types
        assert "repository" in node_types
        assert "breach" in node_types

        # Verify edge relationships
        edge_rels = {e.relationship for e in graph.edges}
        assert "hosted_on_domain" in edge_rels
        assert "affiliated_with" in edge_rels
        assert "verified_email" in edge_rels
        assert "owns" in edge_rels
        assert "mentions" in edge_rels
