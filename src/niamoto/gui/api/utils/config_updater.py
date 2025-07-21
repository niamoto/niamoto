"""Utility to update Niamoto configuration files based on GUI imports."""

import yaml
from pathlib import Path
from typing import Dict, Any, Optional


def clean_unused_config(config_path: Path) -> None:
    """Remove plots and shapes configuration if they are empty."""
    if not config_path.exists():
        return

    with open(config_path, "r") as f:
        config = yaml.safe_load(f) or {}

    # Remove plots if empty or None
    if "plots" in config and not config["plots"]:
        del config["plots"]

    # Remove shapes if empty list
    if "shapes" in config and (not config["shapes"] or len(config["shapes"]) == 0):
        del config["shapes"]

    # Write back the cleaned config
    with open(config_path, "w") as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False)


def update_import_config(
    config_path: Path,
    import_type: str,
    filename: str,
    field_mappings: Dict[str, str],
    advanced_options: Optional[Dict[str, Any]] = None,
) -> None:
    """Update import.yml with new import configuration."""

    # Read existing config
    if config_path.exists():
        with open(config_path, "r") as f:
            config = yaml.safe_load(f) or {}
    else:
        config = {}

    # Build the import configuration based on type
    if import_type == "taxonomy":
        taxonomy_config = {
            "path": f"imports/{filename}",
        }

        # Build hierarchy configuration
        hierarchy = {"levels": []}

        # Get ranks from advanced options or use defaults
        ranks = ["family", "genus", "species", "infra"]
        if advanced_options and "ranks" in advanced_options:
            ranks = advanced_options["ranks"]

        # Build levels from field mappings
        for rank in ranks:
            if rank in field_mappings:
                hierarchy["levels"].append(
                    {"name": rank, "column": field_mappings[rank]}
                )

        # Add special columns
        if "taxon_id" in field_mappings:
            hierarchy["taxon_id_column"] = field_mappings["taxon_id"]
        if "authors" in field_mappings:
            hierarchy["authors_column"] = field_mappings["authors"]

        taxonomy_config["hierarchy"] = hierarchy

        # Add API enrichment if enabled
        if advanced_options:
            if api_config := advanced_options.get("apiEnrichment"):
                if api_config.get("enabled"):
                    taxonomy_config["api_enrichment"] = {
                        "enabled": True,
                        "plugin": api_config.get("plugin", "api_taxonomy_enricher"),
                        "api_url": api_config.get("api_url"),
                        "auth_method": api_config.get("auth_method", "none"),
                        "query_field": api_config.get("query_field", "full_name"),
                        "rate_limit": api_config.get("rate_limit", 2.0),
                        "cache_results": api_config.get("cache_results", True),
                    }

                    # Add auth params if present
                    if auth_params := api_config.get("auth_params"):
                        taxonomy_config["api_enrichment"]["auth_params"] = auth_params

                    # Add response mapping if present
                    if response_mapping := api_config.get("response_mapping"):
                        taxonomy_config["api_enrichment"]["response_mapping"] = (
                            response_mapping
                        )

        config["taxonomy"] = taxonomy_config

    elif import_type == "plots":
        # If no filename provided, remove plots configuration
        if not filename or filename == "null":
            if "plots" in config:
                del config["plots"]
        else:
            plots_config = {
                "type": "csv",
                "path": f"imports/{filename}",
                "identifier": field_mappings.get("identifier", "id"),
                "locality_field": field_mappings.get("locality", "locality"),
                "location_field": field_mappings.get("location", "geometry"),
            }

        if advanced_options:
            # Add link fields if specified
            if link_field := advanced_options.get("linkField"):
                plots_config["link_field"] = link_field
            if occurrence_link_field := advanced_options.get("occurrenceLinkField"):
                plots_config["occurrence_link_field"] = occurrence_link_field

            # Add hierarchy if enabled
            if hierarchy := advanced_options.get("hierarchy"):
                if hierarchy.get("enabled") and hierarchy.get("levels"):
                    plots_config["hierarchy"] = {
                        "enabled": True,
                        "levels": hierarchy["levels"],
                        "aggregate_geometry": hierarchy.get("aggregate_geometry", True),
                    }

            config["plots"] = plots_config

    elif import_type == "occurrences":
        config["occurrences"] = {
            "type": "csv",
            "path": f"imports/{filename}",
            "identifier": field_mappings.get("taxon_id", "taxon_id"),
            "location_field": field_mappings.get("location", "geometry"),
        }

        # Add plot field if mapped
        if plot_field := field_mappings.get("plot_name"):
            config["occurrences"]["plot_field"] = plot_field

    elif import_type == "shapes":
        # For shapes, we need to handle it as a list
        # Get the type from field_mappings first, then advanced_options.shape_type as fallback
        shape_type = field_mappings.get("type")
        if not shape_type and advanced_options:
            shape_type = advanced_options.get("shape_type", "default")
        if not shape_type:
            shape_type = "default"

        shape_config = {
            "type": shape_type,
            "path": f"imports/{filename}",
            "name_field": field_mappings.get("name", "name"),
        }

        # Add id field if mapped
        if "id" in field_mappings and field_mappings["id"]:
            shape_config["id_field"] = field_mappings["id"]

        # Add properties if specified
        if advanced_options and advanced_options.get("properties"):
            # properties should be a list of field names
            properties = advanced_options["properties"]
            if isinstance(properties, str):
                # If it's a comma-separated string, split it
                properties = [p.strip() for p in properties.split(",") if p.strip()]
            elif not isinstance(properties, list):
                properties = []
            # Only add if not empty
            if properties:
                shape_config["properties"] = properties

        # Initialize shapes as list if not exists
        if "shapes" not in config:
            config["shapes"] = []

        # If advanced_options contains a flag indicating this is the first shape
        # in a batch, clear all existing shapes
        if advanced_options and advanced_options.get("is_first_shape", False):
            config["shapes"] = []

        # Check if this shape already exists (same path and type)
        # to avoid duplicates within the current import session
        existing_index = None
        for i, existing_shape in enumerate(config["shapes"]):
            if (
                existing_shape.get("path") == shape_config["path"]
                and existing_shape.get("type") == shape_config["type"]
            ):
                existing_index = i
                break

        if existing_index is not None:
            # Update existing shape
            config["shapes"][existing_index] = shape_config
        else:
            # Add new shape
            config["shapes"].append(shape_config)

    # Write updated config back to file
    with open(config_path, "w") as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False)
