/**
 * Types for Widget Gallery - Template-based widget configuration
 */

export type WidgetCategory = 'navigation' | 'info' | 'map' | 'chart' | 'gauge' | 'donut' | 'table'

export interface TemplateInfo {
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
  plugin: string
  category: WidgetCategory
  icon: string
  confidence: number
  source: 'auto' | 'template' | 'generic' | 'class_object'
  source_name: string  // Actual source dataset name (from import.yml)
  matched_column: string | null
  match_reason: string | null
  is_recommended: boolean
  config: Record<string, unknown>
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

export interface GenerateConfigRequest {
  template_ids: string[]
  group_by: string
}

export interface GenerateConfigResponse {
  group_by: string
  sources: Array<Record<string, unknown>>
  widgets_data: Record<string, unknown>
}

// Category display info
export const CATEGORY_INFO: Record<WidgetCategory, { label: string; color: string; bgColor: string }> = {
  navigation: { label: 'Navigation', color: 'text-violet-600', bgColor: 'bg-violet-50 dark:bg-violet-950/30' },
  info: { label: 'Information', color: 'text-blue-600', bgColor: 'bg-blue-50 dark:bg-blue-950/30' },
  map: { label: 'Carte', color: 'text-emerald-600', bgColor: 'bg-emerald-50 dark:bg-emerald-950/30' },
  chart: { label: 'Graphique', color: 'text-amber-600', bgColor: 'bg-amber-50 dark:bg-amber-950/30' },
  gauge: { label: 'Jauge', color: 'text-teal-600', bgColor: 'bg-teal-50 dark:bg-teal-950/30' },
  donut: { label: 'Donut', color: 'text-orange-600', bgColor: 'bg-orange-50 dark:bg-orange-950/30' },
  table: { label: 'Tableau', color: 'text-slate-600', bgColor: 'bg-slate-50 dark:bg-slate-950/30' },
}

// Source display info
export const SOURCE_INFO: Record<string, { label: string; description: string }> = {
  auto: { label: 'Auto-detected', description: 'Automatic matching with your columns' },
  template: { label: 'Template', description: 'Recommended business template' },
  generic: { label: 'Generic', description: 'Suggestion based on data type' },
  class_object: { label: 'Pre-computed CSV', description: 'Pre-computed imported data' },
}

// Plugin descriptions for user-friendly display
export interface PluginInfo {
  label: string
  description: string
  getDetailedLabel?: (config: Record<string, unknown>) => string
}

export const PLUGIN_INFO: Record<string, PluginInfo> = {
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

/**
 * Get plugin description
 */
export function getPluginDescription(plugin: string): string {
  return PLUGIN_INFO[plugin]?.description || ''
}

// Field group for grouped gallery view
export interface FieldGroup {
  field: string
  displayName: string
  source: 'auto' | 'class_object'
  suggestions: TemplateSuggestion[]
  primarySuggestion: TemplateSuggestion
  selectedCount: number
  hasRecommended: boolean
}

/**
 * Group suggestions by matched_column field
 */
export function groupSuggestionsByField(
  suggestions: TemplateSuggestion[],
  selectedIds: Set<string>
): FieldGroup[] {
  const groups = new Map<string, TemplateSuggestion[]>()

  // Group by matched_column
  suggestions.forEach((suggestion) => {
    const field = suggestion.matched_column || 'other'
    if (!groups.has(field)) {
      groups.set(field, [])
    }
    groups.get(field)!.push(suggestion)
  })

  // Transform to FieldGroup array
  return Array.from(groups.entries())
    .map(([field, fieldSuggestions]): FieldGroup => {
      // Sort by confidence within group (highest first)
      const sorted = [...fieldSuggestions].sort((a, b) => b.confidence - a.confidence)
      const hasRecommended = sorted.some((s) => s.is_recommended)

      // Humanize field name for display
      const displayName = field
        .replace(/_/g, ' ')
        .replace(/\b\w/g, (c) => c.toUpperCase())

      return {
        field,
        displayName,
        source: sorted[0].source === 'class_object' ? 'class_object' : 'auto',
        suggestions: sorted,
        primarySuggestion: sorted[0],
        selectedCount: sorted.filter((s) => selectedIds.has(s.template_id)).length,
        hasRecommended,
      }
    })
    // Sort groups: recommended first, then by max confidence
    .sort((a, b) => {
      if (a.hasRecommended !== b.hasRecommended) return a.hasRecommended ? -1 : 1
      return b.primarySuggestion.confidence - a.primarySuggestion.confidence
    })
}
