"""
DevScout AI – Normalized Source System.

Provides structured source tracking, deduplication, URL canonicalization, and
provenance verification across all research and analysis agents. Every finding
can be mapped back to an exact retrieved source.
"""

from __future__ import annotations

import datetime
from typing import Any, Dict, List, Optional
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

TRACKING_PARAMS = frozenset({
    "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
    "ref", "ref_src", "fbclid", "gclid", "_hsenc", "_hsmi", "mc_cid", "mc_eid",
    "igshid", "yclid", "wbraid", "gbraid", "si"
})


def _utc_now_iso() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def canonicalize_url(url: str) -> str:
    """
    Canonicalizes and normalizes URLs:
    - Lowercases scheme and hostname.
    - Strips fragment identifiers (#...).
    - Removes known analytics and tracking query parameters (utm_*, fbclid, gclid, etc.).
    - Preserves and deterministically sorts meaningful query parameters.
    - Normalizes equivalent GitHub/GitLab repository URLs (strips .git, trailing slashes).
    """
    if not url or not isinstance(url, str):
        return ""

    raw = url.strip()
    if not raw.startswith("http://") and not raw.startswith("https://"):
        return raw.rstrip("/")

    try:
        parsed = urlparse(raw)
        scheme = parsed.scheme.lower() or "https"
        netloc = parsed.netloc.lower()

        # Remove default ports (80 for http, 443 for https)
        if ":80" in netloc and scheme == "http":
            netloc = netloc.replace(":80", "")
        elif ":443" in netloc and scheme == "https":
            netloc = netloc.replace(":443", "")

        path = parsed.path
        if path.endswith("/") and len(path) > 1:
            path = path.rstrip("/")

        # Normalize GitHub repository paths
        if "github.com" in netloc or "gitlab.com" in netloc:
            if path.endswith(".git"):
                path = path[:-4]

        # Filter out tracking query parameters and sort remaining deterministically
        query_dict = parse_qs(parsed.query, keep_blank_values=False)
        filtered_query = {
            k: v for k, v in query_dict.items()
            if k.lower() not in TRACKING_PARAMS
        }
        sorted_query_tuples = sorted(filtered_query.items(), key=lambda x: x[0])
        new_query = urlencode(sorted_query_tuples, doseq=True)

        return urlunparse((scheme, netloc, path, "", new_query, ""))
    except Exception:
        return raw.rstrip("/")


