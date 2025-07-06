"""Utility to update Niamoto configuration files based on GUI imports."""

import yaml
from pathlib import Path
from typing import Dict, Any, Optional


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
            "type": "csv",
            "path": f"imports/{filename}",
            "source": "occurrence",  # We're using import_taxonomy_from_occurrences
        }

        if advanced_options:
            # Add ranks if specified
            if ranks := advanced_options.get("ranks"):
                taxonomy_config["ranks"] = ",".join(ranks)

            # Add API enrichment if enabled
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

        # Add occurrence columns mapping
        taxonomy_config["occurrence_columns"] = field_mappings

        config["taxonomy"] = taxonomy_config

    elif import_type == "plots":
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
        shape_config = {
            "type": advanced_options.get("type", "default")
            if advanced_options
            else "default",
            "path": f"imports/{filename}",
            "name_field": field_mappings.get("name", "name"),
        }

        # Add id field if mapped
        if "id" in field_mappings:
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

        # Add or update shape configuration
        config["shapes"].append(shape_config)

    # Write updated config back to file
    with open(config_path, "w") as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False)
