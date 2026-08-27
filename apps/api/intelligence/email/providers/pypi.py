"""
PyPI (Python Package Index) Public Package Registry Provider Plugin.

Searches PyPI public metadata for packages maintained or authored by the target email/user.
Strictly distinguishes exact author email matches from candidate username packages.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List
from loguru import logger
from ..models import (
    AccountFinding,
    EmailTarget,
    Evidence,
    FindingStatus,
    ProviderResult,
    utc_now_iso,
)
from .base import BaseEmailProvider


class PyPIEmailProvider(BaseEmailProvider):
    provider_name: str = "pypi"

    def is_available(self) -> bool:
        return True

    def lookup(self, target: EmailTarget) -> ProviderResult:
        email = target.normalized_email or target.raw_email
        local_part = target.local_part
        domain = target.domain

        findings, packages = self.search_pypi(email=email, local_part=local_part, domain=domain)
        all_evidence: List[Evidence] = []
        for f in findings:
            all_evidence.extend(f.evidence)

        if not findings:
            return ProviderResult(
                provider=self.provider_name,
                finding_type="account",
                status=FindingStatus.NO_EVIDENCE,
                confidence_level=FindingStatus.NO_EVIDENCE,
                confidence_score=0.0,
                retrieved_at=utc_now_iso(),
                findings=[]
            )

        top_status = FindingStatus.NO_EVIDENCE
        if any(f.status == FindingStatus.VERIFIED for f in findings):
            top_status = FindingStatus.VERIFIED
            top_score = 1.0
        elif any(f.status == FindingStatus.HIGH_CONFIDENCE for f in findings):
            top_status = FindingStatus.HIGH_CONFIDENCE
            top_score = 0.85
        elif any(f.status == FindingStatus.PROBABLE for f in findings):
            top_status = FindingStatus.PROBABLE
            top_score = 0.65
        else:
            top_status = FindingStatus.CANDIDATE
            top_score = 0.25

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
            metadata={"packages_count": len(packages), "packages": packages}
        )

    def search_pypi(
        self, email: str, local_part: str, domain: str
    ) -> tuple[List[AccountFinding], List[Dict[str, Any]]]:
        findings: List[AccountFinding] = []
        packages: List[Dict[str, Any]] = []

        # Query PyPI public simple search API or project search
        # E.g. search candidate packages matching username
        if not local_part:
            return findings, packages

        clean_pkg = re.sub(r"[^a-zA-Z0-9_-]", "", local_part.lower())
        candidate_names = [clean_pkg] if clean_pkg else []

        for pkg_name in candidate_names:
            try:
                url = f"https://pypi.org/pypi/{pkg_name}/json"
                resp = self._safe_request(url, headers={"Accept": "application/json"}, timeout=8)
                if resp and resp.status_code == 200:
                    data = resp.json()
                    info = data.get("info", {})
                    author = info.get("author", "")
                    author_email = (info.get("author_email") or "").strip().lower()
                    maintainer_email = (info.get("maintainer_email") or "").strip().lower()
                    home_page = info.get("home_page") or info.get("project_url")
                    summary = info.get("summary", "")
                    version = info.get("version", "latest")

                    pkg_meta = {
                        "name": pkg_name,
                        "version": version,
                        "summary": summary,
                        "author": author,
                        "url": f"https://pypi.org/project/{pkg_name}/"
                    }
                    packages.append(pkg_meta)

                    # Check exact email match
                    is_exact_email = (email.lower() in author_email) or (email.lower() in maintainer_email)
                    is_domain_match = bool(domain and home_page and domain in home_page.lower())

                    if is_exact_email:
                        status = FindingStatus.VERIFIED
                        conf = 1.0
                        method = "pypi_exact_author_email"
                        snippet = f"PyPI package '{pkg_name}' v{version} authored with exact matching email '{email}'."
                    elif is_domain_match:
                        status = FindingStatus.PROBABLE
                        conf = 0.70
                        method = "pypi_project_domain_match"
                        snippet = f"PyPI package '{pkg_name}' matches username prefix, and project website matches domain '{domain}'."
                    else:
                        status = FindingStatus.CANDIDATE
                        conf = 0.25
                        method = "pypi_candidate_package_name_match"
                        snippet = f"PyPI package '{pkg_name}' matches email prefix (unverified candidate package)."

                    ev_id = f"pypi_{pkg_name}"
                    ev = Evidence(
                        evidence_id=ev_id,
                        provider="pypi",
                        source_type="package_registry",
                        title=f"PyPI Package: {pkg_name}",
                        url=f"https://pypi.org/project/{pkg_name}/",
                        retrieved_at=utc_now_iso(),
                        supports="pypi_package_author",
                        strength="deterministic" if is_exact_email else "weak",
                        snippet=snippet,
                        raw_data=pkg_meta
                    )

                    finding = AccountFinding(
                        provider="pypi",
                        finding_type="account",
                        platform="pypi",
                        status=status,
                        confidence_level=status,
                        confidence_score=conf,
                        evidence_ids=[ev_id],
                        account_identifier=author or pkg_name,
                        profile_url=f"https://pypi.org/project/{pkg_name}/",
                        display_name=author or pkg_name,
                        bio=summary,
                        method=method,
                        public_email_match=is_exact_email,
                        username_match=True,
                        website_match=is_domain_match,
                        ecosystem_category="package_registry",
                        evidence=[ev],
                        metadata=pkg_meta
                    )
                    findings.append(finding)
            except Exception as e:
                logger.debug(f"[PyPIEmailProvider] Error probing PyPI for '{pkg_name}': {e}")

        return findings, packages


# Backward-compatible alias
PyPIProvider = PyPIEmailProvider
