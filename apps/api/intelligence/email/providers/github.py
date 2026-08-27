"""
GitHub Developer Identity & Account Provider.

Discovers public GitHub developer accounts using commit history author emails,
public profile emails, and strict candidate handle checks.
"""

from __future__ import annotations

import os
from typing import Any, Dict, List
from loguru import logger
import requests
from ..models import AccountFinding, FindingStatus, Evidence, utc_now_iso
from .base import BaseProvider


class GitHubProvider(BaseProvider):
    platform_name: str = "github"

    def __init__(self, timeout: int = 15):
        super().__init__(timeout=timeout)
        token = os.getenv("GITHUB_TOKEN", "")
        self.headers = {"Accept": "application/vnd.github.v3+json"}
        if token:
            self.headers["Authorization"] = f"token {token}"

    def search(self, email: str, local_part: str, domain: str) -> List[AccountFinding]:
        findings: List[AccountFinding] = []
        found_logins: set[str] = set()

        # ── Strategy 1: Public Commit Search (VERIFIED - exact author email) ──
        try:
            commit_headers = {
                **self.headers,
                "Accept": "application/vnd.github.cloak-preview+json",
            }
            url = f"https://api.github.com/search/commits?q=author-email:{requests.utils.quote(email)}&per_page=5&sort=author-date"
            resp = self._safe_request(url, headers=commit_headers)
            if resp and resp.status_code == 200:
                items = resp.json().get("items", [])
                for item in items:
                    author = item.get("author") or {}
                    committer = item.get("committer") or {}
                    commit_sha = item.get("sha", "")[:8]
                    repo_info = item.get("repository", {})
                    repo_name = repo_info.get("full_name", "")
                    commit_url = item.get("html_url", "")

                    for actor in [author, committer]:
                        login = actor.get("login")
                        if login and login not in found_logins:
                            found_logins.add(login)
                            profile_data = self._fetch_user_profile(login)

                            ev_id = f"gh_commit_{commit_sha}"
                            evidence_item = Evidence(
                                evidence_id=ev_id,
                                provider="github",
                                source_type="public_commit",
                                title=f"GitHub Commit Author in {repo_name}",
                                url=commit_url or f"https://github.com/{login}",
                                retrieved_at=utc_now_iso(),
                                supports="github_identity",
                                strength="deterministic",
                                snippet=f"Public commit {commit_sha} in {repo_name} lists '{email}' as author/committer.",
                                raw_data={"login": login, "sha": commit_sha, "repo": repo_name}
                            )

                            finding = AccountFinding(
                                provider="github",
                                finding_type="account",
                                platform="github",
                                status=FindingStatus.VERIFIED,
                                confidence_level=FindingStatus.VERIFIED,
                                confidence_score=1.0,
                                evidence_ids=[ev_id],
                                account_identifier=login,
                                profile_url=f"https://github.com/{login}",
                                display_name=profile_data.get("name") or login,
                                avatar_url=profile_data.get("avatar_url") or actor.get("avatar_url"),
                                bio=profile_data.get("bio"),
                                method="public_commit_author_email",
                                evidence=[evidence_item],
                                metadata={
                                    "public_repos": profile_data.get("public_repos", 0),
                                    "followers": profile_data.get("followers", 0),
                                    "company": profile_data.get("company"),
                                    "blog": profile_data.get("blog"),
                                    "location": profile_data.get("location"),
                                    "recent_repo": repo_name
                                }
                            )
                            findings.append(finding)
        except Exception as e:
            logger.debug(f"[GitHubProvider] Commit search error: {e}")

        # ── Strategy 2: Profile Email Match (VERIFIED - public email on profile) ──
        try:
            url = f"https://api.github.com/search/users?q={requests.utils.quote(email)}+in:email&per_page=5"
            resp = self._safe_request(url, headers=self.headers)
            if resp and resp.status_code == 200:
                for u in resp.json().get("items", []):
                    login = u.get("login", "")
                    if login and login not in found_logins:
                        found_logins.add(login)
                        profile_data = self._fetch_user_profile(login)

                        ev_id = f"gh_profile_{login}"
                        evidence_item = Evidence(
                            evidence_id=ev_id,
                            provider="github",
                            source_type="profile_email",
                            title=f"GitHub Profile Email: {login}",
                            url=f"https://github.com/{login}",
                            retrieved_at=utc_now_iso(),
                            supports="github_identity",
                            strength="deterministic",
                            snippet=f"User profile '{login}' publicly displays email address '{email}'.",
                            raw_data=profile_data
                        )

                        finding = AccountFinding(
                            provider="github",
                            finding_type="account",
                            platform="github",
                            status=FindingStatus.VERIFIED,
                            confidence_level=FindingStatus.VERIFIED,
                            confidence_score=1.0,
                            evidence_ids=[ev_id],
                            account_identifier=login,
                            profile_url=f"https://github.com/{login}",
                            display_name=profile_data.get("name") or login,
                            avatar_url=profile_data.get("avatar_url") or u.get("avatar_url"),
                            bio=profile_data.get("bio"),
                            method="public_profile_email",
                            evidence=[evidence_item],
                            metadata={
                                "public_repos": profile_data.get("public_repos", 0),
                                "followers": profile_data.get("followers", 0),
                                "company": profile_data.get("company"),
                                "blog": profile_data.get("blog"),
                                "location": profile_data.get("location")
                            }
                        )
                        findings.append(finding)
        except Exception as e:
            logger.debug(f"[GitHubProvider] Profile search error: {e}")

        # ── Strategy 3: Handle Prefix Guess (STRICTLY CANDIDATE / PROBABLE) ──
        if local_part and local_part.lower() not in [login.lower() for login in found_logins]:
            candidate_handle = local_part.strip()
            clean_handle = candidate_handle.replace(".", "").replace("+", "")
            for handle in [candidate_handle, clean_handle]:
                if not handle or len(handle) < 2 or handle in found_logins:
                    continue
                profile = self._fetch_user_profile(handle)
                if profile and profile.get("login"):
                    login = profile["login"]
                    found_logins.add(login)

                    pub_email = (profile.get("email") or "").strip().lower()
                    bio = (profile.get("bio") or "").lower()
                    company = (profile.get("company") or "").lower()
                    blog = (profile.get("blog") or "").lower()

                    if pub_email == email.lower():
                        status = FindingStatus.VERIFIED
                        conf = 1.0
                        method = "public_profile_email"
                        snippet = f"GitHub user '{login}' matches email prefix and has exact matching public profile email '{email}'."
                    elif domain and (domain in bio or domain in company or domain in blog):
                        status = FindingStatus.PROBABLE
                        conf = 0.70
                        method = "inferred_handle_domain_correlation"
                        snippet = f"GitHub handle '{login}' matches email prefix, and user bio/website references '{domain}'."
                    else:
                        status = FindingStatus.CANDIDATE
                        conf = 0.25
                        method = "unverified_handle_prefix_guess"
                        snippet = f"GitHub handle '{login}' matches email prefix '{handle}', but no cryptographic or email link was verified. Treat as an unconfirmed candidate lead only."

                    ev_id = f"gh_candidate_{login}"
                    evidence_item = Evidence(
                        evidence_id=ev_id,
                        provider="github",
                        source_type="candidate_handle",
                        title=f"GitHub Profile: {login} ({status.value})",
                        url=f"https://github.com/{login}",
                        retrieved_at=utc_now_iso(),
                        supports="github_identity",
                        strength="moderate" if status == FindingStatus.PROBABLE else "weak",
                        snippet=snippet,
                        raw_data={"login": login, "public_email": pub_email}
                    )

                    finding = AccountFinding(
                        provider="github",
                        finding_type="account",
                        platform="github",
                        status=status,
                        confidence_level=status,
                        confidence_score=conf,
                        evidence_ids=[ev_id],
                        account_identifier=login,
                        profile_url=f"https://github.com/{login}",
                        display_name=profile.get("name") or login,
                        avatar_url=profile.get("avatar_url"),
                        bio=profile.get("bio"),
                        method=method,
                        evidence=[evidence_item],
                        metadata={
                            "public_repos": profile.get("public_repos", 0),
                            "followers": profile.get("followers", 0),
                            "company": profile.get("company"),
                            "blog": profile.get("blog"),
                            "location": profile.get("location")
                        }
                    )
                    findings.append(finding)
                    break

        return findings

    def _fetch_user_profile(self, username: str) -> Dict[str, Any]:
        try:
            url = f"https://api.github.com/users/{username}"
            resp = self._safe_request(url, headers=self.headers, timeout=10)
            if resp and resp.status_code == 200:
                return resp.json()
        except Exception:
            pass
        return {}

    def fetch_user_repositories(self, username: str, limit: int = 6) -> List[Dict[str, Any]]:
        try:
            url = f"https://api.github.com/users/{username}/repos?sort=pushed&per_page={limit}"
            resp = self._safe_request(url, headers=self.headers, timeout=10)
            if resp and resp.status_code == 200:
                repos = []
                for r in resp.json():
                    repos.append({
                        "name": r.get("name", ""),
                        "full_name": r.get("full_name", ""),
                        "url": r.get("html_url", ""),
                        "description": r.get("description"),
                        "stars": r.get("stargazers_count", 0),
                        "forks": r.get("forks_count", 0),
                        "language": r.get("language"),
                        "updated_at": r.get("pushed_at") or r.get("updated_at")
                    })
                return repos
        except Exception:
            pass
        return []
