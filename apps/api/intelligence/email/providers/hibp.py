"""
Breach Exposure Provider (HIBP / Public Security Disclosures).

Fetches high-level breach event metadata (breach title, domain, date, exposed data classes).
STRICT SAFETY REQUIREMENT: NEVER exposes, stores, or queries passwords, hashes, tokens,
or private database dump contents.
"""

from __future__ import annotations

import os
from typing import List, Tuple
from loguru import logger
import requests
from ..models import BreachFinding
from .base import BaseProvider


class HIBPProvider(BaseProvider):
    platform_name: str = "hibp"

    def __init__(self, timeout: int = 10):
        super().__init__(timeout=timeout)
        self.api_key = os.getenv("HIBP_API_KEY", "")

    def check_breaches(self, email: str) -> Tuple[List[BreachFinding], str]:
        """
        Queries breach disclosures. Returns (findings, status_string).
        status_string: 'checked', 'unavailable', or 'error'
        """
        if not self.api_key:
            # When HIBP API key is unconfigured, return UNAVAILABLE cleanly
            return [], "unavailable"

        findings: List[BreachFinding] = []
        try:
            url = f"https://haveibeenpwned.com/api/v3/breachedaccount/{requests.utils.quote(email.strip().lower())}?truncateResponse=false"
            headers = {
                "hibp-api-key": self.api_key,
                "user-agent": "DevScoutAI-Research/1.0"
            }
            resp = self._safe_request(url, headers=headers, timeout=12)
            if not resp:
                return [], "unavailable"

            if resp.status_code == 200:
                for b in resp.json():
                    findings.append(BreachFinding(
                        breach_name=b.get("Title") or b.get("Name", "Security Breach"),
                        domain=b.get("Domain", ""),
                        breach_date=b.get("BreachDate"),
                        data_classes=b.get("DataClasses", []),
                        is_verified=b.get("IsVerified", True),
                        description=b.get("Description", "")[:200]
                    ))
                return findings, "checked"

            elif resp.status_code == 404:
                # No breach records found for this email address
                return [], "checked"

            elif resp.status_code in (401, 403):
                logger.warning("[HIBPProvider] Invalid or expired HIBP API key.")
                return [], "unavailable"

            elif resp.status_code == 429:
                logger.warning("[HIBPProvider] Rate limited by HIBP API.")
                return [], "unavailable"

        except Exception as e:
            logger.debug(f"[HIBPProvider] Error: {e}")
            return [], "error"

        return findings, "checked"

    def search(self, email: str, local_part: str, domain: str):
        return []
