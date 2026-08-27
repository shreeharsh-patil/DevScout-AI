"""
Comprehensive Test Suite for Advanced Email Validation & Domain Intelligence (Phase 3).

Validates:
- Role-based address detection (admin@, support@, contact@, sales@, info@, security@, hello@, etc.)
- Domain classification (consumer_provider, custom_domain, corporate_domain,
  education_domain, government_domain, disposable, unknown)
- Role-based accounts NOT treated as personal individual identities
- MX record lookup and uncertainty reporting on timeouts/network errors (never claiming non-existence)
- In-memory domain intelligence caching and strict timeout handling
- Zero SMTP RCPT TO or email transmission
"""

import socket
from unittest.mock import MagicMock, patch
import pytest
import requests

from intelligence.email.identity_resolver import IdentityResolverAgent
from intelligence.email.models import (
    DeveloperFootprint,
    DomainClassification,
    EmailTarget,
    FindingStatus,
)
from intelligence.email.validator import EmailValidatorAgent, _DOMAIN_INTEL_CACHE


class TestRoleBasedEmailDetection:
    def test_detects_common_role_prefixes(self):
        role_emails = [
            ("admin@company.com", "administrative"),
            ("administrator@domain.io", "administrative"),
            ("root@server.internal", "system"),
            ("support@stripe.com", "customer_support"),
            ("help@github.com", "customer_support"),
            ("contact@uber.com", "general_contact"),
            ("info@techcorp.org", "general_inquiries"),
            ("inquiries@agency.com", "general_inquiries"),
            ("sales@salesforce.com", "sales"),
            ("security@google.com", "security_reports"),
            ("security-reports@corp.com", "security_reports"),
            ("hello@airbnb.com", "general_contact"),
            ("team@startup.io", "team_mailbox"),
            ("billing@saas.com", "billing"),
            ("careers@company.com", "recruitment"),
            ("jobs@startup.com", "recruitment"),
            ("hr@enterprise.com", "human_resources"),
            ("marketing@brand.com", "marketing"),
            ("engineering@tech.com", "engineering"),
            ("dev@project.org", "engineering"),
            ("legal@lawfirm.com", "legal"),
            ("privacy@dataprotection.eu", "compliance"),
            ("abuse@registrar.net", "abuse_reports"),
        ]

        with patch.object(EmailValidatorAgent, "_lookup_mx_records", return_value=(["mx.test.com"], "valid")):
            with patch.object(EmailValidatorAgent, "_check_website", return_value={"is_active": False, "title": None, "title_org": None}):
                for email, expected_role in role_emails:
                    target = EmailValidatorAgent.validate_with_domain_intelligence(email)
                    assert target.is_valid is True
                    assert target.is_role_account is True, f"Failed for {email}"
                    assert target.role_type == expected_role, f"Wrong role for {email}"

    def test_detects_tagged_and_subaddressed_role_emails(self):
        with patch.object(EmailValidatorAgent, "_lookup_mx_records", return_value=(["mx.test.com"], "valid")):
            with patch.object(EmailValidatorAgent, "_check_website", return_value={"is_active": False, "title": None, "title_org": None}):
                target = EmailValidatorAgent.validate_with_domain_intelligence("support+urgent-ticket@company.com")
                assert target.is_role_account is True
                assert target.role_type == "customer_support"

                target_info = EmailValidatorAgent.validate_with_domain_intelligence("info-eu@branch.com")
                assert target_info.is_role_account is True
                assert target_info.role_type == "general_inquiries"

    def test_personal_developer_emails_are_not_role_accounts(self):
        personal_emails = [
            "linus.torvalds@linux-foundation.org",
            "shreeharsh@gmail.com",
            "dan.abramov@facebook.com",
            "guido@python.org",
            "s.patil@university.edu",
        ]

        with patch.object(EmailValidatorAgent, "_lookup_mx_records", return_value=(["mx.test.com"], "valid")):
            with patch.object(EmailValidatorAgent, "_check_website", return_value={"is_active": False, "title": None, "title_org": None}):
                for email in personal_emails:
                    target = EmailValidatorAgent.validate_with_domain_intelligence(email)
                    assert target.is_valid is True
                    assert target.is_role_account is False
                    assert target.role_type is None


