"""
Breach Exposure Assessment Agent.

Queries security disclosures and returns public breach event information
with STRICT ZERO-CREDENTIAL exposure guarantees.
"""

from __future__ import annotations

from typing import List, Tuple
from ..models import BreachFinding
from ..providers.hibp import HIBPProvider


class BreachExposureAgent:
    """Audits public breach events associated with the target email."""

    def __init__(self):
        self.provider = HIBPProvider()

    def check_exposure(self, email: str) -> Tuple[List[BreachFinding], str]:
        return self.provider.check_breaches(email)
