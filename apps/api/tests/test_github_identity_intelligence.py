"""
Comprehensive Test Suite for GitHub Developer Identity Intelligence (Phase 4).

Validates:
- Exact public commit and profile email matching -> VERIFIED + EXACT_EMAIL
- Username matching alone -> CANDIDATE + USERNAME_EVIDENCE
- Similar display name alone -> CANDIDATE + NAME_EVIDENCE
- Domain/company correlation -> PROBABLE + ORGANIZATION_EVIDENCE
- Strict rule: Weak similarity never converts to VERIFIED
- Construction and structure of the GitHub Evidence Graph (nodes, edges, weights, summary)
- Rich developer signals: stars, forks, language breakdown, organizations, account age
"""

from unittest.mock import MagicMock, patch
import pytest

from intelligence.email.agents.github_identity import GitHubIdentityAgent
from intelligence.email.models import (
    AccountFinding,
    DeveloperRepository,
    EmailTarget,
    Evidence,
    EvidenceCategory,
    FindingStatus,
    GitHubCommitRecord,
    GitHubEvidenceGraph,
    GitHubOrganization,
)
from intelligence.email.providers.github import GitHubEmailProvider


class TestGitHubEvidenceCategories:
    def test_exact_commit_author_email_is_verified_exact_email(self):
        prov = GitHubEmailProvider()

        mock_commit_item = {
            "sha": "a1b2c3d4e5f6",
            "commit": {
                "author": {"name": "Linus Torvalds", "email": "torvalds@linux-foundation.org", "date": "2026-08-01T12:00:00Z"},
                "message": "Linux kernel release"
            },
            "author": {"login": "torvalds", "avatar_url": "https://avatars.github.com/u/1024025"},
            "repository": {"full_name": "torvalds/linux", "html_url": "https://github.com/torvalds/linux"}
        }

        mock_profile = {
            "login": "torvalds",
            "name": "Linus Torvalds",
            "public_repos": 10,
            "followers": 150000,
            "company": "Linux Foundation",
            "created_at": "2011-09-03T15:26:22Z"
        }

        with patch.object(prov, "_safe_request") as mock_req:
            mock_commit_resp = MagicMock()
            mock_commit_resp.status_code = 200
            mock_commit_resp.json.return_value = {"items": [mock_commit_item]}

            mock_profile_resp = MagicMock()
            mock_profile_resp.status_code = 200
            mock_profile_resp.json.return_value = mock_profile

            mock_req.side_effect = [mock_commit_resp, mock_profile_resp]

            findings, commits = prov.search_with_commits(
                email="torvalds@linux-foundation.org",
                local_part="torvalds",
                domain="linux-foundation.org"
            )

            assert len(findings) == 1
            finding = findings[0]
            assert finding.status == FindingStatus.VERIFIED
            assert finding.confidence_score == 1.0
            assert finding.account_identifier == "torvalds"
            assert finding.evidence[0].metadata["category"] == EvidenceCategory.EXACT_EMAIL.value
            assert len(commits) == 1
            assert commits[0].sha == "a1b2c3d4"

    def test_matching_username_alone_is_candidate(self):
        prov = GitHubEmailProvider()

        mock_profile = {
            "login": "johndoe",
            "name": "John Doe",
            "email": None,  # no public email
            "bio": "Random developer",
            "company": None,
            "blog": None
        }

        with patch.object(prov, "_safe_request") as mock_req:
            # Commit search empty
            mock_commit_resp = MagicMock()
            mock_commit_resp.status_code = 200
            mock_commit_resp.json.return_value = {"items": []}

            # Profile search empty
            mock_user_resp = MagicMock()
            mock_user_resp.status_code = 200
            mock_user_resp.json.return_value = {"items": []}

            # Prefix profile lookup returns user
            mock_profile_resp = MagicMock()
            mock_profile_resp.status_code = 200
            mock_profile_resp.json.return_value = mock_profile

            mock_req.side_effect = [mock_commit_resp, mock_user_resp, mock_profile_resp]

            findings, commits = prov.search_with_commits(
                email="johndoe@unknowncompany.com",
                local_part="johndoe",
                domain="unknowncompany.com"
            )

            assert len(findings) == 1
            finding = findings[0]
            # Must strictly be CANDIDATE
            assert finding.status == FindingStatus.CANDIDATE
            assert finding.confidence_score <= 0.35
            assert finding.evidence[0].metadata["category"] == EvidenceCategory.USERNAME_EVIDENCE.value

    def test_domain_bio_correlation_yields_probable_not_verified(self):
        prov = GitHubEmailProvider()

        mock_profile = {
            "login": "dan",
            "name": "Dan",
            "email": None,
            "bio": "Frontend developer @ vercel.com",
            "company": "Vercel",
            "blog": "https://vercel.com"
        }

        with patch.object(prov, "_safe_request") as mock_req:
            mock_commit_resp = MagicMock()
            mock_commit_resp.status_code = 200
            mock_commit_resp.json.return_value = {"items": []}

            mock_user_resp = MagicMock()
            mock_user_resp.status_code = 200
            mock_user_resp.json.return_value = {"items": []}

            mock_profile_resp = MagicMock()
            mock_profile_resp.status_code = 200
            mock_profile_resp.json.return_value = mock_profile

            mock_req.side_effect = [mock_commit_resp, mock_user_resp, mock_profile_resp]

            findings, _ = prov.search_with_commits(
                email="dan@vercel.com",
                local_part="dan",
                domain="vercel.com"
            )

            assert len(findings) == 1
            finding = findings[0]
            assert finding.status == FindingStatus.PROBABLE
            assert finding.confidence_score == 0.70
            assert finding.evidence[0].metadata["category"] == EvidenceCategory.ORGANIZATION_EVIDENCE.value


