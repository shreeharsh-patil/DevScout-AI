"""
Email Intelligence Reporter.

Generates comprehensive, evidence-backed Markdown intelligence reports
with verified identity signals, developer footprint, and normalized source citations.
"""

from __future__ import annotations

from typing import Any, Dict, List
from .models import (
    AccountFinding,
    BreachFinding,
    ConfidenceAssessment,
    ConfidenceLevel,
    DeveloperFootprint,
    EmailValidationResult,
    IdentitySignals,
    UsernameCandidate,
    WebMentionFinding,
)


class EmailIntelligenceReporter:
    """Renders structured Markdown reports for email intelligence investigations."""

    @staticmethod
    def generate_report(
        email: str,
        validation: EmailValidationResult,
        confidence: ConfidenceAssessment,
        accounts: List[AccountFinding],
        footprint: DeveloperFootprint,
        web_mentions: List[WebMentionFinding],
        breaches: List[BreachFinding],
        breach_status: str,
        username_candidates: List[UsernameCandidate],
        identity_signals: IdentitySignals,
        sources: List[Dict[str, Any]]
    ) -> str:
        lines: List[str] = []

        # ── Title & Overview Header ──
        lines.append(f"# \U0001f50d Email Intelligence Report: `{email}`\n")
        lines.append(f"> **Target Address**: `{email}`  ")
        lines.append(f"> **Domain Type**: `{validation.provider_type.value.upper()}` (`{validation.domain}`)  ")
        lines.append(f"> **Overall Footprint Score**: **{confidence.score} / 100** ({confidence.level.value.replace('_', ' ')})  ")
        lines.append(f"> **Disposable Domain**: `{'YES (Temporary)' if validation.disposable else 'NO'}`\n")

        # ── 1. Verified Identities Summary ──
        verified_accs = [a for a in accounts if a.status == ConfidenceLevel.VERIFIED]
        lines.append("## \u2705 Verified Identities")
        if verified_accs:
            for acc in verified_accs:
                profile_link = f"[{acc.display_name or acc.account_identifier}]({acc.profile_url})" if acc.profile_url else f"`{acc.account_identifier}`"
                lines.append(f"- **{acc.platform.upper()}**: {profile_link} (Method: `{acc.method}`)")
                if acc.bio:
                    lines.append(f"  > *\"{acc.bio}\"*")
        else:
            lines.append("*No public profiles directly confirmed via exact cryptographic hash or verified commit email.*")
        lines.append("")

        # ── 2. Account Signals Matrix ──
        lines.append("## \U0001f310 Public Account Signals")
        lines.append("| Platform | Status | Confidence | Identifier | Method / Evidence |")
        lines.append("| :--- | :--- | :--- | :--- | :--- |")

        for acc in accounts:
            status_badge = {
                ConfidenceLevel.VERIFIED: "\u2705 VERIFIED",
                ConfidenceLevel.HIGH_CONFIDENCE: "\U0001f535 HIGH CONFIDENCE",
                ConfidenceLevel.PROBABLE: "\U0001f7e1 PROBABLE",
                ConfidenceLevel.CANDIDATE: "\u26aa CANDIDATE",
                ConfidenceLevel.NO_EVIDENCE: "\u274c NO EVIDENCE",
                ConfidenceLevel.UNAVAILABLE: "\u26a0\ufe0f UNAVAILABLE",
            }.get(acc.status, acc.status.value)

            profile_text = f"[{acc.account_identifier}]({acc.profile_url})" if acc.profile_url and acc.account_identifier else (acc.account_identifier or "—")
            method_desc = acc.method.replace("_", " ")

            lines.append(
                f"| **{acc.platform.capitalize()}** | `{status_badge}` | {int(acc.confidence * 100)}% | {profile_text} | {method_desc} |"
            )

        if not accounts:
            lines.append("| *None* | `NO EVIDENCE` | 0% | — | Searched supported registries |")
        lines.append("")

        # ── 3. Developer Footprint ──
        lines.append("## \U0001f4bb Developer Technical Footprint")
        if footprint.has_footprint:
            if footprint.github_handle:
                lines.append(f"- **GitHub Profile**: [{footprint.github_handle}](https://github.com/{footprint.github_handle})")
            if footprint.gitlab_handle:
                lines.append(f"- **GitLab Profile**: [{footprint.gitlab_handle}](https://gitlab.com/{footprint.gitlab_handle})")
            if footprint.npm_maintainer:
                lines.append(f"- **npm Maintainer**: [{footprint.npm_maintainer}](https://www.npmjs.com/~{footprint.npm_maintainer})")
            if footprint.top_languages:
                lines.append(f"- **Primary Languages**: {', '.join(f'`{language}`' for language in footprint.top_languages)}")
            if footprint.organizations:
                lines.append(f"- **Public Organizations / Affiliations**: {', '.join(footprint.organizations)}")

            # Repositories table
            if footprint.repositories:
                lines.append("\n### Public Repositories")
                lines.append("| Repository | Language | Stars | Last Update |")
                lines.append("| :--- | :--- | :--- | :--- |")
                for r in footprint.repositories[:6]:
                    repo_link = f"[{r.name}]({r.url})"
                    lang = f"`{r.language}`" if r.language else "—"
                    updated = r.updated_at[:10] if r.updated_at else "—"
                    lines.append(f"| {repo_link} | {lang} | \u2b50 {r.stars} | {updated} |")

            # npm packages
            if footprint.npm_packages:
                lines.append("\n### npm Packages")
                for pkg in footprint.npm_packages[:5]:
                    lines.append(f"- **`{pkg.get('name')}`** (v{pkg.get('version', 'latest')}): {pkg.get('description', 'No description')}")
        else:
            lines.append("*No public developer repositories, packages, or commits found associated with this email target.*")
        lines.append("")

        # ── 4. Public Web Footprint ──
        lines.append("## \U0001f30e Public Web Footprint")
        exact_mentions = [m for m in web_mentions if m.correlation_type.value == "exact_email_mention"]
        other_mentions = [m for m in web_mentions if m.correlation_type.value != "exact_email_mention"]

        if web_mentions:
            lines.append(f"Discovered **{len(exact_mentions)} exact mention(s)** and **{len(other_mentions)} correlated web reference(s)**:\n")
            for m in web_mentions[:6]:
                corr_label = "Exact Match" if m.correlation_type.value == "exact_email_mention" else "Correlation"
                lines.append(f"- [{m.title}]({m.url}) (`{m.domain}`) — *{corr_label}*")
                if m.snippet:
                    clean_snippet = m.snippet.replace("\n", " ")[:160]
                    lines.append(f"  > \"{clean_snippet}...\"")
        else:
            lines.append("*No public web search mentions retrieved.*")
        lines.append("")

        # ── 5. Breach Exposure Notice ──
        lines.append("## \U0001f6e1\ufe0f Breach Exposure Audit")
        if breach_status == "unavailable":
            lines.append("> \u2139\ufe0f *Breach lookup provider unconfigured (`HIBP_API_KEY` not set). Module is marked `UNAVAILABLE`.*")
        elif breaches:
            lines.append(f"> \u26a0\ufe0f **Found in {len(breaches)} public security breach event(s)**.")
            lines.append("> *Strict Security Policy: Zero credentials, passwords, or hashes are ever queried or stored.*\n")
            lines.append("| Breach Event | Domain | Date | Exposed Data Classes |")
            lines.append("| :--- | :--- | :--- | :--- |")
            for b in breaches:
                classes = ", ".join(b.data_classes[:4]) if b.data_classes else "Account Data"
                date_str = b.breach_date or "Unknown"
                lines.append(f"| **{b.breach_name}** | `{b.domain}` | {date_str} | {classes} |")
        else:
            lines.append("> \u2705 *No known public breach disclosures found for this email address.*")
        lines.append("")

        # ── 6. Candidate Usernames ──
        lines.append("## \U0001f464 Possible Candidate Usernames")
        lines.append("> *Notice: The following handles are candidate hypotheses derived from email local-part syntax. They are strictly unverified unless independent public evidence connects them.*")
        if username_candidates:
            lines.append("")
            for cand in username_candidates:
                lines.append(f"- `{cand.username}` (`{cand.generation_rule.replace('_', ' ')}`) — `CANDIDATE`")
        lines.append("")

        # ── 7. Identity Signals ──
        lines.append("## \U0001f9ec Identity Signals Synthesis")
        lines.append(f"- **Possible Name**: `{identity_signals.possible_name or 'Not identified'}`")
        if identity_signals.websites:
            lines.append(f"- **Associated Websites**: {', '.join(f'[{w}]({w})' for w in identity_signals.websites)}")
        if identity_signals.organizations:
            lines.append(f"- **Associated Organizations**: {', '.join(identity_signals.organizations)}")
        if identity_signals.locations:
            lines.append(f"- **Locations**: {', '.join(identity_signals.locations)}")
        if identity_signals.ambiguity_note:
            lines.append(f"\n> \u26a0\ufe0f **Identity Ambiguity**: {identity_signals.ambiguity_note}")
        lines.append("")

        # ── 8. Confidence Assessment ──
        lines.append("## \U0001f4ca Confidence Assessment")
        lines.append(f"- **Tier**: `{confidence.level.value}`")
        lines.append(f"- **Deterministic Score**: **{confidence.score}/100**")
        lines.append(f"- **Breakdown**: `{confidence.verified_count} Verified` • `{confidence.high_confidence_count} High Confidence` • `{confidence.probable_count} Probable` • `{confidence.candidate_count} Candidate(s)`\n")
        lines.append("### Evaluation Rationale:")
        for r in confidence.reasons:
            lines.append(f"- \u2714 {r}")
        lines.append("")

        # ── 9. Normalized Sources & Citations ──
        lines.append("## \U0001f4da Sources & Verification")
        if sources:
            lines.append("| [ID] | Source Title | Platform | URL |")
            lines.append("| :--- | :--- | :--- | :--- |")
            for s in sources:
                src_id = s.get("source_id", "—")
                title = s.get("title", "Reference")
                platform = s.get("platform", "web").capitalize()
                url = s.get("url", "#")
                lines.append(f"| `[{src_id}]` | [{title}]({url}) | {platform} | `{url[:60]}...` |")
        else:
            lines.append("*No external citations recorded.*")
        lines.append("")

        return "\n".join(lines)
