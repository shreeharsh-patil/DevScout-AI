"""
Public Web Mention Discovery Provider.

Searches public search indices for exact occurrences of the email address,
deduplicates results, and classifies correlation type (exact email mention vs name/handle correlation).
"""

from __future__ import annotations

import datetime
import re
from typing import List, Tuple
from urllib.parse import urlparse
from loguru import logger
import requests
from ..models import CorrelationType, WebMentionFinding
from .base import BaseProvider


def _utc_now_iso() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


class WebSearchProvider(BaseProvider):
    platform_name: str = "web"

    def search_mentions(self, email: str, local_part: str) -> List[WebMentionFinding]:
        findings: List[WebMentionFinding] = []
        seen_urls: set[str] = set()

        try:
            # 1. Exact string search
            query = f'"{email}"'
            url = f"https://s.jina.ai/{requests.utils.quote(query)}"
            resp = self._safe_request(url, timeout=20)
            if resp and resp.status_code == 200:
                findings.extend(self._parse_jina_output(resp.text, email, local_part, seen_urls))
        except Exception as e:
            logger.debug(f"[WebSearchProvider] Error during search: {e}")

        return findings[:10]  # Cap at top 10 deduplicated mentions

    def _parse_jina_output(
        self, text: str, email: str, local_part: str, seen_urls: set[str]
    ) -> List[WebMentionFinding]:
        results: List[WebMentionFinding] = []
        if not text:
            return results

        # Jina returns markdown with [Title](URL) or Title: ... URL: ...
        # Match URL citations
        blocks = text.split("\n\n")
        idx = 1
        for block in blocks:
            urls = re.findall(r'https?://[^\s)\]"\'>]+', block)
            if not urls:
                continue

            target_url = urls[0]
            clean_url = target_url.rstrip("/")
            if clean_url in seen_urls or "jina.ai" in clean_url:
                continue

            seen_urls.add(clean_url)

            # Determine title & snippet
            lines = [l.strip() for l in block.split("\n") if l.strip()]
            title = lines[0].replace("[", "").replace("]", "") if lines else f"Web Mention {idx}"
            snippet = " ".join(lines[1:3]) if len(lines) > 1 else block[:200]

            # Classify correlation type
            if email.lower() in block.lower():
                corr_type = CorrelationType.EXACT_EMAIL_MENTION
            elif local_part.lower() in block.lower():
                corr_type = CorrelationType.USERNAME_CORRELATION
            else:
                corr_type = CorrelationType.NAME_CORRELATION

            try:
                domain = urlparse(clean_url).netloc
            except Exception:
                domain = "web"

            finding = WebMentionFinding(
                source_id=f"web_mention_{idx}",
                url=clean_url,
                title=title[:120],
                domain=domain,
                snippet=snippet[:250],
                correlation_type=corr_type,
                retrieved_at=_utc_now_iso()
            )
            results.append(finding)
            idx += 1

        return results

    def search(self, email: str, local_part: str, domain: str):
        # Implements BaseProvider search contract
        return []
