"""
Tests for the Niamoto to Darwin Core Occurrence transformer.
"""

import json
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock

import pytest

from niamoto.core.plugins.transformers.formats.niamoto_to_dwc_occurrence import (
    NiamotoDwCTransformer,
    NiamotoDwCConfig,
)
from niamoto.core.plugins.models import DwcTransformerParams
from niamoto.common.exceptions import DataTransformError


@pytest.fixture
def mock_db():
    """Create a mock database."""
    db = Mock()
    db.engine = Mock()
    return db


@pytest.fixture
def transformer(mock_db):
    """Create a transformer instance."""
    return NiamotoDwCTransformer(mock_db)


@pytest.fixture
def sample_taxon_data():
    """Sample taxon data."""
    return {
        "id": 123,
        "taxon_id": 123,
        "full_name": "Araucaria columnaris (Forster) Hook.",
        "rank": "species",
        "metadata": {
            "endemic": True,
            "images": [
                {"url": "http://example.com/image1.jpg"},
                {"url": "http://example.com/image2.jpg"},
            ],
        },
    }


@pytest.fixture
def sample_occurrence_data():
    """Sample occurrence data."""
    return {
        "id": 1,
        "taxon_ref_id": 123,
        "family": "Araucariaceae",
        "elevation": 150.5,
        "month_obs": 6,
        "dbh": 35.5,
        "holdridge": 2,
        "rainfall": 1200,
        "um": True,  # ultramafic substrate
        "forest": True,
        "flower": 1,
        "fruit": 0,
        "geometry": "POINT (165.7683 -21.6461)",
    }


@pytest.fixture
def sample_mapping_config():
    """Sample mapping configuration."""
    return {
        "occurrence_list_source": "occurrences",
        "mapping": {
            "occurrenceID": {
                "generator": "unique_occurrence_id",
                "params": {"prefix": "niaocc_"},
            },
            "scientificName": "@taxon.full_name",
            "family": "@source.family",
            "decimalLatitude": {
                "generator": "format_coordinates",
                "params": {"source_field": "@source.geometry", "type": "latitude"},
            },
            "decimalLongitude": {
                "generator": "format_coordinates",
                "params": {"source_field": "@source.geometry", "type": "longitude"},
            },
            "elevation": "@source.elevation",
            "establishmentMeans": {"generator": "map_establishment_means"},
            "occurrenceStatus": {"generator": "map_occurrence_status"},
            "associatedMedia": {"generator": "format_media_urls"},
            "month": {"generator": "extract_month"},
            "habitat": {
                "generator": "format_habitat",
                "params": {
                    "holdridge_field": "@source.holdridge",
                    "rainfall_field": "@source.rainfall",
                    "substrate_field": "@source.um",
                    "forest_field": "@source.forest",
                },
            },
        },
    }


