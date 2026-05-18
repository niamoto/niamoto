"""Path helpers shared by exporter plugins."""

from pathlib import Path
from typing import Union


def safe_output_path(output_root: Path, relative_path: Union[str, Path]) -> Path:
    """Resolve a configured output path without leaving the export directory."""
    root = output_root.resolve()
    path = Path(str(relative_path))

    if path.is_absolute():
        raise ValueError(f"Output path must be relative: {relative_path}")

    if any(part == ".." for part in path.parts):
        raise ValueError(f"Output path escapes output directory: {relative_path}")

    candidate = (root / path).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise ValueError(
            f"Output path escapes output directory: {relative_path}"
        ) from exc

    return output_root / path
