from unittest.mock import MagicMock, Mock, patch

import pandas as pd
import pytest

from niamoto.common.exceptions import DataLoadError, DatabaseError, DatabaseQueryError
from niamoto.core.plugins.loaders.adjacency_list import AdjacencyListLoader
from niamoto.core.plugins.loaders._sql_identifier import quote_identifier
from niamoto.core.plugins.loaders.direct_reference import DirectReferenceLoader
from niamoto.core.plugins.loaders.join_table import JoinTableLoader
from niamoto.core.plugins.loaders.nested_set import NestedSetLoader
from niamoto.core.plugins.loaders.spatial import SpatialLoader
from niamoto.core.plugins.loaders.stats_loader import StatsLoader


def test_quote_identifier_accepts_simple_and_qualified_names():
    assert quote_identifier("entity_occurrences") == '"entity_occurrences"'
    assert quote_identifier("main.id") == '"main"."id"'


@pytest.mark.parametrize(
    "value",
    ["id) OR 1=1 --", "table; DROP TABLE plots", "bad-name", "1starts_with_digit"],
)
def test_quote_identifier_rejects_unsafe_names(value):
    with pytest.raises(ValueError, match="Invalid SQL identifier"):
        quote_identifier(value)


def _registry_missing():
    registry = Mock()
    registry.get.side_effect = DatabaseQueryError(
        query="registry_lookup", message="missing"
    )
    return registry


def test_direct_reference_rejects_unsafe_ref_key_before_read_sql():
    db = MagicMock()
    db.has_table.return_value = True
    db.get_table_columns.side_effect = lambda name: {
        "main_table": ["id", "ref_id"],
        "ref_table": ["id", "external_id"],
    }.get(name, [])
    loader = DirectReferenceLoader(db, registry=_registry_missing())
    config = {
        "plugin": "direct_reference",
        "params": {
            "data": "main_table",
            "grouping": "ref_table",
            "key": "ref_id",
            "ref_key": "external_id) OR 1=1 --",
        },
    }

    with patch("pandas.read_sql") as read_sql:
        with pytest.raises(DatabaseError, match="Invalid reference key field"):
            loader.load_data(1, config)

    read_sql.assert_not_called()


def test_join_table_rejects_unsafe_join_key_before_read_sql():
    db = MagicMock()
    db.has_table.return_value = True
    db.get_table_columns.return_value = ["id"]
    loader = JoinTableLoader(db, registry=_registry_missing())
    config = {
        "plugin": "join_table",
        "params": {
            "data": "main_table",
            "grouping": "ref_table",
            "key": "id",
            "join_table": "links",
            "keys": {
                "source": "source_id) OR 1=1 --",
                "reference": "reference_id",
            },
        },
    }

    with patch("pandas.read_sql") as read_sql:
        with pytest.raises(ValueError, match="Invalid source key field"):
            loader.load_data(1, config)

    read_sql.assert_not_called()


def test_nested_set_rejects_unsafe_table_before_sql_execution():
    db = MagicMock()
    loader = NestedSetLoader(db, registry=_registry_missing())
    config = {
        "data": "occurrences; DROP TABLE occurrences",
        "grouping": "taxons",
        "key": "taxon_id",
        "fields": {"left": "lft", "right": "rght", "parent": "parent_id"},
    }

    with pytest.raises(ValueError, match="Invalid data table name"):
        loader.load_data(1, config)

    db.connection.assert_not_called()


@pytest.mark.parametrize(
    ("field_path", "unsafe_value", "expected_message"),
    [
        (
            ("data",),
            "occurrences; DROP TABLE occurrences",
            "Invalid characters in data table name",
        ),
        (
            ("grouping",),
            "taxons; DROP TABLE taxons",
            "Invalid characters in grouping table name",
        ),
        (
            ("params", "key"),
            "taxon_id) OR 1=1 --",
            "Invalid characters in foreign key field",
        ),
        (
            ("params", "parent_field"),
            "parent_id) OR 1=1 --",
            "Invalid characters in parent field",
        ),
        (
            ("params", "hierarchy_id_field"),
            "id) OR 1=1 --",
            "Invalid characters in hierarchy id field",
        ),
    ],
)
def test_adjacency_list_rejects_unsafe_identifier_before_sql_execution(
    field_path,
    unsafe_value,
    expected_message,
):
    db = MagicMock()
    loader = AdjacencyListLoader(db, registry=_registry_missing())
    config = {
        "data": "occurrences",
        "grouping": "taxons",
        "params": {
            "key": "taxon_id",
            "parent_field": "parent_id",
            "hierarchy_id_field": "id",
        },
    }
    target = config
    for key in field_path[:-1]:
        target = target[key]
    target[field_path[-1]] = unsafe_value

    with patch("pandas.read_sql") as read_sql:
        with pytest.raises(ValueError, match=expected_message):
            loader.load_data(1, config)

    db.connection.assert_not_called()
    read_sql.assert_not_called()


def test_spatial_rejects_unsafe_geometry_field_before_sql_execution():
    db = MagicMock()
    loader = SpatialLoader(db, registry=_registry_missing())
    config = {
        "main": "occurrences",
        "reference": {"name": "plots"},
        "params": {
            "key": "geometry",
            "geometry_field": "geom) OR 1=1 --",
        },
    }

    with pytest.raises(ValueError, match="Invalid geometry field"):
        loader.load_data(1, config)

    db.execute.assert_not_called()


def test_stats_loader_rejects_unsafe_database_identifier_before_read_sql():
    db = MagicMock()
    loader = StatsLoader(db)
    config = {
        "plugin": "stats_loader",
        "data": "main_table",
        "grouping": "ref_table",
        "key": "foreign_key) OR 1=1 --",
    }

    with patch("pandas.read_sql") as read_sql:
        with pytest.raises(DataLoadError):
            loader.load_data(1, config)

    read_sql.assert_not_called()


def test_stats_loader_accepts_safe_database_identifiers():
    db = MagicMock()
    conn = MagicMock()
    conn.__enter__.return_value = conn
    conn.__exit__.return_value = False
    db.connection.return_value = conn
    loader = StatsLoader(db)
    loader.imports_config = {}
    config = {
        "plugin": "stats_loader",
        "data": "main_table",
        "grouping": "ref_table",
        "key": "foreign_key",
    }
    expected = pd.DataFrame({"id": [1]})

    with patch("pandas.read_sql", return_value=expected) as read_sql:
        result = loader.load_data(1, config)

    pd.testing.assert_frame_equal(result, expected)
    query = str(read_sql.call_args.args[0])
    assert 'FROM "main_table" m' in query
    assert 'JOIN "ref_table" ref ON m."foreign_key" = ref.id' in query
