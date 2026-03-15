"""
Pydantic models for templates API.

These models define the request/response schemas for template-related endpoints.
Extracted from templates.py for better organization.
"""

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


# =============================================================================
# TEMPLATE INFO MODELS
# =============================================================================


class TemplateInfo(BaseModel):
    """Basic template information."""

    id: str
    name: str
    description: str
    plugin: str
    category: str
    icon: str
    is_recommended: bool
    has_auto_detect: bool


class TemplateSuggestionResponse(BaseModel):
    """A template suggestion with confidence."""

    template_id: str
    name: str
    description: str
    plugin: str  # transformer plugin
    category: str
    icon: str
    confidence: float
    source: str  # "auto" | "template" | "generic"
    source_name: str  # Actual source dataset name (from import.yml)
    matched_column: Optional[str] = None
    match_reason: Optional[str] = None
    is_recommended: bool
    config: Dict[str, Any]  # transformer params
    widget_plugin: Optional[str] = None  # widget plugin (enables inline preview)
    widget_params: Optional[Dict[str, Any]] = (
        None  # widget params (x_axis, y_axis, etc.)
    )
    alternatives: List[str] = []  # Alternative template IDs


class TemplatesListResponse(BaseModel):
    """Response for listing templates."""

    templates: List[TemplateInfo]
    categories: List[str]
    total: int


class SuggestionsResponse(BaseModel):
    """Response for template suggestions."""

    suggestions: List[TemplateSuggestionResponse]
    entity_type: str
    columns_analyzed: int
    total_suggestions: int


# =============================================================================
# CONFIG GENERATION MODELS
# =============================================================================


class SelectedTemplate(BaseModel):
    """A selected template with its configuration."""

    template_id: str
    plugin: str  # Transformer plugin name
    config: Dict[str, Any] = {}
    widget_plugin: Optional[str] = None  # Widget plugin (from suggestion)
    widget_params: Optional[Dict[str, Any]] = None  # Widget params (from suggestion)


class GenerateConfigRequest(BaseModel):
    """Request to generate transform config."""

    templates: List[SelectedTemplate] = Field(
        ..., description="List of selected templates with configs"
    )
    group_by: str = Field(
        ..., description="Reference name for group_by (from import.yml)"
    )
    reference_kind: str = Field(
        default="generic",
        description="Reference kind: hierarchical | generic | spatial",
    )


class GenerateConfigResponse(BaseModel):
    """Response with generated config."""

    group_by: str
    sources: List[Dict[str, Any]]
    widgets_data: Dict[str, Any]


class SaveConfigRequest(BaseModel):
    """Request to save generated config to transform.yml."""

    group_by: str = Field(..., description="Reference name for the group")
    sources: List[Dict[str, Any]] = Field(..., description="Sources configuration")
    widgets_data: Dict[str, Any] = Field(..., description="Widgets configuration")
    mode: Literal["merge", "replace"] = Field(
        default="replace",
        description="'merge' adds new widgets to existing, 'replace' overwrites all widgets",
    )


class SaveConfigResponse(BaseModel):
    """Response after saving config."""

    success: bool
    message: str
    file_path: str
    widgets_added: int
    widgets_updated: int


# =============================================================================
# CLASS OBJECT / WIDGET SUGGESTION MODELS
# =============================================================================


class ClassObjectSuggestion(BaseModel):
    """A single class_object with its analysis and suggested configuration."""

    name: str
    category: (
        str  # scalar, binary, ternary, multi_category, numeric_bins, large_category
    )
    cardinality: int
    class_names: List[str]
    value_type: str  # numeric or categorical
    suggested_plugin: str
    confidence: float
    auto_config: Dict[str, Any]
    mapping_hints: Dict[str, str]
    related_class_objects: List[str]
    pattern_group: Optional[str]


class WidgetTemplate(BaseModel):
    """A predefined widget template for complex configurations."""

    name: str
    description: str
    plugin: str
    complexity: str  # simple, medium, complex
    example_config: Dict[str, Any]
    applicable_categories: List[str]
    variables: List[Dict[str, str]] = []  # For template variables


class PluginParameter(BaseModel):
    """A parameter definition for a plugin wizard."""

    name: str
    type: str  # class_object_select, class_object_list, binary_mapping_list, etc.
    label: str
    filter_category: Any  # str or list of str
    required: bool = True
    min_items: Optional[int] = None


class PluginSchema(BaseModel):
    """Schema describing a plugin's parameters for wizard UI."""

    name: str
    description: str
    complexity: str  # simple, medium, complex
    applicable_categories: List[str]
    parameters: List[PluginParameter]


class WidgetSuggestionsResponse(BaseModel):
    """Response for class_object-based widget suggestions."""

    source_name: str
    source_path: str
    class_objects: List[ClassObjectSuggestion]
    pattern_groups: Dict[str, List[str]]
    plugin_schemas: Dict[str, PluginSchema]  # Plugin schemas for wizard
    categories_summary: Dict[str, int]  # Count per category


# =============================================================================
# COMBINED WIDGET MODELS
# =============================================================================


class CombinedWidgetRequest(BaseModel):
    """Request for combined widget suggestions based on selected fields."""

    selected_fields: List[str] = Field(
        ..., description="List of field names selected by user", min_length=2
    )
    source_name: str = Field(
        default="occurrences", description="Name of the data source entity"
    )


class CombinedWidgetSuggestion(BaseModel):
    """A suggested combined widget configuration."""

    pattern_type: str
    name: str
    description: str
    fields: List[str]
    field_roles: Dict[str, str]
    confidence: float
    is_recommended: bool
    transformer_config: Dict[str, Any]
    widget_config: Dict[str, Any]


class CombinedWidgetResponse(BaseModel):
    """Response with combined widget suggestions."""

    suggestions: List[CombinedWidgetSuggestion]
    semantic_groups: List[Dict[str, Any]]


class SemanticGroupsResponse(BaseModel):
    """Response with detected semantic groups for proactive suggestions."""

    groups: List[Dict[str, Any]]


# =============================================================================
# INLINE PREVIEW MODELS
# =============================================================================


class InlinePreviewRequest(BaseModel):
    """Request for generating an inline widget preview (POST)."""

    group_by: str
    transformer_plugin: str
    transformer_params: Dict[str, Any] = {}
    widget_plugin: str
    widget_params: Optional[Dict[str, Any]] = None
    widget_title: str = "Preview"
