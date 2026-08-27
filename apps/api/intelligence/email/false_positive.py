"""
Dedicated False-Positive Prevention & Source Quality Layer (Phases 16 & 17).

Prevents inaccurate identity associations:
1. Detects high-frequency common usernames & generic email local parts
2. Computes contradiction penalties (different website -25, different org -20, different display name -10)
3. Enforces Source Quality hierarchy (FIRST_PARTY > DIRECT_PUBLIC_EVIDENCE > SECONDARY > WEAK > UNVERIFIED)
4. Guarantees that search snippets never outweigh verified first-party registry records.
"""

from __future__ import annotations

from typing import List, Set, Tuple
from .models import (
    AccountFinding,
    Evidence,
    FindingStatus,
    SourceQuality,
)

COMMON_USERNAMES: Set[str] = {
    "admin", "administrator", "root", "dev", "developer", "test", "demo",
    "user", "guest", "info", "contact", "support", "sales", "security",
    "john", "alex", "mike", "david", "chris", "sam", "dan", "tom",
    "james", "paul", "mark", "jason", "ryan", "matt", "eric", "brian",
    "andrew", "kevin", "steve", "daniel", "robert", "michael", "william"
}


class FalsePositiveDetector:
    """Evaluates candidate account leads for false-positive indicators and contradictions."""

    @classmethod
    def evaluate_account(
        cls,
        account: AccountFinding,
        target_email: str,
        target_local: str,
        target_domain: str,
        verified_accounts: List[AccountFinding]
    ) -> Tuple[AccountFinding, List[str]]:
        """
        Applies contradiction checks and source quality weighting to an AccountFinding.
        Returns the adjusted account and any contradiction notes.
        """
        contradictions: List[str] = []
        is_verified = account.status == FindingStatus.VERIFIED or account.public_email_match

        # Direct verified accounts with cryptographic/commit proof bypass syntactic ambiguity
        if is_verified:
            return account, []

        identifier = (account.account_identifier or "").strip().lower()

        # ── 1. Common Username Heuristic ──
        if identifier in COMMON_USERNAMES or target_local.lower() in COMMON_USERNAMES:
            contradictions.append(
                f"Handle '@{identifier}' is a high-frequency common username; unverified handle match carries severe collision risk."
            )
            account.status = FindingStatus.CANDIDATE
            account.confidence_score = min(account.confidence_score, 0.20)

        # ── 2. Contradictions against Verified Baseline Accounts ──
        for v_acc in verified_accounts:
            # Different personal website / blog
            v_blog = (v_acc.metadata.get("blog") or v_acc.metadata.get("website_url") or "").strip().lower()
            cand_blog = (account.metadata.get("blog") or account.metadata.get("website_url") or "").strip().lower()
            if v_blog and cand_blog and v_blog != cand_blog and len(v_blog) > 5 and len(cand_blog) > 5:
                contradictions.append(
                    f"Contradicting website: Verified profile links '{v_blog}', but candidate '@{identifier}' links '{cand_blog}' (-25 score penalty)."
                )
                account.confidence_score = max(0.05, account.confidence_score - 0.25)
                account.status = FindingStatus.CANDIDATE

            # Different organization / company
            v_org = (v_acc.metadata.get("company") or "").strip().lower().lstrip("@")
            cand_org = (account.metadata.get("company") or "").strip().lower().lstrip("@")
            if v_org and cand_org and v_org != cand_org and len(v_org) >= 3 and len(cand_org) >= 3:
                contradictions.append(
                    f"Contradicting organization: Verified profile lists '{v_org}', but candidate lists '{cand_org}' (-20 score penalty)."
                )
                account.confidence_score = max(0.05, account.confidence_score - 0.20)
                account.status = FindingStatus.CANDIDATE

            # Different personal name
            v_name = (v_acc.display_name or "").strip().lower()
            cand_name = (account.display_name or "").strip().lower()
            if v_name and cand_name and v_name != cand_name and len(v_name) >= 4 and len(cand_name) >= 4:
                contradictions.append(
                    f"Contradicting display name: Verified profile displays '{v_acc.display_name}', but candidate displays '{account.display_name}' (-10 score penalty)."
                )
                account.confidence_score = max(0.05, account.confidence_score - 0.10)
                account.status = FindingStatus.CANDIDATE

        # ── 3. Source Quality Enforcement ──
        # Search snippet or weak unconfirmed candidate can never exceed 0.35 confidence
        for ev in account.evidence:
            if ev.source_quality in (SourceQuality.WEAK, SourceQuality.UNVERIFIED) and not is_verified:
                account.confidence_score = min(account.confidence_score, 0.35)

        return account, contradictions

    @classmethod
    def filter_and_calibrate(
        cls,
        accounts: List[AccountFinding],
        target_email: str,
        target_local: str,
        target_domain: str
    ) -> Tuple[List[AccountFinding], List[str]]:
        """Calibrates all accounts against contradictions and common username collisions."""
        verified_baseline = [a for a in accounts if a.status == FindingStatus.VERIFIED or a.public_email_match]
        all_contradictions: List[str] = []
        calibrated: List[AccountFinding] = []

        for acc in accounts:
            adjusted, contras = cls.evaluate_account(
                acc, target_email, target_local, target_domain, verified_baseline
            )
            all_contradictions.extend(contras)
            calibrated.append(adjusted)

        return calibrated, all_contradictions
