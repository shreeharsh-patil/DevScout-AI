"""
Developer Footprint Synthesis Agent.

Aggregates public developer profiles, package authoring (npm), code repositories (GitHub/GitLab),
and technical activity into a comprehensive developer footprint report.
"""

from __future__ import annotations

from typing import List
from ..models import AccountFinding, DeveloperFootprint
from ..providers.npm import NpmProvider
from .github_identity import GitHubIdentityAgent


class DeveloperFootprintAgent:
    """Consolidates developer technical footprint across platforms."""

    def __init__(self):
        self.github_agent = GitHubIdentityAgent()
        self.npm_provider = NpmProvider()

    def build_footprint(
        self,
        email: str,
        local_part: str,
        domain: str,
        account_findings: List[AccountFinding]
    ) -> DeveloperFootprint:
        # 1. GitHub footprint
        footprint = self.github_agent.analyze_identity(email, local_part, domain, account_findings)

        # 2. GitLab footprint
        gitlab_accs = [a for a in account_findings if a.platform == "gitlab"]
        if gitlab_accs:
            footprint.gitlab_handle = gitlab_accs[0].account_identifier
            footprint.has_footprint = True

        # 3. npm package maintainer footprint
        npm_accs = [a for a in account_findings if a.platform == "npm"]
        if npm_accs:
            npm_user = npm_accs[0].account_identifier or local_part
            footprint.npm_maintainer = npm_user
            footprint.has_footprint = True
            packages = self.npm_provider.fetch_maintainer_packages(email)
            if not packages and npm_user:
                packages = self.npm_provider.fetch_maintainer_packages(npm_user)
            footprint.npm_packages = packages

        return footprint
