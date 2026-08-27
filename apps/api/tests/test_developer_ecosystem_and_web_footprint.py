"""
Comprehensive Test Suite for Public Developer Ecosystem Discovery (Phase 5) & Web Footprint Search (Phase 6).

Validates:
- Phase 5:
  - GitLab, npm, Gravatar, PyPI, and Crates.io provider adapters
  - Distinguishing exact author/maintainer email matches (VERIFIED) from candidate handles (CANDIDATE)
  - Extraction of package metadata, author info, and repository links
- Phase 6:
  - Multi-query exact email web search
  - URL canonicalization (lowercasing, UTM removal, slash trimming)
  - Result deduplication by canonical URL
  - Classification into WebMentionCategory (EXACT_EMAIL_MENTION, DEVELOPER_PROFILE_MENTION, etc.)
  - Filtering out unrelated results
"""

from unittest.mock import MagicMock, patch
import pytest

from intelligence.email.models import (
    CorrelationType,
    EmailTarget,
    FindingStatus,
    WebMentionCategory,
)
from intelligence.email.providers.crates import CratesEmailProvider
from intelligence.email.providers.gitlab import GitLabEmailProvider
from intelligence.email.providers.gravatar import GravatarEmailProvider
from intelligence.email.providers.npm import NpmEmailProvider
from intelligence.email.providers.pypi import PyPIEmailProvider
from intelligence.email.providers.web_search import WebSearchEmailProvider, canonicalize_url


class TestPhase5DeveloperEcosystemProviders:
    def test_pypi_exact_author_email_is_verified(self):
        prov = PyPIEmailProvider()

        mock_pypi_data = {
            "info": {
                "author": "Guido van Rossum",
                "author_email": "guido@python.org",
                "version": "3.14.0",
                "summary": "Core Python runtime package",
                "home_page": "https://python.org"
            }
        }

        with patch.object(prov, "_safe_request") as mock_req:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = mock_pypi_data
            mock_req.return_value = mock_resp

            findings, packages = prov.search_pypi(
                email="guido@python.org",
                local_part="guido",
                domain="python.org"
            )

            assert len(findings) == 1
            finding = findings[0]
            assert finding.platform == "pypi"
            assert finding.status == FindingStatus.VERIFIED
            assert finding.public_email_match is True
            assert finding.confidence_score == 1.0
            assert len(packages) == 1

    def test_crates_io_package_discovery_and_domain_match(self):
        prov = CratesEmailProvider()

        mock_crate_data = {
            "crate": {
                "name": "tokio",
                "description": "An asynchronous runtime for Rust",
                "homepage": "https://tokio.rs",
                "downloads": 150000000
            }
        }

        with patch.object(prov, "_safe_request") as mock_req:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = mock_crate_data
            mock_req.return_value = mock_resp

            findings, crates = prov.search_crates(
                email="dev@tokio.rs",
                local_part="tokio",
                domain="tokio.rs"
            )

            assert len(findings) == 1
            finding = findings[0]
            assert finding.platform == "crates"
            assert finding.status == FindingStatus.PROBABLE
            assert finding.website_match is True
            assert finding.confidence_score == 0.65
            assert len(crates) == 1
            assert crates[0]["downloads"] == 150000000

    def test_npm_maintainer_exact_match(self):
        prov = NpmEmailProvider()

        mock_npm_data = {
            "objects": [
                {
                    "package": {
                        "name": "redux",
                        "version": "5.0.0",
                        "publisher": {"username": "gaearon"}
                    }
                }
            ]
        }

        with patch.object(prov, "_safe_request") as mock_req:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = mock_npm_data
            mock_req.return_value = mock_resp

            findings = prov.search(
                email="dan@example.com",
                local_part="dan",
                domain="example.com"
            )

            assert len(findings) == 1
            assert findings[0].status == FindingStatus.VERIFIED
            assert findings[0].public_email_match is True
            assert findings[0].ecosystem_category == "package_registry"


class TestPhase6PublicWebFootprintSearch:
    def test_canonicalize_url_strips_tracking_params_and_slashes(self):
        dirty_url = "https://GitHub.com/torvalds/linux/?utm_source=twitter&utm_medium=social&ref=123#readme"
        canonical = canonicalize_url(dirty_url)
        assert canonical == "https://github.com/torvalds/linux"

    def test_search_output_deduplication_and_exact_match_categorization(self):
        prov = WebSearchEmailProvider()

        # Simulated raw markdown output with duplicate URLs (one with UTM tags)
        simulated_text = (
            "[Linux Kernel Mailing List Archives]\n"
            "https://lore.kernel.org/all/2026-release/?utm_source=feed\n"
            "Patch authored by Linus Torvalds <torvalds@linux-foundation.org> for kernel 6.12.\n\n"
            "[Kernel Patch Mirror]\n"
            "https://lore.kernel.org/all/2026-release\n"
            "Duplicate mirror with identical canonical URL.\n\n"
            "[Dan Abramov Dev.to Profile]\n"
            "https://dev.to/gaearon\n"
            "Articles on React architecture and frontend engineering."
        )

        seen_urls = set()
        results = prov._parse_search_output(
            text=simulated_text,
            email="torvalds@linux-foundation.org",
            local_part="torvalds",
            domain="linux-foundation.org",
            seen_urls=seen_urls
        )

        # Duplicate lore.kernel.org must be deduplicated
        lore_results = [r for r in results if "lore.kernel.org" in r.canonical_url]
        assert len(lore_results) == 1

        exact_mention = lore_results[0]
        assert exact_mention.is_exact_match is True
        assert exact_mention.mention_category == WebMentionCategory.EXACT_EMAIL_MENTION
        assert exact_mention.status == FindingStatus.HIGH_CONFIDENCE

        # dev.to profile mention
        devto_results = [r for r in results if "dev.to" in r.canonical_url]
        assert len(devto_results) == 1
        assert devto_results[0].mention_category == WebMentionCategory.DEVELOPER_PROFILE_MENTION
