"""Integration tests for ImporterService with derived references.

This module contains critical end-to-end tests for the derived reference system.
"""

from __future__ import annotations

import pytest
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point
from shapely import wkt
from pyproj import Transformer

from niamoto.core.services.importer import ImporterService
from niamoto.common.database import Database
from niamoto.common.exceptions import ValidationError
from niamoto.core.imports.config_models import (
    GenericImportConfig,
    EntitiesConfig,
    ReferenceEntityConfig,
    DatasetEntityConfig,
    ConnectorConfig,
    ConnectorType,
    EntitySchema,
    ExtractionConfig,
    HierarchyLevel,
    HierarchyConfig,
    HierarchyStrategy,
    ReferenceKind,
    MultiFeatureSource,
)
from niamoto.core.imports.registry import EntityRegistry, EntityKind
from niamoto.core.imports.engine import GenericImporter


@pytest.mark.integration
def test_end_to_end_derived_taxonomy(tmp_path):
    """CRITICAL TEST: End-to-end derived taxonomy scenario.

    Steps:
    1. Import occurrences dataset
    2. Derive taxonomy reference
    3. Verify hierarchy structure
    4. Verify registry metadata
    """
    # 1. Create sample occurrences CSV
    occurrences_csv = tmp_path / "occurrences.csv"
    pd.DataFrame(
        {
            "id": [1, 2, 3, 4],
            "id_taxonref": [101, 102, 103, 101],
            "family": ["Arecaceae", "Arecaceae", "Cunoniaceae", "Arecaceae"],
            "genus": ["Burretiokentia", "Burretiokentia", "Codia", "Burretiokentia"],
            "species": ["vieillardii", "koghiensis", "mackeeana", "vieillardii"],
            "taxaname": [
                "Burretiokentia vieillardii",
                "Burretiokentia koghiensis",
                "Codia mackeeana",
                "Burretiokentia vieillardii",
            ],
            "dbh": [10.5, 12.3, 8.7, 9.2],
        }
    ).to_csv(occurrences_csv, index=False)

    # 2. Create import configuration
    config = GenericImportConfig(
        entities=EntitiesConfig(
            datasets={
                "occurrences": DatasetEntityConfig(
                    connector=ConnectorConfig(
                        type=ConnectorType.FILE, path=str(occurrences_csv)
                    ),
                    schema=EntitySchema(id_field="id", fields=[]),
                )
            },
            references={
                "taxonomy": ReferenceEntityConfig(
                    kind=ReferenceKind.HIERARCHICAL,
                    connector=ConnectorConfig(
                        type=ConnectorType.DERIVED,
                        source="occurrences",
                        extraction=ExtractionConfig(
                            levels=[
                                HierarchyLevel(name="family", column="family"),
                                HierarchyLevel(name="genus", column="genus"),
                                HierarchyLevel(name="species", column="species"),
                            ],
                            id_column="id_taxonref",
                            name_column="taxaname",
                            id_strategy="hash",
                        ),
                    ),
                    schema=EntitySchema(id_field="id", fields=[]),
                    hierarchy=HierarchyConfig(
                        strategy=HierarchyStrategy.ADJACENCY_LIST,
                        levels=["family", "genus", "species"],
                    ),
                )
            },
        )
    )

    # 3. Execute import
    db_path = tmp_path / "test.duckdb"
    service = ImporterService(str(db_path))
    result = service.import_all(config)

    assert "Import completed successfully" in result

    # 4. Verify dataset table
    occ_df = pd.read_sql("SELECT * FROM dataset_occurrences", service.db.engine)
    assert len(occ_df) == 4

    # 5. Verify derived taxonomy table
    taxo_df = pd.read_sql(
        "SELECT * FROM entity_taxonomy ORDER BY level, id", service.db.engine
    )

    # Should have: 2 families (Arecaceae, Cunoniaceae), 2 genera, 3 species = 7 total
    assert len(taxo_df) == 7

    families = taxo_df[taxo_df["level"] == 0]
    genera = taxo_df[taxo_df["level"] == 1]
    species = taxo_df[taxo_df["level"] == 2]

    assert len(families) == 2
    assert set(families["rank_value"]) == {"Arecaceae", "Cunoniaceae"}

    assert len(genera) == 2
    assert set(genera["rank_value"]) == {"Burretiokentia", "Codia"}

    assert len(species) == 3
    assert set(species["rank_value"]) == {"vieillardii", "koghiensis", "mackeeana"}

    # 6. Verify hierarchy
    arecaceae_id = families[families["rank_value"] == "Arecaceae"]["id"].iloc[0]
    burretiokentia = genera[genera["rank_value"] == "Burretiokentia"].iloc[0]
    assert burretiokentia["parent_id"] == arecaceae_id

    # 7. Verify registry metadata
    entity = service.registry.get("taxonomy")
    assert entity is not None
    assert entity.config["derived"]["source_entity"] == "occurrences"
    assert entity.config["derived"]["id_strategy"] == "hash"
    assert entity.config["derived"]["extraction_levels"] == [
        "family",
        "genus",
        "species",
    ]


