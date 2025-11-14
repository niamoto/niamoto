"""Tests for GUI API models."""

import pytest
from pydantic import ValidationError

from niamoto.gui.api.models import (
    ConfigSection,
    ImportConfig,
    TransformConfig,
    ExportConfig,
    NiamotoConfig,
    ValidationResponse,
    GenerateResponse,
)


class TestConfigSection:
    """Test ConfigSection base model."""

    def test_config_section_creation(self):
        """Test creating a ConfigSection instance."""
        section = ConfigSection()
        assert isinstance(section, ConfigSection)


class TestImportConfig:
    """Test ImportConfig model."""

    def test_import_config_empty(self):
        """Test creating empty ImportConfig."""
        config = ImportConfig()
        assert config.taxonomy is None
        assert config.occurrences is None
        assert config.plots is None
        assert config.shapes is None

    def test_import_config_with_taxonomy(self):
        """Test ImportConfig with taxonomy."""
        data = {"taxonomy": {"source": "csv", "path": "taxonomy.csv"}}
        config = ImportConfig(**data)
        assert config.taxonomy == {"source": "csv", "path": "taxonomy.csv"}
        assert config.occurrences is None

    def test_import_config_with_occurrences(self):
        """Test ImportConfig with occurrences."""
        data = {
            "occurrences": {
                "source": "csv",
                "path": "occurrences.csv",
                "fields": ["id", "taxon", "location"],
            }
        }
        config = ImportConfig(**data)
        assert config.occurrences["source"] == "csv"
        assert "fields" in config.occurrences

    def test_import_config_with_plots(self):
        """Test ImportConfig with plots."""
        data = {"plots": {"source": "shapefile", "path": "plots.shp"}}
        config = ImportConfig(**data)
        assert config.plots == {"source": "shapefile", "path": "plots.shp"}

    def test_import_config_with_shapes(self):
        """Test ImportConfig with shapes."""
        data = {
            "shapes": [
                {"name": "provinces", "path": "provinces.shp"},
                {"name": "regions", "path": "regions.shp"},
            ]
        }
        config = ImportConfig(**data)
        assert len(config.shapes) == 2
        assert config.shapes[0]["name"] == "provinces"

    def test_import_config_with_all_fields(self):
        """Test ImportConfig with all fields populated."""
        data = {
            "taxonomy": {"source": "csv", "path": "taxonomy.csv"},
            "occurrences": {"source": "csv", "path": "occurrences.csv"},
            "plots": {"source": "shapefile", "path": "plots.shp"},
            "shapes": [{"name": "provinces", "path": "provinces.shp"}],
        }
        config = ImportConfig(**data)
        assert config.taxonomy is not None
        assert config.occurrences is not None
        assert config.plots is not None
        assert len(config.shapes) == 1


class TestTransformConfig:
    """Test TransformConfig model."""

    def test_transform_config_creation(self):
        """Test creating TransformConfig instance."""
        config = TransformConfig()
        assert isinstance(config, TransformConfig)

    def test_transform_config_is_flexible(self):
        """Test that TransformConfig accepts any structure."""
        # Since it inherits from ConfigSection with pass, it should accept any fields
        config = TransformConfig()
        assert isinstance(config, ConfigSection)


class TestExportConfig:
    """Test ExportConfig model."""

    def test_export_config_empty(self):
        """Test creating empty ExportConfig."""
        config = ExportConfig()
        assert config.site is None
        assert config.exports is None

    def test_export_config_with_site(self):
        """Test ExportConfig with site configuration."""
        data = {"site": {"title": "Niamoto Portal", "description": "Biodiversity data"}}
        config = ExportConfig(**data)
        assert config.site["title"] == "Niamoto Portal"
        assert config.site["description"] == "Biodiversity data"

    def test_export_config_with_exports(self):
        """Test ExportConfig with exports list."""
        data = {
            "exports": [
                {"name": "web", "format": "html"},
                {"name": "api", "format": "json"},
            ]
        }
        config = ExportConfig(**data)
        assert len(config.exports) == 2
        assert config.exports[0]["name"] == "web"

    def test_export_config_complete(self):
        """Test ExportConfig with all fields."""
        data = {
            "site": {"title": "Portal"},
            "exports": [{"name": "web", "format": "html"}],
        }
        config = ExportConfig(**data)
        assert config.site is not None
        assert config.exports is not None


