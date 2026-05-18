"""Shared URL validation helpers for server-side HTTP fetches."""

from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlparse, urlunparse

from fastapi import HTTPException

_LOCAL_HOSTNAMES = {"localhost", "localhost.localdomain"}


def validate_public_http_url(
    raw_url: str,
    *,
    detail: str = "URL is not allowed.",
) -> str:
    """Return a normalized HTTP(S) URL that is safe for server-side fetching."""
    normalized = raw_url.strip()
    parsed = urlparse(normalized)
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.netloc
        or not parsed.hostname
    ):
        raise HTTPException(status_code=400, detail="Invalid URL.")

    if parsed.username or parsed.password:
        raise HTTPException(status_code=400, detail=detail)

    _validate_public_host(parsed.hostname, parsed.port, detail)
    return urlunparse(parsed._replace(fragment=""))


def _validate_public_host(hostname: str, port: int | None, detail: str) -> None:
    hostname = hostname.strip("[]").lower()
    if hostname in _LOCAL_HOSTNAMES or hostname.endswith(".localhost"):
        raise HTTPException(status_code=400, detail=detail)

    try:
        _ensure_public_ip(ipaddress.ip_address(hostname), detail)
        return
    except ValueError:
        pass

    try:
        resolved = socket.getaddrinfo(
            hostname,
            port,
            type=socket.SOCK_STREAM,
        )
    except socket.gaierror:
        return

    for result in resolved:
        sockaddr = result[4]
        if sockaddr:
            _ensure_public_ip(ipaddress.ip_address(sockaddr[0]), detail)


def _ensure_public_ip(ip_address: ipaddress._BaseAddress, detail: str) -> None:
    if not ip_address.is_global:
        raise HTTPException(status_code=400, detail=detail)
