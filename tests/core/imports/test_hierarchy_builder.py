"""Tests for HierarchyBuilder - derived references extraction."""

from __future__ import annotations

import pytest
import pandas as pd

from niamoto.common.database import Database
from niamoto.core.imports.hierarchy_builder import HierarchyBuilder
from niamoto.core.imports.config_models import HierarchyLevel, ExtractionConfig


@pytest.fixture
def duckdb_database(tmp_path):
    """Create a temporary DuckDB database with sample occurrences."""
    db_path = tmp_path / "test.duckdb"
    db = Database(str(db_path))

    # Create sample occurrences table
    df = pd.DataFrame(
        {
            "id": [1, 2, 3, 4, 5],
            "id_taxonref": [101, 102, 103, 101, 104],
            "family": [
                "Arecaceae",
                "Arecaceae",
                "Cunoniaceae",
                "Arecaceae",
                "Cunoniaceae",
            ],
            "genus": [
                "Burretiokentia",
                "Burretiokentia",
                "Codia",
                "Burretiokentia",
                "Codia",
            ],
            "species": [
                "vieillardii",
                "koghiensis",
                "mackeeana",
                "vieillardii",
                "spatulata",
            ],
            "taxaname": [
                "Burretiokentia vieillardii",
                "Burretiokentia koghiensis",
                "Codia mackeeana",
                "Burretiokentia vieillardii",
                "Codia spatulata",
            ],
            "dbh": [10.5, 12.3, 8.7, 9.2, 11.0],
        }
    )
    df.to_sql("dataset_occurrences", db.engine, if_exists="replace", index=False)

    try:
        yield db
    finally:
        try:
            db.close_db_session()
        except Exception:
            pass
        if getattr(db, "engine", None):
            db.engine.dispose()


def test_extract_taxonomy_from_occurrences(duckdb_database):
    """Test extracting taxonomy hierarchy from occurrences dataset."""
    builder = HierarchyBuilder(duckdb_database)

    config = ExtractionConfig(
        levels=[
            HierarchyLevel(name="family", column="family"),
            HierarchyLevel(name="genus", column="genus"),
            HierarchyLevel(name="species", column="species"),
        ],
        id_column="id_taxonref",
        name_column="taxaname",
        incomplete_rows="skip",
        id_strategy="hash",
    )

    result_df = builder.build_from_dataset("dataset_occurrences", config, "taxonomy")

    # Assertions
    assert len(result_df) > 0
    assert "id" in result_df.columns
    assert "parent_id" in result_df.columns
    assert "level" in result_df.columns

    # Check hierarchy integrity
    families = result_df[result_df["level"] == 0]
    genera = result_df[result_df["level"] == 1]
    species = result_df[result_df["level"] == 2]

    # Should have 2 families, 2 genera, 4 species
    assert len(families) == 2
    assert len(genera) == 2
    assert len(species) == 4

    # Families have no parent
    assert all(families["parent_id"].isna())

    # Genera point to families
    assert all(genera["parent_id"].isin(families["id"]))


def test_stable_ids_reproducibility(duckdb_database):
    """Test that hash-based IDs are stable across runs."""
    builder = HierarchyBuilder(duckdb_database)
    config = ExtractionConfig(
        levels=[HierarchyLevel(name="family", column="family")],
        id_strategy="hash",
    )

    df1 = builder.build_from_dataset("dataset_occurrences", config, "taxonomy")
    df2 = builder.build_from_dataset("dataset_occurrences", config, "taxonomy")

    # Same IDs across runs
    assert df1["id"].equals(df2["id"])


def test_fill_unknown_strategy(duckdb_database):
    """Test fill_unknown strategy for incomplete rows."""
    # Add incomplete row
    incomplete_df = pd.DataFrame(
        {
            "id": [6],
            "id_taxonref": [105],
            "family": ["Myrtaceae"],
            "genus": [None],
            "species": [None],
            "taxaname": ["Myrtaceae sp."],
            "dbh": [5.0],
        }
    )
    incomplete_df.to_sql(
        "dataset_occurrences", duckdb_database.engine, if_exists="append", index=False
    )

    builder = HierarchyBuilder(duckdb_database)
    config = ExtractionConfig(
        levels=[
            HierarchyLevel(name="family", column="family"),
            HierarchyLevel(name="genus", column="genus"),
            HierarchyLevel(name="species", column="species"),
        ],
        incomplete_rows="fill_unknown",
        id_strategy="hash",
    )

    result_df = builder.build_from_dataset("dataset_occurrences", config, "taxonomy")

    # Check that Unknown values were filled
    myrtaceae_genus = result_df[
        (result_df["level"] == 1) & (result_df["full_path"].str.contains("Myrtaceae"))
    ]
    assert len(myrtaceae_genus) > 0
    assert "Unknown genus" in myrtaceae_genus["rank_value"].values


