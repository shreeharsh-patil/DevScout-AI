"""
Identity Resolver Agent.

Correlates and synthesizes cross-platform public signals (names, bios, avatars, websites, orgs)
while strictly isolating candidate guesses, role-based accounts, and annotating identity ambiguity.
"""

from __future__ import annotations

from typing import List, Optional
from .models import (
    AccountFinding,
    DeveloperFootprint,
    EmailTarget,
    FindingStatus,
    IdentityFinding,
    UsernameCandidate,
    utc_now_iso,
)


class IdentityResolverAgent:
    """Correlates multiple public signals into unified identity metadata."""

    @staticmethod
    def resolve(
        local_part: str,
        domain: str,
        account_findings: List[AccountFinding],
        footprint: DeveloperFootprint,
        username_candidates: List[UsernameCandidate],
        target: Optional[EmailTarget] = None
    ) -> IdentityFinding:
        possible_names: List[str] = []
        possible_usernames: List[str] = []
        developer_profiles: List[dict] = []
        websites: List[str] = []
        organizations: List[str] = []
        locations: List[str] = []
        public_bios: List[str] = []
        avatars: List[str] = []
        evidence_ids: List[str] = []

        is_role = target.is_role_account if target else False
        role_type = target.role_type if target else None

        if target and target.organization_name and target.organization_name not in organizations:
            organizations.append(target.organization_name)
        if target and target.website_url and target.website_url not in websites:
            websites.append(target.website_url)

        verified_findings = [a for a in account_findings if a.status == FindingStatus.VERIFIED]
        target_findings = verified_findings if verified_findings else account_findings

        for finding in target_findings:
            evidence_ids.extend(finding.evidence_ids)

            if finding.display_name and finding.display_name not in possible_names:
                possible_names.append(finding.display_name)

            if finding.account_identifier and finding.account_identifier not in possible_usernames:
                possible_usernames.append(finding.account_identifier)

            if finding.profile_url:
                developer_profiles.append({
                    "platform": finding.platform,
                    "url": finding.profile_url,
                    "status": finding.status.value
                })

            if finding.avatar_url and finding.avatar_url not in avatars:
                avatars.append(finding.avatar_url)

            if finding.bio and finding.bio not in public_bios:
                public_bios.append(finding.bio)

            meta = finding.metadata
            blog = meta.get("blog")
            if blog and blog not in websites:
                websites.append(blog)

            company = meta.get("company")
            if company and company not in organizations:
                organizations.append(company.lstrip("@").strip())

            loc = meta.get("location")
            if loc and loc not in locations:
                locations.append(loc)

        for cand in username_candidates:
            if cand.username not in possible_usernames:
                possible_usernames.append(cand.username)

        # Do NOT synthesize personal name if this is a role-based mailbox
        resolved_name = possible_names[0] if possible_names else None
        if not resolved_name and not is_role and "." in local_part:
            parts = local_part.split(".")
            if len(parts) == 2 and all(p.isalpha() for p in parts):
                resolved_name = f"{parts[0].capitalize()} {parts[1].capitalize()}"

        ambiguity_note = None
        if is_role:
            ambiguity_note = (
                f"Target email is a role-based / department mailbox ({role_type or 'generic role'}), "
                "not an individual personal identity. Associated signals reflect corporate / team presence."
            )
        elif len(possible_names) > 2:
            ambiguity_note = (
                f"Multiple distinct names ({', '.join(possible_names[:3])}) were returned across candidate accounts. "
                "Treat identity correlation with caution."
            )

        status = FindingStatus.VERIFIED if verified_findings else FindingStatus.PROBABLE if (possible_names or organizations) else FindingStatus.CANDIDATE
        score = 1.0 if verified_findings else 0.60 if (possible_names or organizations) else 0.25

        return IdentityFinding(
            provider="identity_resolver",
            finding_type="identity",
            status=status,
            confidence_level=status,
            confidence_score=score,
            evidence_ids=list(dict.fromkeys(evidence_ids)),
            retrieved_at=utc_now_iso(),
            possible_name=resolved_name,
            possible_usernames=possible_usernames[:8],
            developer_profiles=developer_profiles,
            websites=websites,
            organizations=organizations,
            locations=locations,
            public_bios=public_bios[:3],
            avatars=avatars[:4],
            ambiguity_note=ambiguity_note,
            metadata={"is_role_account": is_role, "role_type": role_type}
        )
