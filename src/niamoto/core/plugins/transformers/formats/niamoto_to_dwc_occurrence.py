# src/niamoto/core/plugins/transformers/niamoto_to_dwc_occurrence.py

"""
Transformer plugin for converting Niamoto data to Darwin Core Occurrence format.

This transformer maps Niamoto taxon occurrence data to the Darwin Core standard,
which is widely used for biodiversity data exchange.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Literal
import re

from niamoto.core.plugins.base import TransformerPlugin, PluginType, register
from niamoto.core.plugins.models import DwcTransformerParams, PluginConfig
from niamoto.common.exceptions import DataTransformError

logger = logging.getLogger(__name__)


class NiamotoDwCConfig(PluginConfig):
    """Configuration for Darwin Core transformer plugin."""

    plugin: Literal["niamoto_to_dwc_occurrence"] = "niamoto_to_dwc_occurrence"
    params: DwcTransformerParams


@register("niamoto_to_dwc_occurrence", PluginType.TRANSFORMER)
class NiamotoDwCTransformer(TransformerPlugin):
    """Transform Niamoto data to Darwin Core Occurrence format."""

    config_model = NiamotoDwCConfig

    def __init__(self, db: Any):
        """Initialize the transformer."""
        super().__init__(db)
        self._current_taxon = None
        self._occurrence_index = 0

    def validate_config(self, config: Dict[str, Any]) -> NiamotoDwCConfig:
        """
        Validate the configuration using Pydantic model.

        Args:
            config: Configuration dictionary to validate

        Returns:
            Validated NiamotoDwCConfig instance

        Raises:
            ValueError: If configuration is invalid
        """
        try:
            # Accept already validated configs (handle potential duplicate class definitions)
            if hasattr(config, "plugin") and hasattr(config, "params"):
                if getattr(config, "plugin") == "niamoto_to_dwc_occurrence":
                    return self.config_model.model_validate(config)

            # Accept direct params objects coming from the typed UI flow (or any BaseModel with mapping)
            if hasattr(config, "model_dump"):
                dumped = config.model_dump()
                if "mapping" in dumped:
                    config = {
                        "plugin": "niamoto_to_dwc_occurrence",
                        "params": config,
                    }

            # Handle both old format (direct params) and new format (with params key)
            if (
                isinstance(config, dict)
                and "params" not in config
                and "mapping" in config
            ):
                # Old format: wrap in params for compatibility
                config = {
                    "plugin": "niamoto_to_dwc_occurrence",
                    "params": {
                        "occurrence_list_source": config.get(
                            "occurrence_list_source", "occurrences"
                        ),
                        "mapping": config["mapping"],
                    },
                }
            return self.config_model.model_validate(config)
        except Exception as e:
            raise ValueError(f"Invalid configuration: {str(e)}")

    def transform(
        self, data: Dict[str, Any], config: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Transform Niamoto taxon data to Darwin Core occurrences.

        Args:
            data: Niamoto taxon data with occurrences
            config: Configuration dictionary with params

        Returns:
            List of Darwin Core formatted occurrences
        """
        try:
            # Validate config and get typed parameters
            validated_config = self.validate_config(config)
            params = validated_config.params

            # Store current taxon data for reference in mapping
            self._current_taxon = data

            # Get mapping from typed params
            mapping = params.mapping

            # Get taxon ID (field is called 'taxon_id' in the taxon table)
            taxon_id = data.get("taxon_id") or data.get("id")
            if not taxon_id:
                logger.warning("Taxon data missing 'taxon_id' or 'id' field")
                return []

            # Fetch occurrences from database for this taxon
            occurrences = self._fetch_occurrences_from_db(taxon_id)
            if not occurrences:
                logger.debug(f"No occurrences found for taxon {taxon_id}, skipping")
                return []

            # Transform each occurrence
            dwc_occurrences = []
            for index, occurrence in enumerate(occurrences):
                self._occurrence_index = index
                try:
                    dwc_record = self._map_occurrence(occurrence, mapping)
                    dwc_occurrences.append(dwc_record)
                except Exception as e:
                    logger.error(f"Error mapping occurrence {index}: {str(e)}")
                    # Continue by default for robustness
                    continue

            return dwc_occurrences

        except Exception as e:
            raise DataTransformError(f"Darwin Core transformation failed: {str(e)}")

    def _fetch_occurrences_from_db(self, taxon_id: int) -> List[Dict[str, Any]]:
        """Fetch occurrences for a taxon from the database."""
        try:
            from sqlalchemy import text

            # The correct relationship is:
            # taxon.taxon_id (1-1667) -> taxon_ref.id (1-1667) -> occurrences.taxon_ref_id (179-1667)
            # AND taxon_ref.taxon_id (1598-16871) -> occurrences.id_taxonref (1598-16871)

            # First try: get occurrences using taxon_ref_id (the correct foreign key)
            query = text("""
                SELECT o.* FROM occurrences o
                WHERE o.taxon_ref_id = :taxon_id
            """)

            with self.db.engine.connect() as connection:
                result = connection.execute(query, {"taxon_id": taxon_id})
                rows = result.fetchall()

                if not rows:
                    # Second try: get taxon_ref.taxon_id and use that for id_taxonref
                    query2 = text("""
                        SELECT o.* FROM occurrences o
                        JOIN taxon_ref tr ON o.id_taxonref = tr.taxon_id
                        WHERE tr.id = :taxon_id
                    """)
                    result = connection.execute(query2, {"taxon_id": taxon_id})
                    rows = result.fetchall()

                if not rows:
                    return []

                # Convert rows to dictionaries
                columns = result.keys()
                occurrences = []
                for row in rows:
                    occurrence_dict = dict(zip(columns, row))
                    occurrences.append(occurrence_dict)

                logger.info(
                    f"Found {len(occurrences)} occurrences for taxon {taxon_id}"
                )
                return occurrences

        except Exception as e:
            logger.error(f"Error fetching occurrences for taxon {taxon_id}: {str(e)}")
            return []

    def _map_occurrence(
        self, occurrence: Dict[str, Any], mapping: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Map a single occurrence to Darwin Core format."""
        dwc_record = {}

        for dwc_term, mapping_config in mapping.items():
            if dwc_term == "error_handling":  # Skip non-DwC configuration
                continue

            try:
                value = self._resolve_mapping(occurrence, mapping_config)
                if value is not None:
                    dwc_record[dwc_term] = value
            except Exception as e:
                logger.debug(f"Could not map {dwc_term}: {str(e)}")

        return dwc_record

    def _resolve_mapping(self, occurrence: Dict[str, Any], mapping_config: Any) -> Any:
        """Resolve a mapping configuration to a value."""
        # Import here to avoid circular imports
        from niamoto.core.plugins.models import DwcMappingValue

        # Handle DwcMappingValue objects from Pydantic models
        if isinstance(mapping_config, DwcMappingValue):
            if mapping_config.generator:
                return self._apply_generator(
                    occurrence,
                    mapping_config.generator,
                    mapping_config.params,
                )
            elif mapping_config.source:
                return self._resolve_reference(occurrence, mapping_config.source)

        elif isinstance(mapping_config, str):
            # Simple string value or reference
            if mapping_config.startswith("@"):
                return self._resolve_reference(occurrence, mapping_config)
            else:
                # Static value
                return mapping_config

        elif isinstance(mapping_config, dict):
            # Legacy dict format (shouldn't happen with Pydantic validation, but kept for safety)
            if "generator" in mapping_config:
                return self._apply_generator(
                    occurrence,
                    mapping_config["generator"],
                    mapping_config.get("params", {}),
                )
            elif "source" in mapping_config:
                return self._resolve_reference(occurrence, mapping_config["source"])
            else:
                # Dict value as-is
                return mapping_config

        else:
            # Other types (int, bool, etc.)
            return mapping_config

    def _resolve_reference(self, occurrence: Dict[str, Any], reference: str) -> Any:
        """Resolve @ references to actual values."""
        if not reference.startswith("@"):
            return reference

        # Remove @ prefix
        ref_path = reference[1:]

        if ref_path.startswith("source."):
            # Reference to occurrence data
            return self._get_nested_value(occurrence, ref_path[7:])
        elif ref_path.startswith("taxon."):
            # Reference to parent taxon data
            return self._get_nested_value(self._current_taxon, ref_path[6:])
        else:
            # Unknown reference type
            logger.warning(f"Unknown reference type: {reference}")
            return None

    def _get_nested_value(self, data: Dict[str, Any], path: str) -> Any:
        """Get value from nested dictionary using dot notation."""
        if not path:
            return data

        keys = path.split(".")
        current = data

        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current.get(key)
            else:
                return None

        return current

    def _apply_generator(
        self, occurrence: Dict[str, Any], generator_name: str, params: Dict[str, Any]
    ) -> Any:
        """Apply a generator function to produce a value."""
        generators = {
            "unique_occurrence_id": self._generate_unique_occurrence_id,
            "unique_event_id": self._generate_unique_event_id,
            "unique_identification_id": self._generate_unique_identification_id,
            "extract_specific_epithet": self._extract_specific_epithet,
            "extract_infraspecific_epithet": self._extract_infraspecific_epithet,
            "format_event_date": self._format_event_date,
            "extract_year": self._extract_year,
            "extract_month": self._extract_month,
            "extract_day": self._extract_day,
            "format_media_urls": self._format_media_urls,
            "format_coordinates": self._format_coordinates,
            "map_establishment_means": self._map_establishment_means,
            "map_occurrence_status": self._map_occurrence_status,
            "format_measurements": self._format_measurements,
            "format_phenology": self._format_phenology,
            "format_habitat": self._format_habitat,
            "count_occurrences": self._count_occurrences,
            "current_date": self._current_date,
            "count_processed_taxa": self._count_processed_taxa,
            "count_total_occurrences": self._count_total_occurrences,
        }

        if generator_name in generators:
            return generators[generator_name](occurrence, params)
        else:
            logger.warning(f"Unknown generator: {generator_name}")
            return None

    # Generator implementations
    def _generate_unique_occurrence_id(
        self, occurrence: Dict[str, Any], params: Dict[str, Any]
    ) -> str:
        """Generate unique occurrence ID."""
        prefix = params.get("prefix", "niaocc_")

        # Try to use existing ID from source
        source_field = params.get("source_field")
        if source_field:
            value = self._resolve_reference(occurrence, source_field)
            if value:
                return f"{prefix}{value}"

        # Fallback: use taxon ID + index
        taxon_id = self._current_taxon.get("id", "unknown")
        return f"{prefix}{taxon_id}_{self._occurrence_index}"

    def _generate_unique_event_id(
        self, occurrence: Dict[str, Any], params: Dict[str, Any]
    ) -> str:
        """Generate unique event ID."""
        prefix = params.get("prefix", "niaevt_")

        # Try to use existing ID from source
        source_field = params.get("source_field")
        if source_field:
            value = self._resolve_reference(occurrence, source_field)
            if value:
                return f"{prefix}{value}"

        # Fallback: use occurrence ID pattern
        occ_id = self._generate_unique_occurrence_id(occurrence, {"prefix": ""})
        return f"{prefix}{occ_id}"

    def _generate_unique_identification_id(
        self, occurrence: Dict[str, Any], params: Dict[str, Any]
    ) -> str:
        """Generate unique identification ID."""
        prefix = params.get("prefix", "niaid_")

        # Use same pattern as occurrence ID
        occ_id = self._generate_unique_occurrence_id(occurrence, {"prefix": ""})
        return f"{prefix}{occ_id}"

    def _extract_specific_epithet(
        self, occurrence: Dict[str, Any], params: Dict[str, Any]
    ) -> Optional[str]:
        """Extract specific epithet from scientific name."""
        source_field = params.get("source_field", "@taxon.full_name")
        full_name = self._resolve_reference(occurrence, source_field)

        if full_name and isinstance(full_name, str):
            # Remove author info first
            name_without_author = re.sub(r"\s+\([^)]+\)", "", full_name)
            parts = name_without_author.split()

            if len(parts) >= 2:
                # Second part is specific epithet
                return parts[1]

        return None

    def _extract_infraspecific_epithet(
        self, occurrence: Dict[str, Any], params: Dict[str, Any]
    ) -> Optional[str]:
        """Extract infraspecific epithet from scientific name."""
        source_field = params.get("source_field", "@taxon.full_name")
        full_name = self._resolve_reference(occurrence, source_field)

        if full_name and isinstance(full_name, str):
            # Remove author info
            name_without_author = re.sub(r"\s+\([^)]+\)", "", full_name)

            # Look for infraspecific markers
            infra_markers = ["subsp.", "var.", "f.", "forma", "subvar.", "race"]
            for marker in infra_markers:
                if marker in name_without_author:
                    parts = name_without_author.split(marker)
                    if len(parts) > 1:
                        # Get the part after the marker
                        infra_part = parts[1].strip().split()[0]
                        return infra_part

        return None

    def _format_event_date(
        self, occurrence: Dict[str, Any], params: Dict[str, Any]
    ) -> Optional[str]:
        """Format event date to ISO 8601."""
        source_field = params.get("source_field", "@source.date")
        date_value = self._resolve_reference(occurrence, source_field)

        if not date_value:
            return None

        # Handle month_obs field (numeric month value)
        if isinstance(date_value, (int, float)):
            month = int(date_value)
            if 1 <= month <= 12:
                # We don't have year info, so we can't create a full date
                # Return None here, but month will be handled by extract_month
                return None

        # Handle different date formats
        if isinstance(date_value, datetime):
            return date_value.strftime("%Y-%m-%d")
        elif isinstance(date_value, str):
            # Try to parse and reformat
            try:
                # Simple date parsing - extend as needed
                if "/" in date_value:
                    parts = date_value.split("/")
                    if len(parts) == 3:
                        # Assume DD/MM/YYYY
                        return f"{parts[2]}-{parts[1]:0>2}-{parts[0]:0>2}"
                return date_value
            except Exception:
                return date_value

        return str(date_value)

    def _extract_year(
        self, occurrence: Dict[str, Any], params: Dict[str, Any]
    ) -> Optional[int]:
        """Extract year from date."""
        date_str = self._format_event_date(occurrence, params)
        if date_str and len(date_str) >= 4:
            try:
                return int(date_str[:4])
            except ValueError:
                pass
        return None

    def _extract_month(
        self, occurrence: Dict[str, Any], params: Dict[str, Any]
    ) -> Optional[int]:
        """Extract month from date or month_obs field."""
        # First try the month_obs field directly
        source_field = params.get("source_field", "@source.month_obs")
        month_value = self._resolve_reference(occurrence, source_field)

        if month_value is not None:
            try:
                month = int(month_value)
                if 1 <= month <= 12:
                    return month
            except (ValueError, TypeError):
                pass

        # Fallback to extracting from date string
        date_str = self._format_event_date(occurrence, params)
        if date_str and len(date_str) >= 7:
            try:
                return int(date_str[5:7])
            except ValueError:
                pass
        return None

    def _extract_day(
        self, occurrence: Dict[str, Any], params: Dict[str, Any]
    ) -> Optional[int]:
        """Extract day from date."""
        date_str = self._format_event_date(occurrence, params)
        if date_str and len(date_str) >= 10:
            try:
                return int(date_str[8:10])
            except ValueError:
                pass
        return None

    def _format_media_urls(
        self, occurrence: Dict[str, Any], params: Dict[str, Any]
    ) -> Optional[str]:
        """Format media URLs as pipe-separated string."""
        source_list = params.get("source_list", "@taxon.metadata.images")
        url_key = params.get("url_key", "url")

        media_list = self._resolve_reference(occurrence, source_list)
        if isinstance(media_list, list):
            urls = []
            for media in media_list:
                if isinstance(media, dict) and url_key in media:
                    urls.append(media[url_key])
                elif isinstance(media, str):
                    urls.append(media)

            if urls:
                return " | ".join(urls)

        return None

    def _format_coordinates(
        self, occurrence: Dict[str, Any], params: Dict[str, Any]
    ) -> Optional[float]:
        """Format coordinate value from geometry or direct fields."""
        source_field = params.get("source_field")
        coord_type = params.get("type", "latitude")  # latitude or longitude

        if source_field:
            value = self._resolve_reference(occurrence, source_field)
            if value is not None:
                try:
                    # Handle POINT geometry format like "POINT (165.7683 -21.6461)"
                    if isinstance(value, str) and value.startswith("POINT"):
                        # Extract coordinates from POINT(x y) format
                        import re

                        coords_match = re.search(r"POINT \(([^)]+)\)", value)
                        if coords_match:
                            coords_str = coords_match.group(1)
                            coords = coords_str.split()
                            if len(coords) >= 2:
                                lng, lat = float(coords[0]), float(coords[1])
                                if coord_type == "latitude" and -90 <= lat <= 90:
                                    return lat
                                elif coord_type == "longitude" and -180 <= lng <= 180:
                                    return lng
                    else:
                        # Direct numeric value
                        coord = float(value)
                        # Validate coordinate ranges
                        if coord_type == "latitude" and -90 <= coord <= 90:
                            return coord
                        elif coord_type == "longitude" and -180 <= coord <= 180:
                            return coord
                except (ValueError, TypeError):
                    pass

        return None

    def _map_establishment_means(
        self, occurrence: Dict[str, Any], params: Dict[str, Any]
    ) -> Optional[str]:
        """Map endemic status to establishment means."""
        endemic_field = params.get("endemic_field", "@taxon.metadata.endemic")
        endemic = self._resolve_reference(occurrence, endemic_field)

        if endemic is True:
            return "native"
        elif endemic is False:
            return "introduced"

        return None

    def _map_occurrence_status(
        self, occurrence: Dict[str, Any], params: Dict[str, Any]
    ) -> str:
        """Map occurrence status (default to present)."""
        # Could check for absence data
        status_field = params.get("status_field")
        if status_field:
            status = self._resolve_reference(occurrence, status_field)
            if status:
                return str(status)

        return "present"

    def _format_measurements(
        self, occurrence: Dict[str, Any], params: Dict[str, Any]
    ) -> Optional[str]:
        """Format measurements as JSON string for dynamicProperties."""
        measurements = params.get("measurements", [])
        if not measurements:
            return None

        dynamic_props = {}
        for measurement in measurements:
            field = measurement.get("field")
            name = measurement.get("name")
            unit = measurement.get("unit", "")

            if field and name:
                value = self._resolve_reference(occurrence, field)
                if value is not None:
                    dynamic_props[name] = {"value": value, "unit": unit}

        if dynamic_props:
            import json

            return json.dumps(dynamic_props)

        return None

    def _format_phenology(
        self, occurrence: Dict[str, Any], params: Dict[str, Any]
    ) -> Optional[str]:
        """Format phenology information."""
        flower_field = params.get("flower_field")
        fruit_field = params.get("fruit_field")

        conditions = []

        if flower_field:
            flower = self._resolve_reference(occurrence, flower_field)
            if flower and str(flower).lower() not in ["", "none", "null", "0"]:
                conditions.append("flowering")

        if fruit_field:
            fruit = self._resolve_reference(occurrence, fruit_field)
            if fruit and str(fruit).lower() not in ["", "none", "null", "0"]:
                conditions.append("fruiting")

        return "; ".join(conditions) if conditions else None

    def _format_habitat(
        self, occurrence: Dict[str, Any], params: Dict[str, Any]
    ) -> Optional[str]:
        """Format habitat information."""
        holdridge_field = params.get("holdridge_field")
        rainfall_field = params.get("rainfall_field")
        substrate_field = params.get("substrate_field")
        forest_field = params.get("forest_field")

        habitat_parts = []

        # Holdridge life zone
        if holdridge_field:
            holdridge = self._resolve_reference(occurrence, holdridge_field)
            if holdridge is not None:
                holdridge_map = {
                    "1": "Dry",
                    "2": "Moist",
                    "3": "Wet",
                    1: "Dry",
                    2: "Moist",
                    3: "Wet",
                }
                zone = holdridge_map.get(str(holdridge), f"Zone {holdridge}")
                habitat_parts.append(f"Holdridge life zone: {zone}")

        # Rainfall
        if rainfall_field:
            rainfall = self._resolve_reference(occurrence, rainfall_field)
            if rainfall is not None:
                habitat_parts.append(f"Annual rainfall: {rainfall}mm")

        # Substrate
        if substrate_field:
            substrate = self._resolve_reference(occurrence, substrate_field)
            if substrate is not None:
                substrate_type = "ultramafic" if substrate else "non-ultramafic"
                habitat_parts.append(f"Substrate: {substrate_type}")

        # Forest
        if forest_field:
            forest = self._resolve_reference(occurrence, forest_field)
            if forest is not None:
                forest_type = "forest" if forest else "non-forest"
                habitat_parts.append(f"Habitat: {forest_type}")

        return "; ".join(habitat_parts) if habitat_parts else None

    def _count_occurrences(
        self, occurrence: Dict[str, Any], params: Dict[str, Any]
    ) -> int:
        """Count occurrences for the current taxon (for index generation)."""
        # Get taxon ID from the current taxon data
        taxon_id = self._current_taxon.get("taxon_id") or self._current_taxon.get("id")
        if not taxon_id:
            return 0

        # Fetch occurrences count from database
        occurrences = self._fetch_occurrences_from_db(taxon_id)
        return len(occurrences)

    def _current_date(self, occurrence: Dict[str, Any], params: Dict[str, Any]) -> str:
        """Generate current date in specified format."""
        from datetime import datetime

        date_format = params.get("format", "%Y-%m-%d")
        return datetime.now().strftime(date_format)

    def _count_processed_taxa(
        self, occurrence: Dict[str, Any], params: Dict[str, Any]
    ) -> int:
        """Count total number of taxa being processed (placeholder)."""
        # This would need to be implemented at the exporter level
        # For now, return a placeholder value
        return 0

    def _count_total_occurrences(
        self, occurrence: Dict[str, Any], params: Dict[str, Any]
    ) -> int:
        """Count total number of occurrences across all taxa (placeholder)."""
        # This would need to be implemented at the exporter level
        # For now, return a placeholder value
        return 0
