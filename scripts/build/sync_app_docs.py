#!/usr/bin/env python3
"""Generate the in-app documentation pack from the public docs tree."""

from __future__ import annotations

import argparse
from pathlib import Path

from niamoto.gui.help_content.builder import (
    build_help_content,
    default_docs_root,
    default_help_content_root,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate the in-app documentation pack from the public docs tree."
    )
    parser.add_argument(
        "--docs-root",
        type=Path,
        default=default_docs_root(),
        help="Source docs directory (defaults to the repository docs/ tree).",
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=default_help_content_root(),
        help="Destination directory for generated help content.",
    )
    args = parser.parse_args()

    result = build_help_content(
        docs_root=args.docs_root,
        output_root=args.output_root,
    )
    print(
        f"Generated in-app docs pack: {result.sections} sections, "
        f"{result.pages} pages, {result.assets} assets"
    )
    print(f"Manifest: {result.manifest_path}")
    print(f"Search index: {result.search_index_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
