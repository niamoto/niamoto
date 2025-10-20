"""Tests for AdjacencyListLoader plugin."""

import pytest
import tempfile
from pathlib import Path
from sqlalchemy import text

from niamoto.common.database import Database
from niamoto.core.plugins.loaders.adjacency_list import (
    AdjacencyListLoader,
    AdjacencyListConfig,
    AdjacencyListParams,
)


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    temp_dir = tempfile.mkdtemp()
    db_path = str(Path(temp_dir) / "test.duckdb")

    db = Database(db_path)
    yield db

    # Cleanup
    import shutil

    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def adjacency_list_loader(temp_db):
    """Create adjacency list loader instance."""
    return AdjacencyListLoader(temp_db)


@pytest.fixture
def hierarchy_data(temp_db):
    """Create sample hierarchy and data tables."""
    test_db = temp_db
    # Create hierarchy table (adjacency list)
    test_db.execute_sql("""
        CREATE TABLE test_hierarchy (
            id INTEGER PRIMARY KEY,
            parent_id INTEGER,
            name TEXT,
            level INTEGER
        )
    """)

    # Insert hierarchy:
    # 1 (Plantae) -> 2 (Magnoliophyta) -> 3 (Magnoliopsida) -> 4 (Fabales)
    #                                                        -> 5 (Rosales)
    hierarchy_data = [
        (1, None, "Plantae", 0),  # Kingdom
        (2, 1, "Magnoliophyta", 1),  # Phylum
        (3, 2, "Magnoliopsida", 2),  # Class
        (4, 3, "Fabales", 3),  # Order 1
        (5, 3, "Rosales", 3),  # Order 2
    ]

    with test_db.engine.connect() as conn:
        for row in hierarchy_data:
            conn.execute(
                text("INSERT INTO test_hierarchy VALUES (:id, :parent, :name, :level)"),
                {"id": row[0], "parent": row[1], "name": row[2], "level": row[3]},
            )
        conn.commit()

    # Create data table
    test_db.execute_sql("""
        CREATE TABLE test_occurrences (
            id INTEGER PRIMARY KEY,
            taxon_id INTEGER,
            location TEXT
        )
    """)

    # Insert occurrences at different levels
    occurrences = [
        (1, 4, "Site A"),  # Fabales
        (2, 4, "Site B"),  # Fabales
        (3, 5, "Site C"),  # Rosales
        (4, 3, "Site D"),  # Magnoliopsida (parent of both orders)
    ]

    with test_db.engine.connect() as conn:
        for row in occurrences:
            conn.execute(
                text("INSERT INTO test_occurrences VALUES (:id, :taxon, :loc)"),
                {"id": row[0], "taxon": row[1], "loc": row[2]},
            )
        conn.commit()

    return test_db


def test_adjacency_list_config_validation():
    """Test configuration validation."""
    config = AdjacencyListConfig(
        plugin="adjacency_list",
        params=AdjacencyListParams(
            key="taxon_id",
            parent_field="parent_id",
            include_children=True,
        ),
    )

    assert config.plugin == "adjacency_list"
    assert config.params.key == "taxon_id"
    assert config.params.parent_field == "parent_id"
    assert config.params.include_children is True


def test_load_single_node_only(adjacency_list_loader, hierarchy_data):
    """Test loading data for single node without children."""
    config = {
        "data": "test_occurrences",
        "grouping": "test_hierarchy",
        "params": {
            "key": "taxon_id",
            "parent_field": "parent_id",
            "include_children": False,
        },
    }

    # Load data for Fabales (id=4) only
    result = adjacency_list_loader.load_data(4, config)

    assert len(result) == 2  # Only direct Fabales occurrences
    assert set(result["location"]) == {"Site A", "Site B"}


def test_load_node_with_children(adjacency_list_loader, hierarchy_data):
    """Test loading data for node including all descendants."""
    config = {
        "data": "test_occurrences",
        "grouping": "test_hierarchy",
        "params": {
            "key": "taxon_id",
            "parent_field": "parent_id",
            "include_children": True,
        },
    }

    # Load data for Magnoliopsida (id=3) - should include Fabales and Rosales
    result = adjacency_list_loader.load_data(3, config)

    # Should get:
    # - 1 occurrence at Magnoliopsida level (Site D)
    # - 2 occurrences at Fabales level (Site A, B)
    # - 1 occurrence at Rosales level (Site C)
    assert len(result) == 4
    assert set(result["location"]) == {"Site A", "Site B", "Site C", "Site D"}


def test_load_leaf_node(adjacency_list_loader, hierarchy_data):
    """Test loading data for leaf node (no children)."""
    config = {
        "data": "test_occurrences",
        "grouping": "test_hierarchy",
        "params": {
            "key": "taxon_id",
            "parent_field": "parent_id",
            "include_children": True,
        },
    }

    # Load data for Rosales (id=5) - leaf node
    result = adjacency_list_loader.load_data(5, config)

    assert len(result) == 1
    assert result.iloc[0]["location"] == "Site C"


def test_load_root_node(adjacency_list_loader, hierarchy_data):
    """Test loading data for root node (entire tree)."""
    config = {
        "data": "test_occurrences",
        "grouping": "test_hierarchy",
        "params": {
            "key": "taxon_id",
            "parent_field": "parent_id",
            "include_children": True,
        },
    }

    # Load data for Plantae (id=1) - root node
    result = adjacency_list_loader.load_data(1, config)

    # Should get all occurrences (entire tree)
    assert len(result) == 4


def test_load_nonexistent_node(adjacency_list_loader, hierarchy_data):
    """Test loading data for non-existent node."""
    config = {
        "data": "test_occurrences",
        "grouping": "test_hierarchy",
        "params": {
            "key": "taxon_id",
            "parent_field": "parent_id",
            "include_children": True,
        },
    }

    # Load data for non-existent node
    result = adjacency_list_loader.load_data(999, config)

    assert len(result) == 0


def test_backward_compatibility_config(adjacency_list_loader, hierarchy_data):
    """Test backward compatibility with flat config structure."""
    config = {
        "data": "test_occurrences",
        "grouping": "test_hierarchy",
        "key": "taxon_id",  # Top-level key
        "parent_field": "parent_id",
        "include_children": True,
    }

    result = adjacency_list_loader.load_data(4, config)

    assert len(result) == 2  # Fabales occurrences