class TestDomainClassifications:
    def test_consumer_webmail_classification(self):
        target = EmailValidatorAgent.validate_with_domain_intelligence("user123@gmail.com")
        assert target.domain_classification == DomainClassification.CONSUMER_PROVIDER
        assert target.is_disposable is False
        assert target.is_custom_domain is False
        assert target.has_mx_records is True

    def test_disposable_domain_classification(self):
        target = EmailValidatorAgent.validate_with_domain_intelligence("temp_throwaway@mailinator.com")
        assert target.domain_classification == DomainClassification.DISPOSABLE
        assert target.is_disposable is True
        assert target.is_custom_domain is False

    def test_education_domain_classification(self):
        with patch.object(EmailValidatorAgent, "_lookup_mx_records", return_value=(["mx.stanford.edu"], "valid")):
            with patch.object(EmailValidatorAgent, "_check_website", return_value={"is_active": True, "title": "Stanford", "title_org": "Stanford"}):
                target = EmailValidatorAgent.validate_with_domain_intelligence("researcher@cs.stanford.edu")
                assert target.domain_classification == DomainClassification.EDUCATION_DOMAIN
                assert target.is_disposable is False

    def test_government_domain_classification(self):
        with patch.object(EmailValidatorAgent, "_lookup_mx_records", return_value=(["mx.nasa.gov"], "valid")):
            with patch.object(EmailValidatorAgent, "_check_website", return_value={"is_active": True, "title": "NASA", "title_org": "NASA"}):
                target = EmailValidatorAgent.validate_with_domain_intelligence("scientist@nasa.gov")
                assert target.domain_classification == DomainClassification.GOVERNMENT_DOMAIN
                assert target.is_disposable is False

    def test_corporate_and_custom_domain_classification(self):
        mock_doh_resp = MagicMock()
        mock_doh_resp.status_code = 200
        mock_doh_resp.json.return_value = {
            "Status": 0,
            "Answer": [{"type": 15, "data": "10 aspmx.l.google.com."}]
        }

        mock_web_resp = MagicMock()
        mock_web_resp.status_code = 200
        mock_web_resp.text = "<html><head><title>Stripe - Financial Infrastructure</title></head></html>"

        with patch("requests.get", return_value=mock_doh_resp):
            with patch("http_client.get", return_value=mock_web_resp):
                with patch("intelligence.email.validator.validate_public_url", side_effect=lambda url: url):
                    target = EmailValidatorAgent.validate_with_domain_intelligence("engineer@stripe-payments.com")
                    assert target.domain_classification == DomainClassification.CORPORATE_DOMAIN
                    assert target.is_custom_domain is True
                    assert target.has_mx_records is True
                    assert "aspmx.l.google.com" in target.mx_records
                    assert target.website_title == "Stripe - Financial Infrastructure"
                    assert target.organization_name == "Stripe"


class TestRoleBasedIdentityIsolation:
    def test_role_account_never_synthesizes_personal_name(self):
        with patch.object(EmailValidatorAgent, "_lookup_mx_records", return_value=(["mx.megacorp.io"], "valid")):
            with patch.object(EmailValidatorAgent, "_check_website", return_value={"is_active": True, "title": "Megacorp", "title_org": "Megacorp"}):
                target = EmailValidatorAgent.validate_with_domain_intelligence("support@megacorp.io")
                assert target.is_role_account is True

                identity = IdentityResolverAgent.resolve(
                    local_part=target.local_part,
                    domain=target.domain,
                    account_findings=[],
                    footprint=DeveloperFootprint(),
                    username_candidates=[],
                    target=target
                )

                # Name must NOT be synthesized as "Support"
                assert identity.possible_name is None
                # Ambiguity note should explicitly clarify this is a role-based mailbox
                assert identity.ambiguity_note is not None
                assert "role-based" in identity.ambiguity_note.lower()


class TestMXUncertaintyAndTimeoutHandling:
    def test_dns_timeout_reports_uncertainty_rather_than_non_existence(self):
        _DOMAIN_INTEL_CACHE.pop("flaky-dns-domain.org", None)

        with patch("requests.get", side_effect=requests.Timeout("Connection timed out")):
            with patch("socket.getaddrinfo", side_effect=socket.gaierror("DNS resolution failed")):
                target = EmailValidatorAgent.validate_with_domain_intelligence("dev@flaky-dns-domain.org")

                assert target.is_valid is True
                assert target.mx_status == "uncertain"
                assert target.validation_error is None

    def test_nxdomain_reports_none(self):
        _DOMAIN_INTEL_CACHE.pop("definitely-fake-domain-12345.xyz", None)

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"Status": 3, "Answer": []}

        with patch("requests.get", return_value=mock_resp):
            target = EmailValidatorAgent.validate_with_domain_intelligence("fake@definitely-fake-domain-12345.xyz")
            assert target.is_valid is True
            assert target.mx_status == "none"
            assert target.has_mx_records is False


class TestDomainIntelligenceCaching:
    def test_caches_repeated_domain_lookups(self):
        _DOMAIN_INTEL_CACHE.clear()

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "Status": 0,
            "Answer": [{"type": 15, "data": "10 mail.cached-corp.com."}]
        }

        with patch("requests.get", return_value=mock_resp) as mock_doh:
            with patch.object(EmailValidatorAgent, "_check_website", return_value={"is_active": False}):
                target1 = EmailValidatorAgent.validate_with_domain_intelligence("alice@cached-corp.com")
                target2 = EmailValidatorAgent.validate_with_domain_intelligence("bob@cached-corp.com")

            assert target1.domain == "cached-corp.com"
            assert target2.domain == "cached-corp.com"
            # Second call must hit the cache without calling requests.get again
            assert mock_doh.call_count == 1
