"""Tests for nested_set loader plugin migration to EntityRegistry."""

import pytest
import pandas as pd
from unittest.mock import Mock, MagicMock

from niamoto.core.plugins.loaders.nested_set import NestedSetLoader
from niamoto.core.imports.registry import EntityRegistry, EntityKind


@pytest.fixture
def mock_db():
    """Create a mock database."""
    db = Mock()
    # Create a mock engine instead of real SQLAlchemy engine
    mock_engine = Mock()
    db.engine = mock_engine
    return db


@pytest.fixture
def mock_registry(mock_db):
    """Create a mock EntityRegistry."""
    registry = Mock(spec=EntityRegistry)

    # Mock entity metadata for resolution
    mock_taxons = Mock()
    mock_taxons.table_name = "entity_taxons"
    mock_taxons.kind = EntityKind.REFERENCE

    mock_occurrences = Mock()
    mock_occurrences.table_name = "entity_occurrences"
    mock_occurrences.kind = EntityKind.DATASET

    # Setup registry.get() to return appropriate metadata
    def get_entity(name):
        if name == "taxons":
            return mock_taxons
        elif name == "occurrences":
            return mock_occurrences
        else:
            raise Exception(f"Entity not found: {name}")

    registry.get = Mock(side_effect=get_entity)
    return registry


@pytest.fixture
def loader(mock_db, mock_registry):
    """Create a NestedSetLoader instance."""
    return NestedSetLoader(mock_db, registry=mock_registry)


class TestNestedSetLoaderInitialization:
    """Test loader initialization with EntityRegistry."""

    def test_init_with_registry(self, mock_db, mock_registry):
        """Test initialization with provided registry."""
        loader = NestedSetLoader(mock_db, registry=mock_registry)
        assert loader.db == mock_db
        assert loader.registry == mock_registry

    def test_init_without_registry(self, mock_db):
        """Test initialization creates registry if not provided."""
        loader = NestedSetLoader(mock_db)
        assert loader.db == mock_db
        assert loader.registry is not None
        assert isinstance(loader.registry, EntityRegistry)


class TestTableNameResolution:
    """Test _resolve_table_name method."""

    def test_resolve_entity_name_to_table(self, loader, mock_registry):
        """Test resolving logical entity name to physical table name."""
        result = loader._resolve_table_name("taxons")
        assert result == "entity_taxons"
        mock_registry.get.assert_called_once_with("taxons")

    def test_resolve_occurrences(self, loader, mock_registry):
        """Test resolving occurrences entity."""
        result = loader._resolve_table_name("occurrences")
        assert result == "entity_occurrences"

    def test_fallback_on_registry_error(self, loader, mock_registry):
        """Test fallback to original name if registry lookup fails."""
        # Make registry.get raise exception for unknown entity
        result = loader._resolve_table_name("unknown_entity")
        assert result == "unknown_entity"

    def test_fallback_with_physical_table_name(self, loader, mock_registry):
        """Test backward compatibility with physical table names."""
        # Simulate config using physical table name directly
        mock_registry.get.side_effect = Exception("Not in registry")
        result = loader._resolve_table_name("some_physical_table")
        assert result == "some_physical_table"


class TestConfigValidation:
    """Test configuration validation."""

    def test_validate_config_with_params(self, loader):
        """Test validation with properly structured params."""
        config = {
            "plugin": "nested_set",
            "params": {
                "key": "taxon_id",
                "ref_key": "id",
                "fields": {"left": "lft", "right": "rght", "parent": "parent_id"},
            },
        }
        validated = loader.validate_config(config)
        assert validated.params.key == "taxon_id"
        assert validated.params.ref_key == "id"
        assert validated.params.fields["left"] == "lft"

    def test_validate_config_backward_compatibility(self, loader):
        """Test backward compatibility with top-level fields."""
        config = {
            "key": "taxon_id",
            "ref_key": "id",
            "fields": {"left": "lft", "right": "rght", "parent": "parent_id"},
        }
        validated = loader.validate_config(config)
        assert validated.params.key == "taxon_id"
        assert validated.params.ref_key == "id"


