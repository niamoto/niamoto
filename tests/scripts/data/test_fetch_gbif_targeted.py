"""Tests for targeted GBIF fetch script network boundaries."""

from __future__ import annotations

import io
import csv

import pytest

from scripts.data import fetch_gbif_targeted


class JsonResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        self.close()


def test_fetch_page_passes_timeout_to_urlopen(monkeypatch):
    calls = []

    def fake_urlopen(request, *, timeout):
        calls.append((request, timeout))
        return JsonResponse(b'{"count": 0, "results": []}')

    monkeypatch.setattr(fetch_gbif_targeted, "urlopen", fake_urlopen)

    payload = fetch_gbif_targeted.fetch_page(
        {"country": "NC"},
        timeout_seconds=12.5,
    )

    assert payload == {"count": 0, "results": []}
    assert calls[0][1] == 12.5


def test_fetch_occurrences_adds_context_to_page_errors(monkeypatch):
    def fail_fetch_page(params, *, timeout_seconds):
        raise TimeoutError("timed out")

    monkeypatch.setattr(fetch_gbif_targeted, "fetch_page", fail_fetch_page)

    with pytest.raises(RuntimeError) as exc_info:
        fetch_gbif_targeted.fetch_occurrences(
            country_code="NC",
            kingdom_key=6,
            max_records=10,
            max_scan_records=20,
            page_size=5,
            pause_seconds=0,
            profile="general",
            timeout_seconds=1,
        )

    assert "country=NC offset=0 limit=5" in str(exc_info.value)


def test_write_csv_preserves_headers_for_empty_records(tmp_path):
    output_path = tmp_path / "occurrences.csv"

    columns = fetch_gbif_targeted.write_csv(output_path, [])

    with output_path.open(newline="", encoding="utf-8") as handle:
        reader = csv.reader(handle)
        header = next(reader)

    assert columns == list(fetch_gbif_targeted.PREFERRED_COLUMNS)
    assert header == list(fetch_gbif_targeted.PREFERRED_COLUMNS)
