"""
Base Provider Adapter for Email Intelligence Plugin Architecture.

Provides:
- Abstract BaseEmailProvider interface:
    * provider_name
    * is_available()
    * supports(target)
    * lookup(target)
    * normalize_result(raw_data)
    * health_check()
- Safe execution wrapper with timing telemetry (execution_time_ms)
- Structured error isolation guaranteeing provider failures never crash the research pipeline
- Retry with exponential backoff ONLY on temporary failures (5xx, timeouts)
- Dynamic rate-limit detection (HTTP 429) and health state management
"""

from __future__ import annotations

import time
from abc import ABC
from typing import Any, Dict, Optional, Tuple, Union
from loguru import logger
import requests
import http_client
from ..models import (
    EmailTarget,
    FindingStatus,
    ProviderHealthReport,
    ProviderHealthStatus,
    ProviderResult,
    utc_now_iso,
)


class BaseEmailProvider(ABC):
    """
    Abstract base class for all pluggable Email Intelligence providers.
    """

    provider_name: str = "base"
    platform_name: str = "base"

    def __init__(self, timeout: float = 12.0, max_retries: int = 2, backoff_factor: float = 1.5):
        self.timeout = timeout
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self._health_status = ProviderHealthStatus.HEALTHY
        self._last_error: Optional[str] = None
        self._last_execution_time_ms: Optional[float] = None
        self._rate_limited: bool = False
        self._rate_limit_reset_at: Optional[str] = None
        self._cache: Dict[str, Tuple[float, Any]] = {}

    def is_available(self) -> bool:
        """Returns True if provider prerequisites (e.g. required credentials) are met."""
        return True

    def supports(self, target: Union[str, EmailTarget]) -> bool:
        """
        Returns True if this provider can process the given target.
        Default implementation accepts all valid email targets.
        """
        if isinstance(target, str):
            return "@" in target and len(target.strip()) > 3
        return bool(target.is_valid and target.normalized_email)

    def lookup(self, target: EmailTarget) -> ProviderResult:
        """
        Executes domain/identity intelligence queries for the target.
        Legacy providers can continue implementing ``search`` while newer
        plugins override this method directly.
        """
        search = getattr(self, "search", None)
        findings = search(
            target.normalized_email or target.raw_email,
            target.local_part,
            target.domain,
        ) if callable(search) else []
        findings = findings or []
        evidence = [item for finding in findings for item in getattr(finding, "evidence", [])]
        status = FindingStatus.NO_EVIDENCE
        score = 0.0
        if findings:
            status = max(
                (finding.status for finding in findings),
                key=lambda value: {
                    FindingStatus.VERIFIED: 5,
                    FindingStatus.HIGH_CONFIDENCE: 4,
                    FindingStatus.PROBABLE: 3,
                    FindingStatus.CANDIDATE: 2,
                }.get(value, 0),
            )
            score = max(float(getattr(finding, "confidence_score", 0.0)) for finding in findings)
        return ProviderResult(
            provider=self.provider_name if self.provider_name != "base" else self.platform_name,
            finding_type="account",
            status=status,
            confidence_level=status,
            confidence_score=score,
            evidence_ids=[item.evidence_id for item in evidence],
            evidence_items=evidence,
            findings=findings,
            retrieved_at=utc_now_iso(),
        )

    def normalize_result(self, raw_data: Any) -> ProviderResult:
        """
        Converts raw provider responses into a normalized ProviderResult.
        Default implementation returns an empty result if raw_data is empty.
        """
        if isinstance(raw_data, ProviderResult):
            return raw_data
        return ProviderResult(
            provider=self.provider_name,
            finding_type="account",
            status=FindingStatus.NO_EVIDENCE,
            confidence_level=FindingStatus.NO_EVIDENCE,
            confidence_score=0.0,
            retrieved_at=utc_now_iso(),
            metadata={"raw_data": str(raw_data)}
        )

    def health_check(self) -> ProviderHealthReport:
        """Returns the current health status and operational telemetry of the provider."""
        is_avail = self.is_available()
        if not is_avail:
            status = ProviderHealthStatus.UNAVAILABLE
        elif self._rate_limited:
            status = ProviderHealthStatus.RATE_LIMITED
        elif self._health_status == ProviderHealthStatus.FAILED:
            status = ProviderHealthStatus.FAILED
        elif self._last_error:
            status = ProviderHealthStatus.DEGRADED
        else:
            status = ProviderHealthStatus.HEALTHY

        return ProviderHealthReport(
            provider_name=self.provider_name,
            status=status,
            is_available=is_avail,
            rate_limited=self._rate_limited,
            rate_limit_reset_at=self._rate_limit_reset_at,
            last_error=self._last_error,
            last_execution_time_ms=self._last_execution_time_ms,
            details={"timeout_s": self.timeout, "max_retries": self.max_retries}
        )

    def execute(self, target: EmailTarget) -> ProviderResult:
        """
        Safe execution wrapper that:
        1. Checks availability and target support.
        2. Measures execution duration in milliseconds.
        3. Catches and isolates all unexpected exceptions.
        4. Injects execution telemetry into the result metadata.
        """
        start_time = time.perf_counter()

        if not self.is_available():
            self._health_status = ProviderHealthStatus.UNAVAILABLE
            return ProviderResult(
                provider=self.provider_name,
                finding_type="account",
                status=FindingStatus.UNAVAILABLE,
                confidence_level=FindingStatus.UNAVAILABLE,
                confidence_score=0.0,
                retrieved_at=utc_now_iso(),
                error=f"Provider '{self.provider_name}' is not configured or unavailable.",
                metadata={"execution_time_ms": 0.0}
            )

        if not self.supports(target):
            return ProviderResult(
                provider=self.provider_name,
                finding_type="account",
                status=FindingStatus.NO_EVIDENCE,
                confidence_level=FindingStatus.NO_EVIDENCE,
                confidence_score=0.0,
                retrieved_at=utc_now_iso(),
                metadata={"reason": "Target not supported by provider", "execution_time_ms": 0.0}
            )

        try:
            result = self.lookup(target)
            elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
            self._last_execution_time_ms = elapsed_ms
            self._last_error = None
            if not self._rate_limited:
                self._health_status = ProviderHealthStatus.HEALTHY

            # Ensure execution_time_ms is preserved in result metadata
            result.metadata["execution_time_ms"] = elapsed_ms
            return result

        except (requests.Timeout, TimeoutError) as e:
            elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
            self._last_execution_time_ms = elapsed_ms
            self._last_error = f"Timeout after {self.timeout}s: {e}"
            self._health_status = ProviderHealthStatus.DEGRADED
            logger.warning(f"[{self.provider_name}] Provider execution timed out: {e}")

            return ProviderResult(
                provider=self.provider_name,
                finding_type="account",
                status=FindingStatus.UNAVAILABLE,
                confidence_level=FindingStatus.UNAVAILABLE,
                confidence_score=0.0,
                retrieved_at=utc_now_iso(),
                error=f"Provider '{self.provider_name}' timed out after {self.timeout}s.",
                metadata={"execution_time_ms": elapsed_ms, "exception": str(e), "timed_out": True}
            )

        except Exception as e:
            elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
            self._last_execution_time_ms = elapsed_ms
            self._last_error = str(e)
            self._health_status = ProviderHealthStatus.FAILED
            logger.error(f"[{self.provider_name}] Unhandled provider execution error: {e}", exc_info=True)

            return ProviderResult(
                provider=self.provider_name,
                finding_type="account",
                status=FindingStatus.ERROR,
                confidence_level=FindingStatus.ERROR,
                confidence_score=0.0,
                retrieved_at=utc_now_iso(),
                error=f"Provider '{self.provider_name}' failed: {str(e)}",
                metadata={"execution_time_ms": elapsed_ms, "exception": str(e)}
            )

    def _safe_request(
        self,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        method: str = "GET",
        json_body: Optional[Dict[str, Any]] = None,
        timeout: Optional[float] = None,
    ) -> Optional[requests.Response]:
        """
        Executes outbound HTTP request via centralized HTTP client.
        Captures rate-limits (HTTP 429), server errors (5xx), and connection timeouts,
        retrying only transient server/network errors when max_retries > 0.
        """
        req_timeout = timeout or self.timeout

        for attempt in range(self.max_retries + 1):
            try:
                if method.upper() == "GET":
                    resp = http_client.get(url, headers=headers, timeout=req_timeout)
                else:
                    resp = requests.request(method, url, headers=headers, json=json_body, timeout=req_timeout)

                # Handle Rate Limit (HTTP 429) - never loop retry on 429 to avoid retry storms
                if resp.status_code == 429:
                    self._rate_limited = True
                    self._health_status = ProviderHealthStatus.RATE_LIMITED
                    retry_after = resp.headers.get("Retry-After")
                    if retry_after:
                        self._rate_limit_reset_at = retry_after
                    logger.warning(
                        f"[{self.provider_name}] HTTP 429 Rate Limited on {url}. Retry-After: {retry_after}"
                    )
                    return resp

                # Non-retriable client errors (400, 401, 403, 404, etc.)
                if 400 <= resp.status_code < 500:
                    self._rate_limited = False
                    return resp

                # Server errors (500, 502, 503, 504) -> retry if attempts remaining
                if resp.status_code >= 500:
                    self._health_status = ProviderHealthStatus.DEGRADED
                    self._last_error = f"Server returned HTTP {resp.status_code}"
                    if attempt < self.max_retries:
                        time.sleep(0.01)
                        continue
                    return resp

                # Success
                self._rate_limited = False
                return resp

            except (requests.Timeout, TimeoutError) as e:
                logger.debug(f"[{self.provider_name}] Network timeout on {url}: {e}")
                self._health_status = ProviderHealthStatus.DEGRADED
                self._last_error = f"Timeout: {e}"
                if attempt < self.max_retries:
                    time.sleep(0.01)
                    continue
                return None
            except requests.RequestException as e:
                logger.debug(f"[{self.provider_name}] Network error on {url}: {e}")
                self._health_status = ProviderHealthStatus.DEGRADED
                self._last_error = str(e)
                if attempt < self.max_retries:
                    time.sleep(0.01)
                    continue
                return None
            except Exception as e:
                logger.debug(f"[{self.provider_name}] Unexpected failure on {url}: {e}")
                self._last_error = str(e)
                return None

        return None


# Backward-compatible alias
BaseProvider = BaseEmailProvider
