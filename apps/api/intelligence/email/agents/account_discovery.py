"""
Account Discovery Agent.

Coordinates public account discovery across provider adapters (GitHub, Gravatar, npm, GitLab),
normalizing results and guaranteeing complete error isolation.
"""

from __future__ import annotations

from typing import List
from loguru import logger
from ..models import AccountFinding
from ..providers import (
    BaseProvider,
    GitHubProvider,
    GitLabProvider,
    GravatarProvider,
    NpmProvider,
)


class AccountDiscoveryAgent:
    """Discovers public developer accounts across supported public platforms."""

    def __init__(self):
        self.providers: List[BaseProvider] = [
            GitHubProvider(),
            GravatarProvider(),
            NpmProvider(),
            GitLabProvider(),
        ]

    def discover_all(self, email: str, local_part: str, domain: str) -> List[AccountFinding]:
        all_findings: List[AccountFinding] = []

        for provider in self.providers:
            try:
                findings = provider.search(email, local_part, domain)
                if findings:
                    all_findings.extend(findings)
            except Exception as e:
                logger.warning(f"[{provider.platform_name}] Unhandled exception in discovery: {e}")

        return all_findings
