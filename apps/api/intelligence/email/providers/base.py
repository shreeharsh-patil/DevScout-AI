"""
Base Provider Adapter for Email Intelligence.

Provides common HTTP request wrapping, exponential backoff, rate-limit detection,
and structured error isolation.
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple
from loguru import logger
import requests
import http_client
from ..models import AccountFinding


class BaseProvider(ABC):
    """Abstract base class for all account and footprint discovery providers."""

    platform_name: str = "base"

    def __init__(self, timeout: int = 15, max_retries: int = 2):
        self.timeout = timeout
        self.max_retries = max_retries
        self._cache: Dict[str, Tuple[float, Any]] = {}

    def _safe_request(
        self,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        method: str = "GET",
        json_body: Optional[Dict[str, Any]] = None,
        timeout: Optional[int] = None,
    ) -> Optional[requests.Response]:
        """
        Executes HTTP request with rate-limit and transient error backoff.
        Guarantees provider failure never crashes caller.
        """
        req_timeout = timeout or self.timeout
        for attempt in range(self.max_retries + 1):
            try:
                if method.upper() == "GET":
                    resp = http_client.get(url, headers=headers, timeout=req_timeout)
                else:
                    resp = requests.request(method, url, headers=headers, json=json_body, timeout=req_timeout)

                if resp.status_code == 429:
                    logger.warning(f"[{self.platform_name}] Rate limit hit on {url} (HTTP 429).")
                    if attempt < self.max_retries:
                        time.sleep(1.5 * (attempt + 1))
                        continue
                    return resp

                if resp.status_code >= 500 and attempt < self.max_retries:
                    time.sleep(1.0 * (attempt + 1))
                    continue

                return resp
            except (requests.RequestException, Exception) as e:
                logger.debug(f"[{self.platform_name}] Request error on {url} (attempt {attempt+1}/{self.max_retries+1}): {e}")
                if attempt < self.max_retries:
                    time.sleep(1.0 * (attempt + 1))
                else:
                    return None
        return None

    @abstractmethod
    def search(self, email: str, local_part: str, domain: str) -> List[AccountFinding]:
        """Discovers accounts and public presence for given email target."""
        pass
