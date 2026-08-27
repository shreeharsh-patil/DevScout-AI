"""
Username Correlation & Permutation Agent.

Generates candidate username hypotheses from email local-parts.
All generated handles are strictly labeled CANDIDATE and are never elevated
to verified status without independent cryptographic or public commit evidence.
"""

from __future__ import annotations

import re
from typing import List, Set
from ..models import ConfidenceLevel, UsernameCandidate


class UsernameCorrelationAgent:
    """Generates and evaluates candidate username hypotheses."""

    @staticmethod
    def generate_candidates(local_part: str) -> List[UsernameCandidate]:
        candidates: List[UsernameCandidate] = []
        seen: Set[str] = set()

        clean_local = (local_part or "").strip()
        if not clean_local:
            return candidates

        def _add(username: str, rule: str):
            u_clean = username.strip().lower()
            if u_clean and len(u_clean) >= 2 and u_clean not in seen:
                seen.add(u_clean)
                candidates.append(
                    UsernameCandidate(
                        username=u_clean,
                        generation_rule=rule,
                        confidence_level=ConfidenceLevel.CANDIDATE,
                        matched_platforms=[],
                        evidence_note="Candidate handle derived from email syntax. Unverified without independent public evidence."
                    )
                )

        # 1. Exact local part
        _add(clean_local, "exact_local_part")

        # 2. Dot-separated split (e.g. john.doe -> johndoe, john-doe, john_doe, john, doe)
        if "." in clean_local:
            parts = clean_local.split(".")
            _add("".join(parts), "concatenated_no_dots")
            _add("-".join(parts), "hyphen_separated")
            _add("_".join(parts), "underscore_separated")
            if len(parts) > 1 and len(parts[0]) >= 3:
                _add(parts[0], "first_name_prefix")

        # 3. Plus/tag stripped (e.g. john+dev -> john)
        if "+" in clean_local:
            base = clean_local.split("+")[0]
            _add(base, "plus_tag_removed")

        # 4. Underscore/hyphen replacements
        if "_" in clean_local:
            parts = clean_local.split("_")
            _add("".join(parts), "concatenated_no_underscores")
            _add("-".join(parts), "hyphen_separated")

        if "-" in clean_local:
            parts = clean_local.split("-")
            _add("".join(parts), "concatenated_no_hyphens")
            _add("_".join(parts), "underscore_separated")

        # 5. Number stripped suffix (e.g. johndoe99 -> johndoe)
        num_stripped = re.sub(r"\d+$", "", clean_local)
        if num_stripped and num_stripped != clean_local and len(num_stripped) >= 3:
            _add(num_stripped, "numeric_suffix_removed")

        return candidates[:8]
