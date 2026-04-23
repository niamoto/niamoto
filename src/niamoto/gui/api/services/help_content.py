"""Service helpers for generated in-app documentation content."""

from __future__ import annotations

import json
from pathlib import Path

from fastapi import HTTPException


HELP_CONTENT_ROOT = Path(__file__).resolve().parents[2] / "help_content"


class HelpContentService:
    """Read generated help-content artifacts from the package tree."""

    def __init__(self, root: Path | None = None) -> None:
        self.root = (root or HELP_CONTENT_ROOT).resolve()
        self.pages_root = self.root / "pages"
        self.assets_root = self.root / "assets"

    def load_manifest(self) -> dict:
        return self._read_json(self.root / "manifest.json")

    def load_search_index(self) -> dict:
        return self._read_json(self.root / "search-index.json")

    def load_page(self, slug: str) -> dict:
        safe_slug = self._sanitize_relative_path(slug)
        return self._read_json(self.pages_root / f"{safe_slug}.json")

    def resolve_asset_path(self, asset_path: str) -> Path:
        try:
            safe_asset_path = self._sanitize_relative_path(asset_path)
        except HTTPException as exc:
            raise HTTPException(
                status_code=404, detail="Documentation asset not found"
            ) from exc
        candidate = (self.assets_root / safe_asset_path).resolve()
        try:
            candidate.relative_to(self.assets_root)
        except ValueError as exc:
            raise HTTPException(
                status_code=404, detail="Documentation asset not found"
            ) from exc

        if not candidate.exists() or not candidate.is_file():
            raise HTTPException(status_code=404, detail="Documentation asset not found")
        return candidate

    def _read_json(self, path: Path) -> dict:
        if not path.exists():
            raise HTTPException(
                status_code=503,
                detail="Documentation content is not available in this build",
            )
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise HTTPException(
                status_code=500,
                detail="Documentation content is corrupted",
            ) from exc

    @staticmethod
    def _sanitize_relative_path(raw_path: str) -> Path:
        cleaned = raw_path.strip().strip("/")
        if not cleaned:
            raise HTTPException(status_code=404, detail="Documentation page not found")
        candidate = Path(cleaned)
        if candidate.is_absolute() or ".." in candidate.parts:
            raise HTTPException(status_code=404, detail="Documentation page not found")
        return candidate
