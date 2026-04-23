from __future__ import annotations

import sys
import warnings
from pathlib import Path

from niamoto.common import bundle


def test_get_base_path_uses_meipass_when_frozen(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path), raising=False)

    assert bundle.get_base_path() == tmp_path


def test_get_base_path_warns_when_expected_source_layout_is_missing(
    monkeypatch, tmp_path: Path
) -> None:
    fake_bundle_file = tmp_path / "pkg" / "niamoto" / "common" / "bundle.py"
    fake_bundle_file.parent.mkdir(parents=True)
    fake_bundle_file.write_text("# fake\n", encoding="utf-8")

    monkeypatch.setattr(sys, "frozen", False, raising=False)
    monkeypatch.delattr(sys, "_MEIPASS", raising=False)
    monkeypatch.setattr(bundle, "__file__", str(fake_bundle_file))

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        base_path = bundle.get_base_path()

    assert base_path == tmp_path
    assert any("expected src/niamoto" in str(item.message) for item in caught)


def test_get_resource_path_joins_to_base_path(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(bundle, "get_base_path", lambda: tmp_path)

    assert (
        bundle.get_resource_path("src/niamoto/gui/app.py")
        == tmp_path / "src/niamoto/gui/app.py"
    )


def test_is_frozen_requires_both_flags(monkeypatch) -> None:
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.delattr(sys, "_MEIPASS", raising=False)
    assert bundle.is_frozen() is False

    monkeypatch.setattr(sys, "_MEIPASS", "/tmp/bundle", raising=False)
    assert bundle.is_frozen() is True
