"""
Templates service module.

Provides business logic for widget template suggestions, preview rendering,
and configuration generation.
"""

from niamoto.gui.api.services.templates.utils import (
    # Config loader (import config)
    load_import_config,
    get_hierarchy_info,
    build_reference_info,
    # Entity finder
    find_representative_entity,
    find_entity_by_id,
    # Data loader
    load_sample_data,
    load_class_object_data_for_preview,
    # Widget utils
    CLASS_OBJECT_EXTRACTORS,
    map_transformer_to_widget,
    generate_widget_title,
    generate_widget_params,
    is_class_object_template,
    find_widget_for_transformer,
    parse_dynamic_template_id,
    find_widget_group,
    load_configured_widget,
)

from niamoto.gui.api.services.templates.config_service import (
    load_transform_config,
    save_transform_config,
    load_export_config,
    save_export_config,
    find_transform_group,
    find_export_group,
    find_or_create_transform_group,
)

__all__ = [
    # Config loader (import config)
    "load_import_config",
    "get_hierarchy_info",
    "build_reference_info",
    # Config service (transform/export config)
    "load_transform_config",
    "save_transform_config",
    "load_export_config",
    "save_export_config",
    "find_transform_group",
    "find_export_group",
    "find_or_create_transform_group",
    # Entity finder
    "find_representative_entity",
    "find_entity_by_id",
    # Data loader
    "load_sample_data",
    "load_class_object_data_for_preview",
    # Widget utils
    "CLASS_OBJECT_EXTRACTORS",
    "map_transformer_to_widget",
    "generate_widget_title",
    "generate_widget_params",
    "is_class_object_template",
    "find_widget_for_transformer",
    "parse_dynamic_template_id",
    "find_widget_group",
    "load_configured_widget",
]