class SourceCollector:
    """
    Collects, deduplicates, and formats retrieved research sources.
    Assigns sequential or explicit canonical source IDs and guarantees
    1-to-1 evidence mapping.
    """

    def __init__(self):
        self._sources: List[Dict[str, Any]] = []
        self._url_to_index: Dict[str, int] = {}
        self._id_to_source: Dict[str, Dict[str, Any]] = {}

    def add_source(
        self,
        title: str,
        url: str,
        platform: str,
        source_type: str,
        snippet: str = "",
        metadata: Optional[Dict[str, Any]] = None,
        retrieved_at: Optional[str] = None,
        source_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Adds a retrieved source. If the canonical URL already exists, returns the existing source,
        merging any richer snippet or metadata.
        """
        clean_url = canonicalize_url(url) if url else ""
        dedup_key = clean_url.lower() if clean_url else title.strip().lower()

        if dedup_key and dedup_key in self._url_to_index:
            idx = self._url_to_index[dedup_key]
            existing = self._sources[idx]
            # Enrich snippet if new one is present
            if snippet:
                if not existing.get("snippet"):
                    existing["snippet"] = snippet[:500]
                elif snippet not in existing["snippet"] and len(existing["snippet"]) < 400:
                    existing["snippet"] = f"{existing['snippet']}; {snippet}"[:500]
            # Merge metadata
            if metadata:
                merged_meta = dict(existing.get("metadata") or {})
                merged_meta.update(metadata)
                existing["metadata"] = merged_meta
            # Map alias ID if caller provided a new source_id
            if source_id and source_id not in self._id_to_source:
                self._id_to_source[source_id] = existing
            return existing

        idx = len(self._sources) + 1
        canonical_id = str(source_id) if source_id else str(idx)

        # Detect platform from URL if not specified
        if not platform or platform == "web":
            low_url = clean_url.lower()
            if "github.com" in low_url or "api.github.com" in low_url:
                platform = "github"
            elif "npmjs.com" in low_url or "registry.npmjs.org" in low_url:
                platform = "npm"
            elif "gitlab.com" in low_url:
                platform = "gitlab"
            elif "pypi.org" in low_url or "pypi.python.org" in low_url:
                platform = "pypi"
            elif "crates.io" in low_url:
                platform = "crates"
            elif "youtube.com" in low_url or "youtu.be" in low_url:
                platform = "youtube"
            elif "reddit.com" in low_url:
                platform = "reddit"
            elif "news.ycombinator.com" in low_url or "algolia.com" in low_url:
                platform = "hackernews"
            elif "linkedin.com" in low_url:
                platform = "linkedin"
            elif "gravatar.com" in low_url:
                platform = "gravatar"
            elif "rdap." in low_url or "whois" in low_url:
                platform = "whois"
            elif "haveibeenpwned.com" in low_url:
                platform = "hibp"
            else:
                platform = "web"

        source: Dict[str, Any] = {
            "source_id": canonical_id,
            "title": title.strip() or f"Source {canonical_id}",
            "url": clean_url,
            "platform": platform.lower(),
            "source_type": source_type.lower(),
            "retrieved_at": retrieved_at or _utc_now_iso(),
            "snippet": snippet[:500] if snippet else "",
            "metadata": metadata or {},
        }

        self._sources.append(source)
        if dedup_key:
            self._url_to_index[dedup_key] = len(self._sources) - 1
        self._id_to_source[canonical_id] = source
        return source

    def extend(self, other_sources: List[Dict[str, Any]]) -> None:
        """Merges a list of existing source dictionaries."""
        for s in other_sources:
            if isinstance(s, dict):
                self.add_source(
                    title=s.get("title", ""),
                    url=s.get("url", ""),
                    platform=s.get("platform", "web"),
                    source_type=s.get("source_type", "web_page"),
                    snippet=s.get("snippet", ""),
                    metadata=s.get("metadata"),
                    retrieved_at=s.get("retrieved_at"),
                    source_id=s.get("source_id")
                )

    def get_source_by_id(self, source_id: str) -> Optional[Dict[str, Any]]:
        """Finds a source by canonical ID or alias."""
        return self._id_to_source.get(str(source_id))

    def get_sources(self) -> List[Dict[str, Any]]:
        """Returns all collected, deduplicated sources."""
        return list(self._sources)

    def format_sources_for_prompt(self, max_sources: int = 15) -> str:
        """
        Formats sources into a prompt context block for the LLM to cite via [1], [2], etc.
        """
        if not self._sources:
            return "No verified sources available."

        lines = []
        for s in self._sources[:max_sources]:
            sid = s["source_id"]
            title = s["title"]
            url = s["url"]
            snippet = s.get("snippet", "")
            line = f"[{sid}] {title}"
            if url:
                line += f" ({url})"
            if snippet:
                line += f" — Snippet: {snippet[:150]}"
            lines.append(line)

        return "\n".join(lines)

    def format_markdown_sources_section(self) -> str:
        """
        Generates a clean, clickable 'Sources & Verification' section for the markdown report.
        """
        if not self._sources:
            return ""

        lines = [
            "---",
            "",
            "## 📚 Sources & Verification",
            "",
            "The findings in this report are grounded in the following retrieved sources:",
            "",
            "| # | Source Title | Platform | Type | Verified Link |",
            "| :--- | :--- | :--- | :--- | :--- |"
        ]

        for s in self._sources:
            sid = s["source_id"]
            title = s["title"].replace("|", "/")
            platform = s["platform"]
            stype = s["source_type"].replace("_", " ").title()
            url = s["url"]

            if url and url.startswith("http"):
                try:
                    parsed = urlparse(url)
                    disp_link = f"[{parsed.netloc}{parsed.path[:20]}...]({url})" if len(parsed.path) > 20 else f"[{parsed.netloc}{parsed.path}]({url})"
                except Exception:
                    disp_link = f"[Link]({url})"
            elif url:
                disp_link = url
            else:
                disp_link = "*Internal Telemetry*"

            lines.append(f"| **[{sid}]** | **{title}** | `{platform}` | {stype} | {disp_link} |")

        # Add expandable snippets if available
        has_snippets = any(bool(s.get("snippet")) for s in self._sources)
        if has_snippets:
            lines.extend([
                "",
                "### 🔍 Source Snippets & Evidence",
                ""
            ])
            for s in self._sources:
                if s.get("snippet"):
                    lines.append(f"- **[{s['source_id']}] {s['title']}**: `{s['snippet'][:250]}...`")

        return "\n".join(lines)
