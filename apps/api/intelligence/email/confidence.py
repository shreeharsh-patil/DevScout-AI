"""
Deterministic Evidence-Based Confidence Engine.

Calculates confidence levels (VERIFIED, HIGH_CONFIDENCE, PROBABLE, CANDIDATE, NO_EVIDENCE)
strictly from concrete evidence items. Guessed usernames and weak string similarities
are NEVER treated as verified.
"""

from __future__ import annotations

from typing import List
from .models import AccountFinding, ConfidenceAssessment, ConfidenceLevel, WebMentionFinding


class ConfidenceEngine:
    """Evaluates evidence items and assigns deterministic confidence scores and tiers."""

    @staticmethod
    def evaluate(
        account_findings: List[AccountFinding],
        web_mentions: List[WebMentionFinding],
        breaches_count: int,
        has_domain_ownership: bool = False
    ) -> ConfidenceAssessment:
        reasons: List[str] = []
        score = 0

        verified_accounts = [a for a in account_findings if a.status == ConfidenceLevel.VERIFIED]
        high_conf_accounts = [a for a in account_findings if a.status == ConfidenceLevel.HIGH_CONFIDENCE]
        probable_accounts = [a for a in account_findings if a.status == ConfidenceLevel.PROBABLE]
        candidate_accounts = [a for a in account_findings if a.status == ConfidenceLevel.CANDIDATE]

        exact_web_mentions = [m for m in web_mentions if m.correlation_type.value == "exact_email_mention"]

        # ── 1. Deterministic Verified Signals ──
        has_github_commit_match = any(
            a.platform == "github" and any("commit" in e.source_type or "commit" in a.method for e in a.evidence)
            for a in verified_accounts
        )
        has_github_profile_email = any(
            a.platform == "github" and any("profile_email" in e.source_type or "profile_email" in a.method for e in a.evidence)
            for a in verified_accounts
        )
        has_gravatar_profile = any(
            a.platform == "gravatar" and a.status == ConfidenceLevel.VERIFIED
            for a in verified_accounts
        )
        has_npm_maintainer = any(
            a.platform == "npm" and a.status in (ConfidenceLevel.VERIFIED, ConfidenceLevel.HIGH_CONFIDENCE)
            for a in verified_accounts + high_conf_accounts
        )

        if has_github_commit_match:
            score += 45
            reasons.append("Exact email discovered in public GitHub commit author/committer history.")

        if has_github_profile_email:
            score += 35
            reasons.append("Exact email listed publicly on verified GitHub developer profile.")

        if has_gravatar_profile:
            score += 30
            reasons.append("Verified public Gravatar profile matched via cryptographic hash.")

        if has_npm_maintainer:
            score += 25
            reasons.append("Public npm package registry author/maintainer record matches email.")

        if exact_web_mentions:
            web_score = min(20, len(exact_web_mentions) * 8)
            score += web_score
            reasons.append(f"{len(exact_web_mentions)} public web source(s) contain exact email address text.")

        if breaches_count > 0:
            score += min(15, breaches_count * 5)
            reasons.append(f"Email present in {breaches_count} verified public security breach disclosure(s).")

        if has_domain_ownership:
            score += 15
            reasons.append("Email domain ownership matches public WHOIS/RDAP registry metadata.")

        # ── 2. Candidate Handles (DO NOT inflate verified score) ──
        if candidate_accounts and not verified_accounts and not high_conf_accounts:
            score = min(score + 10, 25)
            reasons.append(f"{len(candidate_accounts)} candidate username lead(s) discovered from email prefix (unverified).")

        # Clamp score between 0 and 100
        final_score = min(100, max(0, score))

        # ── 3. Deterministic Level Assignment ──
        if verified_accounts or (has_github_commit_match or has_github_profile_email or has_gravatar_profile):
            if len(verified_accounts) >= 2 or (has_github_commit_match and has_gravatar_profile):
                level = ConfidenceLevel.VERIFIED
            elif final_score >= 70:
                level = ConfidenceLevel.VERIFIED
            else:
                level = ConfidenceLevel.HIGH_CONFIDENCE
        elif high_conf_accounts or (exact_web_mentions and breaches_count > 0):
            level = ConfidenceLevel.HIGH_CONFIDENCE
        elif probable_accounts or (exact_web_mentions or has_domain_ownership):
            level = ConfidenceLevel.PROBABLE
        elif candidate_accounts:
            level = ConfidenceLevel.CANDIDATE
        else:
            level = ConfidenceLevel.NO_EVIDENCE
            if not reasons:
                reasons.append("No public accounts, commits, or web mentions found for target email.")

        return ConfidenceAssessment(
            level=level,
            score=final_score,
            reasons=reasons,
            verified_count=len(verified_accounts),
            high_confidence_count=len(high_conf_accounts),
            probable_count=len(probable_accounts),
            candidate_count=len(candidate_accounts),
            formula_breakdown={
                "github_commits": has_github_commit_match,
                "github_profile": has_github_profile_email,
                "gravatar": has_gravatar_profile,
                "npm": has_npm_maintainer,
                "exact_web_mentions_count": len(exact_web_mentions),
                "breaches_count": breaches_count,
                "domain_ownership": has_domain_ownership,
            }
        )
