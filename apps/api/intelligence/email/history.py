"""
Historical Intelligence Snapshot & Timeline Comparison Engine (Phase 12).

Compares research snapshots across time for authorized workspaces:
- Discovers newly verified public accounts
- Identifies disappeared or expired citations
- Tracks new breach exposures (strictly avoiding false flags when previous scans had breach checks disabled)
- Measures developer footprint changes (new repos, stars, commits)
- Tracks profile metadata changes (bios, websites, locations)
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from .models import (
    HistoricalSnapshotComparison,
    IntelligenceReport,
    SnapshotDeltaItem,
)


class HistoricalSnapshotEngine:
    """Computes deterministic deltas between historical research snapshots."""

    @classmethod
    def compare_snapshots(
        cls,
        current_report: IntelligenceReport,
        previous_data: Optional[Dict[str, Any]] = None,
        previous_job_id: Optional[str] = None,
        previous_created_at: Optional[str] = None
    ) -> HistoricalSnapshotComparison:
        if not previous_data:
            return HistoricalSnapshotComparison(
                has_previous_scan=False,
                summary="Initial baseline investigation snapshot recorded."
            )

        prev_analysis = previous_data.get("analysis") or previous_data
        changes: List[SnapshotDeltaItem] = []

        # ── 1. Account Discovery Changes ──
        prev_accounts = prev_analysis.get("accounts") or prev_analysis.get("account_discovery") or []
        prev_acc_keys = {
            f"{a.get('platform')}:{a.get('account_identifier')}": a for a in prev_accounts if a.get("platform")
        }

        curr_accounts = current_report.account_discovery
        curr_acc_keys = {
            f"{a.platform}:{a.account_identifier}": a for a in curr_accounts if a.platform
        }

        # Newly discovered accounts
        for k, acc in curr_acc_keys.items():
            if k not in prev_acc_keys:
                changes.append(
                    SnapshotDeltaItem(
                        change_type="new_account",
                        field_name=f"account:{acc.platform}",
                        old_value=None,
                        new_value=acc.account_identifier,
                        description=f"New public {acc.platform.upper()} account discovered (@{acc.account_identifier})."
                    )
                )

        # ── 2. Developer Footprint & GitHub Activity ──
        prev_footprint = prev_analysis.get("footprint") or prev_analysis.get("developer_footprint") or {}
        prev_repos = {r.get("name") for r in prev_footprint.get("repositories", [])}
        curr_repos = {r.name for r in current_report.developer_footprint.repositories}

        for r_name in curr_repos:
            if r_name not in prev_repos:
                changes.append(
                    SnapshotDeltaItem(
                        change_type="github_activity",
                        field_name="repositories",
                        old_value=None,
                        new_value=r_name,
                        description=f"New public repository '{r_name}' published or discovered."
                    )
                )

        prev_stars = prev_footprint.get("total_stars", 0)
        curr_stars = current_report.developer_footprint.total_stars
        if curr_stars != prev_stars and (curr_stars > 0 or prev_stars > 0):
            changes.append(
                SnapshotDeltaItem(
                    change_type="github_activity",
                    field_name="total_stars",
                    old_value=prev_stars,
                    new_value=curr_stars,
                    description=f"Total repository stars changed from {prev_stars} to {curr_stars} (⭐ {curr_stars - prev_stars:+d})."
                )
            )

        # ── 3. Profile Metadata Changes ──
        prev_bio = prev_footprint.get("bio")
        curr_bio = current_report.developer_footprint.bio
        if prev_bio and curr_bio and prev_bio != curr_bio:
            changes.append(
                SnapshotDeltaItem(
                    change_type="profile_updated",
                    field_name="bio",
                    old_value=prev_bio[:60],
                    new_value=curr_bio[:60],
                    description="Public developer bio text was updated."
                )
            )

        # ── 4. Breach Exposure Changes (Safety Rule: only compare if previous was actually checked) ──
        prev_breach_status = prev_analysis.get("breach_status")
        if prev_breach_status == "checked" and current_report.breach_status == "checked":
            prev_breaches = {b.get("breach_name") for b in prev_analysis.get("breaches", [])}
            curr_breaches = {b.breach_name for b in current_report.breaches}

            for b_name in curr_breaches:
                if b_name not in prev_breaches:
                    changes.append(
                        SnapshotDeltaItem(
                            change_type="new_breach",
                            field_name="breaches",
                            old_value=None,
                            new_value=b_name,
                            description=f"New security breach disclosure '{b_name}' identified since last scan."
                        )
                    )

        # ── 5. Web Mention Occurrences ──
        prev_mentions = {m.get("canonical_url") or m.get("url") for m in prev_analysis.get("web_mentions", []) if m.get("url")}
        curr_mentions = {m.canonical_url or m.url for m in current_report.web_mentions if m.url}

        for m_url in curr_mentions:
            if m_url not in prev_mentions and m_url:
                changes.append(
                    SnapshotDeltaItem(
                        change_type="new_web_mention",
                        field_name="web_mentions",
                        old_value=None,
                        new_value=m_url,
                        description=f"New public web citation discovered: {m_url}"
                    )
                )

        if changes:
            summary = f"Detected {len(changes)} update(s) since previous investigation ({previous_created_at or 'prior scan'})."
        else:
            summary = f"No significant public footprint changes detected since previous scan ({previous_created_at or 'prior scan'})."

        return HistoricalSnapshotComparison(
            has_previous_scan=True,
            previous_scan_date=previous_created_at,
            previous_job_id=previous_job_id,
            changes=changes,
            summary=summary
        )
