"""
Phase 4: Corpus MVP — integration tests for the suggestion pipeline.

Tests run the full profiling + suggestion pipeline on fixture datasets.
Assertions are semantic (properties, not exact values) — no golden files.
"""

import pytest
from pathlib import Path

from niamoto.core.imports.profiler import DataProfiler
from niamoto.core.imports.data_analyzer import DataAnalyzer
from niamoto.core.imports.widget_generator import WidgetGenerator
from niamoto.core.plugins.plugin_loader import PluginLoader

FIXTURES = Path(__file__).parent.parent / "fixtures" / "datasets"


@pytest.fixture(autouse=True, scope="module")
def _ensure_plugins_loaded():
    """Ensure plugins are loaded for SmartMatcher."""
    loader = PluginLoader()
    loader.load_plugins_with_cascade()


def run_full_pipeline(file_path: Path):
    """Run profiling + enrichment + suggestion pipeline on a file.

    Returns (profile, enriched_profiles, widget_suggestions).
    """
    profiler = DataProfiler(ml_detector=None)
    analyzer = DataAnalyzer()
    generator = WidgetGenerator()

    # 1. Profile
    profile = profiler.profile(file_path)

    # 2. Load data for enrichment (may be sampled — that's fine for testing)
    import pandas as pd

    suffix = file_path.suffix.lower()
    if suffix in (".tsv", ".txt"):
        df = pd.read_csv(file_path, sep="\t", nrows=1000)
    elif suffix == ".csv":
        try:
            df = pd.read_csv(file_path, nrows=1000)
        except UnicodeDecodeError:
            df = pd.read_csv(file_path, nrows=1000, encoding="latin-1")
    elif suffix in (".geojson", ".json"):
        try:
            import geopandas as gpd

            df = gpd.read_file(file_path)
        except ImportError:
            df = pd.read_json(file_path)
    elif suffix in (".xlsx", ".xls"):
        df = pd.read_excel(file_path)
    else:
        df = pd.read_csv(file_path, nrows=1000)

    # 3. Enrich
    enriched_profiles = []
    for col_profile in profile.columns:
        if col_profile.name in df.columns:
            try:
                enriched = analyzer.enrich_profile(col_profile, df[col_profile.name])
                enriched_profiles.append(enriched)
            except Exception:
                continue

    # 4. Widget suggestions
    widget_suggestions = generator.generate_for_columns(enriched_profiles)

    return profile, enriched_profiles, widget_suggestions


# ── Dataset specs ──────────────────────────────────────────────────────────

DATASETS_MVP = {
    "gbif_terrestrial": {
        "path": FIXTURES / "gbif_terrestrial.tsv",
        "expect_taxonomy": True,
        "expect_spatial": True,
        "expect_min_suggestions": 3,
        "reject_columns": ["gbifID", "occurrenceID"],
    },
    "gbif_marine": {
        "path": FIXTURES / "gbif_marine.tsv",
        "expect_spatial": True,
        "expect_min_suggestions": 2,
    },
    "minimal": {
        "path": FIXTURES / "minimal.csv",
        "expect_spatial": True,
        "expect_min_suggestions": 1,
    },
    "adversarial": {
        "path": FIXTURES / "adversarial.csv",
        "expect_no_crash": True,
    },
}

# Extended datasets (Phase 4+)
DATASETS_EXTENDED = {
    "checklist": {
        "path": FIXTURES / "checklist.csv",
        "expect_taxonomy": True,
        "expect_spatial": False,
        "expect_min_suggestions": 1,
    },
    "custom_forest": {
        "path": FIXTURES / "custom_forest.csv",
        "expect_min_suggestions": 2,
    },
    "geojson_inventory": {
        "path": FIXTURES / "inventory.geojson",
        "expect_min_suggestions": 1,
    },
}

# Combine all datasets
DATASETS_ALL = {**DATASETS_MVP, **DATASETS_EXTENDED}


# ── Tests ──────────────────────────────────────────────────────────────────


class TestPipelineDoesNotCrash:
    """Each dataset: profiling + suggestions without error."""

    @pytest.mark.parametrize("name,spec", DATASETS_ALL.items())
    def test_no_crash(self, name, spec):
        profile, enriched, suggestions = run_full_pipeline(spec["path"])
        assert profile is not None
        if not spec.get("expect_no_crash"):
            assert profile.record_count > 0


class TestPipelineSemanticDetection:
    """Verify taxonomy and spatial columns are detected when expected."""

    @pytest.mark.parametrize("name,spec", DATASETS_ALL.items())
    def test_taxonomy_detection(self, name, spec):
        if not spec.get("expect_taxonomy"):
            pytest.skip("No taxonomy expected")

        profile, _, _ = run_full_pipeline(spec["path"])
        taxonomy_cols = [
            c
            for c in profile.columns
            if c.semantic_type and "taxonomy" in c.semantic_type
        ]
        assert len(taxonomy_cols) > 0, (
            f"{name}: no taxonomy columns detected. "
            f"Types: {[(c.name, c.semantic_type) for c in profile.columns]}"
        )

    @pytest.mark.parametrize("name,spec", DATASETS_ALL.items())
    def test_spatial_detection(self, name, spec):
        if not spec.get("expect_spatial"):
            pytest.skip("No spatial expected")

        profile, _, _ = run_full_pipeline(spec["path"])
        spatial_cols = [
            c
            for c in profile.columns
            if c.semantic_type and "location" in c.semantic_type
        ]
        assert len(spatial_cols) > 0, (
            f"{name}: no spatial columns detected. "
            f"Types: {[(c.name, c.semantic_type) for c in profile.columns]}"
        )


class TestPipelineSuggestionQuality:
    """Verify suggestion count and column rejection."""

    @pytest.mark.parametrize("name,spec", DATASETS_ALL.items())
    def test_minimum_suggestions(self, name, spec):
        min_sug = spec.get("expect_min_suggestions", 0)
        if min_sug == 0:
            pytest.skip("No minimum expected")

        _, _, suggestions = run_full_pipeline(spec["path"])
        assert len(suggestions) >= min_sug, (
            f"{name}: {len(suggestions)} suggestions, expected >= {min_sug}"
        )

    @pytest.mark.parametrize("name,spec", DATASETS_ALL.items())
    def test_rejected_columns(self, name, spec):
        reject = spec.get("reject_columns", [])
        if not reject:
            pytest.skip("No columns to reject")

        _, _, suggestions = run_full_pipeline(spec["path"])
        suggested_cols = {s.column for s in suggestions if hasattr(s, "column")}
        for col in reject:
            assert col not in suggested_cols, (
                f"{name}: ID column '{col}' should not produce suggestions"
            )

    @pytest.mark.parametrize("name,spec", DATASETS_ALL.items())
    def test_confidence_reasonable(self, name, spec):
        if spec.get("expect_no_crash"):
            pytest.skip("Adversarial — confidence not guaranteed")

        _, _, suggestions = run_full_pipeline(spec["path"])
        for s in suggestions:
            assert s.confidence >= 0.1, (
                f"{name}: suggestion for column has very low confidence {s.confidence}"
            )