@pytest.mark.integration
def test_circular_dependency_detection(tmp_path):
    """Test that circular dependencies are detected and rejected."""
    config = GenericImportConfig(
        entities=EntitiesConfig(
            references={
                "ref_a": ReferenceEntityConfig(
                    connector=ConnectorConfig(
                        type=ConnectorType.DERIVED,
                        source="ref_b",
                        extraction=ExtractionConfig(
                            levels=[HierarchyLevel(name="level1", column="col1")]
                        ),
                    ),
                    schema=EntitySchema(id_field="id", fields=[]),
                ),
                "ref_b": ReferenceEntityConfig(
                    connector=ConnectorConfig(
                        type=ConnectorType.DERIVED,
                        source="ref_a",
                        extraction=ExtractionConfig(
                            levels=[HierarchyLevel(name="level1", column="col1")]
                        ),
                    ),
                    schema=EntitySchema(id_field="id", fields=[]),
                ),
            }
        )
    )

    db_path = tmp_path / "test.duckdb"
    service = ImporterService(str(db_path))

    with pytest.raises(ValidationError, match="Circular dependency"):
        service.import_all(config)


@pytest.mark.integration
def test_source_not_found_error(tmp_path):
    """Test error when source entity doesn't exist."""
    config = GenericImportConfig(
        entities=EntitiesConfig(
            references={
                "taxonomy": ReferenceEntityConfig(
                    connector=ConnectorConfig(
                        type=ConnectorType.DERIVED,
                        source="nonexistent",
                        extraction=ExtractionConfig(
                            levels=[HierarchyLevel(name="family", column="family")]
                        ),
                    ),
                    schema=EntitySchema(id_field="id", fields=[]),
                )
            }
        )
    )

    db_path = tmp_path / "test.duckdb"
    service = ImporterService(str(db_path))

    with pytest.raises(ValidationError, match="Source entity 'nonexistent' not found"):
        service.import_all(config)


@pytest.mark.integration
def test_import_phases_order(tmp_path):
    """Test that imports happen in correct order: datasets → derived → direct."""
    # Create files
    occurrences_csv = tmp_path / "occurrences.csv"
    pd.DataFrame(
        {
            "id": [1],
            "family": ["Arecaceae"],
        }
    ).to_csv(occurrences_csv, index=False)

    direct_ref_csv = tmp_path / "direct.csv"
    pd.DataFrame(
        {
            "id": [1],
            "name": ["ref1"],
        }
    ).to_csv(direct_ref_csv, index=False)

    config = GenericImportConfig(
        entities=EntitiesConfig(
            datasets={
                "occurrences": DatasetEntityConfig(
                    connector=ConnectorConfig(
                        type=ConnectorType.FILE, path=str(occurrences_csv)
                    ),
                    schema=EntitySchema(id_field="id", fields=[]),
                )
            },
            references={
                # Define derived first (but should import after datasets)
                "taxonomy": ReferenceEntityConfig(
                    connector=ConnectorConfig(
                        type=ConnectorType.DERIVED,
                        source="occurrences",
                        extraction=ExtractionConfig(
                            levels=[HierarchyLevel(name="family", column="family")]
                        ),
                    ),
                    schema=EntitySchema(id_field="id", fields=[]),
                ),
                # Define direct second (but should import last)
                "direct": ReferenceEntityConfig(
                    connector=ConnectorConfig(
                        type=ConnectorType.FILE, path=str(direct_ref_csv)
                    ),
                    schema=EntitySchema(id_field="id", fields=[]),
                ),
            },
        )
    )

    db_path = tmp_path / "test.duckdb"
    service = ImporterService(str(db_path))
    result = service.import_all(config)

    # Verify result messages show correct order
    assert "[Dataset]" in result
    assert "[Derived Ref]" in result
    assert "[Direct Ref]" in result

    # Verify all tables exist
    assert service.db.has_table("dataset_occurrences")
    assert service.db.has_table("entity_taxonomy")
    assert service.db.has_table("entity_direct")


def test_multi_feature_import_reprojects_to_wgs84(tmp_path, monkeypatch):
    """Multi-feature spatial imports should normalise geometries to WGS84."""
    db_path = tmp_path / "multi_feature.duckdb"
    db = Database(str(db_path))
    registry = EntityRegistry(db)
    importer = GenericImporter(db, registry)

    # Geometry defined in EPSG:3163 (New Caledonia projected CRS)
    projected_point = Point(500000, 200000)
    gdf_projected = gpd.GeoDataFrame(
        {"geometry": [projected_point], "nom": ["Feature A"]},
        crs="EPSG:3163",
    )

    # Ensure importer reads our synthetic data regardless of file contents
    monkeypatch.setattr(
        "niamoto.core.imports.engine.gpd.read_file",
        lambda path: gdf_projected.copy(),
    )

    fake_source = tmp_path / "communes.gpkg"
    fake_source.write_bytes(b"")  # Path must exist for the importer

    sources = [
        MultiFeatureSource(name="Communes", path=str(fake_source), name_field="nom"),
    ]

    result = importer.import_multi_feature(
        entity_name="shapes_test",
        table_name="entity_shapes_test",
        sources=sources,
        kind=EntityKind.REFERENCE,
        id_field="id",
    )

    assert result.rows == 2  # One type node + one feature

    df = pd.read_sql(
        'SELECT name, location, shape_type FROM "entity_shapes_test"',
        db.engine,
    )
    shape_row = df[df["shape_type"] == "shape"].iloc[0]
    geom = wkt.loads(shape_row["location"])

    # Coordinates must now be in longitude/latitude range
    assert -180 <= geom.x <= 180
    assert -90 <= geom.y <= 90

    transformer = Transformer.from_crs("EPSG:3163", "EPSG:4326", always_xy=True)
    expected_lon, expected_lat = transformer.transform(
        projected_point.x, projected_point.y
    )
    assert geom.x == pytest.approx(expected_lon, abs=1e-5)
    assert geom.y == pytest.approx(expected_lat, abs=1e-5)
