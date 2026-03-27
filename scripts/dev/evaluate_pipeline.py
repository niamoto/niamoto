#!/usr/bin/env python3
"""Evaluate the suggestion pipeline on any dataset.

Quick diagnostic tool to test profiling + suggestions on real data.
Shows: detected types, suggestions generated, timing, memory usage.

Usage:
    python scripts/evaluate_pipeline.py path/to/data.csv
    python scripts/evaluate_pipeline.py path/to/data.tsv path/to/other.csv
    python scripts/evaluate_pipeline.py test-instance/niamoto-gb/imports/occurrences.csv
"""

import sys
import time
import tracemalloc
from pathlib import Path

# Ensure project is importable
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from niamoto.core.imports.profiler import DataProfiler
from niamoto.core.imports.data_analyzer import DataAnalyzer
from niamoto.core.imports.widget_generator import WidgetGenerator
from niamoto.core.plugins.plugin_loader import PluginLoader


def evaluate_file(file_path: Path) -> dict:
    """Run the full pipeline on a file and return diagnostics."""
    print(f"\n{'=' * 70}")
    print(f"  {file_path.name} ({file_path.stat().st_size / 1024 / 1024:.1f} MB)")
    print(f"{'=' * 70}")

    profiler = DataProfiler(ml_detector=None)
    analyzer = DataAnalyzer()
    generator = WidgetGenerator()

    # ── 1. Profile ──
    tracemalloc.start()
    t0 = time.perf_counter()

    profile = profiler.profile(file_path)

    t_profile = time.perf_counter() - t0
    mem_profile = tracemalloc.get_traced_memory()[1] / 1024 / 1024
    tracemalloc.stop()

    print(f"\n  Profiling: {t_profile:.2f}s | Peak memory: {mem_profile:.1f} MB")
    print(
        f"  Rows: {profile.record_count} | Columns: {len(profile.columns)} | Type: {profile.detected_type}"
    )

    # ── 2. Column detection ──
    print(f"\n  {'Column':<30} {'Type':<12} {'Semantic':<30} {'Null%':>6}")
    print(f"  {'-' * 80}")

    for col in profile.columns:
        semantic = col.semantic_type or "-"
        null_pct = f"{col.null_ratio * 100:.0f}%" if col.null_ratio else "0%"
        dtype_short = col.dtype[:10]
        print(f"  {col.name:<30} {dtype_short:<12} {semantic:<30} {null_pct:>6}")

    # ── 3. Enrich + suggest ──
    import pandas as pd

    suffix = file_path.suffix.lower()
    if suffix in (".tsv", ".txt"):
        df = pd.read_csv(file_path, sep="\t", nrows=50_000)
    elif suffix == ".csv":
        try:
            df = pd.read_csv(file_path, nrows=50_000)
        except UnicodeDecodeError:
            df = pd.read_csv(file_path, nrows=50_000, encoding="latin-1")
    elif suffix in (".geojson", ".json"):
        try:
            import geopandas as gpd

            df = gpd.read_file(file_path)
        except ImportError:
            df = pd.read_json(file_path)
    elif suffix in (".xlsx", ".xls"):
        df = pd.read_excel(file_path)
    else:
        df = pd.read_csv(file_path, nrows=50_000)

    t0 = time.perf_counter()

    enriched = []
    skipped = []
    errors = []
    for col_profile in profile.columns:
        if col_profile.name in df.columns:
            try:
                e = analyzer.enrich_profile(col_profile, df[col_profile.name])
                enriched.append(e)
            except Exception as ex:
                errors.append((col_profile.name, str(ex)))
        else:
            skipped.append(col_profile.name)

    suggestions = generator.generate_for_columns(enriched)

    t_suggest = time.perf_counter() - t0

    print(f"\n  Enrichment + suggestions: {t_suggest:.2f}s")
    print(
        f"  Enriched: {len(enriched)} | Skipped: {len(skipped)} | Errors: {len(errors)}"
    )

    if errors:
        print("\n  Errors:")
        for col, err in errors:
            print(f"    {col}: {err}")

    # ── 4. Suggestions ──
    print(f"\n  Suggestions ({len(suggestions)} total):")
    print(
        f"  {'Column':<25} {'Transformer':<25} {'Widget':<20} {'Conf':>5} {'Primary':>8}"
    )
    print(f"  {'-' * 85}")

    for s in suggestions:
        col = getattr(s, "column", "-")
        primary = "★" if s.is_primary else ""
        print(
            f"  {col:<25} {s.transformer_plugin:<25} {s.widget_plugin:<20} {s.confidence:>5.2f} {primary:>8}"
        )

    # ── 5. Summary ──
    taxonomy_cols = [
        c for c in profile.columns if c.semantic_type and "taxonomy" in c.semantic_type
    ]
    spatial_cols = [
        c for c in profile.columns if c.semantic_type and "location" in c.semantic_type
    ]
    temporal_cols = [
        c for c in profile.columns if c.semantic_type and "temporal" in c.semantic_type
    ]
    id_cols = [
        c
        for c in profile.columns
        if c.semantic_type and "identifier" in c.semantic_type
    ]

    print("\n  Summary:")
    print(
        f"    Taxonomy columns: {len(taxonomy_cols)} ({', '.join(c.name for c in taxonomy_cols)})"
    )
    print(
        f"    Spatial columns:  {len(spatial_cols)} ({', '.join(c.name for c in spatial_cols)})"
    )
    print(
        f"    Temporal columns: {len(temporal_cols)} ({', '.join(c.name for c in temporal_cols)})"
    )
    print(
        f"    ID columns:       {len(id_cols)} ({', '.join(c.name for c in id_cols)})"
    )
    print(f"    Total time:       {t_profile + t_suggest:.2f}s")

    return {
        "file": str(file_path),
        "rows": profile.record_count,
        "columns": len(profile.columns),
        "suggestions": len(suggestions),
        "taxonomy": len(taxonomy_cols),
        "spatial": len(spatial_cols),
        "time_s": round(t_profile + t_suggest, 2),
        "memory_mb": round(mem_profile, 1),
    }


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    # Load plugins once
    loader = PluginLoader()
    loader.load_plugins_with_cascade()

    results = []
    for path_str in sys.argv[1:]:
        path = Path(path_str)
        if not path.exists():
            print(f"\n  ERROR: {path} not found")
            continue
        results.append(evaluate_file(path))

    if len(results) > 1:
        print(f"\n{'=' * 70}")
        print("  COMPARISON")
        print(f"{'=' * 70}")
        print(
            f"  {'File':<35} {'Rows':>8} {'Cols':>5} {'Sugg':>5} {'Tax':>4} {'Spat':>5} {'Time':>7} {'Mem':>8}"
        )
        print(f"  {'-' * 80}")
        for r in results:
            name = Path(r["file"]).name[:33]
            print(
                f"  {name:<35} {r['rows']:>8} {r['columns']:>5} {r['suggestions']:>5} "
                f"{r['taxonomy']:>4} {r['spatial']:>5} {r['time_s']:>6.2f}s {r['memory_mb']:>6.1f}MB"
            )


if __name__ == "__main__":
    main()
