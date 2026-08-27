"""
Public Web Mention Discovery Provider.

Searches public search indices for exact occurrences of the email address,
deduplicates results, and classifies correlation type (exact email mention vs name/handle correlation).
"""

from __future__ import annotations

import re
from typing import List
from urllib.parse import urlparse
from loguru import logger
import requests
from ..models import CorrelationType, FindingStatus, WebMention, utc_now_iso
from .base import BaseProvider


class WebSearchProvider(BaseProvider):
    platform_name: str = "web"

    def search_mentions(self, email: str, local_part: str) -> List[WebMention]:
        findings: List[WebMention] = []
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

        return findings[:10]

    def _parse_jina_output(
        self, text: str, email: str, local_part: str, seen_urls: set[str]
    ) -> List[WebMention]:
        results: List[WebMention] = []
        if not text:
            return results

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

            lines = [line.strip() for line in block.split("\n") if line.strip()]
            title = lines[0].replace("[", "").replace("]", "") if lines else f"Web Mention {idx}"
            snippet = " ".join(lines[1:3]) if len(lines) > 1 else block[:200]

            if email.lower() in block.lower():
                corr_type = CorrelationType.EXACT_EMAIL_MENTION
                status = FindingStatus.HIGH_CONFIDENCE
                score = 0.85
            elif local_part.lower() in block.lower():
                corr_type = CorrelationType.USERNAME_CORRELATION
                status = FindingStatus.CANDIDATE
                score = 0.35
            else:
                corr_type = CorrelationType.NAME_CORRELATION
                status = FindingStatus.PROBABLE
                score = 0.50

            try:
                domain = urlparse(clean_url).netloc
            except Exception:
                domain = "web"

            src_id = f"web_mention_{idx}"
            finding = WebMention(
                provider="web",
                finding_type="web_mention",
                status=status,
                confidence_level=status,
                confidence_score=score,
                evidence_ids=[src_id],
                retrieved_at=utc_now_iso(),
                source_id=src_id,
                url=clean_url,
                title=title[:120],
                domain=domain,
                snippet=snippet[:250],
                correlation_type=corr_type,
                metadata={"domain": domain}
            )
            results.append(finding)
            idx += 1

        return results

    def search(self, email: str, local_part: str, domain: str):
        return []
