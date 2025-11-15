#!/usr/bin/env python3
"""
Test the complete bootstrap process.
This creates a new Niamoto instance from scratch using auto-detection.
"""

import sys
from pathlib import Path
import tempfile
import shutil

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from niamoto.core.imports.bootstrap import DataBootstrap


def test_bootstrap():
    """Test the bootstrap process with real data."""
    print("=" * 80)
    print("NIAMOTO BOOTSTRAP TEST")
    print("=" * 80)
    print()

    # Paths
    data_dir = Path(__file__).parent.parent / "test-instance" / "niamoto-og" / "imports"
    temp_dir = Path(tempfile.mkdtemp(prefix="niamoto_bootstrap_"))

    print(f"📁 Data directory: {data_dir}")
    print(f"📁 Output directory: {temp_dir}")
    print()

    try:
        # Run bootstrap
        bootstrap = DataBootstrap(instance_path=temp_dir / "instance")
        results = bootstrap.run(
            data_dir=data_dir,
            output_dir=temp_dir / "config",
            auto_confirm=True,  # Skip confirmation for testing
            interactive=True,
        )

        # Show results
        print("\n" + "=" * 80)
        print("BOOTSTRAP RESULTS")
        print("=" * 80)

        print(f"\nStatus: {results['status']}")
        print(f"Steps completed: {len(results['steps'])}")

        for step in results["steps"]:
            print(f"  ✓ {step['name']}: {step['status']}")

        # List created files
        print(f"\n📁 Files created in {temp_dir}:")
        import os

        for root, dirs, files in os.walk(temp_dir):
            root_path = Path(root)
            level = root_path.relative_to(temp_dir).parts
            indent = "  " * len(level)
            print(f"{indent}{root_path.name}/")
            subindent = "  " * (len(level) + 1)
            for file in files:
                print(f"{subindent}{file}")

        # Show import.yml content
        import_config = temp_dir / "config" / "import.yml"
        if import_config.exists():
            print("\n📝 Generated import.yml (first 50 lines):")
            print("-" * 40)
            with open(import_config) as f:
                lines = f.readlines()
                for line in lines[:50]:
                    print(line.rstrip())
            if len(lines) > 50:
                print("... (truncated)")

        # Keep temp directory for inspection
        print(f"\n💾 Bootstrap files saved to: {temp_dir}")
        print("   (This directory will not be automatically deleted)")

    except Exception as e:
        print(f"\n❌ Error during bootstrap: {e}")
        import traceback

        traceback.print_exc()

        # Clean up on error
        if temp_dir.exists():
            shutil.rmtree(temp_dir)

    print("\n" + "=" * 80)
    print("TEST COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    test_bootstrap()
