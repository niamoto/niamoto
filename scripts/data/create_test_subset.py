#!/usr/bin/env python3
"""Create a small test subset from occurrences.csv for faster development.

This script extracts a representative sample with:
- 3-5 families with low occurrence counts
- Complete taxonomy hierarchy (family → genus → species → infra)
- Variety of plots and geographic locations
- Total ~500-1000 occurrences (vs 203k)
"""

import pandas as pd
import sys
from pathlib import Path


def create_test_subset(
    input_file: Path,
    output_file: Path,
    target_families: int = 4,
    max_occurrences_per_family: int = 250,
):
    """Create a test subset from occurrences CSV.

    Args:
        input_file: Path to original occurrences.csv
        output_file: Path to output subset CSV
        target_families: Number of families to include
        max_occurrences_per_family: Max occurrences per family
    """
    print(f"📊 Reading {input_file}...")
    df = pd.read_csv(input_file)
    print(f"   Total rows: {len(df):,}")

    # Count occurrences by family
    family_counts = df["family"].value_counts()
    print("\n📈 Family distribution:")
    print(f"   Total families: {len(family_counts)}")
    print("   Top 10 families:")
    for family, count in family_counts.head(10).items():
        print(f"      {family}: {count:,} occurrences")

    # Select families with LOW counts (easier to test)
    # Avoid families with 0 or NaN
    valid_families = family_counts[
        (family_counts > 50)  # At least 50 occurrences
        & (family_counts < 2000)  # But not too many
    ]

    selected_families = valid_families.head(target_families).index.tolist()

    print("\n✅ Selected families for test subset:")
    for family in selected_families:
        count = family_counts[family]
        print(f"   • {family}: {count:,} occurrences")

    # Extract subset
    subset = df[df["family"].isin(selected_families)].copy()

    # Limit occurrences per family
    subset_limited = []
    for family in selected_families:
        family_data = subset[subset["family"] == family]
        if len(family_data) > max_occurrences_per_family:
            # Sample randomly to get variety of plots/locations
            family_sample = family_data.sample(
                n=max_occurrences_per_family, random_state=42
            )
        else:
            family_sample = family_data
        subset_limited.append(family_sample)

    final_subset = pd.concat(subset_limited, ignore_index=True)

    print("\n📦 Final subset statistics:")
    print(f"   Total rows: {len(final_subset):,}")
    print(f"   Families: {final_subset['family'].nunique()}")
    print(f"   Genera: {final_subset['genus'].nunique()}")
    print(f"   Species: {final_subset['species'].nunique()}")
    print(f"   Plots: {final_subset['plot_name'].nunique()}")
    print(f"   Unique taxon IDs: {final_subset['id_taxonref'].nunique()}")

    # Show taxonomy structure
    print("\n🌳 Taxonomy structure:")
    for family in selected_families:
        family_data = final_subset[final_subset["family"] == family]
        genera = family_data["genus"].nunique()
        species = family_data["species"].nunique()
        occurrences = len(family_data)
        print(
            f"   {family}: {genera} genera, {species} species, {occurrences} occurrences"
        )

    # Save subset
    output_file.parent.mkdir(parents=True, exist_ok=True)
    final_subset.to_csv(output_file, index=False)
    print(f"\n💾 Saved to: {output_file}")

    # Calculate size reduction
    original_size = input_file.stat().st_size / (1024 * 1024)  # MB
    subset_size = output_file.stat().st_size / (1024 * 1024)  # MB
    reduction = ((original_size - subset_size) / original_size) * 100

    print("\n📉 Size reduction:")
    print(f"   Original: {original_size:.2f} MB")
    print(f"   Subset: {subset_size:.2f} MB")
    print(f"   Reduction: {reduction:.1f}%")

    return final_subset


def main():
    """Main entry point."""
    # Paths
    project_root = Path(__file__).parent.parent
    instance_dir = project_root / "test-instance" / "niamoto-nc"

    input_file = instance_dir / "imports" / "occurrences.csv"
    output_file = instance_dir / "imports" / "occurrences_subset.csv"

    if not input_file.exists():
        print(f"❌ Error: Input file not found: {input_file}")
        sys.exit(1)

    print("=" * 60)
    print("🧪 Creating Test Subset for Fast Development")
    print("=" * 60)

    # Create subset
    create_test_subset(
        input_file=input_file,
        output_file=output_file,
        target_families=4,  # 4 families
        max_occurrences_per_family=250,  # Max 250 per family = ~1000 total
    )

    print("\n" + "=" * 60)
    print("✅ Test subset created successfully!")
    print("=" * 60)
    print("\n📝 Next steps:")
    print("   1. Update import.yml to use: occurrences_subset.csv")
    print("   2. Run: niamoto import")
    print("   3. Run: niamoto transform")
    print("   4. Expected ~5-10x faster than full dataset")
    print("\n💡 To revert:")
    print("   Change back to: occurrences.csv in import.yml")


if __name__ == "__main__":
    main()