class TestNiamotoDwCTransformer:
    """Test the NiamotoDwCTransformer class."""

    def test_initialization(self, transformer, mock_db):
        """Test transformer initialization."""
        assert transformer.db == mock_db
        assert transformer._current_taxon is None
        assert transformer._occurrence_index == 0

    def test_validate_config_valid(self, transformer):
        """Test config validation with valid config."""
        config = {
            "mapping": {
                "occurrenceID": "@source.id",
                "scientificName": "@taxon.full_name",
            }
        }

        result = transformer.validate_config(config)

        # Now result is a NiamotoDwCConfig object
        assert isinstance(result, NiamotoDwCConfig)
        assert result.params.mapping == config["mapping"]
        assert result.params.occurrence_list_source == "occurrences"  # Default added

    def test_validate_config_invalid_type(self, transformer):
        """Test config validation with invalid type."""
        with pytest.raises(ValueError, match="Invalid configuration"):
            transformer.validate_config("not a dict")

    def test_validate_config_missing_mapping(self, transformer):
        """Test config validation without mapping section."""
        with pytest.raises(ValueError, match="Invalid configuration"):
            transformer.validate_config({})

    def test_validate_config_invalid_mapping_type(self, transformer):
        """Test config validation with invalid mapping type."""
        with pytest.raises(ValueError, match="Invalid configuration"):
            transformer.validate_config({"mapping": "not a dict"})

    def test_validate_config_accepts_params_instance(self, transformer):
        """Test config validation when provided a params object directly."""
        params = DwcTransformerParams(
            occurrence_list_source="occurrences",
            mapping={"scientificName": "@taxon.full_name"},
        )

        result = transformer.validate_config(params)

        assert isinstance(result, NiamotoDwCConfig)
        assert result.params.mapping == params.mapping

    def test_transform_no_taxon_id(self, transformer, sample_mapping_config):
        """Test transform when taxon data has no ID."""
        data = {"name": "Test taxon"}  # No id or taxon_id

        result = transformer.transform(data, sample_mapping_config)

        assert result == []

    def test_transform_no_occurrences(
        self, transformer, mock_db, sample_taxon_data, sample_mapping_config
    ):
        """Test transform when no occurrences found."""
        # Mock database to return no occurrences
        mock_connection = Mock()
        mock_result = Mock()
        mock_result.fetchall.return_value = []
        mock_connection.execute.return_value = mock_result
        mock_context = MagicMock()
        mock_context.__enter__.return_value = mock_connection
        mock_db.engine.connect.return_value = mock_context

        result = transformer.transform(sample_taxon_data, sample_mapping_config)

        assert result == []

    def test_transform_success(
        self,
        transformer,
        mock_db,
        sample_taxon_data,
        sample_occurrence_data,
        sample_mapping_config,
    ):
        """Test successful transformation."""
        # Mock database to return occurrences
        mock_connection = Mock()
        mock_result = Mock()
        mock_result.fetchall.return_value = [
            (
                1,
                123,
                "Araucariaceae",
                150.5,
                6,
                35.5,
                2,
                1200,
                True,
                True,
                1,
                0,
                "POINT (165.7683 -21.6461)",
            )
        ]
        mock_result.keys.return_value = [
            "id",
            "taxon_ref_id",
            "family",
            "elevation",
            "month_obs",
            "dbh",
            "holdridge",
            "rainfall",
            "um",
            "forest",
            "flower",
            "fruit",
            "geometry",
        ]
        mock_connection.execute.return_value = mock_result
        mock_context = MagicMock()
        mock_context.__enter__.return_value = mock_connection
        mock_db.engine.connect.return_value = mock_context

        result = transformer.transform(sample_taxon_data, sample_mapping_config)

        assert len(result) == 1
        dwc_record = result[0]
        assert dwc_record["occurrenceID"] == "niaocc_123_0"
        assert dwc_record["scientificName"] == "Araucaria columnaris (Forster) Hook."
        assert dwc_record["family"] == "Araucariaceae"
        assert dwc_record["elevation"] == 150.5
        assert dwc_record["establishmentMeans"] == "native"  # endemic = True
        assert dwc_record["occurrenceStatus"] == "present"
        assert dwc_record["month"] == 6
        assert dwc_record["decimalLatitude"] == -21.6461
        assert dwc_record["decimalLongitude"] == 165.7683

    def test_transform_with_pydantic_config(
        self, transformer, mock_db, sample_taxon_data, sample_mapping_config
    ):
        """Test transform with new format configuration."""
        # Create config in the new format with params
        config = {
            "plugin": "niamoto_to_dwc_occurrence",
            "params": sample_mapping_config,
        }

        # Mock database
        mock_connection = Mock()
        mock_result = Mock()
        mock_result.fetchall.return_value = []
        mock_connection.execute.return_value = mock_result
        mock_context = MagicMock()
        mock_context.__enter__.return_value = mock_connection
        mock_db.engine.connect.return_value = mock_context

        result = transformer.transform(sample_taxon_data, config)

        assert result == []

    def test_transform_error_handling(
        self, transformer, mock_db, sample_taxon_data, sample_mapping_config
    ):
        """Test transform error handling."""
        # Make an attribute access fail to trigger the outer exception handler
        with patch.object(
            transformer,
            "_fetch_occurrences_from_db",
            side_effect=Exception("Critical error"),
        ):
            with pytest.raises(
                DataTransformError, match="Darwin Core transformation failed"
            ):
                transformer.transform(sample_taxon_data, sample_mapping_config)

    def test_fetch_occurrences_from_db_primary_query(self, transformer, mock_db):
        """Test fetching occurrences with primary query."""
        mock_connection = Mock()
        mock_result = Mock()
        mock_result.fetchall.return_value = [(1, 123, "Araucariaceae", 150.5)]
        mock_result.keys.return_value = ["id", "taxon_ref_id", "family", "elevation"]
        mock_connection.execute.return_value = mock_result
        mock_context = MagicMock()
        mock_context.__enter__.return_value = mock_connection
        mock_db.engine.connect.return_value = mock_context

        result = transformer._fetch_occurrences_from_db(123)

        assert len(result) == 1
        assert result[0]["id"] == 1
        assert result[0]["taxon_ref_id"] == 123
        assert result[0]["family"] == "Araucariaceae"

    def test_fetch_occurrences_from_db_fallback_query(self, transformer, mock_db):
        """Test fetching occurrences with fallback query."""
        mock_connection = Mock()

        # First query returns no results
        mock_result1 = Mock()
        mock_result1.fetchall.return_value = []

        # Second query returns results
        mock_result2 = Mock()
        mock_result2.fetchall.return_value = [(2, 456, "Lauraceae", 200.0)]
        mock_result2.keys.return_value = ["id", "id_taxonref", "family", "elevation"]

        mock_connection.execute.side_effect = [mock_result1, mock_result2]
        mock_context = MagicMock()
        mock_context.__enter__.return_value = mock_connection
        mock_db.engine.connect.return_value = mock_context

        result = transformer._fetch_occurrences_from_db(123)

        assert len(result) == 1
        assert result[0]["id"] == 2

    def test_fetch_occurrences_from_db_error(self, transformer, mock_db):
        """Test error handling in fetch_occurrences_from_db."""
        mock_db.engine.connect.side_effect = Exception("Connection failed")

        result = transformer._fetch_occurrences_from_db(123)

        assert result == []

    def test_map_occurrence_basic(self, transformer, sample_occurrence_data):
        """Test basic occurrence mapping."""
        transformer._current_taxon = {"full_name": "Test species"}

        mapping = {
            "occurrenceID": "@source.id",
            "scientificName": "@taxon.full_name",
            "elevation": "@source.elevation",
        }

        result = transformer._map_occurrence(sample_occurrence_data, mapping)

        assert result["occurrenceID"] == 1
        assert result["scientificName"] == "Test species"
        assert result["elevation"] == 150.5

    def test_map_occurrence_skip_error_handling(
        self, transformer, sample_occurrence_data
    ):
        """Test that error_handling key is skipped in mapping."""
        mapping = {
            "occurrenceID": "@source.id",
            "error_handling": {"continue_on_error": True},
        }

        result = transformer._map_occurrence(sample_occurrence_data, mapping)

        assert "occurrenceID" in result
        assert "error_handling" not in result

    def test_map_occurrence_with_errors(self, transformer, sample_occurrence_data):
        """Test mapping with errors in some fields."""
        mapping = {
            "occurrenceID": "@source.id",
            "badField": "@source.nonexistent",
            "elevation": "@source.elevation",
        }

        result = transformer._map_occurrence(sample_occurrence_data, mapping)

        assert result["occurrenceID"] == 1
        assert "badField" not in result  # Should be skipped
        assert result["elevation"] == 150.5

    def test_resolve_mapping_static_string(self, transformer):
        """Test resolving static string mapping."""
        result = transformer._resolve_mapping({}, "static value")
        assert result == "static value"

    def test_resolve_mapping_reference(self, transformer, sample_occurrence_data):
        """Test resolving @ reference."""
        result = transformer._resolve_mapping(sample_occurrence_data, "@source.family")
        assert result == "Araucariaceae"

    def test_resolve_mapping_dict_with_generator(
        self, transformer, sample_occurrence_data
    ):
        """Test resolving dict mapping with generator."""
        transformer._occurrence_index = 5
        transformer._current_taxon = {"id": 123}

        mapping = {"generator": "unique_occurrence_id", "params": {"prefix": "test_"}}

        result = transformer._resolve_mapping(sample_occurrence_data, mapping)
        assert result == "test_123_5"

    def test_resolve_mapping_dict_with_source(
        self, transformer, sample_occurrence_data
    ):
        """Test resolving dict mapping with source."""
        mapping = {"source": "@source.elevation"}

        result = transformer._resolve_mapping(sample_occurrence_data, mapping)
        assert result == 150.5

    def test_resolve_mapping_dict_as_is(self, transformer):
        """Test resolving dict without generator or source."""
        mapping = {"key": "value", "nested": {"data": True}}
        result = transformer._resolve_mapping({}, mapping)
        assert result == mapping

    def test_resolve_mapping_other_types(self, transformer):
        """Test resolving other types (int, bool, etc)."""
        assert transformer._resolve_mapping({}, 42) == 42
        assert transformer._resolve_mapping({}, True) is True
        assert transformer._resolve_mapping({}, None) is None

    def test_resolve_reference_source(self, transformer, sample_occurrence_data):
        """Test resolving source references."""
        result = transformer._resolve_reference(
            sample_occurrence_data, "@source.family"
        )
        assert result == "Araucariaceae"

    def test_resolve_reference_taxon(self, transformer, sample_occurrence_data):
        """Test resolving taxon references."""
        transformer._current_taxon = {"rank": "species", "full_name": "Test species"}

        result = transformer._resolve_reference(sample_occurrence_data, "@taxon.rank")
        assert result == "species"

    def test_resolve_reference_unknown(self, transformer):
        """Test resolving unknown reference type."""
        result = transformer._resolve_reference({}, "@unknown.field")
        assert result is None

    def test_resolve_reference_no_prefix(self, transformer):
        """Test resolving reference without @ prefix."""
        result = transformer._resolve_reference({}, "source.field")
        assert result == "source.field"

    def test_get_nested_value_simple(self, transformer):
        """Test getting nested value with simple path."""
        data = {"field": "value"}
        result = transformer._get_nested_value(data, "field")
        assert result == "value"

    def test_get_nested_value_nested(self, transformer):
        """Test getting deeply nested value."""
        data = {"level1": {"level2": {"level3": "deep value"}}}
        result = transformer._get_nested_value(data, "level1.level2.level3")
        assert result == "deep value"

    def test_get_nested_value_missing(self, transformer):
        """Test getting missing nested value."""
        data = {"field": "value"}
        result = transformer._get_nested_value(data, "missing.field")
        assert result is None

    def test_get_nested_value_empty_path(self, transformer):
        """Test getting value with empty path."""
        data = {"field": "value"}
        result = transformer._get_nested_value(data, "")
        assert result == data

    def test_apply_generator_known(self, transformer, sample_occurrence_data):
        """Test applying known generator."""
        transformer._current_taxon = {"id": 123}
        transformer._occurrence_index = 0

        result = transformer._apply_generator(
            sample_occurrence_data, "unique_occurrence_id", {"prefix": "test_"}
        )
        assert result == "test_123_0"

    def test_apply_generator_unknown(self, transformer):
        """Test applying unknown generator."""
        result = transformer._apply_generator({}, "unknown_generator", {})
        assert result is None