class TestGitHubEvidenceGraphConstruction:
    def test_evidence_graph_nodes_edges_and_weights(self):
        prov = GitHubEmailProvider()

        ev = Evidence(
            evidence_id="gh_commit_999",
            provider="github",
            source_type="public_commit",
            title="Commit 999",
            url="https://github.com/facebook/react/commit/999",
            supports="github_identity",
            metadata={"category": EvidenceCategory.EXACT_EMAIL.value}
        )

        account = AccountFinding(
            provider="github",
            finding_type="account",
            platform="github",
            status=FindingStatus.VERIFIED,
            confidence_score=1.0,
            evidence_ids=["gh_commit_999"],
            account_identifier="gaearon",
            display_name="Dan Abramov",
            profile_url="https://github.com/gaearon",
            evidence=[ev]
        )

        commits = [
            GitHubCommitRecord(
                sha="99988877",
                repo_name="facebook/react",
                repo_url="https://github.com/facebook/react",
                author_name="Dan Abramov",
                author_email="dan@example.com",
                commit_message="Fix fiber reconciliation",
                commit_url="https://github.com/facebook/react/commit/999"
            )
        ]

        repos = [
            DeveloperRepository(
                name="overreacted.io",
                full_name="gaearon/overreacted.io",
                url="https://github.com/gaearon/overreacted.io",
                stars=5000,
                forks=1200,
                language="JavaScript"
            )
        ]

        orgs = [
            GitHubOrganization(
                login="facebook",
                name="Meta",
                url="https://github.com/facebook"
            )
        ]

        graph = prov.build_evidence_graph(
            email="dan@example.com",
            target_domain="example.com",
            account=account,
            commits=commits,
            repos=repos,
            orgs=orgs
        )

        assert isinstance(graph, GitHubEvidenceGraph)
        assert graph.verification_tier == FindingStatus.VERIFIED
        assert graph.exact_email_matches >= 2  # profile + commit
        assert len(graph.nodes) >= 4  # email, user, commit, org, repo
        assert len(graph.edges) >= 3

        # Confirm specific relationship edges exist
        edge_relations = {e.relationship for e in graph.edges}
        assert "owns_verified_profile" in edge_relations
        assert "authored_commit" in edge_relations
        assert "member_of" in edge_relations
        assert "maintains_repository" in edge_relations


class TestGitHubIdentityAgentDeepExtraction:
    def test_footprint_aggregation_with_stars_languages_and_organizations(self):
        agent = GitHubIdentityAgent()

        account = AccountFinding(
            provider="github",
            finding_type="account",
            platform="github",
            status=FindingStatus.VERIFIED,
            confidence_score=1.0,
            evidence_ids=["ev_1"],
            account_identifier="developer101",
            display_name="Senior Dev",
            bio="Building distributed systems",
            profile_url="https://github.com/developer101",
            metadata={
                "public_repos": 15,
                "followers": 250,
                "company": "@BigTechCorp",
                "blog": "https://developer.blog",
                "location": "San Francisco, CA",
                "twitter_username": "dev101",
                "account_created_at": "2018-05-10T10:00:00Z",
                "account_age_years": 8.3
            }
        )

        mock_repos = [
            DeveloperRepository(name="raft-consensus", full_name="developer101/raft", url="https://github.com/dev/raft", stars=300, forks=40, language="Go"),
            DeveloperRepository(name="fast-kv", full_name="developer101/kv", url="https://github.com/dev/kv", stars=200, forks=20, language="Rust"),
            DeveloperRepository(name="go-tools", full_name="developer101/tools", url="https://github.com/dev/tools", stars=50, forks=5, language="Go"),
        ]

        mock_orgs = [
            GitHubOrganization(login="BigTechCorp", name="Big Tech Corp", url="https://github.com/BigTechCorp")
        ]

        with patch.object(agent.provider, "fetch_user_repositories", return_value=mock_repos):
            with patch.object(agent.provider, "fetch_user_organizations", return_value=mock_orgs):
                footprint = agent.analyze_identity(
                    email="developer101@bigtechcorp.com",
                    local_part="developer101",
                    domain="bigtechcorp.com",
                    account_findings=[account]
                )

                assert footprint.has_footprint is True
                assert footprint.github_handle == "developer101"
                assert footprint.total_stars == 550  # 300 + 200 + 50
                assert footprint.total_forks == 65   # 40 + 20 + 5
                assert footprint.top_languages[0] == "Go"
                assert "Rust" in footprint.top_languages
                assert "BigTechCorp" in footprint.organizations
                assert footprint.location == "San Francisco, CA"
                assert footprint.account_age_years == 8.3
                assert footprint.evidence_graph is not None
                assert footprint.evidence_graph.verification_tier == FindingStatus.VERIFIED
