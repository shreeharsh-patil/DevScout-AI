import pytest
from agents.email_osint import (
    validate_email,
    EmailOSINT,
    CONFIDENCE_VERIFIED,
    CONFIDENCE_PROBABLE,
    CONFIDENCE_CANDIDATE,
    CONFIDENCE_NO_EVIDENCE,
)
from agents.analyzer import AnalyzerAgent
from agents.reporter import ReporterAgent


class TestEmailValidation:
    """Test strict email syntax and format validation."""

    def test_valid_emails(self):
        valid_cases = [
            "alice@example.com",
            "john.doe@company.co.uk",
            "developer+test@domain.org",
            "first_last@tech.io",
            "user-name@sub.domain.com",
        ]
        for email in valid_cases:
            is_valid, err = validate_email(email)
            assert is_valid is True, f"Expected '{email}' to be valid, but got error: {err}"
            assert err == ""

    def test_malformed_emails_rejected(self):
        invalid_cases = [
            "",
            "   ",
            "not-an-email",
            "missing-domain@",
            "@missing-local.com",
            "spaces in@email.com",
            "double..dot@domain.com",
            "user@domain..com",
            "user@no-tld",
            "a" * 255 + "@domain.com",  # Exceeds max length
        ]
        for email in invalid_cases:
            is_valid, err = validate_email(email)
            assert is_valid is False, f"Expected '{email}' to be rejected as invalid."
            assert len(err) > 0


