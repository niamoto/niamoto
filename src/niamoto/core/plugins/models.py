# core/plugins/models.py
"""
Pydantic models for validating the Niamoto export.yml configuration file.

This module defines the overall structure of the export configuration, including
targets, groups, static pages, widgets, and base configurations for plugins
and their parameters. Specific parameter models for individual plugins
(e.g., BarPlotParams, InfoGridParams) are defined within the plugin files themselves.
"""

from typing import Dict, Any, Optional, List, Union

# Use pydantic v2 features if available (e.g., model_validator instead of root_validator)
from pydantic import BaseModel, Field, model_validator, ValidationError, ConfigDict

# --- Base Models ---


class BasePluginParams(BaseModel):
    """
    Base model for the 'params' dictionary within plugin configurations.
    Specific plugins should define their own parameter model inheriting from this.
    Allows extra fields by default if needed, or set model_config = ConfigDict(extra='forbid')
    in subclasses for stricter validation.
    """

    model_config = ConfigDict(
        extra="allow"
    )  # Allow unspecified fields in params, or change to 'forbid'


class PluginConfig(BaseModel):
    """
    Base model representing a plugin configuration entry in YAML
    (e.g., within a list of transformers or potentially exporters/loaders if used).
    """

    plugin: str = Field(..., description="Registered name of the plugin")
    source: Optional[str] = Field(
        None, description="Optional key identifying the input data source"
    )
    params: Dict[str, Any] = Field(
        default_factory=dict, description="Dictionary of plugin-specific parameters"
    )


class WidgetConfig(BaseModel):
    """
    Model representing a widget configuration within the 'widgets' list
    of a 'web_pages' target group.
    """

    plugin: str = Field(..., description="Registered name of the widget plugin")
    data_source: str = Field(
        ..., description="Key identifying the data for this widget"
    )
    params: Dict[str, Any] = Field(
        default_factory=dict,
        description="Dictionary of parameters specific to this widget plugin",
    )
    # Common display options often controlled at the widget level in the config
    title: Optional[str] = Field(
        None, description="Optional title displayed above the widget"
    )
    description: Optional[str] = Field(
        None, description="Optional description displayed below the title"
    )
    # Note: width/height removed, better handled via CSS or specific layout params


# --- Models for HTML Exporter ('web_pages') ---


class SiteConfig(BaseModel):
    """Global site configuration options."""

    title: str = "Niamoto Data Export"
    logo_header: Optional[str] = None
    logo_footer: Optional[str] = None
    lang: str = "en"


class NavigationItem(BaseModel):
    """A single item in the site navigation menu."""

    text: str
    url: str


class StaticPageContext(BaseModel):
    """Context data for a static page."""

    title: Optional[str] = None
    content_source: Optional[str] = None
    content_markdown: Optional[str] = None

    model_config = ConfigDict(extra="allow")  # Allow other custom context keys

    @model_validator(mode="before")
    @classmethod
    def check_content_source_or_markdown(cls, values):
        if values.get("content_source") and values.get("content_markdown"):
            raise ValueError(
                "Cannot specify both 'content_source' and 'content_markdown'."
            )
        return values


class StaticPageConfig(BaseModel):
    """Configuration for a single static page."""

    name: str = Field(..., description="Internal name/identifier for the page")
    template: str = Field(..., description="Path to the Jinja2 template file")
    output_file: str = Field(
        ..., description="Output HTML file path relative to target output_dir"
    )
    context: Optional[StaticPageContext] = Field(default_factory=dict)


class HtmlExporterParams(BasePluginParams):
    """Parameters specific to the 'html_page_exporter'."""

    template_dir: str = Field(
        ..., description="Path to the project's Jinja2 template directory"
    )
    output_dir: str = Field(
        ..., description="Directory where the static site will be generated"
    )
    base_template: str = Field(
        "_base.html", description="Default base template for pages"
    )
    copy_assets_from: List[str] = Field(
        default_factory=list, description="List of user asset directories/files to copy"
    )
    site: SiteConfig = Field(default_factory=SiteConfig)
    navigation: List[NavigationItem] = Field(default_factory=list)
    include_default_assets: bool = Field(
        default=True,
        description="Whether to automatically include Niamoto's default CSS/JS assets",
    )


