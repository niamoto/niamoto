"""Tests for the generic ImporterService."""

from __future__ import annotations

from unittest import mock

import pandas as pd
import pytest

from niamoto.common.exceptions import ValidationError, FileReadError
from niamoto.common.database import Database
from niamoto.core.services.importer import ImporterService
from niamoto.core.imports.engine import ImportResult, GenericImporter
from niamoto.core.imports.registry import EntityKind, EntityRegistry
from niamoto.core.imports.config_models import (
    GenericImportConfig,
    ReferenceEntityConfig,
    DatasetEntityConfig,
    ConnectorConfig,
    ConnectorType,
    EntitySchema,
    EntitiesConfig,
)


@pytest.fixture
def mock_database():
    """Mock Database with spec to catch invalid method calls."""
    with mock.patch("niamoto.core.services.importer.Database") as db_cls:
        # Use spec= to ensure only valid Database methods can be called
        db_instance = mock.Mock(spec=Database)
        db_instance.engine = mock.Mock()
        db_instance.has_table = mock.Mock(return_value=False)
        db_cls.return_value = db_instance
        yield db_cls


@pytest.fixture
def mock_registry():
    """Mock EntityRegistry with spec to catch invalid method calls."""
    with mock.patch("niamoto.core.services.importer.EntityRegistry") as registry_cls:
        # Use spec= to ensure only valid EntityRegistry methods can be called
        registry = mock.Mock(spec=EntityRegistry)
        registry_cls.return_value = registry
        yield registry


@pytest.fixture
def mock_engine(monkeypatch):
    """Mock GenericImporter with spec to catch invalid method calls."""
    # Use spec= to ensure only valid GenericImporter methods can be called
    importer_mock = mock.Mock(spec=GenericImporter)
    monkeypatch.setattr(
        "niamoto.core.services.importer.GenericImporter",
        lambda db, registry: importer_mock,
    )
    return importer_mock


@pytest.fixture
def service(mock_database, mock_registry, mock_engine):
    return ImporterService("/tmp/test.db")


def test_import_reference_creates_registry_entry(service, mock_engine, tmp_path):
    """Test importing a reference entity (e.g., species taxonomy)."""
    csv_path = tmp_path / "species.csv"
    df = pd.DataFrame({"species_id": [1, 2], "name": ["Species A", "Species B"]})
    df.to_csv(csv_path, index=False)

    mock_engine.import_from_csv.return_value = ImportResult(
        rows=2, table="entity_species"
    )

    config = ReferenceEntityConfig(
        connector=ConnectorConfig(type=ConnectorType.FILE, path=str(csv_path)),
        schema=EntitySchema(id_field="species_id", fields=[]),
    )

    msg = service.import_reference("species", config)

    assert "Imported 2 records into entity_species" in msg
    mock_engine.import_from_csv.assert_called_once()
    kwargs = mock_engine.import_from_csv.call_args.kwargs
    assert kwargs["entity_name"] == "species"
    assert kwargs["table_name"] == "entity_species"
    assert kwargs["kind"] is EntityKind.REFERENCE


def test_import_dataset(service, mock_engine, tmp_path):
    """Test importing a dataset entity (e.g., observations)."""
    csv_path = tmp_path / "observations.csv"
    pd.DataFrame({"occurrence_id": [1], "species_code": ["SP01"]}).to_csv(
        csv_path, index=False
    )

    mock_engine.import_from_csv.return_value = ImportResult(
        rows=1, table="dataset_observations"
    )

    config = DatasetEntityConfig(
        connector=ConnectorConfig(type=ConnectorType.FILE, path=str(csv_path)),
        schema=EntitySchema(id_field="occurrence_id", fields=[]),
    )

    msg = service.import_dataset("observations", config)

    assert "Imported 1 records into dataset_observations" in msg
    kwargs = mock_engine.import_from_csv.call_args.kwargs
    assert kwargs["entity_name"] == "observations"
    assert kwargs["kind"] is EntityKind.DATASET


def test_import_reference_with_reset_table(service, mock_engine, tmp_path):
    """Test importing a reference with table reset."""
    csv_path = tmp_path / "sites.csv"
    pd.DataFrame({"site_id": [1], "site_name": ["Site A"]}).to_csv(
        csv_path, index=False
    )

    # Mock table exists
    service.db.has_table = mock.Mock(return_value=True)
    service.db.execute_sql = mock.Mock()

    mock_engine.import_from_csv.return_value = ImportResult(
        rows=1, table="entity_sites"
    )

    config = ReferenceEntityConfig(
        connector=ConnectorConfig(type=ConnectorType.FILE, path=str(csv_path)),
        schema=EntitySchema(id_field="site_id", fields=[]),
    )

    msg = service.import_reference("sites", config, reset_table=True)

    # Verify table was dropped
    service.db.execute_sql.assert_called_once_with("DROP TABLE IF EXISTS entity_sites")
    assert "Imported 1 records" in msg


def test_import_reference_missing_file(service, mock_engine, tmp_path):
    """Test that importing from a non-existent file raises FileReadError."""
    config = ReferenceEntityConfig(
        connector=ConnectorConfig(
            type=ConnectorType.FILE, path=str(tmp_path / "nonexistent.csv")
        ),
        schema=EntitySchema(id_field="id", fields=[]),
    )

    with pytest.raises(FileReadError):
        service.import_reference("test", config)


def test_import_all(service, mock_engine, tmp_path):
    """Test importing all entities from a complete configuration."""
    # Create test files
    species_csv = tmp_path / "species.csv"
    pd.DataFrame({"species_id": [1, 2]}).to_csv(species_csv, index=False)

    obs_csv = tmp_path / "observations.csv"
    pd.DataFrame({"occurrence_id": [1]}).to_csv(obs_csv, index=False)

    # Mock engine returns
    def mock_import(entity_name, **kwargs):
        return ImportResult(
            rows=2 if entity_name == "species" else 1, table=kwargs["table_name"]
        )

    mock_engine.import_from_csv.side_effect = mock_import

    # Create generic config
    config = GenericImportConfig(
        entities=EntitiesConfig(
            references={
                "species": ReferenceEntityConfig(
                    connector=ConnectorConfig(
                        type=ConnectorType.FILE, path=str(species_csv)
                    ),
                    schema=EntitySchema(id_field="species_id", fields=[]),
                )
            },
            datasets={
                "observations": DatasetEntityConfig(
                    connector=ConnectorConfig(
                        type=ConnectorType.FILE, path=str(obs_csv)
                    ),
                    schema=EntitySchema(id_field="occurrence_id", fields=[]),
                )
            },
        )
    )

    result = service.import_all(config)

    assert "Import completed successfully" in result
    assert "entity_species" in result
    assert "dataset_observations" in result
    assert mock_engine.import_from_csv.call_count == 2


def test_import_reference_invalid_empty_name(service):
    """Test that empty entity name raises ValidationError."""
    config = ReferenceEntityConfig(
        connector=ConnectorConfig(type=ConnectorType.FILE, path="/tmp/test.csv"),
        schema=EntitySchema(id_field="id", fields=[]),
    )

    with pytest.raises(ValidationError, match="Entity name cannot be empty"):
        service.import_reference("", config)


def test_import_dataset_invalid_empty_name(service):
    """Test that empty entity name raises ValidationError."""
    config = DatasetEntityConfig(
        connector=ConnectorConfig(type=ConnectorType.FILE, path="/tmp/test.csv"),
        schema=EntitySchema(id_field="id", fields=[]),
    )

    with pytest.raises(ValidationError, match="Entity name cannot be empty"):
        service.import_dataset("", config)
