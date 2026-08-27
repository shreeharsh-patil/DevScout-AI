"""
GitLab Developer Identity Provider.

Discovers public GitLab developer accounts using the public GitLab REST API.
"""

from __future__ import annotations

from typing import List
from loguru import logger
import requests
from ..models import AccountFinding, FindingStatus, Evidence, utc_now_iso
from .base import BaseProvider


class GitLabProvider(BaseProvider):
    platform_name: str = "gitlab"

    def search(self, email: str, local_part: str, domain: str) -> List[AccountFinding]:
        findings: List[AccountFinding] = []

        # 1. Search public GitLab users by username prefix candidate
        try:
            url = f"https://gitlab.com/api/v4/users?username={requests.utils.quote(local_part)}"
            resp = self._safe_request(url, timeout=10)
            if resp and resp.status_code == 200:
                users = resp.json()
                for u in users:
                    if u.get("username", "").lower() == local_part.lower():
                        login = u.get("username")
                        pub_email = (u.get("public_email") or "").strip().lower()
                        status = (
                            FindingStatus.VERIFIED
                            if pub_email == email.lower()
                            else FindingStatus.CANDIDATE
                        )
                        conf = 1.0 if status == FindingStatus.VERIFIED else 0.25

                        ev_id = f"gitlab_{login}"
                        evidence = Evidence(
                            evidence_id=ev_id,
                            provider="gitlab",
                            source_type="public_profile",
                            title=f"GitLab Profile: {login}",
                            url=u.get("web_url") or f"https://gitlab.com/{login}",
                            retrieved_at=utc_now_iso(),
                            supports="gitlab_identity",
                            strength="deterministic" if status == FindingStatus.VERIFIED else "weak",
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
                            method="gitlab_public_profile_search",
                            evidence=[evidence],
                            metadata={"public_email": pub_email, "state": u.get("state")}
                        )
                        findings.append(finding)
        except Exception as e:
            logger.debug(f"[GitLabProvider] Error: {e}")

        return findings
