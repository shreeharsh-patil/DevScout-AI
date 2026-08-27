"""
Gravatar Intelligence Provider.

Fetches public Gravatar profiles using cryptographic MD5 / SHA256 hashes.
Provides verified avatar images, display names, and public bios.
"""

from __future__ import annotations

import hashlib
from typing import List
from ..models import AccountFinding, FindingStatus, Evidence, utc_now_iso
from .base import BaseProvider


class GravatarProvider(BaseProvider):
    platform_name: str = "gravatar"

    def search(self, email: str, local_part: str, domain: str) -> List[AccountFinding]:
        findings: List[AccountFinding] = []
        normalized_email = email.strip().lower()
        md5_hash = hashlib.md5(normalized_email.encode("utf-8")).hexdigest()
        sha256_hash = hashlib.sha256(normalized_email.encode("utf-8")).hexdigest()

        # 1. Query Gravatar public REST profile endpoint
        profile_url_json = f"https://en.gravatar.com/{md5_hash}.json"
        resp = self._safe_request(profile_url_json, timeout=10)

        has_profile = False
        display_name = None
        about_me = None
        profile_web_url = f"https://gravatar.com/{md5_hash}"
        avatar_url = f"https://www.gravatar.com/avatar/{md5_hash}?d=404&s=200"

        if resp and resp.status_code == 200:
            try:
                entry = resp.json().get("entry", [{}])[0]
                has_profile = True
                display_name = entry.get("displayName") or entry.get("preferredUsername")
                about_me = entry.get("aboutMe")
                profile_web_url = entry.get("profileUrl") or profile_web_url
                avatar_url = entry.get("thumbnailUrl") or avatar_url
            except Exception:
                has_profile = True
        else:
            # 2. Check avatar image presence directly if JSON is 404
            img_check = self._safe_request(f"https://www.gravatar.com/avatar/{md5_hash}?d=404", timeout=5)
            if img_check and img_check.status_code == 200:
                has_profile = True
                avatar_url = f"https://www.gravatar.com/avatar/{md5_hash}?s=200"

        if has_profile:
            ev_id = f"gravatar_{md5_hash[:8]}"
            evidence = Evidence(
                evidence_id=ev_id,
                provider="gravatar",
                source_type="cryptographic_hash_lookup",
                title=f"Gravatar Profile ({display_name or 'Matched Avatar'})",
                url=profile_web_url,
                retrieved_at=utc_now_iso(),
                supports="gravatar_identity",
                strength="deterministic",
                snippet=f"Verified Gravatar record matching MD5({normalized_email})={md5_hash}. Display: '{display_name or 'N/A'}'.",
                raw_data={"md5": md5_hash, "sha256": sha256_hash, "displayName": display_name}
            )

            finding = AccountFinding(
                provider="gravatar",
                finding_type="account",
                platform="gravatar",
                status=FindingStatus.VERIFIED,
                confidence_level=FindingStatus.VERIFIED,
                confidence_score=1.0,
                evidence_ids=[ev_id],
                account_identifier=md5_hash,
                profile_url=profile_web_url,
                display_name=display_name,
                avatar_url=avatar_url,
                bio=about_me,
                method="cryptographic_email_hash_lookup",
                evidence=[evidence],
                metadata={
                    "md5_hash": md5_hash,
                    "sha256_hash": sha256_hash,
                    "avatar_url": avatar_url
                }
            )
            findings.append(finding)
        else:
            finding = AccountFinding(
                provider="gravatar",
                finding_type="account",
                platform="gravatar",
                status=FindingStatus.NO_EVIDENCE,
                confidence_level=FindingStatus.NO_EVIDENCE,
                confidence_score=0.0,
                evidence_ids=[],
                method="cryptographic_email_hash_lookup",
                evidence=[],
                metadata={"md5_hash": md5_hash, "has_profile": False}
            )
            findings.append(finding)

        return findings
