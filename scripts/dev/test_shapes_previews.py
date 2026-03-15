#!/usr/bin/env python3
"""Test batch des previews widgets shapes configurés.

Appelle GET /api/preview/{widget_id}?group_by=shapes pour chacun des
12 widgets shapes et affiche un tableau récapitulatif.

Usage:
    # Avec le serveur lancé :
    uv run python scripts/dev/test_shapes_previews.py
    uv run python scripts/dev/test_shapes_previews.py --port 5173
"""

import argparse
import re
import sys
from urllib.request import Request, urlopen
from urllib.error import URLError


SHAPES_WIDGETS = [
    ("shape_info", "field_aggregator", "info_grid"),
    ("general_info", "class_object_field_aggregator", "info_grid"),
    ("geography", "shape_processor", "interactive_map"),
    ("forest_cover", "class_object_binary_aggregator", "concentric_rings"),
    ("land_use", "class_object_categories_extractor", "bar_plot"),
    ("elevation_distribution", "class_object_series_ratio_aggregator", "bar_plot"),
    ("holdridge", "class_object_categories_mapper", "bar_plot"),
    ("forest_types", "class_object_categories_extractor", "donut_chart"),
    ("forest_cover_by_elevation", "class_object_series_matrix_extractor", "bar_plot"),
    (
        "forest_types_by_elevation",
        "class_object_series_by_axis_extractor",
        "stacked_area_plot",
    ),
    ("fragmentation", "class_object_field_aggregator", "radial_gauge"),
    (
        "fragmentation_distribution",
        "class_object_series_extractor",
        "stacked_area_plot",
    ),
]


def fetch(url):
    """Fetch URL and return (status, body_text)."""
    try:
        req = Request(url, method="GET")
        with urlopen(req, timeout=30) as resp:
            return resp.status, resp.read().decode("utf-8", errors="replace")
    except URLError as e:
        if hasattr(e, "code"):
            try:
                body = e.read().decode("utf-8", errors="replace")
            except Exception:
                body = str(e)
            return e.code, body
        return 0, str(e)
    except Exception as e:
        return -1, str(e)


def classify_html(status, html):
    """Classify preview response."""
    if status == 0:
        return "CONN", "Serveur non joignable"
    if status != 200:
        return "HTTP", f"Status {status}"
    if not html or not html.strip():
        return "EMPTY", "Réponse vide"

    # Check for error
    error_match = re.search(r"class=['\"]error['\"]>([^<]+)", html)
    if error_match:
        return "ERROR", error_match.group(1).strip()[:60]

    # Check for info/warning
    info_match = re.search(r"class=['\"]info['\"]>([^<]+)", html)
    if info_match:
        return "INFO", info_match.group(1).strip()[:60]

    # Check for plotly charts
    if "plotly" in html.lower() or "Plotly" in html:
        return "OK", "Plotly chart"

    # Check for leaflet maps
    if "leaflet" in html.lower() or "L.map" in html:
        return "OK", "Leaflet map"

    # Check for info-grid
    if "info-grid" in html or "grid-item" in html:
        return "OK", "Info grid"

    # Has substantial content
    body_match = re.search(r"<body>(.*?)</body>", html, re.DOTALL)
    body = body_match.group(1).strip() if body_match else html.strip()
    if len(body) > 100:
        return "OK", f"HTML ({len(body)} chars)"

    return "WARN", f"Contenu court ({len(body)} chars)"


def main():
    parser = argparse.ArgumentParser(description="Test shapes widget previews")
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--host", default="127.0.0.1")
    args = parser.parse_args()

    base_url = f"http://{args.host}:{args.port}"

    # Check server is running
    status, _ = fetch(f"{base_url}/api/health")
    if status == 0:
        print(f"Serveur non joignable sur {base_url}")
        print(
            "Lancer d'abord : uv run niamoto gui --work-dir test-instance/niamoto-subset"
        )
        sys.exit(1)

    print(f"\n{'=' * 90}")
    print(f"  Test previews widgets shapes — {base_url}")
    print(f"{'=' * 90}\n")

    ICONS = {
        "OK": "✅",
        "INFO": "ℹ️ ",
        "WARN": "⚠️ ",
        "ERROR": "❌",
        "EMPTY": "🔲",
        "HTTP": "🔴",
        "CONN": "🔌",
    }

    results = []
    for widget_id, transformer, widget_type in SHAPES_WIDGETS:
        url = f"{base_url}/api/preview/{widget_id}?group_by=shapes"
        status, body = fetch(url)
        cat, msg = classify_html(status, body)
        results.append((widget_id, transformer, widget_type, cat, msg))

    # Print results
    print(
        f"  {'Widget':<30} {'Transformer':<40} {'Widget Type':<20} {'Status':<8} {'Details'}"
    )
    print(f"  {'-' * 30} {'-' * 40} {'-' * 20} {'-' * 8} {'-' * 40}")
    for widget_id, transformer, widget_type, cat, msg in results:
        icon = ICONS.get(cat, "?")
        print(f"  {widget_id:<30} {transformer:<40} {widget_type:<20} {icon:<8} {msg}")

    # Summary
    ok = sum(1 for _, _, _, c, _ in results if c == "OK")
    total = len(results)
    print(f"\n  Résultat : {ok}/{total} widgets OK")

    if ok < total:
        print("\n  Widgets en erreur :")
        for widget_id, transformer, widget_type, cat, msg in results:
            if cat != "OK":
                print(f"    - {widget_id}: [{cat}] {msg}")

    return 0 if ok == total else 1


if __name__ == "__main__":
    sys.exit(main())
