from __future__ import annotations

from niamoto.common.hierarchy_context import (
    HierarchyMetadata,
    build_hierarchy_contexts,
    detect_hierarchy_metadata,
    normalize_hierarchy_key,
)


def test_normalize_hierarchy_key_removes_accents_and_punctuation() -> None:
    assert normalize_hierarchy_key("Forêt humide / Sud") == "foret_humide_sud"
    assert normalize_hierarchy_key(None) == ""


def test_detect_hierarchy_metadata_returns_parent_based_shape() -> None:
    metadata = detect_hierarchy_metadata(
        ["ID", "Parent_ID", "Rank_Name", "Full_Name"],
        join_field="ID",
    )

    assert metadata == HierarchyMetadata(
        id_field="ID",
        join_field="ID",
        parent_field="Parent_ID",
        left_field=None,
        right_field=None,
        rank_field="Rank_Name",
        name_field="Full_Name",
    )


def test_detect_hierarchy_metadata_accepts_nested_set_without_parent_id() -> None:
    metadata = detect_hierarchy_metadata(
        ["id", "lft", "rght", "rank", "label"],
        join_field="missing_join",
    )

    assert metadata == HierarchyMetadata(
        id_field="id",
        join_field="id",
        parent_field=None,
        left_field="lft",
        right_field="rght",
        rank_field="rank",
        name_field="label",
    )


def test_detect_hierarchy_metadata_returns_none_when_required_columns_are_missing() -> (
    None
):
    assert detect_hierarchy_metadata(["id", "name", "parent_id"]) is None


def test_build_hierarchy_contexts_uses_parent_field_lineage() -> None:
    metadata = HierarchyMetadata(
        id_field="id",
        join_field="id",
        parent_field="parent_id",
        left_field=None,
        right_field=None,
        rank_field="rank_name",
        name_field="full_name",
    )
    rows = [
        {"id": 1, "parent_id": None, "rank_name": "Kingdom", "full_name": "Animalia"},
        {"id": 2, "parent_id": 1, "rank_name": "Phylum", "full_name": "Chordata"},
        {"id": 3, "parent_id": 2, "rank_name": "Class", "full_name": "Aves"},
    ]

    contexts = build_hierarchy_contexts(rows, metadata)

    assert contexts[3]["kingdom"]["name"] == "Animalia"
    assert contexts[3]["kingdom"]["distance"] == 2
    assert contexts[3]["phylum"]["name"] == "Chordata"
    assert contexts[3]["class"]["distance"] == 0


def test_build_hierarchy_contexts_can_infer_parents_from_nested_set() -> None:
    metadata = HierarchyMetadata(
        id_field="id",
        join_field="id",
        parent_field=None,
        left_field="lft",
        right_field="rght",
        rank_field="rank",
        name_field="name",
    )
    rows = [
        {"id": 1, "lft": 1, "rght": 6, "rank": "Kingdom", "name": "Plantae"},
        {"id": 2, "lft": 2, "rght": 5, "rank": "Family", "name": "Myrtaceae"},
        {"id": 3, "lft": 3, "rght": 4, "rank": "Species", "name": "Syzygium"},
    ]

    contexts = build_hierarchy_contexts(rows, metadata)

    assert contexts[3]["kingdom"]["name"] == "Plantae"
    assert contexts[3]["family"]["name"] == "Myrtaceae"
