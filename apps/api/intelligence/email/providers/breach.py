"""
Breach Exposure Provider Plugin (HIBP / Public Security Disclosures) - Phase 10.

Fetches high-level breach event metadata (breach name, domain, date, added date, data classes,
verified status, retired status, spam list flag, and severity classification).

STRICT SAFETY & PRIVACY REQUIREMENT:
- NEVER queries, fetches, exposes, or stores passwords, password hashes, auth tokens,
  session cookies, private credentials, or raw database dumps.
- Breach exposure auditing exists solely for metadata awareness and high-level risk assessment.
"""

from __future__ import annotations

import os
from typing import List, Tuple
from loguru import logger
import requests
from ..models import (
    BreachFinding,
    EmailTarget,
    Evidence,
    FindingStatus,
    ProviderResult,
    utc_now_iso,
)
from .base import BaseEmailProvider


def classify_breach_severity(data_classes: List[str]) -> str:
    """
    Classifies breach exposure severity strictly based on exposed data categories.
    ZERO credentials or stolen secrets are ever fetched or analyzed.
    """
    lower_classes = {c.lower() for c in data_classes}

    # CRITICAL: Financial, Banking, Government IDs
    critical_signals = {
        "bank account numbers", "credit cards", "social security numbers",
        "passport numbers", "national identification numbers", "financial transactions"
    }
    if any(sig in lower_classes for sig in critical_signals):
        return "CRITICAL"

    # HIGH: Phone numbers, Physical addresses, Dates of birth, Security questions, Password hints
    high_signals = {
        "phone numbers", "physical addresses", "dates of birth",
        "security questions and answers", "password hints", "chat logs", "sms messages"
    }
    if any(sig in lower_classes for sig in high_signals):
        return "HIGH"

    # MEDIUM: Email + Name + Username + IP (Public Profile Info)
    medium_signals = {
        "names", "usernames", "ip addresses", "geographic locations",
        "job titles", "genders", "spoken languages"
    }
    if any(sig in lower_classes for sig in medium_signals):
        return "MEDIUM"

    # LOW: Email only, newsletter memberships, basic subscriber lists
    return "LOW"


class BreachEmailProvider(BaseEmailProvider):
    provider_name: str = "breach"

    def __init__(self, timeout: float = 10.0, max_retries: int = 2):
        super().__init__(timeout=timeout, max_retries=max_retries)
        self.api_key = os.getenv("HIBP_API_KEY", "")

    def is_available(self) -> bool:
        return bool(self.api_key)

    def lookup(self, target: EmailTarget) -> ProviderResult:
        if not self.is_available():
            return ProviderResult(
                provider=self.provider_name,
                finding_type="breach",
                status=FindingStatus.UNAVAILABLE,
                confidence_level=FindingStatus.UNAVAILABLE,
                confidence_score=0.0,
                retrieved_at=utc_now_iso(),
                error="HIBP_API_KEY is not configured.",
                metadata={
                    "breach_status": "unavailable",
                    "privacy_note": "Breach exposure auditing tracks public metadata disclosures only. Zero credentials or passwords are ever queried or stored."
                }
            )

        email = target.normalized_email or target.raw_email
        breaches, status_str = self.check_breaches(email)

        all_evidence: List[Evidence] = []
        for b in breaches:
            ev_id = f"hibp_{b.domain or b.breach_name.lower().replace(' ', '_')}"
            all_evidence.append(
                Evidence(
                    evidence_id=ev_id,
                    provider="breach",
                    source_type="security_audit",
                    title=f"Breach Disclosure: {b.breach_name}",
                    url=f"https://haveibeenpwned.com/account/{email}",
                    retrieved_at=b.retrieved_at,
                    supports="breach_exposure",
                    strength="strong",
                    snippet=f"Email identified in public breach disclosure: {b.breach_name} (Severity: {b.severity}, Date: {b.breach_date or 'Unknown'})."
                )
            )

        if status_str == "unavailable":
            top_status = FindingStatus.UNAVAILABLE
            top_score = 0.0
        elif status_str == "error":
            top_status = FindingStatus.ERROR
            top_score = 0.0
        elif breaches:
            top_status = FindingStatus.VERIFIED
            top_score = 0.90
        else:
            top_status = FindingStatus.NO_EVIDENCE
            top_score = 0.0

        return ProviderResult(
            provider=self.provider_name,
            finding_type="breach",
            status=top_status,
            confidence_level=top_status,
            confidence_score=top_score,
            evidence_ids=[e.evidence_id for e in all_evidence],
            evidence_items=all_evidence,
            findings=breaches,
            retrieved_at=utc_now_iso(),
            metadata={
                "breaches_count": len(breaches),
                "breach_status": status_str,
                "privacy_note": "Breach exposure auditing is strictly restricted to public disclosure metadata. Zero passwords or plaintext credentials are ever fetched or retained."
            }
        )

    def check_breaches(self, email: str) -> Tuple[List[BreachFinding], str]:
        if not self.api_key:
            return [], "unavailable"

        findings: List[BreachFinding] = []
        try:
            url = f"https://haveibeenpwned.com/api/v3/breachedaccount/{requests.utils.quote(email.strip().lower())}?truncateResponse=false"
            headers = {
                "hibp-api-key": self.api_key,
                "user-agent": "DevScoutAI-Research/1.0"
            }
            resp = self._safe_request(url, headers=headers, timeout=self.timeout)
            if not resp:
                return [], "unavailable"

            if resp.status_code == 200:
                for b in resp.json():
                    b_name = b.get("Title") or b.get("Name", "Security Breach")
                    data_classes = b.get("DataClasses", [])
                    severity = classify_breach_severity(data_classes)
                    ev_id = f"hibp_{b.get('Name', 'breach').lower()}"

                    findings.append(BreachFinding(
                        provider="breach",
                        finding_type="breach",
                        status=FindingStatus.VERIFIED,
                        confidence_level=FindingStatus.VERIFIED,
                        confidence_score=0.90,
                        evidence_ids=[ev_id],
                        retrieved_at=utc_now_iso(),
                        breach_name=b_name,
                        domain=b.get("Domain", ""),
                        breach_date=b.get("BreachDate"),
                        added_date=b.get("AddedDate"),
                        data_classes=data_classes,
                        is_verified=b.get("IsVerified", True),
                        is_retired=b.get("IsRetired", False),
                        is_spam_list=b.get("IsSpamList", False),
                        severity=severity,
                        description=b.get("Description", "")[:200],
                        metadata={"dataclasses_count": len(data_classes), "severity": severity}
                    ))
                return findings, "checked"

            elif resp.status_code == 404:
                return [], "checked"

            elif resp.status_code in (401, 403):
                logger.warning("[BreachEmailProvider] Invalid or expired HIBP API key.")
                return [], "unavailable"

            elif resp.status_code == 429:
                logger.warning("[BreachEmailProvider] Rate limited by HIBP API.")
                return [], "unavailable"

        except Exception as e:
            logger.debug(f"[BreachEmailProvider] Error: {e}")
            return [], "error"

        return findings, "checked"


# Backward-compatible alias
HIBPProvider = BreachEmailProvider