def test_skip_incomplete_rows(duckdb_database):
    """Test skip strategy ignores incomplete rows at their incomplete level."""
    # Add incomplete row with missing genus and species
    incomplete_df = pd.DataFrame(
        {
            "id": [6],
            "id_taxonref": [105],
            "family": ["Myrtaceae"],
            "genus": [None],
            "species": [None],
            "taxaname": ["Myrtaceae sp."],
            "dbh": [5.0],
        }
    )
    incomplete_df.to_sql(
        "dataset_occurrences", duckdb_database.engine, if_exists="append", index=False
    )

    builder = HierarchyBuilder(duckdb_database)
    config = ExtractionConfig(
        levels=[
            HierarchyLevel(name="family", column="family"),
            HierarchyLevel(name="genus", column="genus"),
            HierarchyLevel(name="species", column="species"),
        ],
        incomplete_rows="skip",
        id_strategy="hash",
    )

    result_df = builder.build_from_dataset("dataset_occurrences", config, "taxonomy")

    # With skip strategy, family level can be included even if genus/species are missing
    # But the incomplete genus and species levels should not be created for that row
    # Check that Myrtaceae family is present (valid level)
    families = result_df[result_df["level"] == 0]
    assert "Myrtaceae" in families["rank_value"].values

    # But no genus or species should be created for the incomplete Myrtaceae row
    # Only the complete taxa should have genus/species
    genera = result_df[result_df["level"] == 1]
    species = result_df[result_df["level"] == 2]

    # Should still have just the original 2 genera and 4 species from fixture
    assert len(genera) == 2
    assert len(species) == 4


def test_name_column_preserves_rank_value_labels(duckdb_database):
    """Families and genera should surface their own labels when name_column is provided."""
    builder = HierarchyBuilder(duckdb_database)
    config = ExtractionConfig(
        levels=[
            HierarchyLevel(name="family", column="family"),
            HierarchyLevel(name="genus", column="genus"),
            HierarchyLevel(name="species", column="species"),
        ],
        name_column="taxaname",
        id_strategy="hash",
    )

    result_df = builder.build_from_dataset("dataset_occurrences", config, "taxonomy")

    families = result_df[result_df["level"] == 0]
    genera = result_df[result_df["level"] == 1]

    assert not families.empty
    assert not genera.empty

    # Expect display names to match the label of the current rank for derived levels
    assert families["full_name"].equals(families["rank_value"])
    assert genera["full_name"].equals(genera["rank_value"])

    # Species names should still reflect the full taxonomic name from the source column
    species = result_df[result_df["level"] == 2]
    assert not species.empty
    source_names = set(
        pd.read_sql(
            "SELECT DISTINCT taxaname FROM dataset_occurrences", duckdb_database.engine
        )["taxaname"].tolist()
    )
    assert set(species["full_name"]).issubset(source_names)


def test_hierarchy_with_additional_columns(duckdb_database):
    """Test extraction with additional columns."""
    builder = HierarchyBuilder(duckdb_database)
    config = ExtractionConfig(
        levels=[
            HierarchyLevel(name="family", column="family"),
            HierarchyLevel(name="genus", column="genus"),
        ],
        id_column="id_taxonref",
        name_column="taxaname",
        additional_columns=["dbh"],
        id_strategy="hash",
    )

    result_df = builder.build_from_dataset("dataset_occurrences", config, "taxonomy")

    # Verify core hierarchy columns are present
    assert "id" in result_df.columns
    assert "parent_id" in result_df.columns
    assert "level" in result_df.columns
    assert "rank_name" in result_df.columns
    assert "rank_value" in result_df.columns
    assert "full_path" in result_df.columns

    # Note: id_column, name_column, and additional_columns are intentionally
    # excluded from the hierarchy table to prevent row duplication. These should
    # be joined from the source table when needed for display or enrichment.