class IndexGeneratorDisplayField(BaseModel):
    """Configuration for a display field in the index generator."""

    name: str
    source: str  # JSON path like "general_info.name.value"
    fallback: Optional[str] = None  # Fallback field if source is None
    type: str = "text"  # text, select, boolean, json_array
    label: Optional[str] = None
    searchable: bool = False
    format: Optional[str] = None  # badge, map, number, etc.
    mapping: Optional[Dict[str, str]] = None  # For format="map"
    filter_options: Optional[List[Dict[str, str]]] = None  # Static options
    dynamic_options: bool = False  # Generate options from data
    display: str = "normal"  # normal, hidden, image_preview, link

    # Badge-specific fields
    inline_badge: bool = False  # Display as inline badge in title
    badge_color: Optional[str] = (
        None  # CSS classes for badge (e.g., "bg-green-600 text-white")
    )
    badge_style: Optional[str] = None  # Inline CSS styles for badge
    badge_colors: Optional[Dict[str, str]] = None  # Map values to CSS classes
    badge_styles: Optional[Dict[str, str]] = None  # Map values to inline styles
    true_label: Optional[str] = None  # Label for boolean=true
    false_label: Optional[str] = None  # Label for boolean=false
    tooltip_mapping: Optional[Dict[str, str]] = None  # Tooltips for mapped values

    # Link-specific fields (for display="link")
    link_template: Optional[str] = (
        None  # URL template with placeholders (e.g., "https://example.com/{value}")
    )
    link_label: Optional[str] = None  # Link text label
    link_title: Optional[str] = None  # Link title attribute (tooltip)
    link_target: Optional[str] = None  # Link target (_blank, _self, etc.)
    css_class: Optional[str] = None  # CSS classes for styling
    css_style: Optional[str] = None  # Inline CSS styles


class IndexGeneratorFilterConfig(BaseModel):
    """Configuration for filtering items in index generator."""

    field: str  # JSON path to filter on
    values: List[Union[str, int, bool]]  # Allowed values
    operator: str = "in"  # in, not_in, equals, etc.


class IndexGeneratorPageConfig(BaseModel):
    """Configuration for the page display in index generator."""

    title: str
    description: Optional[str] = None
    items_per_page: int = 20


class IndexGeneratorViewConfig(BaseModel):
    """Configuration for display views in index generator."""

    type: str  # grid, list
    template: Optional[str] = None  # Optional custom template
    default: bool = False


class IndexGeneratorConfig(BaseModel):
    """Complete configuration for the index generator."""

    enabled: bool = True
    template: str = "group_index.html"
    page_config: IndexGeneratorPageConfig
    filters: Optional[List[IndexGeneratorFilterConfig]] = None
    display_fields: List[IndexGeneratorDisplayField]
    views: Optional[List[IndexGeneratorViewConfig]] = None
    output_pattern: str = "{group_by}/{id}.html"  # Pattern for detail links


class GroupConfigWeb(BaseModel):
    """Configuration for a group within a 'web_pages' target."""

    group_by: str
    data_source: Optional[str] = None
    index_template: Optional[str] = None  # Template for the index page, optional
    page_template: Optional[str] = None  # Template for the detail page, optional
    output_pattern: str
    index_output_pattern: str
    widgets: List[WidgetConfig]
    index_generator: Optional[IndexGeneratorConfig] = None  # New index generator config


# --- Models for JSON API Exporter ('json_api_exporter') ---


class IndexStructureConfig(BaseModel):
    """Structure configuration for index JSON files."""

    total_key: str = "total"
    list_key: str = "{group}"  # Placeholder for group name (e.g., "taxa", "plots")
    include_total: bool = True


class JsonOptionsConfig(BaseModel):
    """JSON serialization options."""

    indent: Optional[int] = None
    ensure_ascii: bool = False  # Default to false for better unicode handling


class JsonExporterParams(BasePluginParams):
    """Parameters specific to the 'json_api_exporter'."""

    output_dir: str
    detail_output_pattern: str
    index_output_pattern: Optional[str] = None
    index_structure: IndexStructureConfig = Field(default_factory=IndexStructureConfig)
    json_options: JsonOptionsConfig = Field(default_factory=JsonOptionsConfig)


class DetailApiConfig(BaseModel):
    """Configuration for generating detail JSON files."""

    pass_through: bool = True
    fields: Optional[List[Any]] = None  # Define mapping structure if pass_through=False


