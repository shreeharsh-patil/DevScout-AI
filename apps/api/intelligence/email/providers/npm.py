"""
npm Registry Developer Footprint Provider Plugin (Phase 5).

Discovers published npm packages and maintainer profiles associated with public developer emails.
"""

from __future__ import annotations

from typing import Any, Dict, List
from loguru import logger
import requests
from ..models import (
    AccountFinding,
    EmailTarget,
    Evidence,
    FindingStatus,
    ProviderResult,
    utc_now_iso,
)
from .base import BaseEmailProvider


class NpmEmailProvider(BaseEmailProvider):
    provider_name: str = "npm"

    def __init__(self, timeout: float = 12.0, max_retries: int = 2):
        super().__init__(timeout=timeout, max_retries=max_retries)

    def is_available(self) -> bool:
        return True

    def lookup(self, target: EmailTarget) -> ProviderResult:
        email = target.normalized_email or target.raw_email
        findings = self.search(email=email, local_part=target.local_part, domain=target.domain)

        all_evidence: List[Evidence] = []
        for f in findings:
            all_evidence.extend(f.evidence)

        if findings:
            top_status = FindingStatus.VERIFIED
            top_score = 0.95
        else:
            top_status = FindingStatus.NO_EVIDENCE
            top_score = 0.0

        return ProviderResult(
            provider=self.provider_name,
            finding_type="account",
            status=top_status,
            confidence_level=top_status,
            confidence_score=top_score,
            evidence_ids=[e.evidence_id for e in all_evidence],
            evidence_items=all_evidence,
            findings=findings,
            retrieved_at=utc_now_iso(),
            metadata={"npm_maintainer_packages_found": len(findings)}
        )

    def search(self, email: str, local_part: str, domain: str) -> List[AccountFinding]:
        findings: List[AccountFinding] = []
        normalized_email = email.strip().lower()

        try:
            url = f"https://registry.npmjs.org/-/v1/search?text=maintainer:{requests.utils.quote(normalized_email)}&size=10"
            resp = self._safe_request(url, timeout=12)
            if resp and resp.status_code == 200:
                objects = resp.json().get("objects", [])
                if objects:
                    pkg_names = [obj.get("package", {}).get("name", "") for obj in objects if obj.get("package")]
                    first_pkg = objects[0].get("package", {})
                    author_name = first_pkg.get("publisher", {}).get("username") or local_part

                    ev_id = "npm_maintainer_registry"
                    evidence = Evidence(
                        evidence_id=ev_id,
                        provider="npm",
                        source_type="package_registry_maintainer",
                        title=f"npm Package Maintainer ({len(pkg_names)} packages)",
                        url=f"https://www.npmjs.com/~{author_name}",
                        retrieved_at=utc_now_iso(),
                        supports="npm_footprint",
                        strength="strong",
                        snippet=f"Maintainer of npm packages: {', '.join(pkg_names[:5])}",
                        raw_data={"packages": pkg_names, "publisher": author_name}
                    )

                    finding = AccountFinding(
                        provider="npm",
                        finding_type="account",
                        platform="npm",
                        status=FindingStatus.VERIFIED,
                        confidence_level=FindingStatus.VERIFIED,
                        confidence_score=0.95,
                        evidence_ids=[ev_id],
                        account_identifier=author_name,
                        profile_url=f"https://www.npmjs.com/~{author_name}",
                        display_name=author_name,
                        method="npm_maintainer_email_search",
                        public_email_match=True,
                        username_match=True,
                        website_match=False,
                        ecosystem_category="package_registry",
                        evidence=[evidence],
                        metadata={"packages": pkg_names}
                    )
                    findings.append(finding)
        except Exception as e:
            logger.debug(f"[NpmEmailProvider] Error: {e}")

        return findings

    def fetch_maintainer_packages(self, query: str) -> List[Dict[str, Any]]:
        packages: List[Dict[str, Any]] = []
        try:
            url = f"https://registry.npmjs.org/-/v1/search?text=maintainer:{requests.utils.quote(query)}&size=8"
            resp = self._safe_request(url, timeout=10)
            if resp and resp.status_code == 200:
                for item in resp.json().get("objects", []):
                    pkg = item.get("package", {})
                    packages.append({
                        "name": pkg.get("name"),
                        "version": pkg.get("version"),
                        "description": pkg.get("description"),
                        "links": pkg.get("links", {})
                    })
        except Exception as e:
            logger.debug(f"[NpmEmailProvider] fetch_maintainer_packages error: {e}")
        return packages


# Backward-compatible alias
NpmProvider = NpmEmailProvider
