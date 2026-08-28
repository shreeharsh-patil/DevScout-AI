"""
GitHub Developer Identity & Account Provider Plugin (Phase 4).

Performs deep public GitHub intelligence collection:
- Exact profile email matching
- Commit author/committer history & commit metadata
- Repository ownership, stars, forks, languages, topics
- Public organization memberships
- Account creation date, age, recent activity
- Public bios, websites, location, social handles
- Separates evidence into: EXACT_EMAIL, NAME_EVIDENCE, USERNAME_EVIDENCE,
  ORGANIZATION_EVIDENCE, and WEAK_CORRELATION
- Builds a deterministic GitHub Evidence Graph for each matched entity
"""

from __future__ import annotations

import datetime
import os
from typing import Any, Dict, List, Optional, Tuple
from loguru import logger
import requests
from ..models import (
    AccountFinding,
    DeveloperRepository,
    EmailTarget,
    Evidence,
    EvidenceCategory,
    FindingStatus,
    GitHubCommitRecord,
    GitHubEvidenceGraph,
    GitHubEvidenceGraphEdge,
    GitHubEvidenceGraphNode,
    GitHubOrganization,
    ProviderResult,
    utc_now_iso,
)
from .base import BaseEmailProvider, ProviderHealthStatus


class GitHubEmailProvider(BaseEmailProvider):
    provider_name: str = "github"

    def __init__(self, timeout: float = 12.0, max_retries: int = 2):
        super().__init__(timeout=timeout, max_retries=max_retries)
        token = os.getenv("GITHUB_TOKEN", "")
        self.headers = {"Accept": "application/vnd.github.v3+json"}
        if token:
            self.headers["Authorization"] = f"token {token}"

    def is_available(self) -> bool:
        return True

    def lookup(self, target: EmailTarget) -> ProviderResult:
        email = target.normalized_email or target.raw_email
        local_part = target.local_part
        domain = target.domain
        depth = getattr(target, "depth", "standard") or "standard"

        self._last_error = None
        findings, commits = self.search_with_commits(
            email=email, local_part=local_part, domain=domain, target=target, depth=depth
        )
        all_evidence: List[Evidence] = []
        for f in findings:
            all_evidence.extend(f.evidence)

        if (self._rate_limited or self._last_error or self._health_status == ProviderHealthStatus.RATE_LIMITED) and not findings:
            return ProviderResult(
                provider=self.provider_name,
                finding_type="account",
                status=FindingStatus.UNAVAILABLE,
                confidence_level=FindingStatus.UNAVAILABLE,
                confidence_score=0.0,
                retrieved_at=utc_now_iso(),
                error=self._last_error or "GitHub API rate limit exceeded or access forbidden (HTTP 403/429)",
                findings=[],
                metadata={"rate_limited": bool(self._rate_limited)}
            )

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
            metadata={
                "found_accounts_count": len(findings),
                "commits_count": len(commits),
                "commits": [c.model_dump() for c in commits]
            }
        )

    def search(self, email: str, local_part: str, domain: str, depth: str = "standard") -> List[AccountFinding]:
        target = EmailTarget(
            raw_email=email,
            normalized_email=email,
            local_part=local_part,
            domain=domain,
            is_valid=True
        )
        findings, _ = self.search_with_commits(email, local_part, domain, target=target, depth=depth)
        return findings

    def search_with_commits(
        self,
        email: str,
        local_part: str,
        domain: str,
        target: Optional[EmailTarget] = None,
        depth: str = "standard"
    ) -> Tuple[List[AccountFinding], List[GitHubCommitRecord]]:
        account_map: Dict[str, AccountFinding] = {}
        all_commits: List[GitHubCommitRecord] = []
        error_reason: Optional[str] = None
        clean_depth = depth.lower() if depth in ("quick", "standard", "deep") else "standard"

        # ── Strategy 1: Public Commit Search (STANDARD / DEEP only) ──
        if clean_depth != "quick":
            try:
                commit_headers = {
                    **self.headers,
                    "Accept": "application/vnd.github.cloak-preview+json",
                }
                commit_limit = 15 if clean_depth == "deep" else 6
                url = f"https://api.github.com/search/commits?q=author-email:{requests.utils.quote(email)}&per_page={commit_limit}&sort=author-date"
                resp = self._safe_request(url, headers=commit_headers)
                if resp is not None:
                    if resp.status_code == 200:
                        items = resp.json().get("items", [])
                        for item in items:
                            commit_obj = item.get("commit", {})
                            author_meta = commit_obj.get("author", {})
                            author = item.get("author") or {}
                            committer = item.get("committer") or {}
                            commit_sha = item.get("sha", "")[:8]
                            repo_info = item.get("repository", {})
                            repo_name = repo_info.get("full_name", "")
                            commit_url = item.get("html_url", "")
                            commit_msg = commit_obj.get("message", "")
                            commit_date = author_meta.get("date")

                            commit_record = GitHubCommitRecord(
                                sha=commit_sha,
                                repo_name=repo_name,
                                repo_url=repo_info.get("html_url", f"https://github.com/{repo_name}"),
                                author_name=author_meta.get("name", ""),
                                author_email=author_meta.get("email", email),
                                commit_date=commit_date,
                                commit_message=commit_msg[:120] if commit_msg else None,
                                commit_url=commit_url
                            )
                            all_commits.append(commit_record)

                            for actor in [author, committer]:
                                login = actor.get("login")
                                if login:
                                    ev_id = f"gh_commit_{commit_sha}"
                                    evidence_item = Evidence(
                                        evidence_id=ev_id,
                                        provider="github",
                                        source_type="public_commit",
                                        title=f"GitHub Commit in {repo_name} ({commit_sha})",
                                        url=commit_url or f"https://github.com/{login}",
                                        retrieved_at=utc_now_iso(),
                                        supports="github_identity",
                                        strength="deterministic",
                                        snippet=f"Public commit {commit_sha} in {repo_name} lists '{email}' as author/committer.",
                                        raw_data={"login": login, "sha": commit_sha, "repo": repo_name, "message": commit_msg[:100]},
                                        metadata={"category": EvidenceCategory.EXACT_EMAIL.value}
                                    )

                                    if login in account_map:
                                        # Aggregate evidence into existing account finding
                                        existing_finding = account_map[login]
                                        if not any(e.evidence_id == ev_id for e in existing_finding.evidence):
                                            existing_finding.evidence.append(evidence_item)
                                            existing_finding.evidence_ids.append(ev_id)
                                    else:
                                        profile_data = self._fetch_user_profile(login)
                                        finding = self._build_account_finding(
                                            login=login,
                                            profile_data=profile_data,
                                            status=FindingStatus.VERIFIED,
                                            confidence_score=1.0,
                                            method="public_commit_author_email",
                                            evidence=[evidence_item],
                                            recent_repo=repo_name,
                                            actor_avatar=actor.get("avatar_url")
                                        )
                                        account_map[login] = finding
                    elif resp.status_code in (403, 429):
                        error_reason = "GitHub API rate limit exceeded or access forbidden (HTTP 403/429)"
                        self._rate_limited = True
                        self._last_error = error_reason
                    elif resp.status_code >= 500:
                        error_reason = f"GitHub API server error (HTTP {resp.status_code})"
                        self._last_error = error_reason
            except Exception as e:
                logger.debug(f"[GitHubEmailProvider] Commit search error: {e}")
                error_reason = str(e)
                self._last_error = error_reason

        # ── Strategy 2: Profile Email Match (VERIFIED - public email on profile) ──
        try:
            profile_limit = 10 if clean_depth == "deep" else 5
            url = f"https://api.github.com/search/users?q={requests.utils.quote(email)}+in:email&per_page={profile_limit}"
            resp = self._safe_request(url, headers=self.headers)
            if resp is not None:
                if resp.status_code == 200:
                    for u in resp.json().get("items", []):
                        login = u.get("login", "")
                        if login:
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
                                metadata={"category": EvidenceCategory.EXACT_EMAIL.value}
                            )

                            if login in account_map:
                                existing_finding = account_map[login]
                                if not any(e.evidence_id == ev_id for e in existing_finding.evidence):
                                    existing_finding.evidence.append(evidence_item)
                                    existing_finding.evidence_ids.append(ev_id)
                                existing_finding.status = FindingStatus.VERIFIED
                                existing_finding.confidence_score = 1.0
                                existing_finding.public_email_match = True
                            else:
                                profile_data = self._fetch_user_profile(login)
                                finding = self._build_account_finding(
                                    login=login,
                                    profile_data=profile_data,
                                    status=FindingStatus.VERIFIED,
                                    confidence_score=1.0,
                                    method="public_profile_email",
                                    evidence=[evidence_item],
                                    actor_avatar=u.get("avatar_url")
                                )
                                account_map[login] = finding
                elif resp.status_code in (403, 429):
                    error_reason = "GitHub API rate limit exceeded (HTTP 403/429)"
                    self._rate_limited = True
                    self._last_error = error_reason
                elif resp.status_code >= 500 and not error_reason:
                    error_reason = f"GitHub API server error (HTTP {resp.status_code})"
                    self._last_error = error_reason
        except Exception as e:
            logger.debug(f"[GitHubEmailProvider] Profile search error: {e}")
            if not error_reason:
                error_reason = str(e)
                self._last_error = error_reason

        # ── Strategy 3: Handle Prefix Guess (STANDARD / DEEP only - STRICTLY CANDIDATE / PROBABLE) ──
        if clean_depth != "quick" and local_part and local_part.lower() not in [k.lower() for k in account_map]:
            candidate_handle = local_part.strip()
            clean_handle = candidate_handle.replace(".", "").replace("+", "")
            for handle in [candidate_handle, clean_handle]:
                if not handle or len(handle) < 2 or handle.lower() in [k.lower() for k in account_map]:
                    continue
                profile = self._fetch_user_profile(handle)
                if profile and profile.get("login"):
                    login = profile["login"]
                    if login.lower() in [k.lower() for k in account_map]:
                        continue

                    pub_email = (profile.get("email") or "").strip().lower()
                    bio = (profile.get("bio") or "").lower()
                    company = (profile.get("company") or "").lower()
                    blog = (profile.get("blog") or "").lower()
                    disp_name = (profile.get("name") or "").lower()

                    ev_cat = EvidenceCategory.USERNAME_EVIDENCE
                    if pub_email == email.lower():
                        status = FindingStatus.VERIFIED
                        conf = 1.0
                        method = "public_profile_email"
                        snippet = f"GitHub user '{login}' matches email prefix and has exact matching public profile email '{email}'."
                        ev_cat = EvidenceCategory.EXACT_EMAIL
                    elif domain and (domain in bio or domain in company or domain in blog):
                        status = FindingStatus.PROBABLE
                        conf = 0.70
                        method = "inferred_handle_domain_correlation"
                        snippet = f"GitHub handle '{login}' matches email prefix, and user bio/website references '{domain}'."
                        ev_cat = EvidenceCategory.ORGANIZATION_EVIDENCE
                    elif local_part.replace(".", " ") in disp_name:
                        status = FindingStatus.CANDIDATE
                        conf = 0.35
                        method = "display_name_local_part_correlation"
                        snippet = f"GitHub display name '{profile.get('name')}' matches email local part syntax."
                        ev_cat = EvidenceCategory.NAME_EVIDENCE
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
                        strength="strong" if status == FindingStatus.VERIFIED else "moderate" if status == FindingStatus.PROBABLE else "weak",
                        snippet=snippet,
                        raw_data={"login": login, "public_email": pub_email},
                        metadata={"category": ev_cat.value}
                    )

                    finding = self._build_account_finding(
                        login=login,
                        profile_data=profile,
                        status=status,
                        confidence_score=conf,
                        method=method,
                        evidence=[evidence_item]
                    )
                    account_map[login] = finding
                    break

        findings = list(account_map.values())
        return findings, all_commits

    def _build_account_finding(
        self,
        login: str,
        profile_data: Dict[str, Any],
        status: FindingStatus,
        confidence_score: float,
        method: str,
        evidence: List[Evidence],
        recent_repo: Optional[str] = None,
        actor_avatar: Optional[str] = None
    ) -> AccountFinding:
        created_at = profile_data.get("created_at")
        account_age_years = None
        if created_at:
            try:
                created_dt = datetime.datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                account_age_years = round((datetime.datetime.now(datetime.timezone.utc) - created_dt).days / 365.25, 1)
            except Exception:
                pass

        return AccountFinding(
            provider="github",
            finding_type="account",
            platform="github",
            status=status,
            confidence_level=status,
            confidence_score=confidence_score,
            evidence_ids=[e.evidence_id for e in evidence],
            account_identifier=login,
            profile_url=profile_data.get("html_url") or f"https://github.com/{login}",
            display_name=profile_data.get("name") or login,
            avatar_url=profile_data.get("avatar_url") or actor_avatar,
            bio=profile_data.get("bio"),
            method=method,
            evidence=evidence,
            metadata={
                "public_repos": profile_data.get("public_repos", 0),
                "public_gists": profile_data.get("public_gists", 0),
                "followers": profile_data.get("followers", 0),
                "following": profile_data.get("following", 0),
                "company": profile_data.get("company"),
                "blog": profile_data.get("blog"),
                "location": profile_data.get("location"),
                "twitter_username": profile_data.get("twitter_username"),
                "account_created_at": created_at,
                "account_age_years": account_age_years,
                "recent_repo": recent_repo
            }
        )

    def _fetch_user_profile(self, username: str) -> Dict[str, Any]:
        try:
            url = f"https://api.github.com/users/{username}"
            resp = self._safe_request(url, headers=self.headers, timeout=10)
            if resp and resp.status_code == 200:
                return resp.json()
        except Exception:
            pass
        return {}

    def fetch_user_organizations(self, username: str) -> List[GitHubOrganization]:
        """Fetches public organizations the user is a public member of."""
        try:
            url = f"https://api.github.com/users/{username}/orgs"
            resp = self._safe_request(url, headers=self.headers, timeout=10)
            if resp and resp.status_code == 200:
                orgs = []
                for o in resp.json():
                    orgs.append(GitHubOrganization(
                        login=o.get("login", ""),
                        name=o.get("name"),
                        url=f"https://github.com/{o.get('login', '')}",
                        avatar_url=o.get("avatar_url"),
                        description=o.get("description")
                    ))
                return orgs
        except Exception:
            pass
        return []

    def fetch_user_repositories(self, username: str, limit: int = 8) -> List[DeveloperRepository]:
        """Fetches user repositories sorted by recent push activity."""
        try:
            url = f"https://api.github.com/users/{username}/repos?sort=pushed&per_page={limit}"
            resp = self._safe_request(url, headers=self.headers, timeout=10)
            if resp and resp.status_code == 200:
                repos = []
                for r in resp.json():
                    repos.append(DeveloperRepository(
                        name=r.get("name", ""),
                        full_name=r.get("full_name", ""),
                        url=r.get("html_url", ""),
                        description=r.get("description"),
                        stars=r.get("stargazers_count", 0),
                        forks=r.get("forks_count", 0),
                        language=r.get("language"),
                        topics=r.get("topics", []),
                        updated_at=r.get("pushed_at") or r.get("updated_at")
                    ))
                return repos
        except Exception:
            pass
        return []

    def build_evidence_graph(
        self,
        email: str,
        target_domain: str,
        account: AccountFinding,
        commits: List[GitHubCommitRecord],
        repos: List[DeveloperRepository],
        orgs: List[GitHubOrganization]
    ) -> GitHubEvidenceGraph:
        """Constructs a deterministic GitHub Evidence Graph connecting public signals."""
        nodes: List[GitHubEvidenceGraphNode] = []
        edges: List[GitHubEvidenceGraphEdge] = []
        exact_matches = 0
        correlated_signals = 0

        # Root target node
        email_node_id = f"email:{email}"
        nodes.append(GitHubEvidenceGraphNode(
            id=email_node_id,
            label=email,
            node_type="target_email",
            value=email,
            category=EvidenceCategory.EXACT_EMAIL,
            confidence=1.0
        ))

        # GitHub user profile node
        login = account.account_identifier or "unknown"
        user_node_id = f"github_user:{login}"
        nodes.append(GitHubEvidenceGraphNode(
            id=user_node_id,
            label=f"GitHub @{login}",
            node_type="github_user",
            value=login,
            category=EvidenceCategory.EXACT_EMAIL if account.status == FindingStatus.VERIFIED else EvidenceCategory.USERNAME_EVIDENCE,
            confidence=account.confidence_score,
            metadata={"display_name": account.display_name, "status": account.status.value}
        ))

        # Profile link edge
        if account.status == FindingStatus.VERIFIED:
            exact_matches += 1
            edges.append(GitHubEvidenceGraphEdge(
                source=email_node_id,
                target=user_node_id,
                relationship="owns_verified_profile",
                strength="deterministic",
                weight=1.0,
                description=f"Public GitHub user profile @{login} directly exposes email '{email}'."
            ))
        elif account.status == FindingStatus.PROBABLE:
            correlated_signals += 1
            edges.append(GitHubEvidenceGraphEdge(
                source=email_node_id,
                target=user_node_id,
                relationship="domain_correlated_profile",
                strength="moderate",
                weight=0.70,
                description=f"GitHub handle @{login} matches email prefix and bio/company references domain '{target_domain}'."
            ))
        else:
            edges.append(GitHubEvidenceGraphEdge(
                source=email_node_id,
                target=user_node_id,
                relationship="candidate_username_match",
                strength="weak",
                weight=0.25,
                description=f"GitHub handle @{login} matches email local-part syntax (unverified candidate lead)."
            ))

        # Commit nodes and edges
        for c in commits[:4]:
            exact_matches += 1
            commit_node_id = f"commit:{c.sha}"
            nodes.append(GitHubEvidenceGraphNode(
                id=commit_node_id,
                label=f"Commit {c.sha} ({c.repo_name})",
                node_type="commit",
                value=c.sha,
                category=EvidenceCategory.EXACT_EMAIL,
                confidence=1.0,
                metadata={"repo": c.repo_name, "message": c.commit_message}
            ))

            edges.append(GitHubEvidenceGraphEdge(
                source=email_node_id,
                target=commit_node_id,
                relationship="authored_commit",
                strength="deterministic",
                weight=1.0,
                description=f"Email '{email}' explicitly recorded as author/committer in commit {c.sha}."
            ))
            edges.append(GitHubEvidenceGraphEdge(
                source=commit_node_id,
                target=user_node_id,
                relationship="committed_by",
                strength="deterministic",
                weight=1.0,
                description=f"Commit {c.sha} authored in user repository context."
            ))

        # Organization nodes and edges
        for o in orgs[:3]:
            correlated_signals += 1
            org_node_id = f"org:{o.login}"
            nodes.append(GitHubEvidenceGraphNode(
                id=org_node_id,
                label=f"Org: {o.name or o.login}",
                node_type="organization",
                value=o.login,
                category=EvidenceCategory.ORGANIZATION_EVIDENCE,
                confidence=0.85
            ))
            edges.append(GitHubEvidenceGraphEdge(
                source=user_node_id,
                target=org_node_id,
                relationship="member_of",
                strength="strong",
                weight=0.85,
                description=f"Public member of organization {o.login}."
            ))

        # Notable repository nodes and edges
        for r in repos[:3]:
            repo_node_id = f"repo:{r.name}"
            nodes.append(GitHubEvidenceGraphNode(
                id=repo_node_id,
                label=f"Repo: {r.name}",
                node_type="repository",
                value=r.full_name,
                category=EvidenceCategory.WEAK_CORRELATION,
                confidence=0.75,
                metadata={"stars": r.stars, "language": r.language}
            ))
            edges.append(GitHubEvidenceGraphEdge(
                source=user_node_id,
                target=repo_node_id,
                relationship="maintains_repository",
                strength="moderate",
                weight=0.70,
                description=f"Authored repository {r.name} ({r.stars} stars, {r.language or 'N/A'})."
            ))

        summary = (
            f"GitHub Evidence Graph for @{login}: {exact_matches} deterministic email evidence link(s), "
            f"{correlated_signals} organizational/domain correlation(s), {len(repos)} active repository node(s)."
        )

        return GitHubEvidenceGraph(
            nodes=nodes,
            edges=edges,
            summary=summary,
            verification_tier=account.status,
            confidence_score=account.confidence_score,
            exact_email_matches=exact_matches,
            correlated_signals_count=correlated_signals
        )


# Backward-compatible alias
GitHubProvider = GitHubEmailProvider