class TestNiamotoConfig:
    """Test complete NiamotoConfig model."""

    def test_niamoto_config_minimal(self):
        """Test NiamotoConfig with minimal data."""
        data = {"import": {}}
        config = NiamotoConfig(**data)
        assert isinstance(config.import_config, ImportConfig)
        assert config.transform is None
        assert config.export is None

    def test_niamoto_config_with_import_alias(self):
        """Test NiamotoConfig uses 'import' alias."""
        data = {"import": {"taxonomy": {"source": "csv", "path": "taxonomy.csv"}}}
        config = NiamotoConfig(**data)
        assert config.import_config.taxonomy is not None

    def test_niamoto_config_with_transform(self):
        """Test NiamotoConfig with transform section."""
        data = {
            "import": {},
            "transform": {"groups": [{"name": "taxon", "transformers": []}]},
        }
        config = NiamotoConfig(**data)
        assert config.transform is not None
        assert "groups" in config.transform

    def test_niamoto_config_with_export(self):
        """Test NiamotoConfig with export section."""
        data = {
            "import": {},
            "export": {"site": {"title": "Test"}},
        }
        config = NiamotoConfig(**data)
        assert isinstance(config.export, ExportConfig)
        assert config.export.site["title"] == "Test"

    def test_niamoto_config_complete(self):
        """Test complete NiamotoConfig with all sections."""
        data = {
            "import": {
                "taxonomy": {"source": "csv", "path": "taxonomy.csv"},
                "occurrences": {"source": "csv", "path": "occurrences.csv"},
            },
            "transform": {"groups": []},
            "export": {
                "site": {"title": "Portal"},
                "exports": [{"name": "web"}],
            },
        }
        config = NiamotoConfig(**data)
        assert config.import_config.taxonomy is not None
        assert config.import_config.occurrences is not None
        assert config.transform is not None
        assert config.export is not None

    def test_niamoto_config_missing_import_fails(self):
        """Test that NiamotoConfig requires import section."""
        data = {}
        with pytest.raises(ValidationError, match="Field required"):
            NiamotoConfig(**data)

    def test_niamoto_config_populate_by_name(self):
        """Test that populate_by_name allows both 'import' and 'import_config'."""
        # Test with 'import' (alias)
        data1 = {"import": {}}
        config1 = NiamotoConfig(**data1)
        assert isinstance(config1.import_config, ImportConfig)

        # Test with 'import_config' (field name)
        data2 = {"import_config": {}}
        config2 = NiamotoConfig(**data2)
        assert isinstance(config2.import_config, ImportConfig)


class TestValidationResponse:
    """Test ValidationResponse model."""

    def test_validation_response_valid(self):
        """Test ValidationResponse for valid config."""
        response = ValidationResponse(valid=True)
        assert response.valid is True
        assert response.message is None
        assert response.errors is None

    def test_validation_response_invalid_with_message(self):
        """Test ValidationResponse with validation error message."""
        response = ValidationResponse(valid=False, message="Configuration is invalid")
        assert response.valid is False
        assert response.message == "Configuration is invalid"

    def test_validation_response_with_errors_list(self):
        """Test ValidationResponse with list of errors."""
        errors = ["Missing taxonomy field", "Invalid file path"]
        response = ValidationResponse(valid=False, errors=errors)
        assert response.valid is False
        assert len(response.errors) == 2
        assert "Missing taxonomy field" in response.errors

    def test_validation_response_complete(self):
        """Test ValidationResponse with all fields."""
        response = ValidationResponse(
            valid=False,
            message="Validation failed",
            errors=["Error 1", "Error 2"],
        )
        assert response.valid is False
        assert response.message == "Validation failed"
        assert len(response.errors) == 2


class TestGenerateResponse:
    """Test GenerateResponse model."""

    def test_generate_response_creation(self):
        """Test creating GenerateResponse."""
        response = GenerateResponse(
            import_yaml="import:\n  taxonomy: {}",
            transform_yaml="transform:\n  groups: []",
            export_yaml="export:\n  site: {}",
        )
        assert "import:" in response.import_yaml
        assert "transform:" in response.transform_yaml
        assert "export:" in response.export_yaml

    def test_generate_response_all_fields_required(self):
        """Test that all YAML fields are required."""
        # Missing fields should raise ValidationError
        with pytest.raises(ValidationError):
            GenerateResponse(import_yaml="test")

        with pytest.raises(ValidationError):
            GenerateResponse(import_yaml="test", transform_yaml="test")

    def test_generate_response_empty_strings(self):
        """Test GenerateResponse with empty YAML strings."""
        response = GenerateResponse(
            import_yaml="",
            transform_yaml="",
            export_yaml="",
        )
        assert response.import_yaml == ""
        assert response.transform_yaml == ""
        assert response.export_yaml == ""

    def test_generate_response_multiline_yaml(self):
        """Test GenerateResponse with multiline YAML."""
        import_yaml = """import:
  taxonomy:
    source: csv
    path: taxonomy.csv
  occurrences:
    source: csv
    path: occurrences.csv"""

        transform_yaml = """transform:
  groups:
    - name: taxon
      transformers:
        - plugin: field_aggregator"""

        export_yaml = """export:
  site:
    title: Niamoto Portal
  exports:
    - name: web
      format: html"""

        response = GenerateResponse(
            import_yaml=import_yaml,
            transform_yaml=transform_yaml,
            export_yaml=export_yaml,
        )

        assert "taxonomy:" in response.import_yaml
        assert "groups:" in response.transform_yaml
        assert "site:" in response.export_yaml
