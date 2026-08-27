"""Network-input validation helpers."""

from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlparse


def validate_public_url(value: str, *, allowed_hosts: set[str] | None = None) -> str:
    """Return a normalized public HTTP(S) URL and reject SSRF-oriented targets."""
    candidate = (value or "").strip()
    if len(candidate) > 2048:
        raise ValueError("URL is too long")
    if "://" not in candidate:
        candidate = f"https://{candidate}"
    parsed = urlparse(candidate)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("Only HTTP and HTTPS URLs are supported")
    if parsed.username or parsed.password:
        raise ValueError("URLs containing credentials are not supported")

    host = parsed.hostname.rstrip(".").lower()
    if allowed_hosts and host not in allowed_hosts and not any(host.endswith(f".{item}") for item in allowed_hosts):
        raise ValueError("URL host is not allowed for this research type")
    if host in {"localhost", "localhost.localdomain"} or host.endswith((".local", ".internal")):
        raise ValueError("Local network URLs are not allowed")
    try:
        addresses = {item[4][0] for item in socket.getaddrinfo(host, parsed.port or 443, type=socket.SOCK_STREAM)}
    except socket.gaierror as exc:
        raise ValueError("URL hostname could not be resolved") from exc
    for address in addresses:
        ip = ipaddress.ip_address(address)
        if not ip.is_global:
            raise ValueError("Private, loopback, and reserved network URLs are not allowed")
    return candidate
