"""
Email Validation & Domain Intelligence Agent.

Validates RFC standard syntax, normalizes casing, and classifies domain provider types
(common, custom, academic, disposable) into strongly-typed EmailTarget instances.
"""

from __future__ import annotations

import re
from .models import EmailTarget, ProviderType


# Known free/common webmail providers
COMMON_PROVIDERS = {
    "gmail.com", "googlemail.com", "yahoo.com", "ymail.com", "rocketmail.com",
    "outlook.com", "hotmail.com", "live.com", "msn.com",
    "icloud.com", "me.com", "mac.com",
    "protonmail.com", "proton.me", "pm.me",
    "aol.com", "zoho.com", "gmx.com", "gmx.net", "mail.com", "tutanota.com", "tuta.io",
    "fastmail.com", "yandex.com", "yandex.ru", "naver.com"
}

# Known temporary / disposable email services
DISPOSABLE_DOMAINS = {
    "mailinator.com", "guerrillamail.com", "guerrillamailblock.com", "sharklasers.com",
    "grr.la", "tempmail.com", "temp-mail.org", "10minutemail.com", "yopmail.com",
    "yopmail.fr", "yopmail.net", "trashmail.com", "trashmail.net", "dispostable.com",
    "fakeinbox.com", "getairmail.com", "maildrop.cc", "mohmal.com", "inboxkitten.com",
    "throwawaymail.com", "burnermail.io", "tempail.com", "crazymailing.com"
}


class EmailValidatorAgent:
    """Validates and analyzes email syntax and domain characteristics."""

    @staticmethod
    def validate(email: str) -> EmailTarget:
        raw_email = email or ""
        trimmed = raw_email.strip()

        if not trimmed:
            return EmailTarget(
                raw_email=raw_email,
                is_valid=False,
                normalized_email="",
                domain="",
                local_part="",
                provider_type=ProviderType.CUSTOM,
                is_disposable=False,
                validation_error="Email address cannot be empty."
            )

        if len(trimmed) > 254:
            return EmailTarget(
                raw_email=raw_email,
                is_valid=False,
                normalized_email=trimmed.lower(),
                domain="",
                local_part="",
                provider_type=ProviderType.CUSTOM,
                is_disposable=False,
                validation_error="Email address exceeds maximum allowed length of 254 characters."
            )

        # Standard RFC 5322 regex
        pattern = r"^[a-zA-Z0-9.!#$%&'*+/=?^_`{|}~-]+@[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)+$"
        if not re.match(pattern, trimmed):
            return EmailTarget(
                raw_email=raw_email,
                is_valid=False,
                normalized_email=trimmed.lower(),
                domain="",
                local_part="",
                provider_type=ProviderType.CUSTOM,
                is_disposable=False,
                validation_error=f"Invalid email syntax: '{trimmed}'."
            )

        parts = trimmed.split("@")
        if len(parts) != 2:
            return EmailTarget(
                raw_email=raw_email,
                is_valid=False,
                normalized_email=trimmed.lower(),
                domain="",
                local_part="",
                provider_type=ProviderType.CUSTOM,
                is_disposable=False,
                validation_error="Email must contain exactly one '@' separator."
            )

        local_part, domain = parts[0], parts[1].lower()

        if len(local_part) > 64:
            return EmailTarget(
                raw_email=raw_email,
                is_valid=False,
                normalized_email=trimmed.lower(),
                domain=domain,
                local_part=local_part,
                provider_type=ProviderType.CUSTOM,
                is_disposable=False,
                validation_error="Local part of email exceeds maximum allowed length of 64 characters."
            )

        if ".." in local_part or ".." in domain:
            return EmailTarget(
                raw_email=raw_email,
                is_valid=False,
                normalized_email=trimmed.lower(),
                domain=domain,
                local_part=local_part,
                provider_type=ProviderType.CUSTOM,
                is_disposable=False,
                validation_error="Email address cannot contain consecutive periods."
            )

        domain_parts = domain.split(".")
        if len(domain_parts) < 2 or not all(domain_parts) or len(domain_parts[-1]) < 2:
            return EmailTarget(
                raw_email=raw_email,
                is_valid=False,
                normalized_email=trimmed.lower(),
                domain=domain,
                local_part=local_part,
                provider_type=ProviderType.CUSTOM,
                is_disposable=False,
                validation_error="Email domain is invalid or missing top-level domain."
            )

        # Normalize casing: lowercase domain and lowercase common email addresses
        normalized_email = f"{local_part}@{domain}".lower()

        # Classify provider type
        is_disposable = domain in DISPOSABLE_DOMAINS
        if is_disposable:
            provider_type = ProviderType.DISPOSABLE
        elif domain in COMMON_PROVIDERS:
            provider_type = ProviderType.COMMON
        elif any(domain.endswith(suffix) for suffix in [".edu", ".ac.uk", ".edu.cn", ".edu.in", ".ac.jp"]):
            provider_type = ProviderType.ACADEMIC
        else:
            provider_type = ProviderType.CUSTOM

        return EmailTarget(
            raw_email=trimmed,
            is_valid=True,
            normalized_email=normalized_email,
            domain=domain,
            local_part=local_part,
            provider_type=provider_type,
            is_disposable=is_disposable,
            validation_error=None
        )
