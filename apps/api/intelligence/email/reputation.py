"""
Email Reputation and Exposure Risk Signals Engine (Phase 11).

Performs non-invasive, objective technical reputation and footprint exposure analysis.
Strictly uses neutral terminology and categories (NORMAL, LIMITED_PUBLIC_FOOTPRINT,
ELEVATED_EXPOSURE, HIGH_PUBLIC_EXPOSURE, UNCERTAIN) without moral, legal, or criminal judgments.
"""

from __future__ import annotations

import re
from typing import List
from .models import (
    AccountFinding,
    BreachFinding,
    DeveloperFootprint,
    EmailReputationAssessment,
    EmailTarget,
    FindingStatus,
    ReputationCategory,
    ReputationSignal,
    WebMention,
)


class EmailReputationEngine:
    """Evaluates objective technical email and domain exposure attributes."""

    @classmethod
    def evaluate(
        cls,
        target: EmailTarget,
        accounts: List[AccountFinding],
        footprint: DeveloperFootprint,
        web_mentions: List[WebMention],
        breaches: List[BreachFinding]
    ) -> EmailReputationAssessment:
        signals: List[ReputationSignal] = []
        impersonation_risk = "low"

        # 1. Disposable Email Service Check
        if target.is_disposable:
            signals.append(
                ReputationSignal(
                    signal_name="disposable_provider",
                    severity="elevated",
                    description="Email domain belongs to a recognized temporary or disposable mailbox service."
                )
            )

        # 2. Role-Based Mailbox Check
        if target.is_role_account:
            signals.append(
                ReputationSignal(
                    signal_name="role_based_address",
                    severity="info",
                    description=f"Departmental or functional address detected ('{target.role_type or 'generic'}'). Used for organizational routing rather than individual personal identity."
                )
            )

        # 3. Domain MX Routing Health
        if target.mx_status == "missing_mx" or (target.is_valid and not target.has_mx_records and target.mx_status != "unchecked"):
            signals.append(
                ReputationSignal(
                    signal_name="unreachable_mail_routing",
                    severity="medium",
                    description="No active MX records were resolved for this domain during lookup; inbound email delivery may be inactive."
                )
            )
        elif target.mx_status == "uncertain":
            signals.append(
                ReputationSignal(
                    signal_name="dns_lookup_uncertainty",
                    severity="info",
                    description="Domain DNS resolution timed out or encountered intermittent upstream latency; MX status is uncertain."
                )
            )

        # 4. Domain Syntax Heuristics (Punycode, excessive digits/hyphens)
        domain = target.domain.lower() if target.domain else ""
        if domain.startswith("xn--"):
            signals.append(
                ReputationSignal(
                    signal_name="internationalized_punycode_domain",
                    severity="info",
                    description="Domain uses Internationalized Domain Name (IDN) Punycode encoding."
                )
            )
        if domain.count("-") >= 3 or (len(re.findall(r"\d", domain)) >= 5):
            signals.append(
                ReputationSignal(
                    signal_name="high_entropy_domain_syntax",
                    severity="low",
                    description="Domain contains multiple hyphens or numeric sequences uncommon in standard corporate domains."
                )
            )

        # 5. Public Breach Exposure Signals
        if breaches:
            high_sev_breaches = [b for b in breaches if b.severity in ("HIGH", "CRITICAL")]
            if high_sev_breaches:
                signals.append(
                    ReputationSignal(
                        signal_name="elevated_breach_exposure",
                        severity="elevated",
                        description=f"Email appears in {len(high_sev_breaches)} public disclosure(s) involving sensitive metadata categories."
                    )
                )
            else:
                signals.append(
                    ReputationSignal(
                        signal_name="standard_breach_exposure",
                        severity="low",
                        description=f"Email identified in {len(breaches)} historical third-party breach metadata disclosure(s)."
                    )
                )

        # 6. Public Footprint Volume
        verified_accs = [a for a in accounts if a.status == FindingStatus.VERIFIED]
        has_large_footprint = (
            len(verified_accs) >= 2
            or (footprint.total_stars >= 50)
            or (len(footprint.repositories) >= 5)
            or (len(footprint.npm_packages) >= 2)
            or (len(web_mentions) >= 4)
        )

        if has_large_footprint:
            signals.append(
                ReputationSignal(
                    signal_name="extensive_public_developer_footprint",
                    severity="info",
                    description="High volume of verified public developer repositories, packages, or citations discovered across registries."
                )
            )

        # 7. Impersonation & Candidate Ambiguity Risk
        distinct_names = {a.display_name for a in accounts if a.display_name and len(a.display_name) > 3}
        if len(distinct_names) >= 3 and not verified_accs:
            impersonation_risk = "elevated"
            signals.append(
                ReputationSignal(
                    signal_name="conflicting_identity_leads",
                    severity="medium",
                    description="Multiple disparate display names match candidate handle permutations across platforms without cryptographic linkage."
                )
            )
        elif len(distinct_names) == 2 and not verified_accs:
            impersonation_risk = "medium"

        # ── Categorization ──
        if target.is_disposable:
            category = ReputationCategory.ELEVATED_EXPOSURE
        elif target.mx_status == "missing_mx":
            category = ReputationCategory.ELEVATED_EXPOSURE
        elif any(s.signal_name == "elevated_breach_exposure" for s in signals):
            category = ReputationCategory.ELEVATED_EXPOSURE
        elif has_large_footprint:
            category = ReputationCategory.HIGH_PUBLIC_EXPOSURE
        elif target.mx_status == "uncertain":
            category = ReputationCategory.UNCERTAIN
        elif not accounts and not web_mentions and not breaches:
            category = ReputationCategory.LIMITED_PUBLIC_FOOTPRINT
        else:
            category = ReputationCategory.NORMAL


        summary = (
            f"Reputation profile classified as '{category.value.replace('_', ' ').title()}' "
            f"based on {len(signals)} technical signal(s)."
        )

        return EmailReputationAssessment(
            category=category,
            signals=signals,
            impersonation_risk=impersonation_risk,
            summary=summary
        )
