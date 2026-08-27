"""
Crates.io (Rust Package Registry) Public Ecosystem Provider Plugin.

Searches crates.io public metadata for crates authored or maintained by the target handle/email.
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


class CratesEmailProvider(BaseEmailProvider):
    provider_name: str = "crates"

    def is_available(self) -> bool:
        return True

    def lookup(self, target: EmailTarget) -> ProviderResult:
        email = target.normalized_email or target.raw_email
        local_part = target.local_part
        domain = target.domain

        findings, crates = self.search_crates(email=email, local_part=local_part, domain=domain)
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
            metadata={"crates_count": len(crates), "crates": crates}
        )

    def search_crates(
        self, email: str, local_part: str, domain: str
    ) -> tuple[List[AccountFinding], List[Dict[str, Any]]]:
        findings: List[AccountFinding] = []
        crates: List[Dict[str, Any]] = []

        if not local_part:
            return findings, crates

        clean_name = re.sub(r"[^a-zA-Z0-9_-]", "", local_part.lower())
        if not clean_name:
            return findings, crates

        try:
            headers = {"User-Agent": "DevScout-AI (https://github.com/shreeharsh-patil/DevScout-AI)"}
            url = f"https://crates.io/api/v1/crates/{clean_name}"
            resp = self._safe_request(url, headers=headers, timeout=8)
            if resp and resp.status_code == 200:
                data = resp.json().get("crate", {})
                crate_name = data.get("name", clean_name)
                desc = data.get("description", "")
                homepage = data.get("homepage") or data.get("repository") or ""
                downloads = data.get("downloads", 0)

                crate_meta = {
                    "name": crate_name,
                    "description": desc,
                    "homepage": homepage,
                    "downloads": downloads,
                    "url": f"https://crates.io/crates/{crate_name}"
                }
                crates.append(crate_meta)

                is_domain_match = bool(domain and homepage and domain in homepage.lower())
                status = FindingStatus.PROBABLE if is_domain_match else FindingStatus.CANDIDATE
                conf = 0.65 if is_domain_match else 0.25
                method = "crates_domain_match" if is_domain_match else "crates_candidate_name_match"

                ev_id = f"crates_{crate_name}"
                ev = Evidence(
                    evidence_id=ev_id,
                    provider="crates",
                    source_type="package_registry",
                    title=f"Rust Crate: {crate_name}",
                    url=f"https://crates.io/crates/{crate_name}",
                    retrieved_at=utc_now_iso(),
                    supports="rust_crate_author",
                    strength="moderate" if is_domain_match else "weak",
                    snippet=f"Rust crate '{crate_name}' found on crates.io ({downloads:,} downloads). {desc[:100]}",
                    raw_data=crate_meta
                )

                finding = AccountFinding(
                    provider="crates",
                    finding_type="account",
                    platform="crates",
                    status=status,
                    confidence_level=status,
                    confidence_score=conf,
                    evidence_ids=[ev_id],
                    account_identifier=crate_name,
                    profile_url=f"https://crates.io/crates/{crate_name}",
                    display_name=crate_name,
                    bio=desc,
                    method=method,
                    public_email_match=False,
                    username_match=True,
                    website_match=is_domain_match,
                    ecosystem_category="package_registry",
                    evidence=[ev],
                    metadata=crate_meta
                )
                findings.append(finding)
        except Exception as e:
            logger.debug(f"[CratesEmailProvider] Error probing Crates.io for '{clean_name}': {e}")

        return findings, crates


# Backward-compatible alias
CratesProvider = CratesEmailProvider
