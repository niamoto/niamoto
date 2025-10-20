"""Tests for the Entity Registry."""

from __future__ import annotations


import pytest

from niamoto.common.database import Database
from niamoto.common.exceptions import DatabaseQueryError
from niamoto.core.imports.registry import EntityKind, EntityRegistry


@pytest.fixture()
def registry() -> EntityRegistry:
    db = Database("sqlite:///:memory:")
    try:
        yield EntityRegistry(db)
    finally:
        try:
            db.close_db_session()
        except AttributeError:
            pass
        if db.engine:
            db.engine.dispose()


def test_register_and_lookup_reference(registry: EntityRegistry):
    registry.register_entity(
        name="species",
        kind=EntityKind.REFERENCE,
        table_name="entity_species",
        config={"schema": {"id": "species_id"}},
    )

    metadata = registry.get("species")
    assert metadata.name == "species"
    assert metadata.kind is EntityKind.REFERENCE
    assert metadata.table_name == "entity_species"
    assert metadata.config["schema"]["id"] == "species_id"


def test_lookup_by_name(registry: EntityRegistry):
    """Test that we can lookup entities by their name."""
    registry.register_entity(
        name="plots",
        kind=EntityKind.REFERENCE,
        table_name="entity_plots",
        config={"schema": {"id": "plot_id"}},
    )

    metadata = registry.get("plots")
    assert metadata.name == "plots"
    assert metadata.table_name == "entity_plots"


def test_list_entities(registry: EntityRegistry):
    registry.register_entity(
        name="species",
        kind=EntityKind.REFERENCE,
        table_name="entity_species",
        config={},
    )
    registry.register_entity(
        name="observations",
        kind=EntityKind.DATASET,
        table_name="dataset_observations",
        config={},
    )

    all_entities = registry.list_entities()
    assert {entity.name for entity in all_entities} == {
        "species",
        "observations",
    }

    references = registry.list_entities(EntityKind.REFERENCE)
    assert len(references) == 1
    assert references[0].name == "species"


def test_remove_entity(registry: EntityRegistry):
    registry.register_entity(
        name="species",
        kind=EntityKind.REFERENCE,
        table_name="entity_species",
        config={},
    )

    registry.remove("species")

    with pytest.raises(DatabaseQueryError):
        registry.get("species")


def test_invalid_json_config(registry: EntityRegistry):
    """Test that invalid JSON in config raises DatabaseQueryError."""
    # Insert invalid JSON directly into database
    sql = f"""
        INSERT INTO {registry.ENTITIES_TABLE} (name, kind, table_name, config)
        VALUES (:name, :kind, :table_name, :config)
    """
    registry.db.execute_sql(
        sql,
        {
            "name": "bad_entity",
            "kind": "reference",
            "table_name": "entity_bad",
            "config": "{invalid json}",  # Invalid JSON
        },
    )

    with pytest.raises(DatabaseQueryError) as exc_info:
        registry.get("bad_entity")

    assert "Invalid JSON in config field" in str(exc_info.value)


def test_invalid_entity_kind(registry: EntityRegistry):
    """Test that invalid entity kind raises DatabaseQueryError."""
    # Insert invalid kind directly into database
    sql = f"""
        INSERT INTO {registry.ENTITIES_TABLE} (name, kind, table_name, config)
        VALUES (:name, :kind, :table_name, :config)
    """
    registry.db.execute_sql(
        sql,
        {
            "name": "bad_kind_entity",
            "kind": "invalid_kind",  # Invalid enum value
            "table_name": "entity_bad",
            "config": "{}",
        },
    )

    with pytest.raises(DatabaseQueryError) as exc_info:
        registry.get("bad_kind_entity")

    assert "Invalid entity kind value" in str(exc_info.value)
