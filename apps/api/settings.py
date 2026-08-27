"""Runtime configuration with production safety checks."""

from __future__ import annotations

import os
from urllib.parse import urlparse


APP_ENV = os.getenv("APP_ENV", "development").strip().lower()
IS_PRODUCTION = APP_ENV == "production"


def env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


ENABLE_DEMO_AUTH = env_bool("ENABLE_DEMO_AUTH", not IS_PRODUCTION)
ENABLE_DEV_TOKEN_AUTH = env_bool("ENABLE_DEV_TOKEN_AUTH", not IS_PRODUCTION)
TRUST_IDENTITY_HEADERS = env_bool("TRUST_IDENTITY_HEADERS", False)
ALLOW_LOCAL_QUEUE_FALLBACK = env_bool("ALLOW_LOCAL_QUEUE_FALLBACK", False)
REQUIRE_QUEUE = env_bool("REQUIRE_QUEUE", IS_PRODUCTION)
LOG_JSON = env_bool("LOG_JSON", IS_PRODUCTION)

JWT_SECRET = os.getenv("JWT_SECRET", "")
API_SECRET_KEY = os.getenv("API_SECRET_KEY", "")

REQUEST_RATE_LIMIT = max(1, int(os.getenv("REQUEST_RATE_LIMIT", "120")))
RESEARCH_RATE_LIMIT = max(1, int(os.getenv("RESEARCH_RATE_LIMIT", "10")))
RATE_LIMIT_WINDOW_SECONDS = max(1, int(os.getenv("RATE_LIMIT_WINDOW_SECONDS", "60")))


def cors_origins() -> list[str]:
    raw = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:3001")
    origins = list(dict.fromkeys(item.strip().rstrip("/") for item in raw.split(",") if item.strip()))
    for origin in origins:
        parsed = urlparse(origin)
        if origin == "*" or parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise RuntimeError(f"Unsafe CORS origin configured: {origin!r}")
    if IS_PRODUCTION and not origins:
        raise RuntimeError("CORS_ORIGINS must contain at least one trusted production origin")
    return origins


def validate_runtime_config() -> None:
    if IS_PRODUCTION:
        if len(JWT_SECRET) < 32:
            raise RuntimeError("JWT_SECRET must be set to at least 32 characters in production")
        if ENABLE_DEMO_AUTH or ENABLE_DEV_TOKEN_AUTH or TRUST_IDENTITY_HEADERS:
            raise RuntimeError("Demo authentication, dev token issuance, and trusted identity headers must be disabled in production")
    cors_origins()
