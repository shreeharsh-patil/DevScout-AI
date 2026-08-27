"""
npm Registry Developer Footprint Provider.

Discovers published npm packages and maintainer profiles associated with public developer emails.
"""

from __future__ import annotations

from typing import Any, Dict, List
from loguru import logger
import requests
from ..models import AccountFinding, FindingStatus, Evidence, utc_now_iso
from .base import BaseProvider


class NpmProvider(BaseProvider):
    platform_name: str = "npm"

    def search(self, email: str, local_part: str, domain: str) -> List[AccountFinding]:
        findings: List[AccountFinding] = []
        normalized_email = email.strip().lower()

        # 1. Search npm registry for packages matching maintainer email
        try:
            url = f"https://registry.npmjs.org/-/v1/search?text=maintainer:{requests.utils.quote(normalized_email)}&size=10"
            resp = self._safe_request(url, timeout=12)
            if resp and resp.status_code == 200:
                objects = resp.json().get("objects", [])
                if objects:
                    pkg_names = [obj.get("package", {}).get("name", "") for obj in objects if obj.get("package")]
                    first_pkg = objects[0].get("package", {})
                    author_name = first_pkg.get("publisher", {}).get("username") or local_part

                    ev_id = "npm_maintainer_registry"
                    evidence = Evidence(
                        evidence_id=ev_id,
                        provider="npm",
                        source_type="package_registry_maintainer",
                        title=f"npm Package Maintainer ({len(pkg_names)} packages)",
                        url=f"https://www.npmjs.com/~{author_name}",
                        retrieved_at=utc_now_iso(),
                        supports="npm_footprint",
                        strength="strong",
                        snippet=f"Maintainer of npm packages: {', '.join(pkg_names[:5])}",
                        raw_data={"packages": pkg_names, "publisher": author_name}
                    )

                    finding = AccountFinding(
                        provider="npm",
                        finding_type="account",
                        platform="npm",
                        status=FindingStatus.VERIFIED,
                        confidence_level=FindingStatus.VERIFIED,
                        confidence_score=0.95,
                        evidence_ids=[ev_id],
                        account_identifier=author_name,
                        profile_url=f"https://www.npmjs.com/~{author_name}",
                        display_name=author_name,
                        method="npm_maintainer_email_search",
                        evidence=[evidence],
                        metadata={
                            "packages_count": len(pkg_names),
                            "packages": pkg_names
                        }
                    )
                    findings.append(finding)
        except Exception as e:
            logger.debug(f"[NpmProvider] Search error: {e}")

        return findings

    def fetch_maintainer_packages(self, username_or_email: str) -> List[Dict[str, Any]]:
        try:
            url = f"https://registry.npmjs.org/-/v1/search?text=maintainer:{requests.utils.quote(username_or_email)}&size=10"
            resp = self._safe_request(url, timeout=10)
            if resp and resp.status_code == 200:
                results = []
                for obj in resp.json().get("objects", []):
                    pkg = obj.get("package", {})
                    results.append({
                        "name": pkg.get("name", ""),
                        "version": pkg.get("version", ""),
                        "description": pkg.get("description", ""),
                        "links": pkg.get("links", {})
                    })
                return results
        except Exception:
            pass
        return []
