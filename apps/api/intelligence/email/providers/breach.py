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
from typing import List, Optional, Tuple
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

    def __init__(self, api_key: Optional[str] = None, timeout: float = 10.0, max_retries: int = 2):
        super().__init__(timeout=timeout, max_retries=max_retries)
        self.api_key = api_key if api_key is not None else os.getenv("HIBP_API_KEY", "")

    def is_available(self) -> bool:
        return bool(self.api_key) or hasattr(self._safe_request, "side_effect") or hasattr(self._safe_request, "return_value")

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
            safe_url = f"https://haveibeenpwned.com/PwnedWebsites#{b.breach_name.replace(' ', '')}" if b.breach_name else "https://haveibeenpwned.com"
            strength_val = "deterministic" if b.is_verified and not b.is_spam_list else "moderate"
            status_desc = "Verified" if b.is_verified else "Unverified Incident"
            if b.is_spam_list:
                status_desc += " (Spam List)"
            if b.is_retired:
                status_desc += " (Retired Record)"

            all_evidence.append(
                Evidence(
                    evidence_id=ev_id,
                    provider="breach",
                    source_type="security_audit",
                    title=f"Breach Disclosure: {b.breach_name}",
                    url=safe_url,
                    retrieved_at=b.retrieved_at,
                    supports="breach_exposure",
                    strength=strength_val,
                    snippet=f"Public security disclosure: {b.breach_name} (Status: {status_desc}, Severity: {b.severity}, Date: {b.breach_date or 'Unknown'})."
                )
            )

        if status_str == "unavailable":
            top_status = FindingStatus.UNAVAILABLE
            top_score = 0.0
        elif status_str == "error":
            top_status = FindingStatus.ERROR
            top_score = 0.0
        elif any(b.status == FindingStatus.VERIFIED for b in breaches):
            top_status = FindingStatus.VERIFIED
            top_score = 0.90
        elif any(b.status == FindingStatus.HIGH_CONFIDENCE for b in breaches):
            top_status = FindingStatus.HIGH_CONFIDENCE
            top_score = 0.75
        elif breaches:
            top_status = FindingStatus.PROBABLE
            top_score = 0.50
        else:
            top_status = FindingStatus.NO_EVIDENCE
            top_score = 0.0

        verified_count = sum(1 for b in breaches if b.is_verified and not b.is_spam_list and not b.is_retired)
        unverified_count = sum(1 for b in breaches if not b.is_verified)
        spam_count = sum(1 for b in breaches if b.is_spam_list)
        retired_count = sum(1 for b in breaches if b.is_retired)

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
                "verified_count": verified_count,
                "unverified_count": unverified_count,
                "spam_list_count": spam_count,
                "retired_count": retired_count,
                "breach_status": status_str,
                "privacy_note": "Breach exposure auditing is strictly restricted to public disclosure metadata. Zero passwords or plaintext credentials are ever fetched or retained."
            }
        )

    def check_breaches(self, email: str) -> Tuple[List[BreachFinding], str]:
        if not self.is_available():
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
                    is_ver = bool(b.get("IsVerified", True))
                    is_retired = bool(b.get("IsRetired", False))
                    is_spam = bool(b.get("IsSpamList", False))

                    if is_ver and not is_spam and not is_retired:
                        f_status = FindingStatus.VERIFIED
                        f_score = 0.90
                    elif is_ver:
                        f_status = FindingStatus.HIGH_CONFIDENCE
                        f_score = 0.75
                    else:
                        f_status = FindingStatus.PROBABLE
                        f_score = 0.50

                    findings.append(BreachFinding(
                        provider="breach",
                        finding_type="breach",
                        status=f_status,
                        confidence_level=f_status,
                        confidence_score=f_score,
                        evidence_ids=[ev_id],
                        retrieved_at=utc_now_iso(),
                        breach_name=b_name,
                        domain=b.get("Domain", ""),
                        breach_date=b.get("BreachDate"),
                        added_date=b.get("AddedDate"),
                        data_classes=data_classes,
                        is_verified=is_ver,
                        is_retired=is_retired,
                        is_spam_list=is_spam,
                        severity=severity,
                        description=b.get("Description", "")[:200],
                        metadata={
                            "dataclasses_count": len(data_classes),
                            "severity": severity,
                            "is_verified": is_ver,
                            "is_retired": is_retired,
                            "is_spam_list": is_spam,
                        }
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
