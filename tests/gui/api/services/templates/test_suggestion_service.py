"""Unit tests for suggestion_service helper resolution logic."""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional

from niamoto.gui.api.services.templates.suggestion_service import (
    _get_first_dataset_name,
    _pick_identifier_column,
    _pick_name_column,
    _resolve_entity_table,
)


class _Kind(str, Enum):
    REFERENCE = "reference"
    DATASET = "dataset"


@dataclass
class _EntityMeta:
    name: str
    kind: _Kind
    table_name: str
    config: Dict[str, Any]


class _DummyRegistry:
    def __init__(
        self,
        metadata: Optional[Dict[str, _EntityMeta]] = None,
        datasets: Optional[List[_EntityMeta]] = None,
    ):
        self.metadata = metadata or {}
        self.datasets = datasets or []

    def get(self, name: str) -> _EntityMeta:
        if name not in self.metadata:
            raise KeyError(name)
        return self.metadata[name]

    def list_entities(self, kind: Optional[Any] = None) -> List[_EntityMeta]:
        return list(self.datasets)


class _DummyDb:
    def __init__(self, existing_tables: List[str]):
        self.existing_tables = set(existing_tables)

    def has_table(self, table_name: str) -> bool:
        return table_name in self.existing_tables


def test_resolve_entity_table_prefers_registry_mapping():
    db = _DummyDb(existing_tables=["custom_reference_table", "entity_taxons"])
    registry = _DummyRegistry(
        metadata={
            "taxons": _EntityMeta(
                name="taxons",
                kind=_Kind.REFERENCE,
                table_name="custom_reference_table",
                config={},
            )
        }
    )

    resolved = _resolve_entity_table(db, "taxons", registry=registry, kind="reference")

    assert resolved == "custom_reference_table"


def test_resolve_entity_table_fallback_conventions_for_reference():
    db = _DummyDb(existing_tables=["entity_plots"])

    resolved = _resolve_entity_table(db, "plots", registry=None, kind="reference")

    assert resolved == "entity_plots"


def test_pick_identifier_and_name_columns():
    columns = ["plot_uuid", "display_label", "description"]

    id_field = _pick_identifier_column(
        columns, entity_name="plots", preferred="plot_uuid"
    )
    name_field = _pick_name_column(columns, id_field, "plots")

    assert id_field == "plot_uuid"
    assert name_field == "display_label"


def test_get_first_dataset_name_prefers_registry():
    registry = _DummyRegistry(
        datasets=[
            _EntityMeta(
                name="observations",
                kind=_Kind.DATASET,
                table_name="dataset_observations",
                config={},
            )
        ]
    )
    import_config = {"entities": {"datasets": {"occurrences": {}}}}

    dataset = _get_first_dataset_name(import_config, registry=registry)

    assert dataset == "observations"
