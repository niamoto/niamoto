from niamoto.core.utils.column_detector import ColumnDetector


def test_detect_relationships_prefers_plot_identifier_key():
    relationships = ColumnDetector.detect_relationships(
        source_columns=["plot_id"],
        target_columns=["id", "plot_id", "plot_name"],
        source_sample=[
            {"plot_id": "P001"},
            {"plot_id": "P002"},
        ],
        target_sample=[
            {"id": "legacy-1", "plot_id": "P001", "plot_name": "North"},
            {"id": "legacy-2", "plot_id": "P002", "plot_name": "South"},
        ],
        source_entity_name="occurrences",
        target_entity_name="plots",
    )

    assert relationships
    best = relationships[0]
    assert best["source_field"] == "plot_id"
    assert best["target_field"] == "plot_id"


def test_detect_relationships_allows_taxon_identifier_to_match_target_id():
    relationships = ColumnDetector.detect_relationships(
        source_columns=["id_taxonref"],
        target_columns=["id", "family", "genus", "species"],
        source_sample=[
            {"id_taxonref": "101"},
            {"id_taxonref": "201"},
        ],
        target_sample=[
            {
                "id": "101",
                "family": "Araucariaceae",
                "genus": "Araucaria",
                "species": "columnaris",
            },
            {
                "id": "201",
                "family": "Araucariaceae",
                "genus": "Agathis",
                "species": "lanceolata",
            },
        ],
        source_entity_name="occurrences",
        target_entity_name="taxons",
    )

    assert relationships
    assert relationships[0]["target_field"] == "id"
    assert relationships[0]["confidence"] >= 0.7


def test_detect_relationships_penalizes_locality_as_hard_id_join():
    relationships = ColumnDetector.detect_relationships(
        source_columns=["locality_name"],
        target_columns=["id", "locality_name"],
        source_sample=[
            {"locality_name": "Aoupinie"},
            {"locality_name": "Mont Panié"},
        ],
        target_sample=[
            {"id": "Aoupinie", "locality_name": "Aoupinie"},
            {"id": "Mont Panié", "locality_name": "Mont Panié"},
        ],
        source_entity_name="occurrences",
        target_entity_name="localities",
    )

    assert relationships
    best = relationships[0]
    assert best["target_field"] == "locality_name"
    assert all(
        not (
            relationship["target_field"] == "id"
            and relationship["confidence"] >= best["confidence"]
        )
        for relationship in relationships
    )