class TestOSINTConfidenceModel:
    """Test evidence-based confidence categorization and candidate separation."""

    def test_malformed_email_pipeline_response(self):
        engine = EmailOSINT()
        result = engine.run_all("not-a-valid-email")
        assert result["status"] == "invalid_email"
        assert result["confidence_category"] == CONFIDENCE_NO_EVIDENCE
        assert result["profile_completeness"]["score"] == 0
        assert result["profile_completeness"]["categorization"] == "none"

    def test_candidate_guess_does_not_inflate_verified_score(self):
        """
        Critical safety test: A guessed username from email prefix with no email match
        MUST be classified as candidate, is_confirmed=False, and NOT increase verified signal count.
        """
        engine = EmailOSINT()
        
        # Mock data with only a candidate username guess
        data = {
            "gravatar": {"has_profile": False, "confidence_category": CONFIDENCE_NO_EVIDENCE},
            "whois": {"has_data": False, "confidence_category": CONFIDENCE_NO_EVIDENCE},
            "breaches": [],
            "web_mentions": [],
            "social_profiles": [],
            "news_mentions": [],
            "pgp_keys": {"found": False, "confidence_category": CONFIDENCE_NO_EVIDENCE},
            "pastebin": [],
            "github": {
                "accounts_found": 1,
                "confirmed_accounts": [],
                "candidate_accounts": [
                    {
                        "login": "johndoe",
                        "strategy": "username_guess_unverified",
                        "confidence_category": CONFIDENCE_CANDIDATE,
                        "is_confirmed": False,
                        "evidence": "Handle 'johndoe' matches email prefix, but no cryptographic or email link was verified."
                    }
                ],
                "confidence_category": CONFIDENCE_CANDIDATE
            }
        }
        
        completeness = engine._compute_completeness(data)
        assert completeness["score"] == 0, "Candidate guesses must not inflate the verified completeness score"
        assert completeness["signals_found"] == 0
        assert completeness["confidence_category"] == CONFIDENCE_CANDIDATE
        assert "candidate_github_guess" in completeness["candidate_signals"]
        assert "github_presence" not in completeness["verified_signals"]

    def test_verified_commit_match_classified_correctly(self):
        """A public commit with exact author email must be classified as verified."""
        engine = EmailOSINT()
        
        data = {
            "gravatar": {
                "has_profile": True,
                "confidence_category": CONFIDENCE_VERIFIED,
                "evidence": "Cryptographic MD5 hash match."
            },
            "whois": {"has_data": False, "confidence_category": CONFIDENCE_NO_EVIDENCE},
            "breaches": [
                {
                    "name": "Test Breach",
                    "confidence_category": CONFIDENCE_VERIFIED,
                    "evidence": "Verified breach dump"
                }
            ],
            "web_mentions": [],
            "social_profiles": [],
            "news_mentions": [],
            "pgp_keys": {"found": False, "confidence_category": CONFIDENCE_NO_EVIDENCE},
            "pastebin": [],
            "github": {
                "accounts_found": 1,
                "confirmed_accounts": [
                    {
                        "login": "dev_alice",
                        "strategy": "commit_search",
                        "confidence_category": CONFIDENCE_VERIFIED,
                        "is_confirmed": True,
                        "evidence": "Commit author email matches query."
                    }
                ],
                "candidate_accounts": [],
                "confidence_category": CONFIDENCE_VERIFIED
            }
        }
        
        completeness = engine._compute_completeness(data)
        assert completeness["score"] > 0
        assert completeness["signals_found"] == 3  # Gravatar + Breaches + GitHub
        assert completeness["confidence_category"] == CONFIDENCE_VERIFIED
        assert "github_presence" in completeness["verified_signals"]
        assert "gravatar_profile" in completeness["verified_signals"]
        assert "breach_records" in completeness["verified_signals"]

    def test_analyzer_separates_confirmed_and_candidate(self):
        analyzer = AnalyzerAgent()
        analyzer.use_llm = False
        
        # Test analyzer output structure
        email_data = {
            "email": "user@example.com",
            "domain": "example.com",
            "local_part": "user",
            "status": "valid",
            "gravatar": {"has_profile": True, "display_name": "Alice Developer", "confidence_category": "verified"},
            "whois": {"has_data": False},
            "breaches": [],
            "web_mentions": [],
            "social_profiles": [],
            "news_mentions": [],
            "pgp_keys": {"found": False},
            "pastebin": [],
            "github": {
                "accounts_found": 2,
                "confirmed_accounts": [
                    {
                        "login": "alice_verified",
                        "confidence_category": "verified",
                        "is_confirmed": True,
                        "evidence": "Commit author email matches."
                    }
                ],
                "candidate_accounts": [
                    {
                        "login": "alice_guess",
                        "confidence_category": "candidate",
                        "is_confirmed": False,
                        "evidence": "Prefix match only."
                    }
                ],
                "accounts": [
                    {"login": "alice_verified", "confidence_category": "verified", "is_confirmed": True},
                    {"login": "alice_guess", "confidence_category": "candidate", "is_confirmed": False}
                ]
            },
            "data_enrichment": {"possible_name": "Alice Developer"},
            "profile_completeness": {
                "score": 25,
                "categorization": "medium",
                "confidence_category": "verified",
                "verified_signals": ["gravatar_profile", "github_presence"],
                "candidate_signals": ["candidate_github_guess"]
            }
        }
        
        analysis = analyzer.analyze_email(email_data)
        assert analysis["confidence_category"] == "verified"
        assert len(analysis["confirmed_accounts"]) == 1
        assert len(analysis["candidate_accounts"]) == 1
        assert analysis["confirmed_accounts"][0]["login"] == "alice_verified"
        assert analysis["candidate_accounts"][0]["login"] == "alice_guess"

    def test_reporter_renders_confidence_badges_and_sections(self):
        reporter = ReporterAgent()
        
        analysis = {
            "email": "user@example.com",
            "domain": "example.com",
            "status": "valid",
            "possible_name": "Alice Dev",
            "confidence_score": 25,
            "categorization": "medium",
            "confidence_category": "verified",
            "signals_found": ["gravatar_profile", "github_presence"],
            "summary": "Verified identity profile found.",
            "gravatar": {"has_profile": True, "display_name": "Alice Dev", "evidence": "MD5 hash match"},
            "whois": {"has_data": False},
            "breaches": [],
            "social_profiles": [],
            "confirmed_accounts": [
                {
                    "login": "alice_verified",
                    "confidence_category": "verified",
                    "evidence": "Commit author email matches user@example.com",
                    "profile_url": "https://github.com/alice_verified"
                }
            ],
            "candidate_accounts": [
                {
                    "login": "alice_guess",
                    "confidence_category": "candidate",
                    "evidence": "Inferred from prefix; no email match verified",
                    "profile_url": "https://github.com/alice_guess"
                }
            ],
            "github_accounts": [],
            "web_mentions": []
        }
        
        md = reporter.generate_markdown_report(analysis, "email")
        assert "[VERIFIED]" in md
        assert "Confirmed Accounts & Profiles" in md
        assert "Candidate Leads & Inferred Handles (Unverified)" in md
        assert "alice_verified" in md
        assert "alice_guess" in md
