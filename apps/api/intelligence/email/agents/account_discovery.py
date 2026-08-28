"""
Account Discovery Agent (Phase 5).

Coordinates public account discovery across provider adapters (GitHub, Gravatar, npm, GitLab, PyPI, Crates),
normalizing results and guaranteeing complete error isolation.
"""

from __future__ import annotations

from typing import List, Optional
from ..models import AccountFinding, EmailTarget
from ..registry import ProviderRegistry, default_registry


class AccountDiscoveryAgent:
    """
    Facade for discovering public developer accounts across supported public platforms.
    Delegates to centralized ProviderRegistry to avoid duplicate registries.
    """

    def __init__(self, registry: Optional[ProviderRegistry] = None):
        self.registry = registry or default_registry
        self.account_provider_names = ["github", "gravatar", "npm", "gitlab", "pypi", "crates"]

    @property
    def providers(self):
        """Backward-compatibility property returning active provider instances."""
        return [
            self.registry.get(name) for name in self.account_provider_names
            if self.registry.get(name) is not None
        ]

    def discover_all(
        self,
        email: str,
        local_part: str,
        domain: str,
        depth: str = "standard"
    ) -> List[AccountFinding]:
        target = EmailTarget(
            raw_email=email,
            normalized_email=email,
            local_part=local_part,
            domain=domain,
            is_valid=True
        )
        non_account_names = {"web_search", "web", "breach", "hibp", "email_validator"}
        all_registered = self.registry.list_providers()
        custom_account_names = [p for p in all_registered if p not in non_account_names]

        if depth == "quick":
            selected_names = [p for p in ("github", "gravatar") if p in all_registered]
        else:
            selected_names = custom_account_names if custom_account_names else self.account_provider_names

        results = self.registry.execute_all(
            target=target,
            concurrent=True,
            max_workers=6,
            provider_names=selected_names
        )

        all_findings: List[AccountFinding] = []
        for name, res in results.items():
            if res and res.findings:
                for f in res.findings:
                    if isinstance(f, AccountFinding):
                        all_findings.append(f)
        return all_findings
