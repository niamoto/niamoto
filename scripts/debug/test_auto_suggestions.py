#!/usr/bin/env python3
"""
Test script for auto-suggestion system.

This script tests the integration of DataAnalyzer and TransformerSuggester
with the GenericImporter using real data.
"""

import json
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from niamoto.common.database import Database
from niamoto.core.imports.engine import GenericImporter
from niamoto.core.imports.registry import EntityRegistry, EntityKind


def test_auto_suggestions():
    """Test auto-suggestions with test instance data."""

    # Use test instance
    db_path = Path("test-instance/niamoto-nc/db/niamoto.duckdb")
    if not db_path.exists():
        print(f"❌ Database not found: {db_path}")
        return 1

    print("🔧 Connecting to database...")
    db = Database(str(db_path))
    registry = EntityRegistry(db)
    importer = GenericImporter(db, registry)

    # Test with a small CSV (use occurrences if available)
    csv_files = [
        "test-instance/niamoto-nc/imports/occurrences_mini.csv",
        "test-instance/niamoto-nc/imports/occurrences.csv",
        "test-instance/niamoto-nc/imports/plots.csv",
    ]

    test_csv = None
    for csv_file in csv_files:
        if Path(csv_file).exists():
            test_csv = csv_file
            break

    if not test_csv:
        print(f"❌ No test CSV found in: {csv_files}")
        return 1

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
            print("❌ No metadata found")
            return 1

        config = metadata.config
        if "semantic_profile" not in config:
            print("❌ No semantic_profile in metadata")
            return 1

        semantic_profile = config["semantic_profile"]
        print(f"✅ Semantic profile generated at: {semantic_profile['analyzed_at']}")
        print(f"✅ Analyzed {len(semantic_profile['columns'])} columns")
        print(
            f"✅ Generated suggestions for {len(semantic_profile['transformer_suggestions'])} columns"
        )

        # Display sample suggestions
        print("\n📝 Sample suggestions:")
        for col_name, suggestions in list(
            semantic_profile["transformer_suggestions"].items()
        )[:3]:
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
        return 0

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback

        traceback.print_exc()
        return 1
    finally:
        # Cleanup
        try:
            db.execute_sql(f"DROP TABLE IF EXISTS {table_name}")
            # Note: EntityRegistry cleanup would require additional methods
        except Exception:
            pass


if __name__ == "__main__":
    sys.exit(test_auto_suggestions())
