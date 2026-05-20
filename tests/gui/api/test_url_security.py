"""Tests for shared server-side URL security helpers."""

import socket

from fastapi import HTTPException

from niamoto.gui.api.url_security import (
    pin_public_dns_for_url,
    resolve_public_http_url_addresses,
)


def test_resolve_public_http_url_addresses_returns_validated_addresses(monkeypatch):
    monkeypatch.setattr(
        "niamoto.gui.api.url_security.socket.getaddrinfo",
        lambda *args, **kwargs: [
            (socket.AF_INET, socket.SOCK_STREAM, 0, "", ("93.184.216.34", 443))
        ],
    )

    safe_url, addresses = resolve_public_http_url_addresses(
        "https://example.com/path#fragment"
    )

    assert safe_url == "https://example.com/path"
    assert addresses == ("93.184.216.34",)


def test_resolve_public_http_url_addresses_rejects_private_resolution(monkeypatch):
    monkeypatch.setattr(
        "niamoto.gui.api.url_security.socket.getaddrinfo",
        lambda *args, **kwargs: [
            (socket.AF_INET, socket.SOCK_STREAM, 0, "", ("127.0.0.1", 80))
        ],
    )

    try:
        resolve_public_http_url_addresses("http://example.com")
    except HTTPException as exc:
        assert exc.status_code == 400
    else:
        raise AssertionError("private DNS resolution was accepted")


def test_resolve_public_http_url_addresses_rejects_failed_resolution(monkeypatch):
    def fail_resolution(*args, **kwargs):
        raise socket.gaierror("temporary failure")

    monkeypatch.setattr(
        "niamoto.gui.api.url_security.socket.getaddrinfo",
        fail_resolution,
    )

    try:
        resolve_public_http_url_addresses("http://example.invalid")
    except HTTPException as exc:
        assert exc.status_code == 400
    else:
        raise AssertionError("failed DNS resolution was accepted")


def test_pin_public_dns_for_url_reuses_validated_addresses(monkeypatch):
    original_getaddrinfo = socket.getaddrinfo

    with pin_public_dns_for_url("https://example.com/path", ("93.184.216.34",)):
        resolved = socket.getaddrinfo("example.com", 443, type=socket.SOCK_STREAM)

    assert resolved[0][4][0] == "93.184.216.34"
    assert socket.getaddrinfo is original_getaddrinfo
