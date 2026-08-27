"""
GitHub Developer Identity Agent (Phase 4).

Deep-dives into GitHub developer footprint: commit activity, public repositories,
language distribution, stars, forks, organizations, and contribution patterns.
Builds the deterministic GitHub Evidence Graph connecting public signals.
"""

from __future__ import annotations

from typing import Dict, List
from ..models import (
    AccountFinding,
    DeveloperFootprint,
    FindingStatus,
    GitHubCommitRecord,
)
from ..providers.github import GitHubEmailProvider


class GitHubIdentityAgent:
    """Extracts deep developer technical signals and builds GitHub Evidence Graphs."""

    def __init__(self):
        self.provider = GitHubEmailProvider()

    def analyze_identity(
        self,
        email: str,
        local_part: str,
        domain: str,
        account_findings: List[AccountFinding]
    ) -> DeveloperFootprint:
        footprint = DeveloperFootprint()

        # Check if any GitHub account was discovered
        gh_accounts = [a for a in account_findings if a.platform == "github"]
        if not gh_accounts:
            return footprint

        # Prioritize verified accounts over candidates
        verified_gh = [a for a in gh_accounts if a.status == FindingStatus.VERIFIED]
        target_account = verified_gh[0] if verified_gh else gh_accounts[0]
        login = target_account.account_identifier

        if not login:
            return footprint

        footprint.has_footprint = True
        footprint.github_handle = login

        meta = target_account.metadata or {}
        footprint.bio = target_account.bio
        footprint.website_url = meta.get("blog")
        footprint.location = meta.get("location")
        footprint.twitter_username = meta.get("twitter_username")
        footprint.account_created_at = meta.get("account_created_at")
        footprint.account_age_years = meta.get("account_age_years")

        # Extract org/company if present
        company = meta.get("company")
        if company and company not in footprint.organizations:
            footprint.organizations.append(company.lstrip("@").strip())

        # 1. Fetch public organizations
        gh_orgs = self.provider.fetch_user_organizations(login)
        footprint.github_organizations = gh_orgs
        for o in gh_orgs:
            if o.login not in footprint.organizations:
                footprint.organizations.append(o.login)

        # 2. Fetch public repositories
        repos_data = self.provider.fetch_user_repositories(login, limit=10)
        footprint.repositories = repos_data

        total_stars = 0
        total_forks = 0
        languages_count: Dict[str, int] = {}
        recent_pushed = None

        for r in repos_data:
            total_stars += r.stars
            total_forks += r.forks
            if r.language:
                languages_count[r.language] = languages_count.get(r.language, 0) + 1
            if r.updated_at and (not recent_pushed or r.updated_at > recent_pushed):
                recent_pushed = r.updated_at

        footprint.total_stars = total_stars
        footprint.total_forks = total_forks
        footprint.language_breakdown = languages_count
        footprint.recent_activity_date = recent_pushed

        # Calculate top languages sorted by frequency
        sorted_languages = sorted(languages_count.items(), key=lambda x: x[1], reverse=True)
        footprint.top_languages = [lang for lang, _ in sorted_languages[:5]]

        # 3. Collect associated commits
        commits: List[GitHubCommitRecord] = []
        for ev in target_account.evidence:
            if ev.source_type == "public_commit" and ev.raw_data:
                commits.append(
                    GitHubCommitRecord(
                        sha=ev.raw_data.get("sha", ""),
                        repo_name=ev.raw_data.get("repo", ""),
                        repo_url=ev.url,
                        author_name=target_account.display_name or login,
                        author_email=email,
                        commit_message=ev.raw_data.get("message"),
                        commit_url=ev.url
                    )
                )
        footprint.github_commits = commits

        # 4. Build deterministic GitHub Evidence Graph
        evidence_graph = self.provider.build_evidence_graph(
            email=email,
            target_domain=domain,
            account=target_account,
            commits=commits,
            repos=repos_data,
            orgs=gh_orgs
        )
        footprint.evidence_graph = evidence_graph

        followers = meta.get("followers", 0)
        pub_repos = meta.get("public_repos", len(repos_data))
        age_str = f", active for {footprint.account_age_years} years" if footprint.account_age_years else ""
        stars_str = f" with \u2b50 {total_stars} total stars" if total_stars > 0 else ""

        footprint.contributions_summary = (
            f"GitHub developer @{login} ({pub_repos} repos, {followers} followers{stars_str}{age_str}). "
            f"Primary languages: {', '.join(footprint.top_languages) if footprint.top_languages else 'N/A'}."
        )

        return footprint
