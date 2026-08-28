"""
Public Web Footprint Discovery Provider Plugin (Phase 6).

Executes targeted search queries for exact email occurrences, canonicalizes and deduplicates URLs,
and classifies results into structured categories (exact mention, developer profile, doc, forum, etc.).
"""

from __future__ import annotations

import re
from typing import List, Set
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse
from loguru import logger
import requests
from ..models import (
    CorrelationType,
    EmailTarget,
    Evidence,
    FindingStatus,
    ProviderResult,
    WebMention,
    WebMentionCategory,
    utc_now_iso,
)
from .base import BaseEmailProvider


TRACKING_PARAMS = {"utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content", "ref", "fbclid", "gclid"}


def canonicalize_url(url: str) -> str:
    """Normalizes URL by lowercasing host, removing tracking parameters, and stripping trailing slashes."""
    try:
        parsed = urlparse(url)
        scheme = parsed.scheme.lower() or "https"
        netloc = parsed.netloc.lower()
        path = parsed.path.rstrip("/") if parsed.path != "/" else "/"

        # Filter out tracking query parameters
        query_dict = parse_qs(parsed.query)
        filtered_query = {k: v for k, v in query_dict.items() if k.lower() not in TRACKING_PARAMS}
        new_query = urlencode(filtered_query, doseq=True)

        return urlunparse((scheme, netloc, path, "", new_query, ""))
    except Exception:
        return url.strip().rstrip("/")


class WebSearchEmailProvider(BaseEmailProvider):
    provider_name: str = "web_search"

    def __init__(self, timeout: float = 18.0, max_retries: int = 2):
        super().__init__(timeout=timeout, max_retries=max_retries)

    def is_available(self) -> bool:
        return True

    def lookup(self, target: EmailTarget) -> ProviderResult:
        email = target.normalized_email or target.raw_email
        local_part = target.local_part
        domain = target.domain

        mentions = self.search_mentions(email=email, local_part=local_part, domain=domain)

        all_evidence: List[Evidence] = []
        for m in mentions:
            all_evidence.append(
                Evidence(
                    evidence_id=m.source_id or f"web_{m.domain}",
                    provider="web_search",
                    source_type="search_index",
                    title=m.title,
                    url=m.canonical_url or m.url,
                    retrieved_at=m.retrieved_at,
                    supports="web_mentions",
                    strength="strong" if m.is_exact_match else "moderate",
                    snippet=m.snippet,
                    metadata={"category": m.mention_category.value, "domain": m.domain}
                )
            )

        if mentions:
            top_status = (
                FindingStatus.HIGH_CONFIDENCE
                if any(m.is_exact_match for m in mentions)
                else FindingStatus.PROBABLE
            )
            top_score = 0.85 if top_status == FindingStatus.HIGH_CONFIDENCE else 0.50
        else:
            top_status = FindingStatus.NO_EVIDENCE
            top_score = 0.0

        return ProviderResult(
            provider=self.provider_name,
            finding_type="web_mention",
            status=top_status,
            confidence_level=top_status,
            confidence_score=top_score,
            evidence_ids=[e.evidence_id for e in all_evidence],
            evidence_items=all_evidence,
            findings=mentions,
            retrieved_at=utc_now_iso(),
            metadata={"web_mentions_count": len(mentions)}
        )

    def search_mentions(self, email: str, local_part: str = "", domain: str = "") -> List[WebMention]:
        findings: List[WebMention] = []
        seen_canonical_urls: Set[str] = set()

        # Multi-query search patterns
        queries = [
            f'"{email}"',
            f'site:github.com "{email}"',
            f'site:gitlab.com "{email}"',
            f'site:dev.to "{email}"',
        ]

        for query in queries[:2]:  # Execute high-yield exact queries
            try:
                url = f"https://s.jina.ai/{requests.utils.quote(query)}"
                resp = self._safe_request(url, timeout=self.timeout)
                if resp and resp.status_code == 200:
                    parsed = self._parse_search_output(
                        text=resp.text,
                        email=email,
                        local_part=local_part,
                        domain=domain,
                        seen_urls=seen_canonical_urls
                    )
                    findings.extend(parsed)
            except Exception as e:
                logger.debug(f"[WebSearchEmailProvider] Query '{query}' error: {e}")

        return findings[:12]

    def _parse_search_output(
        self,
        text: str,
        email: str,
        local_part: str,
        domain: str,
        seen_urls: Set[str]
    ) -> List[WebMention]:
        results: List[WebMention] = []
        if not text:
            return results

        blocks = text.split("\n\n")
        idx = len(seen_urls) + 1

        for block in blocks:
            urls = re.findall(r'https?://[^\s)\]"\'>]+', block)
            if not urls:
                continue

            raw_url = urls[0]
            canonical = canonicalize_url(raw_url)

            if canonical in seen_urls or "jina.ai" in canonical:
                continue

            seen_urls.add(canonical)

            lines = [line.strip() for line in block.split("\n") if line.strip()]
            title = lines[0].replace("[", "").replace("]", "") if lines else f"Web Mention {idx}"
            # Extract tight snippet
            snippet = " ".join(lines[1:3]) if len(lines) > 1 else block[:240]

            try:
                netloc = urlparse(canonical).netloc.lower()
            except Exception:
                netloc = "web"

            # Check exact email match
            is_exact = email.lower() in block.lower()

            # Classify mention category
            category = self._classify_category(canonical, netloc, title, block, is_exact, domain)

            # Skip clearly unrelated results
            if category == WebMentionCategory.UNRELATED_RESULT and not is_exact:
                continue

            status = FindingStatus.HIGH_CONFIDENCE if is_exact else FindingStatus.PROBABLE
            score = 0.85 if is_exact else 0.50
            corr_type = CorrelationType.EXACT_EMAIL_MENTION if is_exact else CorrelationType.NAME_CORRELATION

            src_id = f"web_mention_{idx}"
            finding = WebMention(
                provider="web_search",
                finding_type="web_mention",
                status=status,
                confidence_level=status,
                confidence_score=score,
                evidence_ids=[src_id],
                retrieved_at=utc_now_iso(),
                source_id=src_id,
                url=raw_url,
                canonical_url=canonical,
                title=title[:120],
                domain=netloc,
                snippet=snippet[:280],
                correlation_type=corr_type,
                mention_category=category,
                is_exact_match=is_exact,
                metadata={"domain": netloc, "canonical_url": canonical}
            )
            results.append(finding)
            idx += 1

        return results

    def _classify_category(
        self, url: str, domain: str, title: str, content: str, is_exact: bool, target_domain: str
    ) -> WebMentionCategory:
        d = domain.lower()
        if any(h in d for h in ["github.com", "gitlab.com", "dev.to", "medium.com", "hashnode.dev", "npm.im", "pypi.org"]):
            return WebMentionCategory.DEVELOPER_PROFILE_MENTION

        if any(h in d for h in ["stackoverflow.com", "stackexchange.com", "reddit.com", "groups.google.com", "discourse."]):
            return WebMentionCategory.FORUM_MENTION

        if any(h in d for h in ["docs.", "documentation", "rfc-editor.org", "w3.org", "ietf.org"]) or url.endswith(".pdf"):
            return WebMentionCategory.DOCUMENT_MENTION

        if target_domain and target_domain in d:
            return WebMentionCategory.ORGANIZATION_MENTION

        if is_exact:
            return WebMentionCategory.EXACT_EMAIL_MENTION

        return WebMentionCategory.UNRELATED_RESULT


# Backward-compatible alias
WebSearchProvider = WebSearchEmailProvider
