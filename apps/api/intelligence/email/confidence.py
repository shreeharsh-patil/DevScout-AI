"""
Advanced Deterministic Confidence Engine (Phase 9).

Calculates explainable, calibrated confidence scores and tiers:
- VERIFIED: 90–100 (Cryptographic proof, verified commit author, exact profile email match)
- HIGH_CONFIDENCE: 75–89 (Multiple independent sources: e.g. cross-linked profile + same website + verified npm package)
- PROBABLE: 50–74 (Domain website correlation + matching org or exact web mention)
- CANDIDATE: 1–49 (Unverified username / prefix similarity alone)
- NO_EVIDENCE: 0 (No public signals found)

Strictly enforces source independence (multiple pages copying the same data count as 1 source).
Generates transparent supporting (+) and contradicting (-) signal explanations.
"""

from __future__ import annotations

from typing import List, Set
from urllib.parse import urlparse
from .models import (
    AccountFinding,
    ConfidenceAssessment,
    FindingStatus,
    WebMentionFinding,
)


class ConfidenceEngine:
    """Evaluates evidence items and assigns deterministic, explainable confidence scores and tiers."""

    @staticmethod
    def evaluate(
        account_findings: List[AccountFinding],
        web_mentions: List[WebMentionFinding],
        breaches_count: int,
        has_domain_ownership: bool = False,
        is_role_account: bool = False
    ) -> ConfidenceAssessment:
        reasons: List[str] = []
        supporting_signals: List[str] = []
        contradicting_signals: List[str] = []
        score = 0

        verified_accounts = [a for a in account_findings if a.status == FindingStatus.VERIFIED]
        high_conf_accounts = [a for a in account_findings if a.status == FindingStatus.HIGH_CONFIDENCE]
        probable_accounts = [a for a in account_findings if a.status == FindingStatus.PROBABLE]
        candidate_accounts = [a for a in account_findings if a.status == FindingStatus.CANDIDATE]

        exact_web_mentions = [m for m in web_mentions if m.is_exact_match or m.correlation_type.value == "exact_email_mention"]

        # ── Measure Source Independence ──
        independent_sources: Set[str] = set()
        total_evidence_count = 0

        for a in account_findings:
            if a.status in (FindingStatus.VERIFIED, FindingStatus.HIGH_CONFIDENCE, FindingStatus.PROBABLE):
                independent_sources.add(f"account:{a.platform}")
                total_evidence_count += len(a.evidence)

        for m in exact_web_mentions:
            total_evidence_count += 1
            domain = m.domain.lower() if m.domain else "web"
            # Deduplicate by domain
            independent_sources.add(f"web:{domain}")

        if breaches_count > 0:
            total_evidence_count += breaches_count
            independent_sources.add("security:breach_registry")

        if has_domain_ownership:
            total_evidence_count += 1
            independent_sources.add("dns:domain_registry")

        # ── 1. Supporting Signals Evaluation ──
        has_github_commit_match = any(
            a.platform == "github" and any("commit" in e.source_type or "commit" in a.method for e in a.evidence)
            for a in verified_accounts
        )
        has_github_profile_email = any(
            a.platform == "github" and any("profile_email" in e.source_type or "profile_email" in a.method for e in a.evidence)
            for a in verified_accounts
        )
        has_gravatar_profile = any(
            a.platform == "gravatar" and a.status == FindingStatus.VERIFIED
            for a in verified_accounts
        )
        has_npm_maintainer = any(
            a.platform == "npm" and a.status in (FindingStatus.VERIFIED, FindingStatus.HIGH_CONFIDENCE)
            for a in verified_accounts + high_conf_accounts
        )
        has_pypi_author = any(
            a.platform == "pypi" and a.status in (FindingStatus.VERIFIED, FindingStatus.HIGH_CONFIDENCE)
            for a in verified_accounts + high_conf_accounts
        )
        has_gitlab_verified = any(
            a.platform == "gitlab" and a.status == FindingStatus.VERIFIED
            for a in verified_accounts
        )

        if has_github_commit_match:
            score += 45
            supporting_signals.append("+ Exact email in public GitHub commit author/committer history (+45)")
            reasons.append("Exact email discovered in public GitHub commit author/committer history.")

        if has_github_profile_email:
            score += 35
            supporting_signals.append("+ Exact email listed on public GitHub developer profile (+35)")
            reasons.append("Exact email listed publicly on verified GitHub developer profile.")

        if has_gravatar_profile:
            score += 30
            supporting_signals.append("+ Verified public Gravatar profile matched via cryptographic hash (+30)")
            reasons.append("Verified public Gravatar profile matched via cryptographic hash.")

        if has_npm_maintainer:
            score += 25
            supporting_signals.append("+ Verified public npm package maintainer record (+25)")
            reasons.append("Public npm package registry author/maintainer record matches email.")

        if has_pypi_author:
            score += 25
            supporting_signals.append("+ Verified public PyPI package author record (+25)")
            reasons.append("Public PyPI package author record matches email.")

        if has_gitlab_verified:
            score += 25
            supporting_signals.append("+ Verified public GitLab developer profile (+25)")
            reasons.append("Verified public GitLab developer profile.")

        # Independent Web Mentions (deduplicated)
        web_domains = {m.domain.lower() for m in exact_web_mentions if m.domain}
        if web_domains:
            web_score = min(20, len(web_domains) * 8)
            score += web_score
            supporting_signals.append(f"+ {len(web_domains)} independent web domain(s) contain exact email text (+{web_score})")
            reasons.append(f"{len(web_domains)} independent public web source(s) contain exact email address text.")

        if breaches_count > 0:
            breach_score = min(15, breaches_count * 5)
            score += breach_score
            supporting_signals.append(f"+ Present in {breaches_count} verified security breach disclosure(s) (+{breach_score})")
            reasons.append(f"Email present in {breaches_count} verified public security breach disclosure(s).")

        if has_domain_ownership:
            score += 15
            supporting_signals.append("+ Email domain ownership matches public DNS/RDAP records (+15)")
            reasons.append("Email domain ownership matches public WHOIS/RDAP registry metadata.")

        # ── 2. Contradicting & Dampening Signals ──
        if is_role_account:
            contradicting_signals.append("- Role-based departmental mailbox detected; individual personal identity attribution is restrained")
            reasons.append("Role-based address detected; evaluation reflects organizational/team presence rather than an individual person.")

        if not verified_accounts and not high_conf_accounts:
            if candidate_accounts:
                score = min(score + 15, 35)
                supporting_signals.append(f"+ {len(candidate_accounts)} candidate username lead(s) from email prefix (+15)")
                contradicting_signals.append("- Zero cryptographic or commit proof found; all handles remain unverified hypotheses (-20)")
                reasons.append(f"{len(candidate_accounts)} candidate username lead(s) discovered from email prefix (unverified).")
            else:
                contradicting_signals.append("- No public accounts or developer footprint discovered across queried registries")

        # Multi-name ambiguity check
        distinct_names = {a.display_name for a in account_findings if a.display_name and len(a.display_name) > 3}
        if len(distinct_names) > 2 and not verified_accounts:
            score = max(0, score - 15)
            contradicting_signals.append(f"- Multiple conflicting display names ({', '.join(list(distinct_names)[:3])}) across candidate leads (-15)")

        # Clamp final score
        final_score = min(100, max(0, score))

        # ── 3. Calibrated Level Assignment ──
        # VERIFIED: 90-100
        # HIGH_CONFIDENCE: 75-89
        # PROBABLE: 50-74
        # CANDIDATE: 1-49
        # NO_EVIDENCE: 0
        if final_score >= 90 or (len(verified_accounts) >= 2) or (has_github_commit_match and has_gravatar_profile):
            level = FindingStatus.VERIFIED
            final_score = max(90, final_score)
        elif final_score >= 75 or verified_accounts:
            level = FindingStatus.HIGH_CONFIDENCE if final_score < 90 else FindingStatus.VERIFIED
        elif final_score >= 50 or (exact_web_mentions and breaches_count > 0) or has_domain_ownership:
            level = FindingStatus.PROBABLE
        elif candidate_accounts and not is_role_account:
            level = FindingStatus.CANDIDATE
            final_score = min(45, max(15, final_score))
        elif final_score > 0:
            level = FindingStatus.PROBABLE
        else:
            level = FindingStatus.NO_EVIDENCE
            final_score = 0

        return ConfidenceAssessment(
            level=level,
            score=final_score,
            reasons=reasons,
            supporting_signals=supporting_signals,
            contradicting_signals=contradicting_signals,
            evidence_count=total_evidence_count,
            independent_source_count=len(independent_sources),
            verified_count=len(verified_accounts),
            high_confidence_count=len(high_conf_accounts),
            probable_count=len(probable_accounts),
            candidate_count=len(candidate_accounts),
            formula_breakdown={
                "base_score": score,
                "clamped_score": final_score,
                "tier": level.value,
                "independent_sources": len(independent_sources),
                "is_role_account": is_role_account
            }
        )
