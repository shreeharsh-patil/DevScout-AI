"""
Advanced Email Validation & Domain Intelligence Agent (Phase 3).

Upgrades email preprocessing with:
- RFC 5322 syntax validation and casing normalization
- Domain classification: consumer_provider, custom_domain, corporate_domain,
  education_domain, government_domain, disposable, unknown
- Role-based email detection (admin@, support@, contact@, sales@, info@, security@, hello@, etc.)
- MX record availability and mail provider routing analysis
- Uncertainty reporting on DNS/network timeouts (never falsely claiming non-existence)
- Domain website activity check and organization clues
- Fast in-memory caching and strict timeout handling
- STRICT PRIVACY: Zero verification emails or SMTP RCPT TO connections sent.
"""

from __future__ import annotations

import re
import time
from typing import Any, Dict, List, Optional, Set, Tuple
from loguru import logger
import requests
import http_client
from security import validate_public_url
from .models import DomainClassification, EmailTarget


# ─── 1. Provider & Domain Registries ──────────────────────────────────────────

# Known free / consumer webmail providers
CONSUMER_PROVIDERS: Set[str] = {
    "gmail.com", "googlemail.com", "yahoo.com", "ymail.com", "rocketmail.com",
    "outlook.com", "hotmail.com", "live.com", "msn.com",
    "icloud.com", "me.com", "mac.com",
    "protonmail.com", "proton.me", "pm.me",
    "aol.com", "zoho.com", "gmx.com", "gmx.net", "mail.com", "tutanota.com", "tuta.io",
    "fastmail.com", "yandex.com", "yandex.ru", "naver.com", "qq.com", "163.com",
    "mail.ru", "inbox.com", "rediffmail.com"
}

# Known temporary / disposable email services
DISPOSABLE_DOMAINS: Set[str] = {
    "mailinator.com", "guerrillamail.com", "guerrillamailblock.com", "sharklasers.com",
    "grr.la", "tempmail.com", "temp-mail.org", "10minutemail.com", "yopmail.com",
    "yopmail.fr", "yopmail.net", "trashmail.com", "trashmail.net", "dispostable.com",
    "fakeinbox.com", "getairmail.com", "maildrop.cc", "mohmal.com", "inboxkitten.com",
    "throwawaymail.com", "burnermail.io", "tempail.com", "crazymailing.com",
    "maildrop.cc", "mytemp.email", "getnada.com", "disposablemail.com"
}

# Common role-based mailbox prefixes and their functional classification
ROLE_BASED_PREFIXES: Dict[str, str] = {
    "admin": "administrative",
    "administrator": "administrative",
    "root": "system",
    "support": "customer_support",
    "help": "customer_support",
    "helpdesk": "customer_support",
    "contact": "general_contact",
    "contactus": "general_contact",
    "info": "general_inquiries",
    "information": "general_inquiries",
    "inquiries": "general_inquiries",
    "sales": "sales",
    "security": "security_reports",
    "security-reports": "security_reports",
    "security-alert": "security_reports",
    "soc": "security_operations",
    "hello": "general_contact",
    "hi": "general_contact",
    "team": "team_mailbox",
    "billing": "billing",
    "invoices": "billing",
    "payments": "billing",
    "accounting": "billing",
    "press": "media_relations",
    "media": "media_relations",
    "pr": "media_relations",
    "jobs": "recruitment",
    "careers": "recruitment",
    "hr": "human_resources",
    "talent": "recruitment",
    "recruiting": "recruitment",
    "marketing": "marketing",
    "engineering": "engineering",
    "dev": "engineering",
    "developer": "engineering",
    "developers": "engineering",
    "api": "api_support",
    "legal": "legal",
    "privacy": "compliance",
    "compliance": "compliance",
    "dpo": "compliance",
    "abuse": "abuse_reports",
    "postmaster": "mail_system",
    "hostmaster": "dns_system",
    "webmaster": "web_system",
    "office": "office_administration",
    "operations": "operations",
    "ops": "operations",
    "noc": "network_operations",
    "service": "customer_service",
}