class TestGeneratorMethods:
    """Test individual generator methods."""

    def test_generate_unique_occurrence_id_with_source(
        self, transformer, sample_occurrence_data
    ):
        """Test generating occurrence ID from source field."""
        params = {"prefix": "occ_", "source_field": "@source.id"}
        result = transformer._generate_unique_occurrence_id(
            sample_occurrence_data, params
        )
        assert result == "occ_1"

    def test_generate_unique_occurrence_id_fallback(self, transformer):
        """Test generating occurrence ID with fallback."""
        transformer._current_taxon = {"id": 456}
        transformer._occurrence_index = 3

        params = {"prefix": "occ_"}
        result = transformer._generate_unique_occurrence_id({}, params)
        assert result == "occ_456_3"

    def test_generate_unique_event_id(self, transformer, sample_occurrence_data):
        """Test generating event ID."""
        transformer._current_taxon = {"id": 123}
        transformer._occurrence_index = 0

        params = {"prefix": "evt_"}
        result = transformer._generate_unique_event_id(sample_occurrence_data, params)
        assert result == "evt_123_0"

    def test_generate_unique_identification_id(
        self, transformer, sample_occurrence_data
    ):
        """Test generating identification ID."""
        transformer._current_taxon = {"id": 123}
        transformer._occurrence_index = 0

        params = {"prefix": "id_"}
        result = transformer._generate_unique_identification_id(
            sample_occurrence_data, params
        )
        assert result == "id_123_0"

    def test_extract_specific_epithet_success(self, transformer):
        """Test extracting specific epithet from scientific name."""
        transformer._current_taxon = {
            "full_name": "Araucaria columnaris (Forster) Hook."
        }

        params = {}
        result = transformer._extract_specific_epithet({}, params)
        assert result == "columnaris"

    def test_extract_specific_epithet_single_word(self, transformer):
        """Test extracting specific epithet from single word name."""
        transformer._current_taxon = {"full_name": "Araucaria"}

        params = {}
        result = transformer._extract_specific_epithet({}, params)
        assert result is None

    def test_extract_specific_epithet_custom_source(self, transformer):
        """Test extracting specific epithet from custom source."""
        params = {"source_field": "@source.scientific_name"}
        occurrence = {"scientific_name": "Genus species subsp. subspecies"}

        result = transformer._extract_specific_epithet(occurrence, params)
        assert result == "species"

    def test_extract_infraspecific_epithet_subspecies(self, transformer):
        """Test extracting infraspecific epithet (subspecies)."""
        transformer._current_taxon = {
            "full_name": "Genus species subsp. subspecies (Author)"
        }

        params = {}
        result = transformer._extract_infraspecific_epithet({}, params)
        assert result == "subspecies"

    def test_extract_infraspecific_epithet_variety(self, transformer):
        """Test extracting infraspecific epithet (variety)."""
        transformer._current_taxon = {"full_name": "Genus species var. variety"}

        params = {}
        result = transformer._extract_infraspecific_epithet({}, params)
        assert result == "variety"

    def test_extract_infraspecific_epithet_none(self, transformer):
        """Test extracting infraspecific epithet when none exists."""
        transformer._current_taxon = {"full_name": "Genus species"}

        params = {}
        result = transformer._extract_infraspecific_epithet({}, params)
        assert result is None

    def test_format_event_date_datetime(self, transformer):
        """Test formatting datetime object."""
        occurrence = {"date": datetime(2023, 6, 15)}
        params = {"source_field": "@source.date"}

        result = transformer._format_event_date(occurrence, params)
        assert result == "2023-06-15"

    def test_format_event_date_string_slash(self, transformer):
        """Test formatting date string with slashes."""
        occurrence = {"date": "15/06/2023"}
        params = {"source_field": "@source.date"}

        result = transformer._format_event_date(occurrence, params)
        assert result == "2023-06-15"

    def test_format_event_date_month_only(self, transformer):
        """Test formatting month-only value."""
        occurrence = {"date": 6}
        params = {"source_field": "@source.date"}

        result = transformer._format_event_date(occurrence, params)
        assert result is None

    def test_format_event_date_none(self, transformer):
        """Test formatting None date."""
        occurrence = {"date": None}
        params = {"source_field": "@source.date"}

        result = transformer._format_event_date(occurrence, params)
        assert result is None

    def test_extract_year(self, transformer):
        """Test extracting year from date."""
        occurrence = {"date": "2023-06-15"}
        params = {"source_field": "@source.date"}

        with patch.object(transformer, "_format_event_date", return_value="2023-06-15"):
            result = transformer._extract_year(occurrence, params)
            assert result == 2023

    def test_extract_month_from_field(self, transformer):
        """Test extracting month from month_obs field."""
        occurrence = {"month_obs": 6}
        params = {"source_field": "@source.month_obs"}

        result = transformer._extract_month(occurrence, params)
        assert result == 6

    def test_extract_month_from_date(self, transformer):
        """Test extracting month from date string."""
        occurrence = {"date": "2023-06-15"}
        params = {"source_field": "@source.date"}

        with patch.object(transformer, "_format_event_date", return_value="2023-06-15"):
            result = transformer._extract_month(occurrence, params)
            assert result == 6

    def test_extract_day(self, transformer):
        """Test extracting day from date."""
        occurrence = {"date": "2023-06-15"}
        params = {"source_field": "@source.date"}

        with patch.object(transformer, "_format_event_date", return_value="2023-06-15"):
            result = transformer._extract_day(occurrence, params)
            assert result == 15

    def test_format_media_urls(self, transformer):
        """Test formatting media URLs."""
        transformer._current_taxon = {
            "metadata": {
                "images": [
                    {"url": "http://example.com/1.jpg"},
                    {"url": "http://example.com/2.jpg"},
                ]
            }
        }

        params = {"source_list": "@taxon.metadata.images", "url_key": "url"}
        result = transformer._format_media_urls({}, params)
        assert result == "http://example.com/1.jpg | http://example.com/2.jpg"

    def test_format_media_urls_string_list(self, transformer):
        """Test formatting media URLs from string list."""
        transformer._current_taxon = {
            "metadata": {
                "images": ["http://example.com/1.jpg", "http://example.com/2.jpg"]
            }
        }

        params = {"source_list": "@taxon.metadata.images"}
        result = transformer._format_media_urls({}, params)
        assert result == "http://example.com/1.jpg | http://example.com/2.jpg"

    def test_format_coordinates_point_geometry(self, transformer):
        """Test formatting coordinates from POINT geometry."""
        occurrence = {"geometry": "POINT (165.7683 -21.6461)"}

        # Test latitude
        params = {"source_field": "@source.geometry", "type": "latitude"}
        result = transformer._format_coordinates(occurrence, params)
        assert result == -21.6461

        # Test longitude
        params = {"source_field": "@source.geometry", "type": "longitude"}
        result = transformer._format_coordinates(occurrence, params)
        assert result == 165.7683

    def test_format_coordinates_direct_value(self, transformer):
        """Test formatting coordinates from direct numeric value."""
        occurrence = {"lat": -21.5, "lng": 165.5}

        # Test latitude
        params = {"source_field": "@source.lat", "type": "latitude"}
        result = transformer._format_coordinates(occurrence, params)
        assert result == -21.5

        # Test longitude
        params = {"source_field": "@source.lng", "type": "longitude"}
        result = transformer._format_coordinates(occurrence, params)
        assert result == 165.5

    def test_format_coordinates_out_of_range(self, transformer):
        """Test formatting coordinates with out-of-range values."""
        occurrence = {"lat": 95.0}  # Invalid latitude

        params = {"source_field": "@source.lat", "type": "latitude"}
        result = transformer._format_coordinates(occurrence, params)
        assert result is None

    def test_map_establishment_means_native(self, transformer):
        """Test mapping endemic status to native."""
        transformer._current_taxon = {"metadata": {"endemic": True}}

        params = {}
        result = transformer._map_establishment_means({}, params)
        assert result == "native"

    def test_map_establishment_means_introduced(self, transformer):
        """Test mapping non-endemic status to introduced."""
        transformer._current_taxon = {"metadata": {"endemic": False}}

        params = {}
        result = transformer._map_establishment_means({}, params)
        assert result == "introduced"

    def test_map_establishment_means_unknown(self, transformer):
        """Test mapping unknown endemic status."""
        transformer._current_taxon = {"metadata": {}}

        params = {}
        result = transformer._map_establishment_means({}, params)
        assert result is None

    def test_map_occurrence_status_default(self, transformer):
        """Test default occurrence status."""
        params = {}
        result = transformer._map_occurrence_status({}, params)
        assert result == "present"

    def test_map_occurrence_status_custom(self, transformer):
        """Test custom occurrence status."""
        occurrence = {"status": "absent"}
        params = {"status_field": "@source.status"}

        result = transformer._map_occurrence_status(occurrence, params)
        assert result == "absent"

    def test_format_measurements(self, transformer):
        """Test formatting measurements as JSON."""
        occurrence = {"dbh": 35.5, "height": 25.0}
        params = {
            "measurements": [
                {"field": "@source.dbh", "name": "diameter", "unit": "cm"},
                {"field": "@source.height", "name": "height", "unit": "m"},
            ]
        }

        result = transformer._format_measurements(occurrence, params)
        parsed = json.loads(result)

        assert parsed["diameter"]["value"] == 35.5
        assert parsed["diameter"]["unit"] == "cm"
        assert parsed["height"]["value"] == 25.0
        assert parsed["height"]["unit"] == "m"

    def test_format_measurements_empty(self, transformer):
        """Test formatting empty measurements."""
        params = {"measurements": []}
        result = transformer._format_measurements({}, params)
        assert result is None

    def test_format_phenology_both(self, transformer):
        """Test formatting phenology with both flowering and fruiting."""
        occurrence = {"flower": 1, "fruit": "yes"}
        params = {"flower_field": "@source.flower", "fruit_field": "@source.fruit"}

        result = transformer._format_phenology(occurrence, params)
        assert result == "flowering; fruiting"

    def test_format_phenology_none(self, transformer):
        """Test formatting phenology with no conditions."""
        occurrence = {"flower": 0, "fruit": None}
        params = {"flower_field": "@source.flower", "fruit_field": "@source.fruit"}

        result = transformer._format_phenology(occurrence, params)
        assert result is None

    def test_format_habitat_comprehensive(self, transformer):
        """Test formatting comprehensive habitat information."""
        occurrence = {"holdridge": 2, "rainfall": 1200, "um": True, "forest": True}
        params = {
            "holdridge_field": "@source.holdridge",
            "rainfall_field": "@source.rainfall",
            "substrate_field": "@source.um",
            "forest_field": "@source.forest",
        }

        result = transformer._format_habitat(occurrence, params)
        assert "Holdridge life zone: Moist" in result
        assert "Annual rainfall: 1200mm" in result
        assert "Substrate: ultramafic" in result
        assert "Habitat: forest" in result

    def test_format_habitat_partial(self, transformer):
        """Test formatting partial habitat information."""
        occurrence = {"holdridge": "1", "forest": False}
        params = {
            "holdridge_field": "@source.holdridge",
            "forest_field": "@source.forest",
        }

        result = transformer._format_habitat(occurrence, params)
        assert "Holdridge life zone: Dry" in result
        assert "Habitat: non-forest" in result
        assert "rainfall" not in result.lower()

    def test_count_occurrences(self, transformer, mock_db):
        """Test counting occurrences for current taxon."""
        transformer._current_taxon = {"taxon_id": 123}

        # Mock fetch to return 3 occurrences
        with patch.object(
            transformer, "_fetch_occurrences_from_db", return_value=[{}, {}, {}]
        ):
            result = transformer._count_occurrences({}, {})
            assert result == 3

    def test_count_occurrences_no_taxon_id(self, transformer):
        """Test counting occurrences when no taxon ID."""
        transformer._current_taxon = {}

        result = transformer._count_occurrences({}, {})
        assert result == 0

    def test_current_date_default(self, transformer):
        """Test generating current date with default format."""
        params = {}
        result = transformer._current_date({}, params)

        # Check format YYYY-MM-DD
        assert len(result) == 10
        assert result[4] == "-"
        assert result[7] == "-"

    def test_current_date_custom_format(self, transformer):
        """Test generating current date with custom format."""
        params = {"format": "%Y%m%d"}
        result = transformer._current_date({}, params)

        # Check format YYYYMMDD
        assert len(result) == 8
        assert result.isdigit()

    def test_count_processed_taxa(self, transformer):
        """Test placeholder for counting processed taxa."""
        result = transformer._count_processed_taxa({}, {})
        assert result == 0

    def test_count_total_occurrences(self, transformer):
        """Test placeholder for counting total occurrences."""
        result = transformer._count_total_occurrences({}, {})
        assert result == 0


