"""
Gravatar Agent for Email Intelligence.

Wraps Gravatar lookup and provides structured avatar/profile signals.
"""

from __future__ import annotations

from typing import List, Optional
from ..models import AccountFinding
from ..providers.gravatar import GravatarProvider


class GravatarAgent:
    """Discovers and extracts public Gravatar profile signals."""

    def __init__(self):
        self.provider = GravatarProvider()

    def lookup(self, email: str, local_part: str, domain: str) -> List[AccountFinding]:
        return self.provider.search(email, local_part, domain)
