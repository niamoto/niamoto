"""Utility to dynamically extract required fields from Niamoto import methods."""

import inspect
from typing import Dict, List, Any
from niamoto.core.services.importer import ImporterService


def get_import_method_info(method_name: str) -> Dict[str, Any]:
    """Extract parameter information from an import method."""
    importer = ImporterService("")  # Dummy path for introspection
    method = getattr(importer, method_name, None)

    if not method:
        return {}

    # Get method signature
    sig = inspect.signature(method)
    params = {}

    for param_name, param in sig.parameters.items():
        if param_name == "self":
            continue

        param_info = {
            "required": param.default == inspect.Parameter.empty,
            "type": str(param.annotation)
            if param.annotation != inspect.Parameter.empty
            else "Any",
            "default": param.default
            if param.default != inspect.Parameter.empty
            else None,
        }
        params[param_name] = param_info

    return params


def get_required_fields_for_import_type(
    import_type: str,
) -> Dict[str, List[Dict[str, Any]]]:
    """Get required fields for each import type based on method signatures."""

    # Map import types to their corresponding methods
    method_mapping = {
        "taxonomy": "import_taxonomy_from_occurrences",
        "plots": "import_plots",
        "occurrences": "import_occurrences",
        "shapes": "import_shapes",
    }

    # Special handling for each import type based on method parameters
    if import_type == "taxonomy":
        # For import_taxonomy_from_occurrences
        return {
            "fields": [
                {
                    "key": "taxon_id",
                    "label": "Taxon ID",
                    "description": "Unique identifier for each taxon",
                    "required": True,
                },
                {
                    "key": "family",
                    "label": "Family",
                    "description": "Family rank column",
                    "required": True,
                },
                {
                    "key": "genus",
                    "label": "Genus",
                    "description": "Genus rank column",
                    "required": True,
                },
                {
                    "key": "species",
                    "label": "Species",
                    "description": "Species rank column",
                    "required": True,
                },
                {
                    "key": "infra",
                    "label": "Infra",
                    "description": "Infraspecific rank",
                    "required": False,
                },
                {
                    "key": "authors",
                    "label": "Authors",
                    "description": "Taxonomic authority",
                    "required": False,
                },
            ],
            "method_params": get_import_method_info(method_mapping[import_type]),
        }

    elif import_type == "plots":
        # For import_plots - check method signature
        params = get_import_method_info(method_mapping[import_type])
        fields = []

        # Core required fields based on PlotRef model
        fields.extend(
            [
                {
                    "key": "identifier",
                    "label": "Plot Identifier",
                    "description": "Unique identifier field (maps to plot_id)",
                    "required": True,
                },
                {
                    "key": "location",
                    "label": "Location",
                    "description": "Geometry field (WKT or coordinates)",
                    "required": True,
                },
                {
                    "key": "locality",
                    "label": "Locality",
                    "description": "Plot locality name",
                    "required": True,
                },
            ]
        )

        # Optional PlotRef model fields
        fields.extend(
            [
                {
                    "key": "plot_id",
                    "label": "Plot ID",
                    "description": "Numeric plot ID (if different from identifier)",
                    "required": False,
                },
                {
                    "key": "plot_type",
                    "label": "Plot Type",
                    "description": "Type of plot (plot/locality/country)",
                    "required": False,
                },
            ]
        )

        # Linking fields for occurrence relationships
        fields.extend(
            [
                {
                    "key": "link_field",
                    "label": "Plot Link Field",
                    "description": "Field in plot_ref for linking with occurrences",
                    "required": False,
                },
                {
                    "key": "occurrence_link_field",
                    "label": "Occurrence Link Field",
                    "description": "Corresponding field in occurrences table",
                    "required": False,
                },
            ]
        )

        # Note: extra_data fields will be mapped dynamically from any unmapped columns

        return {"fields": fields, "method_params": params}

    elif import_type == "occurrences":
        # For import_occurrences
        params = get_import_method_info(method_mapping[import_type])
        fields = []

        # Map method parameters to UI fields
        param_to_field = {
            "taxon_id_column": {
                "key": "taxon_id",
                "label": "Taxon ID",
                "description": "Reference to taxonomy",
            },
            "location_column": {
                "key": "location",
                "label": "Location",
                "description": "Occurrence coordinates (WKT format)",
            },
        }

        for param_name, field_info in param_to_field.items():
            if param_name in params:
                field = field_info.copy()
                field["required"] = params[param_name]["required"]
                fields.append(field)

        # Add optional fields
        fields.append(
            {
                "key": "plot_name",
                "label": "Plot Name",
                "description": "Link to plot",
                "required": False,
            }
        )

        return {"fields": fields, "method_params": params}

    elif import_type == "shapes":
        # For import_shapes - it takes a config list
        return {
            "fields": [
                {
                    "key": "name",
                    "label": "Name",
                    "description": "Shape name field",
                    "required": True,
                },
                {
                    "key": "type",
                    "label": "Type",
                    "description": "Shape type",
                    "required": False,
                },
            ],
            "method_params": get_import_method_info(method_mapping[import_type]),
        }

    return {"fields": [], "method_params": {}}


def get_all_import_types_info() -> Dict[str, Any]:
    """Get information for all import types."""
    import_types = ["taxonomy", "plots", "occurrences", "shapes"]
    info = {}

    for import_type in import_types:
        info[import_type] = get_required_fields_for_import_type(import_type)

    return info
