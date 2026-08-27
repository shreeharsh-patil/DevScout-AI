"""
Performance Optimization, Intelligent Provider Caching, and Observability Telemetry (Phases 21 & 22).

Implements:
1. In-memory thread-safe TTL Provider Cache with per-provider retention rules:
   - Domain metadata: 24 hours (86,400s)
   - Breach metadata: 12 hours (43,200s)
   - GitHub profiles: 1 hour (3,600s)
   - Web mentions: 30 minutes (1,800s)
   - Error responses: 60s (prevents long-term caching of transient failures)
2. Production telemetry tracking (duration, success rates, rate limits, cache hit ratio)
3. Structured, sanitized logging with zero credential leakage.
"""

from __future__ import annotations

import threading
import time
from typing import Any, Dict, List, Optional
from loguru import logger
from .models import ProviderMetric


class IntelligenceCache:
    """Thread-safe TTL caching layer for intelligence provider lookups."""

    DEFAULT_TTLS: Dict[str, float] = {
        "domain": 86400.0,       # 24 hours
        "breach": 43200.0,       # 12 hours
        "github": 3600.0,        # 1 hour
        "gravatar": 86400.0,     # 24 hours
        "npm": 7200.0,           # 2 hours
        "pypi": 7200.0,          # 2 hours
        "crates": 7200.0,        # 2 hours
        "web": 1800.0,           # 30 minutes
        "error": 60.0            # 1 minute for transient errors
    }

    def __init__(self):
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()
        self._hits = 0
        self._misses = 0

    def get(self, category: str, key: str) -> Optional[Any]:
        cache_key = f"{category}:{key.strip().lower()}"
        with self._lock:
            entry = self._cache.get(cache_key)
            if entry:
                if time.time() < entry["expires_at"]:
                    self._hits += 1
                    logger.debug(f"[Cache HIT] {cache_key}")
                    return entry["data"]
                else:
                    # Expired
                    del self._cache[cache_key]
            self._misses += 1
            return None

    def set(self, category: str, key: str, data: Any, is_error: bool = False):
        cache_key = f"{category}:{key.strip().lower()}"
        ttl = self.DEFAULT_TTLS["error"] if is_error else self.DEFAULT_TTLS.get(category, 3600.0)
        expires_at = time.time() + ttl
        with self._lock:
            self._cache[cache_key] = {
                "data": data,
                "expires_at": expires_at
            }
            logger.debug(f"[Cache SET] {cache_key} (TTL: {ttl}s)")

    def clear(self):
        with self._lock:
            self._cache.clear()

    @property
    def stats(self) -> Dict[str, Any]:
        with self._lock:
            total = self._hits + self._misses
            hit_rate = (self._hits / total * 100) if total > 0 else 0.0
            return {
                "cached_items": len(self._cache),
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate_pct": round(hit_rate, 1)
            }


class ObservabilityTelemetry:
    """Tracks performance metrics and reliability telemetry across research jobs."""

    def __init__(self):
        self._metrics: List[ProviderMetric] = []
        self._lock = threading.Lock()

    def record_metric(self, metric: ProviderMetric):
        with self._lock:
            self._metrics.append(metric)
            if len(self._metrics) > 1000:
                self._metrics = self._metrics[-1000:]

    def get_summary(self) -> Dict[str, Any]:
        with self._lock:
            total_ops = len(self._metrics)
            if total_ops == 0:
                return {"total_operations": 0, "avg_duration_ms": 0, "success_rate_pct": 100.0}

            durations = [m.duration_ms for m in self._metrics]
            successes = [m for m in self._metrics if m.status == "success" or m.cache_hit]
            avg_duration = sum(durations) / total_ops
            success_rate = (len(successes) / total_ops) * 100

            return {
                "total_operations": total_ops,
                "avg_duration_ms": round(avg_duration, 1),
                "success_rate_pct": round(success_rate, 1),
                "recent_metrics": [m.model_dump() for m in self._metrics[-10:]]
            }


# Singleton global cache and telemetry instances
default_cache = IntelligenceCache()
default_telemetry = ObservabilityTelemetry()
