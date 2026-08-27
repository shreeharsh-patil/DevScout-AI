"""Shared outbound HTTP client with bounded retries and timeouts."""

from __future__ import annotations

import os

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


DEFAULT_TIMEOUT = (float(os.getenv("HTTP_CONNECT_TIMEOUT", "5")), float(os.getenv("HTTP_READ_TIMEOUT", "20")))

_session = requests.Session()
_session.headers.update({"User-Agent": "DevScoutAI/0.1 (+https://github.com/shreeharsh-patil/DevScout-AI)"})
_retry = Retry(
    total=3,
    connect=3,
    read=2,
    status=3,
    backoff_factor=0.5,
    status_forcelist=(429, 500, 502, 503, 504),
    allowed_methods=frozenset({"GET", "HEAD", "OPTIONS"}),
    respect_retry_after_header=True,
)
_adapter = HTTPAdapter(max_retries=_retry, pool_connections=20, pool_maxsize=20)
_session.mount("https://", _adapter)
_session.mount("http://", _adapter)


def get(url: str, **kwargs):
    kwargs.setdefault("timeout", DEFAULT_TIMEOUT)
    return _session.get(url, **kwargs)