class TestIntegration:
    """Integration tests for the transformer."""

    def test_full_transformation_workflow(
        self, transformer, mock_db, sample_taxon_data
    ):
        """Test complete transformation workflow."""
        # Prepare comprehensive occurrence data
        occurrence_rows = [
            (
                1,
                123,
                "Araucariaceae",
                150.5,
                6,
                35.5,
                2,
                1200,
                True,
                True,
                1,
                0,
                "POINT (165.7683 -21.6461)",
            ),
            (
                2,
                123,
                "Araucariaceae",
                200.0,
                7,
                40.0,
                3,
                1500,
                False,
                True,
                0,
                1,
                "POINT (166.0000 -22.0000)",
            ),
        ]

        # Mock database
        mock_connection = Mock()
        mock_result = Mock()
        mock_result.fetchall.return_value = occurrence_rows
        mock_result.keys.return_value = [
            "id",
            "taxon_ref_id",
            "family",
            "elevation",
            "month_obs",
            "dbh",
            "holdridge",
            "rainfall",
            "um",
            "forest",
            "flower",
            "fruit",
            "geometry",
        ]
        mock_connection.execute.return_value = mock_result
        mock_context = MagicMock()
        mock_context.__enter__.return_value = mock_connection
        mock_db.engine.connect.return_value = mock_context

        # Comprehensive mapping configuration
        config = {
            "mapping": {
                "occurrenceID": {
                    "generator": "unique_occurrence_id",
                    "params": {"prefix": "NIAOCC-", "source_field": "@source.id"},
                },
                "eventID": {
                    "generator": "unique_event_id",
                    "params": {"prefix": "NIAEVT-", "source_field": "@source.id"},
                },
                "scientificName": "@taxon.full_name",
                "family": "@source.family",
                "specificEpithet": {"generator": "extract_specific_epithet"},
                "decimalLatitude": {
                    "generator": "format_coordinates",
                    "params": {"source_field": "@source.geometry", "type": "latitude"},
                },
                "decimalLongitude": {
                    "generator": "format_coordinates",
                    "params": {"source_field": "@source.geometry", "type": "longitude"},
                },
                "minimumElevationInMeters": "@source.elevation",
                "month": {"generator": "extract_month"},
                "establishmentMeans": {"generator": "map_establishment_means"},
                "occurrenceStatus": {"generator": "map_occurrence_status"},
                "measurementOrFact": {
                    "generator": "format_measurements",
                    "params": {
                        "measurements": [
                            {"field": "@source.dbh", "name": "DBH", "unit": "cm"}
                        ]
                    },
                },
                "lifeStage": {
                    "generator": "format_phenology",
                    "params": {
                        "flower_field": "@source.flower",
                        "fruit_field": "@source.fruit",
                    },
                },
                "habitat": {
                    "generator": "format_habitat",
                    "params": {
                        "holdridge_field": "@source.holdridge",
                        "rainfall_field": "@source.rainfall",
                        "substrate_field": "@source.um",
                        "forest_field": "@source.forest",
                    },
                },
                "associatedMedia": {"generator": "format_media_urls"},
                "modified": {"generator": "current_date"},
            }
        }

        # Transform
        result = transformer.transform(sample_taxon_data, config)

        # Verify results
        assert len(result) == 2

        # Check first occurrence
        occ1 = result[0]
        assert occ1["occurrenceID"] == "NIAOCC-1"
        assert occ1["eventID"] == "NIAEVT-1"  # Uses the source field from occurrence ID
        assert occ1["scientificName"] == "Araucaria columnaris (Forster) Hook."
        assert occ1["family"] == "Araucariaceae"
        assert occ1["specificEpithet"] == "columnaris"
        assert occ1["decimalLatitude"] == -21.6461
        assert occ1["decimalLongitude"] == 165.7683
        assert occ1["minimumElevationInMeters"] == 150.5
        assert occ1["month"] == 6
        assert occ1["establishmentMeans"] == "native"
        assert occ1["occurrenceStatus"] == "present"
        assert occ1["lifeStage"] == "flowering"
        assert "Moist" in occ1["habitat"]
        assert "ultramafic" in occ1["habitat"]
        assert (
            "http://example.com/image1.jpg | http://example.com/image2.jpg"
            in occ1["associatedMedia"]
        )

        # Check DBH measurement
        measurements = json.loads(occ1["measurementOrFact"])
        assert measurements["DBH"]["value"] == 35.5
        assert measurements["DBH"]["unit"] == "cm"

        # Check second occurrence has different values
        occ2 = result[1]
        assert occ2["occurrenceID"] == "NIAOCC-2"
        assert occ2["minimumElevationInMeters"] == 200.0
        assert occ2["month"] == 7
        assert occ2["lifeStage"] == "fruiting"
        assert "Wet" in occ2["habitat"]
        assert "non-ultramafic" in occ2["habitat"]

    def test_error_recovery_in_mapping(self, transformer, mock_db, sample_taxon_data):
        """Test that transformer continues processing despite errors in individual mappings."""
        # Mock database
        mock_connection = Mock()
        mock_result = Mock()
        mock_result.fetchall.return_value = [
            (1, 123, None, None, None, None, None, None, None, None, None, None, None)
        ]
        mock_result.keys.return_value = ["id", "taxon_ref_id"] + [
            "col" + str(i) for i in range(11)
        ]
        mock_connection.execute.return_value = mock_result
        mock_context = MagicMock()
        mock_context.__enter__.return_value = mock_connection
        mock_db.engine.connect.return_value = mock_context

        # Config with some fields that will fail
        config = {
            "mapping": {
                "occurrenceID": "@source.id",
                "badField1": {"generator": "nonexistent_generator"},
                "taxonID": "@taxon.taxon_id",
                "badField2": "@source.nonexistent.nested.field",
                "status": "present",
            }
        }

        # Transform should succeed despite errors
        result = transformer.transform(sample_taxon_data, config)

        assert len(result) == 1
        dwc = result[0]
        assert dwc["occurrenceID"] == 1
        assert dwc["taxonID"] == 123
        assert dwc["status"] == "present"
        assert "badField1" not in dwc
        assert "badField2" not in dwc
