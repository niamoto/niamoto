#!/usr/bin/env python3
"""
Test script for auto-detection on real data.
Run this to see how well the auto-detector works with actual Niamoto data.
"""

import sys
from pathlib import Path
import yaml

import pytest

# Add src to path
REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "src"))

from niamoto.core.imports.auto_detector import AutoDetector  # noqa: E402


def test_auto_detection():
    """Test auto-detection on real Niamoto data."""
    print("=" * 80)
    print("NIAMOTO AUTO-DETECTION TEST")
    print("=" * 80)
    print()

    # Path to test data
    import_dir = REPO_ROOT / "test-instance" / "niamoto-og" / "imports"

    if not import_dir.exists():
        pytest.skip(f"Import fixture directory not found: {import_dir}")

    print(f"📁 Analyzing directory: {import_dir}")
    print()

    # Initialize auto-detector
    detector = AutoDetector()

    # Run analysis
    print("🔍 Running auto-detection...")
    print("-" * 40)

    results = detector.analyze_directory(import_dir)

    # Display summary
    print()
    print("📊 DETECTION SUMMARY")
    print("-" * 40)

    summary = results["summary"]
    assert summary["total_files"] > 0
    print(f"Total files analyzed: {summary['total_files']}")
    print(f"Total records: {summary['total_records']:,}")
    print(f"Overall confidence: {results['confidence'] * 100:.1f}%")
    print()

    # Display detected entities
    for entity_type, entities in summary["detected_entities"].items():
        print(f"\n{entity_type.upper()}:")
        for entity in entities:
            print(f"  • {entity['name']} ({entity['type']})")
            print(f"    File: {entity['file']}")
            print(f"    Records: {entity['records']:,}")

    # Display validation
    print()
    print("✅ VALIDATION")
    print("-" * 40)
    validation = results["validation"]

    if validation["valid"]:
        print("✓ Configuration is valid")
    else:
        print("✗ Configuration has issues:")
        for issue in validation["issues"]:
            print(f"  - {issue}")

    if validation.get("warnings"):
        print("\n⚠️  Warnings:")
        for warning in validation["warnings"]:
            print(f"  - {warning}")

    # Display generated configuration
    print()
    print("📝 GENERATED CONFIGURATION")
    print("-" * 40)

    config = results["config"]

    # Save config to file
    output_path = Path(__file__).parent / "auto_generated_import.yml"
    with open(output_path, "w") as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False)

    print(f"Configuration saved to: {output_path}")
    print()
    print("Preview:")
    print(yaml.dump(config, default_flow_style=False, sort_keys=False)[:1000])

    if len(yaml.dump(config, default_flow_style=False, sort_keys=False)) > 1000:
        print("... (truncated)")

    # Display column analysis for key files
    print()
    print("🔬 DETAILED COLUMN ANALYSIS")
    print("-" * 40)

    for profile_dict in results["profiles"][:3]:  # Show first 3 files
        print(f"\nFile: {Path(profile_dict['file_path']).name}")
        print(f"Type: {profile_dict['detected_type']}")
        print(f"Records: {profile_dict['record_count']:,}")
        print("Detected columns:")

        for col in profile_dict["columns"][:10]:  # Show first 10 columns
            if col["semantic_type"]:
                print(
                    f"  • {col['name']} → {col['semantic_type']} ({col['confidence'] * 100:.0f}% confidence)"
                )

    # Compare with existing configuration
    existing_config_path = import_dir / "../config" / "import.yml"
    if existing_config_path.exists():
        print()
        print("📊 COMPARISON WITH EXISTING CONFIG")
        print("-" * 40)

        with open(existing_config_path) as f:
            existing = yaml.safe_load(f)

        # Simple comparison
        print("Existing configuration has:")
        if "taxonomy" in existing:
            print("  • Taxonomy configuration")
        if "plots" in existing:
            print("  • Plots configuration")
        if "occurrences" in existing:
            print("  • Occurrences configuration")
        if "shapes" in existing:
            print(f"  • {len(existing['shapes'])} shape configurations")

        print("\nAuto-detected configuration has:")
        if config.get("references"):
            print(f"  • {len(config['references'])} reference entities")
        if config.get("data"):
            print(f"  • {len(config['data'])} data entities")
        if config.get("shapes"):
            print(f"  • {len(config['shapes'])} shape configurations")

    print()
    print("=" * 80)
    print("TEST COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    test_auto_detection()
