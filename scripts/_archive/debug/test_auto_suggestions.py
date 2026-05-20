#!/usr/bin/env python3
"""
Test script for auto-suggestion system.

This script tests the integration of DataAnalyzer and TransformerSuggester
with the GenericImporter using real data.
"""

import json
import shutil
import sys
from pathlib import Path

import pytest

# Add src to path
REPO_ROOT = Path(__file__).resolve().parents[3]
if not (REPO_ROOT / "src").is_dir():
    raise RuntimeError(f"Could not resolve repository root from {__file__}")
sys.path.insert(0, str(REPO_ROOT / "src"))

from niamoto.common.database import Database  # noqa: E402
from niamoto.core.imports.engine import GenericImporter  # noqa: E402
from niamoto.core.imports.registry import EntityRegistry, EntityKind  # noqa: E402


def test_auto_suggestions(tmp_path: Path):
    """Test auto-suggestions with test instance data."""

    # Use test instance
    fixture_db_path = (
        REPO_ROOT / "test-instance" / "niamoto-nc" / "db" / "niamoto.duckdb"
    )
    if not fixture_db_path.exists():
        pytest.fail(f"Database fixture not found: {fixture_db_path}")
    db_path = tmp_path / "niamoto.duckdb"
    shutil.copy2(fixture_db_path, db_path)

    print("🔧 Connecting to database...")
    db = Database(str(db_path))
    registry = EntityRegistry(db)
    importer = GenericImporter(db, registry)

    # Test with a small real CSV first, then fall back to larger fixtures.
    csv_files = [
        REPO_ROOT / "test-instance" / "niamoto-nc" / "imports" / "plots.csv",
        REPO_ROOT / "test-instance" / "niamoto-nc" / "imports" / "occurrences_mini.csv",
        REPO_ROOT / "test-instance" / "niamoto-nc" / "imports" / "occurrences.csv",
    ]

    test_csv = None
    for csv_file in csv_files:
        if csv_file.exists():
            test_csv = csv_file
            break

    if not test_csv:
        pytest.fail(f"No test CSV found in: {csv_files}")

    print(f"📁 Testing with: {test_csv}")

    # Import with auto-analysis
    entity_name = "test_auto_suggestions"
    table_name = "test_auto_suggestions"

    try:
        print("\n🚀 Importing with auto-analysis...")
        result = importer.import_from_csv(
            entity_name=entity_name,
            table_name=table_name,
            source_path=test_csv,
            kind=EntityKind.DATASET,
        )

        print(f"✅ Imported {result.rows} rows into {result.table}")

        # Retrieve metadata to check semantic_profile
        print("\n📊 Checking semantic profile...")
        metadata = registry.get(entity_name)

        if not metadata or not metadata.config:
            pytest.fail("No metadata found")

        config = metadata.config
        if "semantic_profile" not in config:
            pytest.fail("No semantic_profile in metadata")

        semantic_profile = config["semantic_profile"]
        columns = semantic_profile["columns"]
        semantic_columns = [col for col in columns if col.get("semantic_type")]
        transformer_suggestions = semantic_profile["transformer_suggestions"]

        assert columns, "Semantic profile should include analyzed columns"
        assert semantic_columns, "At least one column should have a semantic type"
        assert transformer_suggestions, "Transformer suggestions should not be empty"
        assert "holdridge" in transformer_suggestions
        assert any(
            suggestion["transformer"] == "categorical_distribution"
            for suggestion in transformer_suggestions["holdridge"]
        )

        for col_name, suggestions in transformer_suggestions.items():
            assert suggestions, f"Column '{col_name}' should have suggestions"
            for suggestion in suggestions:
                assert suggestion.get("transformer")
                assert suggestion.get("reason")
                assert suggestion.get("confidence", 0) > 0
                assert suggestion.get("config", {}).get("plugin")

        print(f"✅ Semantic profile generated at: {semantic_profile['analyzed_at']}")
        print(f"✅ Analyzed {len(columns)} columns")
        print(f"✅ Generated suggestions for {len(transformer_suggestions)} columns")

        # Display sample suggestions
        print("\n📝 Sample suggestions:")
        for col_name, suggestions in list(transformer_suggestions.items())[:3]:
            print(f"\n  Column: {col_name}")
            for suggestion in suggestions:
                print(
                    f"    - {suggestion['transformer']} (confidence: {suggestion['confidence']})"
                )
                print(f"      Reason: {suggestion['reason']}")
                print(f"      Config: {suggestion['config']['plugin']}")

        # Pretty print full profile (optional, comment out if too verbose)
        print("\n" + "=" * 80)
        print("FULL SEMANTIC PROFILE:")
        print("=" * 80)
        print(json.dumps(semantic_profile, indent=2, default=str))

        print("\n✅ Auto-suggestion system working correctly!")

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback

        traceback.print_exc()
        pytest.fail(f"Auto-suggestion test failed: {e}")
    finally:
        # Cleanup
        try:
            db.execute_sql(f"DROP TABLE IF EXISTS {table_name}")
            db.close_db_session()
        except Exception:
            pass


if __name__ == "__main__":
    import tempfile

    with tempfile.TemporaryDirectory(prefix="niamoto-auto-suggestions-") as temp_dir:
        sys.exit(test_auto_suggestions(Path(temp_dir)))
