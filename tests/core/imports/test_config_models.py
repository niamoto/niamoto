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
                        "name_field": "species_name",
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
                            "id": "endemia",
                            "label": "Endemia",
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
    assert species.schema.name_field == "species_name"
    assert len(species.schema.fields) == 3
    assert species.hierarchy is not None
    assert species.hierarchy.strategy is HierarchyStrategy.ADJACENCY_LIST
    assert species.enrichment[0].id == "endemia"
    assert species.enrichment[0].label == "Endemia"
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


def test_generic_import_config_keeps_structured_enrichment_config():
    """Structured enrichment config should remain available through the generic model."""

    config = GenericImportConfig.from_dict(
        {
            "version": "1.0",
            "entities": {
                "references": {
                    "taxons": {
                        "connector": {
                            "type": "duckdb_csv",
                            "path": "data/taxons.csv",
                        },
                        "schema": {"id": "id", "fields": []},
                        "enrichment": [
                            {
                                "id": "gbif",
                                "label": "GBIF",
                                "plugin": "api_taxonomy_enricher",
                                "enabled": True,
                                "config": {
                                    "api_url": "https://api.gbif.org/v2/species/match",
                                    "profile": "gbif_rich",
                                    "taxonomy_source": "col_xr",
                                    "include_taxonomy": True,
                                    "include_occurrences": True,
                                    "include_media": True,
                                    "include_references": True,
                                    "include_distributions": True,
                                    "media_limit": 3,
                                },
                            }
                        ],
                    }
                },
                "datasets": {},
            },
        }
    )

    enrichment = config.entities.references["taxons"].enrichment[0]
    assert enrichment.id == "gbif"
    assert enrichment.config["profile"] == "gbif_rich"
    assert enrichment.config["include_references"] is True
    assert enrichment.config["media_limit"] == 3


def test_generic_import_config_keeps_col_rich_fields():
    """Catalogue of Life structured fields should stay available in the generic model."""

    config = GenericImportConfig.from_dict(
        {
            "version": "1.0",
            "entities": {
                "references": {
                    "taxons": {
                        "connector": {
                            "type": "duckdb_csv",
                            "path": "data/taxons.csv",
                        },
                        "schema": {"id": "id", "fields": []},
                        "enrichment": [
                            {
                                "id": "col",
                                "label": "Catalogue of Life",
                                "plugin": "api_taxonomy_enricher",
                                "enabled": True,
                                "config": {
                                    "api_url": "https://api.checklistbank.org/dataset/314774/nameusage/search",
                                    "profile": "col_rich",
                                    "use_name_verifier": True,
                                    "dataset_key": 314774,
                                    "include_vernaculars": True,
                                    "include_distributions": True,
                                    "include_references": True,
                                    "reference_limit": 5,
                                },
                            }
                        ],
                    }
                },
                "datasets": {},
            },
        }
    )

    enrichment = config.entities.references["taxons"].enrichment[0]
    assert enrichment.id == "col"
    assert enrichment.config["profile"] == "col_rich"
    assert enrichment.config["use_name_verifier"] is True
    assert enrichment.config["dataset_key"] == 314774
    assert enrichment.config["include_vernaculars"] is True
    assert enrichment.config["reference_limit"] == 5


def test_generic_import_config_keeps_bhl_reference_fields():
    """BHL structured fields should stay available in the generic model."""

    config = GenericImportConfig.from_dict(
        {
            "version": "1.0",
            "entities": {
                "references": {
                    "taxons": {
                        "connector": {
                            "type": "duckdb_csv",
                            "path": "data/taxons.csv",
                        },
                        "schema": {"id": "id", "fields": []},
                        "enrichment": [
                            {
                                "id": "bhl",
                                "label": "BHL",
                                "plugin": "api_taxonomy_enricher",
                                "enabled": True,
                                "config": {
                                    "api_url": "https://www.biodiversitylibrary.org/api3",
                                    "profile": "bhl_references",
                                    "auth_method": "api_key",
                                    "auth_params": {
                                        "location": "query",
                                        "name": "apikey",
                                        "key": "secret",
                                    },
                                    "include_publication_details": True,
                                    "include_page_preview": False,
                                    "title_limit": 3,
                                    "page_limit": 2,
                                },
                            }
                        ],
                    }
                },
                "datasets": {},
            },
        }
    )

    enrichment = config.entities.references["taxons"].enrichment[0]
    assert enrichment.id == "bhl"
    assert enrichment.config["profile"] == "bhl_references"
    assert enrichment.config["include_publication_details"] is True
    assert enrichment.config["include_page_preview"] is False
    assert enrichment.config["title_limit"] == 3
    assert enrichment.config["page_limit"] == 2


def test_generic_import_config_keeps_inaturalist_rich_fields():
    """iNaturalist structured fields should stay available in the generic model."""

    config = GenericImportConfig.from_dict(
        {
            "version": "1.0",
            "entities": {
                "references": {
                    "taxons": {
                        "connector": {
                            "type": "duckdb_csv",
                            "path": "data/taxons.csv",
                        },
                        "schema": {"id": "id", "fields": []},
                        "enrichment": [
                            {
                                "id": "inat",
                                "label": "iNaturalist",
                                "plugin": "api_taxonomy_enricher",
                                "enabled": True,
                                "config": {
                                    "api_url": "https://api.inaturalist.org/v1/taxa",
                                    "profile": "inaturalist_rich",
                                    "include_occurrences": True,
                                    "include_media": True,
                                    "include_places": True,
                                    "media_limit": 3,
                                    "observation_limit": 5,
                                },
                            }
                        ],
                    }
                },
                "datasets": {},
            },
        }
    )

    enrichment = config.entities.references["taxons"].enrichment[0]
    assert enrichment.id == "inat"
    assert enrichment.config["profile"] == "inaturalist_rich"
    assert enrichment.config["include_occurrences"] is True
    assert enrichment.config["include_places"] is True
    assert enrichment.config["observation_limit"] == 5
