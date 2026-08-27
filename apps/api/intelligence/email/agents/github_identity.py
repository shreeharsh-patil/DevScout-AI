"""
GitHub Developer Identity Agent.

Deep-dives into GitHub developer footprint: commit activity, public repositories,
language distribution, followers, organizations, and contribution patterns.
"""

from __future__ import annotations

from typing import Dict, List
from ..models import AccountFinding, ConfidenceLevel, DeveloperFootprint, DeveloperRepository
from ..providers.github import GitHubProvider


class GitHubIdentityAgent:
    """Extracts developer technical signals from GitHub."""

    def __init__(self):
        self.provider = GitHubProvider()

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
        verified_gh = [a for a in gh_accounts if a.status == ConfidenceLevel.VERIFIED]
        target_account = verified_gh[0] if verified_gh else gh_accounts[0]
        login = target_account.account_identifier

        if not login:
            return footprint

        footprint.has_footprint = True
        footprint.github_handle = login

        # Extract org/company if present
        company = target_account.metadata.get("company")
        if company:
            footprint.organizations.append(company.lstrip("@").strip())

        # Fetch recent repositories
        repos_data = self.provider.fetch_user_repositories(login, limit=8)
        languages_count: Dict[str, int] = {}

        for r in repos_data:
            dev_repo = DeveloperRepository(
                name=r.get("name", ""),
                full_name=r.get("full_name", ""),
                url=r.get("url", ""),
                description=r.get("description"),
                stars=r.get("stars", 0),
                forks=r.get("forks", 0),
                language=r.get("language"),
                updated_at=r.get("updated_at")
            )
            footprint.repositories.append(dev_repo)
            if dev_repo.language:
                languages_count[dev_repo.language] = languages_count.get(dev_repo.language, 0) + 1

        # Calculate top languages sorted by frequency
        sorted_languages = sorted(languages_count.items(), key=lambda x: x[1], reverse=True)
        footprint.top_languages = [lang for lang, _ in sorted_languages[:5]]

        followers = target_account.metadata.get("followers", 0)
        pub_repos = target_account.metadata.get("public_repos", 0)
        footprint.contributions_summary = (
            f"GitHub developer '{login}' with {pub_repos} public repos and {followers} followers. "
            f"Primary languages: {', '.join(footprint.top_languages) if footprint.top_languages else 'N/A'}."
        )

        return footprint
