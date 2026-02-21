"""API models package.

Re-exports general API models and templates-specific models.
"""

# General API models (originally from api/models.py)
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field, ConfigDict


class ConfigSection(BaseModel):
    """Base model for configuration sections."""

    pass


class ImportConfig(ConfigSection):
    """Import configuration model."""

    taxonomy: Optional[Dict[str, Any]] = None
    occurrences: Optional[Dict[str, Any]] = None
    plots: Optional[Dict[str, Any]] = None
    shapes: Optional[List[Dict[str, Any]]] = None


class TransformConfig(ConfigSection):
    """Transform configuration model."""

    pass


class ExportConfig(ConfigSection):
    """Export configuration model."""

    site: Optional[Dict[str, str]] = None
    exports: Optional[List[Dict[str, Any]]] = None


class NiamotoConfig(BaseModel):
    """Complete Niamoto configuration."""

    model_config = ConfigDict(populate_by_name=True)
    import_config: ImportConfig = Field(alias="import")
    transform: Optional[Dict[str, Any]] = None
    export: Optional[ExportConfig] = None


class ValidationResponse(BaseModel):
    """Response model for validation endpoint."""

    valid: bool
    message: Optional[str] = None
    errors: Optional[List[str]] = None


class GenerateResponse(BaseModel):
    """Response model for YAML generation."""

    import_yaml: str
    transform_yaml: str
    export_yaml: str


# Templates-specific models
from niamoto.gui.api.models.templates import (  # noqa: E402
    TemplateInfo,
    TemplateSuggestionResponse,
    TemplatesListResponse,
    SuggestionsResponse,
    SelectedTemplate,
    GenerateConfigRequest,
    GenerateConfigResponse,
    SaveConfigRequest,
    SaveConfigResponse,
    ClassObjectSuggestion,
    WidgetTemplate,
    PluginParameter,
    PluginSchema,
    WidgetSuggestionsResponse,
    CombinedWidgetRequest,
    CombinedWidgetSuggestion,
    CombinedWidgetResponse,
    SemanticGroupsResponse,
    InlinePreviewRequest,
)

__all__ = [
    # General API models
    "ConfigSection",
    "ImportConfig",
    "TransformConfig",
    "ExportConfig",
    "NiamotoConfig",
    "ValidationResponse",
    "GenerateResponse",
    # Templates models
    "TemplateInfo",
    "TemplateSuggestionResponse",
    "TemplatesListResponse",
    "SuggestionsResponse",
    "SelectedTemplate",
    "GenerateConfigRequest",
    "GenerateConfigResponse",
    "SaveConfigRequest",
    "SaveConfigResponse",
    "ClassObjectSuggestion",
    "WidgetTemplate",
    "PluginParameter",
    "PluginSchema",
    "WidgetSuggestionsResponse",
    "CombinedWidgetRequest",
    "CombinedWidgetSuggestion",
    "CombinedWidgetResponse",
    "SemanticGroupsResponse",
    "InlinePreviewRequest",
]