class IndexApiFieldMapping(BaseModel):
    """Represents one field mapping entry in the index configuration."""

    mapping: Dict[str, Any]

    @model_validator(mode="before")
    @classmethod
    def check_single_entry(cls, values):
        if isinstance(values, dict) and len(values) != 1:
            # Wrap the original dict under 'mapping' key if it's not already
            # This allows writing "- id: id" directly in YAML
            # But internally stores it as mapping={'id': 'id'}
            if "mapping" not in values:  # Avoid double wrapping
                # Check if it's already a valid structure by trying to parse
                try:
                    cls(mapping=values)  # Try parsing as is first
                    return values  # It was already {'mapping': {...}}
                except ValidationError:
                    # Assume it's the short form like {'id': 'id'}
                    return {"mapping": values}
        # If it's already {'mapping': {...}}, proceed
        elif (
            isinstance(values, dict)
            and "mapping" in values
            and len(values["mapping"]) == 1
        ):
            return values
        # If it's just a string like "- field_name", treat as simple mapping
        elif isinstance(values, str):
            return {"mapping": {values: values}}

        raise ValueError("Field mapping must be a dict with one key or a string.")

    def get_output_key(self) -> str:
        return list(self.mapping.keys())[0]

    def get_config(self) -> Any:
        return list(self.mapping.values())[0]


class IndexApiConfig(BaseModel):
    """Configuration for generating index JSON files."""

    fields: List[IndexApiFieldMapping]


class GroupConfigApi(BaseModel):
    """Configuration for a group within a 'json_api_exporter' target."""

    group_by: str
    data_source: Optional[str] = None
    detail: DetailApiConfig = Field(default_factory=DetailApiConfig)
    index: Optional[IndexApiConfig] = None


# --- Models for Darwin Core Exporter (uses json_api_exporter + transformer) ---


class DwcMappingValue(BaseModel):
    """Represents how to generate a value for a DwC term (generator)."""

    generator: str
    params: Dict[str, Any] = Field(default_factory=dict)


class DwcTransformerParams(BasePluginParams):
    """Parameters specific to the 'niamoto_to_dwc_occurrence' transformer."""

    occurrence_list_source: str
    mapping: Dict[str, Union[str, DwcMappingValue]]  # Key is DwC term


class GroupConfigDwc(BaseModel):
    """Configuration for a group within a DwC export target."""

    group_by: str
    data_source: Optional[str] = None
    transformer_plugin: str
    transformer_params: DwcTransformerParams


# --- Top-Level Export Configuration Models ---


class TargetConfig(BaseModel):
    """Model for a single export target defined in the 'exports' list."""

    name: str
    enabled: bool = True
    exporter: str  # Registered name of the exporter plugin
    params: Dict[str, Any] = Field(default_factory=dict)
    static_pages: Optional[List[StaticPageConfig]] = None
    groups: List[Any] = Field(default_factory=list)  # Use Any temporarily

    # Use a validator to ensure params, static_pages, and groups match the exporter type
    @model_validator(mode="after")
    def check_exporter_specific_fields(cls, self):
        exporter_name = self.exporter
        params = self.params
        groups = self.groups
        static_pages = self.static_pages

        try:
            if exporter_name == "html_page_exporter":
                # Validate params
                HtmlExporterParams(**params)
                # Validate groups list contains GroupConfigWeb models
                self.groups = [
                    g if isinstance(g, GroupConfigWeb) else GroupConfigWeb(**g)
                    for g in groups
                ]
                # Validate static_pages (must exist if exporter is html, uses StaticPageConfig)
                self.static_pages = [
                    sp if isinstance(sp, StaticPageConfig) else StaticPageConfig(**sp)
                    for sp in (static_pages or [])
                ]

            elif exporter_name == "json_api_exporter":
                # Validate params
                JsonExporterParams(**params)
                # Validate groups list contains GroupConfigApi or GroupConfigDwc models
                validated_groups = []
                for g in groups:
                    # Heuristic: check if transformer_plugin key exists for DwC type
                    if "transformer_plugin" in g:
                        validated_groups.append(GroupConfigDwc(**g))
                    else:
                        validated_groups.append(GroupConfigApi(**g))
                self.groups = validated_groups
                # Ensure static_pages is None or empty
                if static_pages:
                    raise ValueError(
                        "'static_pages' not allowed for 'json_api_exporter'"
                    )
                self.static_pages = None  # Ensure it's None

            # Add checks for other exporter types here (e.g., csv_exporter)
            # elif exporter_name == "csv_exporter":
            #     CsvExporterParams(**params)
            #     self.groups = [GroupConfigCsv(**g) for g in groups] # Define GroupConfigCsv
            #     ...

            else:
                # Allow unknown exporters but maybe log a warning?
                # Or raise an error if only known exporters are allowed.
                pass  # Or raise ValueError(f"Unknown exporter type: {exporter_name}")

        except ValidationError as e:
            # Improve error message context
            raise ValueError(
                f"Validation failed for target '{self.name}' (exporter: '{exporter_name}'): {e}"
            ) from e

        return self


class ExportConfig(BaseModel):
    """Root model for the entire export.yml configuration file."""

    exports: List[TargetConfig]
