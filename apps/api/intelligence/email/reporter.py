"""
Email Intelligence Reporter (Phases 7 & 8).

Generates comprehensive, evidence-backed Markdown intelligence reports
with verified identities, developer ecosystem signals, Identity Clusters & Disambiguation,
GitHub Evidence Graphs, categorized public web mentions, security disclosures, and normalized sources.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from .models import (
    AccountFinding,
    BreachFinding,
    ConfidenceAssessment,
    ConfidenceLevel,
    DeveloperFootprint,
    EmailTarget,
    IdentityCluster,
    IdentitySignals,
    UsernameCandidate,
    WebMentionFinding,
)


class EmailIntelligenceReporter:
    """Renders structured Markdown reports for email intelligence investigations."""

    @staticmethod
    def generate_report(
        email: str,
        validation: EmailTarget,
        confidence: ConfidenceAssessment,
        accounts: List[AccountFinding],
        footprint: DeveloperFootprint,
        web_mentions: List[WebMentionFinding],
        breaches: List[BreachFinding],
        breach_status: str,
        username_candidates: List[UsernameCandidate],
        identity_signals: Optional[IdentitySignals] = None,
        sources: List[Dict[str, Any]] = None,
        identity_clusters: Optional[List[IdentityCluster]] = None
    ) -> str:

        lines: List[str] = []

        # ── Title & Overview Header ──
        lines.append(f"# \U0001f50d Email Intelligence Report: `{email}`\n")
        lines.append(f"> **Target Address**: `{email}`  ")
        lines.append(f"> **Domain Classification**: `{validation.domain_classification.value.upper()}` (`{validation.domain}`)  ")
        lines.append(f"> **Overall Footprint Score**: **{confidence.score} / 100** ({confidence.level.value.replace('_', ' ')})  ")
        lines.append(f"> **Role / Generic Account**: `{'YES (' + (validation.role_type or 'Role Mailbox') + ')' if validation.is_role_account else 'NO (Personal / Developer)'}`  ")
        lines.append(f"> **MX Routing**: `{validation.mx_status.upper()}` ({validation.mx_host or 'No primary host'})  ")
        lines.append(f"> **Disposable Domain**: `{'YES (Temporary)' if validation.is_disposable else 'NO'}`\n")

        if validation.is_role_account:
            lines.append(
                f"> [!WARNING]\n"
                f"> **Role-Based Mailbox Detected**: `{email}` is identified as a departmental / functional mailbox "
                f"(`{validation.role_type}`). Findings represent organization / team footprint rather than an individual person.\n"
            )

        if validation.organization_name:
            lines.append(f"> **Associated Organization / Site**: **{validation.organization_name}** ({validation.website_url or validation.domain})  \n")

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

        # ── 2. Identity Clusters & Disambiguation ──
        if identity_clusters:
            lines.append("## \U0001f9e9 Identity Clusters & Correlation")
            for cluster in identity_clusters:
                status_icon = "\u2705" if cluster.status == ConfidenceLevel.VERIFIED else "\u26aa"
                lines.append(f"### {status_icon} {cluster.cluster_name}")
                if cluster.shared_signals:
                    lines.append(f"- **Evidence Links**: {', '.join(cluster.shared_signals)}")
                if cluster.ambiguity_warning:
                    lines.append(f"  > \u26a0\ufe0f *{cluster.ambiguity_warning}*")
                for acc in cluster.accounts:
                    p_link = f"[{acc.account_identifier}]({acc.profile_url})" if acc.profile_url else acc.account_identifier
                    lines.append(f"  - `{acc.platform.upper()}`: {p_link} ({acc.status.value})")
                lines.append("")

        # ── 3. Developer Ecosystem & Registries Matrix ──
        lines.append("## \U0001f310 Public Developer Ecosystem & Registries")
        lines.append("| Platform | Category | Status | Identifier | Email Match | Method / Evidence |")
        lines.append("| :--- | :--- | :--- | :--- | :---: | :--- |")

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
            email_match_indicator = "\u2705 Yes" if acc.public_email_match else "\u274c No"
            method_desc = acc.method.replace("_", " ")

            lines.append(
                f"| **{acc.platform.upper()}** | `{acc.ecosystem_category}` | `{status_badge}` | {profile_text} | {email_match_indicator} | {method_desc} |"
            )

        if not accounts:
            lines.append("| *None* | `general` | `NO EVIDENCE` | — | \u274c No | Searched supported registries |")
        lines.append("")

        # ── 4. Developer Footprint & GitHub Intelligence ──
        lines.append("## \U0001f4bb Developer Technical Footprint")
        if footprint.has_footprint:
            if footprint.github_handle:
                stars_pill = f" (\u2b50 {footprint.total_stars} stars)" if footprint.total_stars > 0 else ""
                lines.append(f"- **GitHub Developer**: [`{footprint.github_handle}`](https://github.com/{footprint.github_handle}){stars_pill}")
            if footprint.npm_maintainer:
                lines.append(f"- **npm Package Maintainer**: [`{footprint.npm_maintainer}`](https://www.npmjs.com/~{footprint.npm_maintainer})")
            if footprint.location:
                lines.append(f"- **Location**: {footprint.location}")
            if footprint.top_languages:
                lines.append(f"- **Primary Languages**: {', '.join(f'`{lang}`' for lang in footprint.top_languages)}")
            if footprint.organizations:
                lines.append(f"- **Organizations**: {', '.join(footprint.organizations)}")

            # GitHub Commits Table
            if footprint.github_commits:
                lines.append("\n### Associated Public Commits")
                lines.append("| Commit SHA | Repository | Date | Message |")
                lines.append("| :--- | :--- | :--- | :--- |")
                for c in footprint.github_commits[:5]:
                    msg = (c.commit_message or "Commit")[:50]
                    c_date = c.commit_date[:10] if c.commit_date else "Recent"
                    lines.append(f"| [`{c.sha}`]({c.commit_url}) | [{c.repo_name}]({c.repo_url}) | `{c_date}` | {msg} |")

            # Public Repositories Table
            if footprint.repositories:
                lines.append("\n### Notable Public Repositories")
                lines.append("| Repository | Language | Stars | Forks | Description |")
                lines.append("| :--- | :--- | :--- | :--- | :--- |")
                for r in footprint.repositories[:6]:
                    desc = (r.description or "No description")[:55]
                    lines.append(f"| [{r.name}]({r.url}) | `{r.language or 'N/A'}` | ⭐ {r.stars} | 🍴 {r.forks} | {desc} |")

            # Authored npm Packages
            if footprint.npm_packages:
                lines.append("\n### Authored npm Packages")
                for pkg in footprint.npm_packages[:5]:
                    lines.append(f"- [`{pkg.get('name')}`](https://www.npmjs.com/package/{pkg.get('name')}) (v{pkg.get('version', 'latest')}) - {pkg.get('description', '')[:70]}")

            # Evidence Graph Summary
            if footprint.evidence_graph and footprint.evidence_graph.edges:
                lines.append("\n### 🕸️ GitHub Identity Evidence Graph")
                lines.append(f"> **Graph Summary**: {footprint.evidence_graph.summary}")
                lines.append("| Relationship | Source Node | Target Node | Strength |")
                lines.append("| :--- | :--- | :--- | :--- |")
                for edge in footprint.evidence_graph.edges[:6]:
                    lines.append(f"| `{edge.relationship}` | `{edge.source}` | `{edge.target}` | **{edge.strength.upper()}** |")
        else:
            lines.append("*No public developer repositories, packages, or commits found associated with this email.*")
        lines.append("")

        # ── 5. Public Web Footprint Search ──
        lines.append("## 🌐 Public Web Footprint Search")
        exact_mentions = [m for m in web_mentions if m.is_exact_match or m.correlation_type.value == "exact_email_mention"]
        profile_mentions = [m for m in web_mentions if m.mention_category.value == "developer_profile_mention" and not m.is_exact_match]
        forum_mentions = [m for m in web_mentions if m.mention_category.value == "forum_mention" and not m.is_exact_match]
        doc_mentions = [m for m in web_mentions if m.mention_category.value == "document_mention" and not m.is_exact_match]
        other_mentions = [m for m in web_mentions if m not in exact_mentions and m not in profile_mentions and m not in forum_mentions and m not in doc_mentions]

        if exact_mentions:
            lines.append("### 🔥 Exact Email Occurrences")
            for m in exact_mentions[:5]:
                lines.append(f"- [{m.title}]({m.canonical_url or m.url}) (`{m.domain}`)\n  > \"{m.snippet}\"")

        if profile_mentions:
            lines.append("\n### 👨‍💻 Public Developer Profiles & Portfolios")
            for m in profile_mentions[:4]:
                lines.append(f"- [{m.title}]({m.canonical_url or m.url}) (`{m.domain}`)\n  > \"{m.snippet}\"")

        if forum_mentions:
            lines.append("\n### 💬 Technical Community & Forum Citations")
            for m in forum_mentions[:3]:
                lines.append(f"- [{m.title}]({m.canonical_url or m.url}) (`{m.domain}`)\n  > \"{m.snippet}\"")

        if doc_mentions:
            lines.append("\n### 📄 Documentation & Specification References")
            for m in doc_mentions[:3]:
                lines.append(f"- [{m.title}]({m.canonical_url or m.url}) (`{m.domain}`)\n  > \"{m.snippet}\"")

        if not (exact_mentions or profile_mentions or forum_mentions or doc_mentions or other_mentions):
            lines.append("*No public web occurrences or citations discovered.*")
        lines.append("")

        # ── 6. Breach Exposure Audit ──
        lines.append("## 🔒 Security & Breach Exposure Audit")
        if breach_status == "unavailable":
            lines.append("> [!NOTE]\n> HaveIBeenPwned API key is unconfigured. Breach exposure auditing was skipped (`UNAVAILABLE`).")
        elif breaches:
            verified_count = sum(1 for b in breaches if b.is_verified and not b.is_spam_list and not b.is_retired)
            unverified_count = sum(1 for b in breaches if not b.is_verified)
            spam_count = sum(1 for b in breaches if b.is_spam_list)
            retired_count = sum(1 for b in breaches if b.is_retired)

            lines.append(
                f"- **Verified disclosures**: {verified_count}  \n"
                f"- **Unverified disclosures**: {unverified_count}  \n"
                f"- **Spam lists**: {spam_count}  \n"
                f"- **Retired records**: {retired_count}\n"
            )
            lines.append("| Breach Name | Domain | Verification Status | Severity | Date | Exposed Data Classes |")
            lines.append("| :--- | :--- | :--- | :---: | :--- | :--- |")
            for b in breaches:
                status_label = "Verified" if b.is_verified and not b.is_spam_list and not b.is_retired else "Unverified Incident"
                if b.is_spam_list:
                    status_label = "Spam List"
                elif b.is_retired:
                    status_label = "Retired"
                severity_badge = f"**{b.severity}**"
                data_cls = ", ".join(f"`{c}`" for c in b.data_classes[:4])
                lines.append(f"| **{b.breach_name}** | `{b.domain}` | `{status_label}` | {severity_badge} | {b.breach_date or 'Unknown'} | {data_cls} |")
            lines.append("\n> [!NOTE]\n> **What Breach Exposure Means**: A breach disclosure indicates this email appeared in a third-party service's historical public incident. It does not indicate account compromise on your personal systems.")
            lines.append("\n> [!CAUTION]\n> *Strict Privacy Policy: Zero passwords, plaintexts, or credentials are ever queried, retrieved, stored, or displayed.*")
        else:
            lines.append("✅ *No public breach exposures discovered in audited security disclosures.*")
        lines.append("")


        # ── 7. Candidate Handles (Inferred) ──
        lines.append("## \U0001f3f7\ufe0f Candidate Usernames (Inferred / Unverified)")
        if username_candidates:
            lines.append("> [!IMPORTANT]\n> The following handles are syntactically derived hypotheses. They must **never** be treated as confirmed identities without independent cryptographic or commit evidence.")
            candidate_pills = " ".join(f"`{c.username}`" for c in username_candidates[:8])
            lines.append(f"\n**Candidate Permutations**: {candidate_pills}\n")
        else:
            lines.append("*No candidate handles generated.*")
        lines.append("")

        # ── 8. Normalized Sources Section ──
        lines.append("## \U0001f4da Sources & Verification Citations")
        if sources:
            lines.append("| ID | Platform | Title & URL | Verification Type |")
            lines.append("| :--- | :--- | :--- | :--- |")
            for src in sources:
                src_id = src.get("source_id", "")
                title = src.get("title", "")
                url = src.get("url", "")
                platform = src.get("platform", "")
                stype = src.get("source_type", "")
                lines.append(f"| `[{src_id}]` | **{platform.upper()}** | [{title}]({url}) | `{stype}` |")
        else:
            lines.append("*No external citations retrieved.*")

        return "\n".join(lines)