class TestLoadDataWithRegistry:
    """Test load_data method uses EntityRegistry for table resolution."""

    def test_load_data_resolves_table_names(
        self, loader, mock_db, mock_registry, monkeypatch
    ):
        """Test that load_data resolves entity names via registry."""
        # Setup test data
        config = {
            "data": "occurrences",
            "grouping": "taxons",
            "key": "taxon_id",
            "ref_key": "id",
            "fields": {"left": "lft", "right": "rght", "parent": "parent_id"},
        }

        # Mock database connection and queries
        mock_conn = MagicMock()
        mock_result = Mock()
        mock_result.fetchone.return_value = (1, 10)  # lft=1, rght=10
        mock_conn.execute.return_value = mock_result
        mock_conn.__enter__ = Mock(return_value=mock_conn)
        mock_conn.__exit__ = Mock(return_value=False)

        mock_db.engine.connect.return_value = mock_conn

        # Mock pandas read_sql to avoid actual DB query
        mock_df = pd.DataFrame({"id": [1, 2], "name": ["test1", "test2"]})
        monkeypatch.setattr("pandas.read_sql", Mock(return_value=mock_df))

        # Execute load_data
        result = loader.load_data(group_id=1, config=config)

        # Verify registry was called to resolve table names
        assert mock_registry.get.call_count >= 2
        mock_registry.get.assert_any_call("occurrences")
        mock_registry.get.assert_any_call("taxons")

        # Verify result is a DataFrame
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 2

    def test_load_data_with_custom_entity_names(self, loader, mock_db, monkeypatch):
        """Test load_data works with custom entity names like 'flora', 'observations'."""
        # Setup custom entity registry
        custom_registry = Mock(spec=EntityRegistry)

        mock_flora = Mock()
        mock_flora.table_name = "entity_flora"

        mock_observations = Mock()
        mock_observations.table_name = "entity_observations"

        def get_custom_entity(name):
            if name == "flora":
                return mock_flora
            elif name == "observations":
                return mock_observations
            raise Exception(f"Entity not found: {name}")

        custom_registry.get = Mock(side_effect=get_custom_entity)

        # Create loader with custom registry
        custom_loader = NestedSetLoader(mock_db, registry=custom_registry)

        config = {
            "data": "observations",
            "grouping": "flora",
            "key": "flora_id",
            "ref_key": "id",
            "fields": {"left": "lft", "right": "rght", "parent": "parent_id"},
        }

        # Mock database
        mock_conn = MagicMock()
        mock_result = Mock()
        mock_result.fetchone.return_value = (5, 15)
        mock_conn.execute.return_value = mock_result
        mock_conn.__enter__ = Mock(return_value=mock_conn)
        mock_conn.__exit__ = Mock(return_value=False)
        mock_db.engine.connect.return_value = mock_conn

        mock_df = pd.DataFrame({"id": [10, 20]})
        monkeypatch.setattr("pandas.read_sql", Mock(return_value=mock_df))

        # Execute
        result = custom_loader.load_data(group_id=5, config=config)

        # Verify custom entities were resolved
        custom_registry.get.assert_any_call("observations")
        custom_registry.get.assert_any_call("flora")

        assert isinstance(result, pd.DataFrame)


class TestBackwardCompatibility:
    """Test backward compatibility with configs using physical table names."""

    def test_load_data_with_physical_table_names(
        self, loader, mock_db, mock_registry, monkeypatch
    ):
        """Test that configs with physical table names still work (fallback)."""
        # Simulate config using physical table names directly
        config = {
            "data": "some_physical_table",
            "grouping": "another_physical_table",
            "key": "taxon_id",
            "ref_key": "id",
            "fields": {"left": "lft", "right": "rght", "parent": "parent_id"},
        }

        # Make registry fail for these names (not in registry)
        mock_registry.get.side_effect = Exception("Not found")

        # Mock database
        mock_conn = MagicMock()
        mock_result = Mock()
        mock_result.fetchone.return_value = (1, 5)
        mock_conn.execute.return_value = mock_result
        mock_conn.__enter__ = Mock(return_value=mock_conn)
        mock_conn.__exit__ = Mock(return_value=False)
        mock_db.engine.connect.return_value = mock_conn

        mock_df = pd.DataFrame({"id": [100]})
        monkeypatch.setattr("pandas.read_sql", Mock(return_value=mock_df))

        # Should not raise exception, should fallback to physical names
        result = loader.load_data(group_id=1, config=config)

        assert isinstance(result, pd.DataFrame)
        # Registry was attempted but failed (fallback worked)
        assert mock_registry.get.called


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_load_data_empty_node(self, loader, mock_db):
        """Test load_data returns empty DataFrame when node not found."""
        config = {
            "data": "occurrences",
            "grouping": "taxons",
            "key": "taxon_id",
            "fields": {"left": "lft", "right": "rght", "parent": "parent_id"},
        }

        # Mock connection returning no node
        mock_conn = MagicMock()
        mock_result = Mock()
        mock_result.fetchone.return_value = None
        mock_conn.execute.return_value = mock_result
        mock_conn.__enter__ = Mock(return_value=mock_conn)
        mock_conn.__exit__ = Mock(return_value=False)
        mock_db.engine.connect.return_value = mock_conn

        result = loader.load_data(group_id=999, config=config)

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 0
