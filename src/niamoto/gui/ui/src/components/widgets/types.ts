/**
 * Types for Widget Gallery - Template-based widget configuration
 */

type WidgetCategory = 'navigation' | 'info' | 'map' | 'chart' | 'gauge' | 'donut' | 'table'

interface TemplateInfo {
  id: string
  name: string
  description: string
  plugin: string
  category: WidgetCategory
  icon: string
  is_recommended: boolean
  has_auto_detect: boolean
}

export interface TemplateSuggestion {
  template_id: string
  name: string
  description: string
  plugin: string  // transformer plugin
  widget_plugin?: string  // widget plugin (enables inline preview)
  category: WidgetCategory
  icon: string
  confidence: number
  source: 'auto' | 'template' | 'generic' | 'class_object' | 'entity' | 'reference'
  source_name: string  // Actual source dataset name (from import.yml)
  matched_column: string | null
  match_reason: string | null
  is_recommended: boolean
  config: Record<string, unknown>  // transformer params
  widget_params?: Record<string, unknown>  // widget params (x_axis, y_axis, etc.)
  alternatives: string[]  // Alternative template IDs
}

export interface TemplatesListResponse {
  templates: TemplateInfo[]
  categories: string[]
  total: number
}

export interface SuggestionsResponse {
  suggestions: TemplateSuggestion[]
  entity_type: string
  columns_analyzed: number
  total_suggestions: number
}

export interface GenerateConfigResponse {
  group_by: string
  sources: Array<Record<string, unknown>>
  widgets_data: Record<string, unknown>
}

// Category display info
// Plugin descriptions for user-friendly display
interface PluginInfo {
  label: string
  description: string
  getDetailedLabel?: (config: Record<string, unknown>) => string
}

const PLUGIN_INFO: Record<string, PluginInfo> = {
  // Navigation widget
  hierarchical_nav_widget: {
    label: 'Navigation',
    description: 'Hierarchical or list navigation for the reference',
  },
  // Transformers
  top_ranking: {
    label: 'Top X',
    description: 'Shows the most frequent values',
    getDetailedLabel: (config) => `Top ${config.count || 10}`,
  },
  categorical_distribution: {
    label: 'All categories',
    description: 'Shows the distribution of all values',
  },
  binned_distribution: {
    label: 'Distribution',
    description: 'Distribution by value classes',
  },
  statistical_summary: {
    label: 'Statistics',
    description: 'Mean, min, max and other statistics',
  },
  binary_counter: {
    label: 'Yes/No',
    description: 'Binary count (true/false)',
  },
  geospatial_extractor: {
    label: 'Geolocation',
    description: 'Geographic coordinates extraction',
  },
  field_aggregator: {
    label: 'Aggregation',
    description: 'Multi-field aggregation',
  },
  reference_enrichment_profile: {
    label: 'Enrichment profile',
    description: 'Normalisation des données enrichies par source',
  },
  time_series_analysis: {
    label: 'Time series',
    description: 'Temporal data analysis',
  },
  // Class object extractors
  class_object_series_extractor: {
    label: 'Pre-computed data',
    description: 'Extraction from imported CSV file',
  },
  categories_extractor: {
    label: 'CSV categories',
    description: 'Pre-computed category extraction',
  },
  // Widgets
  bar_plot: {
    label: 'Bar chart',
    description: 'Horizontal or vertical bar chart',
  },
  donut_chart: {
    label: 'Donut chart',
    description: 'Circular chart with center hole',
  },
  radial_gauge: {
    label: 'Gauge',
    description: 'Circular value indicator',
  },
  interactive_map: {
    label: 'Interactive map',
    description: 'Map with geolocated markers',
  },
  info_grid: {
    label: 'Info grid',
    description: 'Grid of informative values',
  },
  enrichment_panel: {
    label: 'Enrichment panel',
    description: 'Panel structuré pour données enrichies',
  },
}

/**
 * Get a user-friendly label for a plugin
 */
export function getPluginLabel(plugin: string, config?: Record<string, unknown>): string {
  const info = PLUGIN_INFO[plugin]
  if (!info) return plugin
  if (info.getDetailedLabel && config) {
    return info.getDetailedLabel(config)
  }
  return info.label
}
