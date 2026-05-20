"""Shared URL validation helpers for server-side HTTP fetches."""

from __future__ import annotations

import ipaddress
import socket
import threading
from contextlib import contextmanager
from collections.abc import Iterator, Sequence
from urllib.parse import urlparse, urlunparse

from fastapi import HTTPException

_LOCAL_HOSTNAMES = {"localhost", "localhost.localdomain"}
_PINNED_DNS_LOCK = threading.RLock()


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

    _resolve_public_host_addresses(parsed.hostname, parsed.port, detail)
    return urlunparse(parsed._replace(fragment=""))


def resolve_public_http_url_addresses(
    raw_url: str,
    *,
    detail: str = "URL is not allowed.",
) -> tuple[str, tuple[str, ...]]:
    """Return a normalized public URL and the public addresses it resolved to."""
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

    addresses = _resolve_public_host_addresses(
        parsed.hostname or "", parsed.port, detail
    )
    return urlunparse(parsed._replace(fragment="")), tuple(sorted(addresses))


@contextmanager
def pin_public_dns_for_url(safe_url: str, addresses: Sequence[str]) -> Iterator[None]:
    """Temporarily pin DNS lookups for a validated URL to validated addresses."""
    if not addresses:
        yield
        return

    parsed = urlparse(safe_url)
    hostname = (parsed.hostname or "").rstrip(".").lower()
    pinned_addresses = tuple(addresses)
    original_getaddrinfo = socket.getaddrinfo

    def pinned_getaddrinfo(host, port, *args, **kwargs):
        requested_host = str(host).rstrip(".").lower()
        if requested_host == hostname:
            return [
                (
                    socket.AF_INET6 if ":" in address else socket.AF_INET,
                    socket.SOCK_STREAM,
                    0,
                    "",
                    (address, port, 0, 0) if ":" in address else (address, port),
                )
                for address in pinned_addresses
            ]
        return original_getaddrinfo(host, port, *args, **kwargs)

    with _PINNED_DNS_LOCK:
        socket.getaddrinfo = pinned_getaddrinfo
        try:
            yield
        finally:
            socket.getaddrinfo = original_getaddrinfo


def _resolve_public_host_addresses(
    hostname: str, port: int | None, detail: str
) -> set[str]:
    hostname = hostname.strip("[]").lower()
    if hostname in _LOCAL_HOSTNAMES or hostname.endswith(".localhost"):
        raise HTTPException(status_code=400, detail=detail)

    try:
        ip = ipaddress.ip_address(hostname)
        _ensure_public_ip(ip, detail)
        return {str(ip)}
    except ValueError:
        pass

    try:
        resolved = socket.getaddrinfo(
            hostname,
            port,
            type=socket.SOCK_STREAM,
        )
    except socket.gaierror:
        raise HTTPException(status_code=400, detail=detail)

    addresses: set[str] = set()
    for result in resolved:
        sockaddr = result[4]
        if sockaddr:
            ip = ipaddress.ip_address(sockaddr[0])
            _ensure_public_ip(ip, detail)
            addresses.add(str(ip))

    return addresses


def _ensure_public_ip(ip_address: ipaddress._BaseAddress, detail: str) -> None:
    if not ip_address.is_global:
        raise HTTPException(status_code=400, detail=detail)
