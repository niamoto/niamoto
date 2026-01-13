"""Utility functions for templates service."""

from niamoto.gui.api.services.templates.utils.config_loader import (
    load_import_config,
    get_hierarchy_info,
    build_reference_info,
)
from niamoto.gui.api.services.templates.utils.entity_finder import (
    find_representative_entity,
    find_entity_by_id,
)
from niamoto.gui.api.services.templates.utils.data_loader import (
    load_sample_data,
    load_class_object_data_for_preview,
)
from niamoto.gui.api.services.templates.utils.widget_utils import (
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

__all__ = [
    # Config loader
    "load_import_config",
    "get_hierarchy_info",
    "build_reference_info",
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
