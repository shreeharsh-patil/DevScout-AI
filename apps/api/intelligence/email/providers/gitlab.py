"""
GitLab Developer Identity Provider Plugin (Phase 5).

Discovers public GitLab developer accounts using the public GitLab REST API.
Strictly distinguishes exact public email matches from candidate usernames.
"""

from __future__ import annotations

from typing import List
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


class GitLabEmailProvider(BaseEmailProvider):
    provider_name: str = "gitlab"

    def __init__(self, timeout: float = 10.0, max_retries: int = 2):
        super().__init__(timeout=timeout, max_retries=max_retries)

    def is_available(self) -> bool:
        return True

    def lookup(self, target: EmailTarget) -> ProviderResult:
        email = target.normalized_email or target.raw_email
        findings = self.search(email=email, local_part=target.local_part, domain=target.domain)

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

        top_status = findings[0].status
        top_score = findings[0].confidence_score

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
            metadata={"gitlab_accounts_found": len(findings)}
        )

    def search(self, email: str, local_part: str, domain: str) -> List[AccountFinding]:
        findings: List[AccountFinding] = []

        try:
            url = f"https://gitlab.com/api/v4/users?username={requests.utils.quote(local_part)}"
            resp = self._safe_request(url, timeout=10)
            if resp and resp.status_code == 200:
                users = resp.json()
                for u in users:
                    if u.get("username", "").lower() == local_part.lower():
                        login = u.get("username")
                        pub_email = (u.get("public_email") or "").strip().lower()
                        is_exact_email = (pub_email == email.lower())
                        website_url = u.get("website_url") or ""
                        is_domain_match = bool(domain and website_url and domain in website_url.lower())

                        if is_exact_email:
                            status = FindingStatus.VERIFIED
                            conf = 1.0
                            method = "gitlab_exact_public_email"
                        elif is_domain_match:
                            status = FindingStatus.PROBABLE
                            conf = 0.70
                            method = "gitlab_website_domain_match"
                        else:
                            status = FindingStatus.CANDIDATE
                            conf = 0.25
                            method = "gitlab_candidate_username_match"

                        ev_id = f"gitlab_{login}"
                        evidence = Evidence(
                            evidence_id=ev_id,
                            provider="gitlab",
                            source_type="public_profile",
                            title=f"GitLab Profile: {login}",
                            url=u.get("web_url") or f"https://gitlab.com/{login}",
                            retrieved_at=utc_now_iso(),
                            supports="gitlab_identity",
                            strength="deterministic" if is_exact_email else "weak",
                            snippet=f"GitLab user '{login}' ({status.value}). Public email: {pub_email or 'Hidden'}.",
                            raw_data=u
                        )

                        finding = AccountFinding(
                            provider="gitlab",
                            finding_type="account",
                            platform="gitlab",
                            status=status,
                            confidence_level=status,
                            confidence_score=conf,
                            evidence_ids=[ev_id],
                            account_identifier=login,
                            profile_url=u.get("web_url") or f"https://gitlab.com/{login}",
                            display_name=u.get("name") or login,
                            avatar_url=u.get("avatar_url"),
                            bio=u.get("bio"),
                            method=method,
                            public_email_match=is_exact_email,
                            username_match=True,
                            website_match=is_domain_match,
                            ecosystem_category="code_hosting",
                            evidence=[evidence],
                            metadata={"public_email": pub_email, "state": u.get("state"), "website_url": website_url}
                        )
                        findings.append(finding)
        except Exception as e:
            logger.debug(f"[GitLabEmailProvider] Error: {e}")

        return findings


# Backward-compatible alias
GitLabProvider = GitLabEmailProvider
