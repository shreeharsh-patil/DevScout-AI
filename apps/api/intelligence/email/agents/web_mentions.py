"""
Web Mention Discovery & Correlation Agent.

Discovers public web occurrences of the target email and filters them by correlation strength.
"""

from __future__ import annotations

from typing import List
from ..models import WebMentionFinding
from ..providers.web import WebSearchProvider


class WebMentionAgent:
    """Discovers and categorizes public web mentions."""

    def __init__(self):
        self.provider = WebSearchProvider()

    def discover_mentions(self, email: str, local_part: str) -> List[WebMentionFinding]:
        return self.provider.search_mentions(email, local_part)