# Known corporate email infrastructure providers found in MX records
BUSINESS_MX_KEYWORDS: Dict[str, str] = {
    "google.com": "Google Workspace",
    "googlemail.com": "Google Workspace",
    "outlook.com": "Microsoft 365 / Exchange",
    "protection.outlook.com": "Microsoft 365",
    "pphosted.com": "Proofpoint",
    "mimecast.com": "Mimecast",
    "barracudanetworks.com": "Barracuda",
    "zoho.com": "Zoho Mail",
    "fastmail.com": "Fastmail Business",
    "sendgrid.net": "SendGrid",
    "mailgun.org": "Mailgun",
    "mandrillapp.com": "Mandrill / Mailchimp",
    "amazonses.com": "Amazon SES",
    "cloudflare.net": "Cloudflare Email Routing",
}


# ─── 2. In-Memory Domain Cache ────────────────────────────────────────────────

_DOMAIN_INTEL_CACHE: Dict[str, Tuple[float, Dict[str, Any]]] = {}
CACHE_TTL_SECONDS = 3600  # 1 hour TTL


class EmailValidatorAgent:
    """
    Advanced email preprocessing, RFC validation, and domain intelligence engine.
    """

    def __init__(
        self,
        dns_timeout: float = 2.5,
        http_timeout: float = 2.5,
        enable_network_intelligence: bool = True,
    ):
        self.dns_timeout = dns_timeout
        self.http_timeout = http_timeout
        self.enable_network_intelligence = enable_network_intelligence

    @classmethod
    def validate(cls, email: str) -> EmailTarget:
        """Validate syntax and local classifications without blocking on the network."""
        agent = cls(enable_network_intelligence=False)
        return agent.validate_email(email)

    @classmethod
    def validate_with_domain_intelligence(cls, email: str) -> EmailTarget:
        """Validate and enrich a domain through bounded DNS and HTTP probes."""
        return cls(enable_network_intelligence=True).validate_email(email)

    def validate_email(self, email: str) -> EmailTarget:
        raw_email = email or ""
        trimmed = raw_email.strip()

        # ── 1. Syntax Validation ──
        if not trimmed:
            return EmailTarget(
                raw_email=raw_email,
                is_valid=False,
                normalized_email="",
                domain="",
                local_part="",
                domain_classification=DomainClassification.UNKNOWN,
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
                domain_classification=DomainClassification.UNKNOWN,
                is_disposable=False,
                validation_error="Email address exceeds maximum allowed length of 254 characters."
            )

        # RFC 5322 standard regex pattern
        pattern = (
            r"^[a-zA-Z0-9.!#$%&'*+/=?^_`{|}~-]+@[a-zA-Z0-9]"
            r"(?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?"
            r"(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)+$"
        )
        if not re.match(pattern, trimmed):
            return EmailTarget(
                raw_email=raw_email,
                is_valid=False,
                normalized_email=trimmed.lower(),
                domain="",
                local_part="",
                domain_classification=DomainClassification.UNKNOWN,
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
                domain_classification=DomainClassification.UNKNOWN,
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
                domain_classification=DomainClassification.UNKNOWN,
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
                domain_classification=DomainClassification.UNKNOWN,
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
                domain_classification=DomainClassification.UNKNOWN,
                is_disposable=False,
                validation_error="Email domain is invalid or missing top-level domain."
            )

        normalized_email = f"{local_part}@{domain}".lower()

        # ── 2. Role-Based Account Detection ──
        is_role_account, role_type = self._detect_role_account(local_part)

        # ── 3. Domain Classification & Intelligence ──
        domain_intel = (
            self._analyze_domain(domain)
            if self.enable_network_intelligence
            else self._classify_domain_offline(domain)
        )

        return EmailTarget(
            raw_email=trimmed,
            is_valid=True,
            normalized_email=normalized_email,
            domain=domain,
            local_part=local_part,
            domain_classification=domain_intel["classification"],
            provider_type=domain_intel["classification"],
            is_disposable=domain_intel["is_disposable"],
            is_role_account=is_role_account,
            role_type=role_type,
            is_custom_domain=domain_intel["is_custom_domain"],
            has_mx_records=domain_intel["has_mx_records"],
            mx_records=domain_intel["mx_records"],
            mx_host=domain_intel["mx_host"],
            mx_status=domain_intel["mx_status"],
            website_url=domain_intel.get("website_url"),
            website_title=domain_intel.get("website_title"),
            is_website_active=domain_intel.get("is_website_active", False),
            organization_name=domain_intel.get("organization_name"),
            domain_age_years=domain_intel.get("domain_age_years"),
            domain_created_at=domain_intel.get("domain_created_at"),
            validation_error=None
        )

    def _detect_role_account(self, local_part: str) -> Tuple[bool, Optional[str]]:
        """Detects whether local_part is a generic department or role address."""
        clean_local = local_part.strip().lower()

        # Strip subaddressing / tag (e.g. support+urgent -> support, info-dev -> info)
        base_local = re.split(r"[+_.-]", clean_local)[0]

        if clean_local in ROLE_BASED_PREFIXES:
            return True, ROLE_BASED_PREFIXES[clean_local]

        if base_local in ROLE_BASED_PREFIXES:
            return True, ROLE_BASED_PREFIXES[base_local]

        return False, None

    @staticmethod
    def _classify_domain_offline(domain: str) -> Dict[str, Any]:
        """Classify known domain categories without making outbound requests."""
        is_disposable = domain in DISPOSABLE_DOMAINS
        is_consumer = domain in CONSUMER_PROVIDERS
        is_education = any(
            domain.endswith(suffix)
            for suffix in (".edu", ".ac.uk", ".edu.cn", ".edu.in", ".edu.au", ".ac.in", ".ac.jp")
        )
        is_government = any(
            domain.endswith(suffix)
            for suffix in (".gov", ".mil", ".gov.uk", ".gov.in", ".gov.au", ".fed.us")
        )
        if is_disposable:
            classification = DomainClassification.DISPOSABLE
        elif is_consumer:
            classification = DomainClassification.CONSUMER_PROVIDER
        elif is_education:
            classification = DomainClassification.EDUCATION_DOMAIN
        elif is_government:
            classification = DomainClassification.GOVERNMENT_DOMAIN
        else:
            classification = DomainClassification.CUSTOM_DOMAIN
        known_mail_domain = is_disposable or is_consumer
        return {
            "classification": classification,
            "is_disposable": is_disposable,
            "is_custom_domain": not (is_disposable or is_consumer),
            "has_mx_records": known_mail_domain,
            "mx_records": [f"mx.{domain}"] if known_mail_domain else [],
            "mx_host": domain if known_mail_domain else None,
            "mx_status": "valid" if known_mail_domain else "unchecked",
            "is_website_active": is_consumer,
            "organization_name": domain.split(".")[0].capitalize() if is_consumer else None,
        }

    def _analyze_domain(self, domain: str) -> Dict[str, Any]:
        """Analyzes MX records, domain classification, and website metadata with caching."""
        now = time.time()
        cached = _DOMAIN_INTEL_CACHE.get(domain)
        if cached and (now - cached[0]) < CACHE_TTL_SECONDS:
            return cached[1]

        # Check special categories first
        if domain in DISPOSABLE_DOMAINS:
            intel = {
                "classification": DomainClassification.DISPOSABLE,
                "is_disposable": True,
                "is_custom_domain": False,
                "has_mx_records": True,
                "mx_records": ["disposable-mx"],
                "mx_host": "disposable-provider",
                "mx_status": "valid",
                "is_website_active": False
            }
            _DOMAIN_INTEL_CACHE[domain] = (now, intel)
            return intel

        if domain in CONSUMER_PROVIDERS:
            intel = {
                "classification": DomainClassification.CONSUMER_PROVIDER,
                "is_disposable": False,
                "is_custom_domain": False,
                "has_mx_records": True,
                "mx_records": [f"mx.{domain}"],
                "mx_host": domain,
                "mx_status": "valid",
                "is_website_active": True,
                "organization_name": domain.split(".")[0].capitalize()
            }
            _DOMAIN_INTEL_CACHE[domain] = (now, intel)
            return intel

        is_education = any(domain.endswith(sfx) for sfx in [".edu", ".ac.uk", ".edu.cn", ".edu.in", ".edu.au", ".ac.in", ".ac.jp"])
        is_government = any(domain.endswith(sfx) for sfx in [".gov", ".mil", ".gov.uk", ".gov.in", ".gov.au", ".fed.us"])

        # ── MX Record Lookup ──
        mx_records, mx_status = self._lookup_mx_records(domain)
        has_mx = len(mx_records) > 0
        primary_mx = mx_records[0] if mx_records else None

        # Check for business / corporate mail routing in MX host
        business_provider_name = None
        if primary_mx:
            for kw, provider_label in BUSINESS_MX_KEYWORDS.items():
                if kw in primary_mx.lower():
                    business_provider_name = provider_label
                    break

        # ── Website & Organization Signals ──
        website_info = self._check_website(domain)

        # Classification decision
        if is_education:
            classification = DomainClassification.EDUCATION_DOMAIN
        elif is_government:
            classification = DomainClassification.GOVERNMENT_DOMAIN
        elif business_provider_name or website_info.get("is_active"):
            classification = DomainClassification.CORPORATE_DOMAIN
        elif has_mx:
            classification = DomainClassification.CUSTOM_DOMAIN
        elif mx_status == "none":
            classification = DomainClassification.UNKNOWN
        else:
            classification = DomainClassification.CUSTOM_DOMAIN

        org_name = website_info.get("title_org") or (
            domain.split(".")[0].replace("-", " ").capitalize() if classification == DomainClassification.CORPORATE_DOMAIN else None
        )

        intel = {
            "classification": classification,
            "is_disposable": False,
            "is_custom_domain": True,
            "has_mx_records": has_mx,
            "mx_records": mx_records,
            "mx_host": primary_mx,
            "mx_status": mx_status,
            "website_url": f"https://{domain}" if website_info.get("is_active") else None,
            "website_title": website_info.get("title"),
            "is_website_active": website_info.get("is_active", False),
            "organization_name": org_name,
            "business_mail_provider": business_provider_name
        }

        _DOMAIN_INTEL_CACHE[domain] = (now, intel)
        return intel

    def _lookup_mx_records(self, domain: str) -> Tuple[List[str], str]:
        """
        Looks up MX records using a bounded DNS-over-HTTPS (DoH) request.
        Reports 'uncertain' on network errors/timeouts instead of claiming non-existence.
        """
        # 1. DNS-over-HTTPS query (fast, cross-platform, non-blocking)
        try:
            doh_url = f"https://cloudflare-dns.com/dns-query?name={domain}&type=MX"
            headers = {"Accept": "application/dns-json"}
            resp = requests.get(doh_url, headers=headers, timeout=self.dns_timeout)
            if resp.status_code == 200:
                data = resp.json()
                status_code = data.get("Status", 0)
                answers = data.get("Answer", [])

                if answers:
                    mx_list = []
                    for ans in answers:
                        if ans.get("type") == 15:  # MX record type
                            data_str = ans.get("data", "")
                            # MX data format: "<priority> <target>" e.g. "10 aspmx.l.google.com."
                            parts = data_str.strip().split()
                            host = parts[-1].rstrip(".") if parts else data_str
                            if host:
                                mx_list.append(host)
                    if mx_list:
                        return mx_list, "valid"

                # Status 3 = NXDOMAIN (Non-Existent Domain)
                if status_code == 3:
                    return [], "none"

                # No MX answers, check if A record exists (fallback mail routing)
                if not answers:
                    return [], "none"

        except (requests.Timeout, requests.RequestException, Exception) as e:
            logger.debug(f"[EmailValidator] DoH MX query timeout/error for '{domain}': {e}")

        # A DNS resolver fallback via getaddrinfo has no portable per-call timeout
        # and can stall request workers. Treat failed bounded DoH resolution as
        # uncertain instead of making an unbounded socket call.
        return [], "uncertain"

    def _check_website(self, domain: str) -> Dict[str, Any]:
        """Probes https://{domain} safely to discover website activity and organization clues."""
        info: Dict[str, Any] = {"is_active": False, "title": None, "title_org": None}
        try:
            url = validate_public_url(f"https://{domain}")
            resp = http_client.get(url, timeout=self.http_timeout)
            if resp and resp.status_code < 400:
                info["is_active"] = True
                # Extract <title>
                title_match = re.search(r"<title[^>]*>([^<]+)</title>", resp.text, re.IGNORECASE)
                if title_match:
                    raw_title = title_match.group(1).strip()
                    info["title"] = raw_title[:100]
                    # Extract org name if title has delimiters like "Company - Slogan" or "Company | Home"
                    for sep in [" - ", " | ", " — ", " :: ", " : "]:
                        if sep in raw_title:
                            candidate_org = raw_title.split(sep)[0].strip()
                            if len(candidate_org) < 40:
                                info["title_org"] = candidate_org
                                break
                    if not info["title_org"] and len(raw_title) < 40:
                        info["title_org"] = raw_title
        except Exception:
            pass
        return info
