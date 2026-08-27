"""
DevScout AI – Normalized Source System.

Provides structured source tracking, deduplication, and provenance verification across
all research and analysis agents. Every finding can be mapped back to an exact retrieved source.
"""

from __future__ import annotations

import datetime
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse


def _utc_now_iso() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


class SourceCollector:
    """
    Collects, deduplicates, and formats retrieved research sources.
    Assigns sequential 1-based source IDs (e.g. '1', '2' or 'src_1', 'src_2').
    """

    def __init__(self):
        self._sources: List[Dict[str, Any]] = []
        self._url_to_index: Dict[str, int] = {}

    def add_source(
        self,
        title: str,
        url: str,
        platform: str,
        source_type: str,
        snippet: str = "",
        metadata: Optional[Dict[str, Any]] = None,
        retrieved_at: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Adds a retrieved source. If the URL already exists, returns the existing source.
        """
        clean_url = (url or "").strip().rstrip("/")
        dedup_key = clean_url.lower() if clean_url else title.strip().lower()

        if dedup_key in self._url_to_index:

            idx = self._url_to_index[dedup_key]
            # If new snippet provided and existing is empty, enrich it
            if snippet and not self._sources[idx].get("snippet"):
                self._sources[idx]["snippet"] = snippet[:500]
            return self._sources[idx]

        idx = len(self._sources) + 1
        source_id = str(idx)

        # Detect platform from URL if not specified
        if not platform or platform == "web":
            if "github.com" in clean_url or "api.github.com" in clean_url:
                platform = "github"
            elif "npmjs.com" in clean_url or "registry.npmjs.org" in clean_url:
                platform = "npm"
            elif "youtube.com" in clean_url or "youtu.be" in clean_url:
                platform = "youtube"
            elif "reddit.com" in clean_url:
                platform = "reddit"
            elif "news.ycombinator.com" in clean_url or "algolia.com" in clean_url:
                platform = "hackernews"
            elif "linkedin.com" in clean_url:
                platform = "linkedin"
            elif "gravatar.com" in clean_url:
                platform = "gravatar"
            elif "rdap." in clean_url or "whois" in clean_url:
                platform = "whois"
            else:
                platform = "web"

        source: Dict[str, Any] = {
            "source_id": source_id,
            "title": title.strip() or f"Source {source_id}",
            "url": clean_url,
            "platform": platform.lower(),
            "source_type": source_type.lower(),
            "retrieved_at": retrieved_at or _utc_now_iso(),
            "snippet": snippet[:500] if snippet else "",
            "metadata": metadata or {},
        }

        self._sources.append(source)
        self._url_to_index[dedup_key] = idx - 1
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
                    retrieved_at=s.get("retrieved_at")
                )

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
                # Clean display domain
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
