"""Request correlation, structured access logs, and bounded local rate limiting."""

from __future__ import annotations

from collections import defaultdict, deque
import threading
import time
import uuid

from fastapi import Request
from fastapi.responses import JSONResponse
from loguru import logger
from starlette.middleware.base import BaseHTTPMiddleware

from settings import RATE_LIMIT_WINDOW_SECONDS, REQUEST_RATE_LIMIT, RESEARCH_RATE_LIMIT


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("x-request-id", "")
        if not request_id or len(request_id) > 128:
            request_id = uuid.uuid4().hex
        started = time.monotonic()
        with logger.contextualize(request_id=request_id):
            try:
                response = await call_next(request)
            except Exception:
                logger.exception("Unhandled request error", method=request.method, path=request.url.path)
                response = JSONResponse(status_code=500, content={"detail": "Internal server error", "request_id": request_id})
            response.headers["X-Request-Id"] = request_id
            response.headers["X-Content-Type-Options"] = "nosniff"
            response.headers["Referrer-Policy"] = "no-referrer"
            logger.info(
                "request_complete",
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                duration_ms=round((time.monotonic() - started) * 1000, 2),
            )
            return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    _events: dict[str, deque[float]] = defaultdict(deque)
    _lock = threading.Lock()

    async def dispatch(self, request: Request, call_next):
        if request.url.path in {"/", "/health", "/api/v1/health", "/api/v1/ready"}:
            return await call_next(request)
        client = request.client.host if request.client else "unknown"
        token = request.headers.get("authorization", "")[-32:]
        key = f"{client}:{token}:{request.url.path if request.url.path in {'/api/v1/research', '/api/v1/auth/token'} else '*'}"
        limit = RESEARCH_RATE_LIMIT if request.url.path in {"/api/v1/research", "/api/v1/auth/token"} else REQUEST_RATE_LIMIT
        now = time.monotonic()
        with self._lock:
            events = self._events[key]
            cutoff = now - RATE_LIMIT_WINDOW_SECONDS
            while events and events[0] <= cutoff:
                events.popleft()
            if len(events) >= limit:
                retry_after = max(1, int(RATE_LIMIT_WINDOW_SECONDS - (now - events[0])))
                return JSONResponse(
                    status_code=429,
                    headers={"Retry-After": str(retry_after)},
                    content={"detail": "Rate limit exceeded. Try again later."},
                )
            events.append(now)
            remaining = max(0, limit - len(events))
        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        return response
