from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import Mock

from niamoto.common.table_resolver import (
    quote_identifier,
    resolve_dataset_table,
    resolve_dataset_table_name,
    resolve_entity_table,
    resolve_existing_table,
    resolve_reference_table_name,
)


def test_quote_identifier_uses_sqlalchemy_identifier_preparer(monkeypatch) -> None:
    mock_preparer = Mock()
    mock_preparer.quote.return_value = '"taxons"'
    mock_dialect = SimpleNamespace(identifier_preparer=mock_preparer)
    monkeypatch.setattr(
        "niamoto.common.table_resolver.inspect",
        lambda engine: SimpleNamespace(dialect=mock_dialect),
    )

    db = SimpleNamespace(engine=object())
    assert quote_identifier(db, "taxons") == '"taxons"'


def test_resolve_dataset_and_reference_table_names_match_case_insensitively() -> None:
    table_names = ["Dataset_Occurrences", "entity_taxons", "plots"]

    assert (
        resolve_dataset_table_name(table_names, "occurrences") == "Dataset_Occurrences"
    )
    assert resolve_reference_table_name(table_names, "taxons") == "entity_taxons"


def test_resolve_existing_table_checks_prefixes_in_order() -> None:
    db = Mock()
    db.has_table.side_effect = lambda name: name == "dataset_occurrences"

    assert (
        resolve_existing_table(db, "occurrences", ("dataset_", "entity_", ""))
        == "dataset_occurrences"
    )
    assert resolve_dataset_table(db, "missing") is None


def test_resolve_entity_table_prefers_registry_metadata_when_table_exists() -> None:
    db = Mock()
    db.has_table.side_effect = lambda name: name == "custom_taxons"
    registry = Mock()
    registry.get.return_value = SimpleNamespace(
        kind=SimpleNamespace(value="reference"),
        table_name="custom_taxons",
    )

    assert (
        resolve_entity_table(db, "taxons", registry=registry, kind="reference")
        == "custom_taxons"
    )


def test_resolve_entity_table_falls_back_to_kind_specific_prefixes() -> None:
    db = Mock()
    db.has_table.side_effect = lambda name: name == "entity_taxons"

    assert (
        resolve_entity_table(db, "taxons", registry=None, kind="reference")
        == "entity_taxons"
    )
