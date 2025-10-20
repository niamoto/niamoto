"""Tests for the generic import configuration models."""

from __future__ import annotations

import pytest

from niamoto.core.imports.config_models import (
    ConnectorConfig,
    ConnectorType,
    GenericImportConfig,
    HierarchyStrategy,
)


def sample_config_dict() -> dict:
    return {
        "version": "1.0",
        "entities": {
            "references": {
                "species": {
                    "connector": {
                        "type": "duckdb_csv",
                        "path": "data/species.csv",
                    },
                    "schema": {
                        "id": "species_id",
                        "fields": [
                            {
                                "name": "family",
                                "type": "string",
                                "semantic": "taxonomy.family",
                            },
                            {
                                "name": "genus",
                                "type": "string",
                                "semantic": "taxonomy.genus",
                            },
                            {
                                "name": "species",
                                "type": "string",
                                "semantic": "taxonomy.species",
                            },
                        ],
                    },
                    "hierarchy": {
                        "type": "adjacency_list",
                        "levels": ["family", "genus", "species"],
                    },
                    "enrichment": [
                        {
                            "plugin": "api_taxonomy_enricher",
                            "config": {"url": "https://api.example.com"},
                        }
                    ],
                }
            },
            "datasets": {
                "observations": {
                    "connector": {
                        "type": "duckdb_csv",
                        "path": "data/observations.csv",
                    },
                    "schema": {
                        "id_field": "occurrence_id",
                        "fields": [
                            {
                                "name": "species_code",
                                "type": "string",
                                "reference": "species.species_id",
                            },
                            {
                                "name": "height",
                                "type": "float",
                            },
                        ],
                    },
                    "links": [
                        {
                            "entity": "species",
                            "field": "species_code",
                            "target_field": "species_id",
                        }
                    ],
                    "options": {"mode": "replace", "chunk_size": 5000},
                }
            },
        },
    }


def test_generic_import_config_parsing():
    config = GenericImportConfig.from_dict(sample_config_dict())

    species = config.entities.references["species"]
    assert species.connector.type is ConnectorType.DUCKDB_CSV
    assert species.schema.id_field == "species_id"
    assert len(species.schema.fields) == 3
    assert species.hierarchy is not None
    assert species.hierarchy.strategy is HierarchyStrategy.ADJACENCY_LIST
    # Levels provided as strings should be converted to HierarchyLevel objects
    assert [level.column for level in species.hierarchy.levels] == [
        "family",
        "genus",
        "species",
    ]

    dataset = config.entities.datasets["observations"]
    assert dataset.connector.path == "data/observations.csv"
    assert dataset.schema.id_field == "occurrence_id"
    assert dataset.links[0].entity == "species"
    assert dataset.options.chunk_size == 5000


def test_connector_requires_path_for_file_types():
    with pytest.raises(ValueError):
        ConnectorConfig(type=ConnectorType.FILE)
