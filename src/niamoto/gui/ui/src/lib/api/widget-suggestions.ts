import { useQuery } from '@tanstack/react-query'
import { apiClient } from '@/shared/lib/api/client'

/**
 * Class object category types
 */
export type ClassObjectCategory =
  | 'scalar'
  | 'binary'
  | 'ternary'
  | 'multi_category'
  | 'numeric_bins'
  | 'large_category'

/**
 * A class_object analysis with suggested plugin and auto-config
 */
export interface ClassObjectSuggestion {
  name: string
  category: ClassObjectCategory
  cardinality: number
  class_names: string[]
  value_type: 'numeric' | 'categorical'
  suggested_plugin: string
  confidence: number
  auto_config: Record<string, unknown>
  mapping_hints: Record<string, string>
  related_class_objects: string[]
  pattern_group: string | null
}

/**
 * A parameter definition for plugin wizard
 */
export interface PluginParameter {
  name: string
  type: 'class_object_select' | 'class_object_list' | 'binary_mapping_list' | 'series_config_list'
  label: string
  filter_category: string | string[]
  required: boolean
  min_items?: number
}

/**
 * Plugin schema for wizard UI
 */
export interface PluginSchema {
  name: string
  description: string
  complexity: 'simple' | 'medium' | 'complex'
  applicable_categories: ClassObjectCategory[]
  parameters: PluginParameter[]
}

/**
 * Response from the widget-suggestions endpoint
 */
export interface WidgetSuggestionsResponse {
  source_name: string
  source_path: string
  class_objects: ClassObjectSuggestion[]
  pattern_groups: Record<string, string[]>
  plugin_schemas: Record<string, PluginSchema>
  categories_summary: Record<ClassObjectCategory, number>
}

/**
 * Category display information (generic, no domain-specific examples)
 */
export const CATEGORY_INFO: Record<
  ClassObjectCategory,
  { label: string; description: string; color: string; bgColor: string }
> = {
  scalar: {
    label: 'Scalaires',
    description: 'Valeurs uniques (metriques simples)',
    color: 'text-blue-600',
    bgColor: 'bg-blue-50 dark:bg-blue-950/30',
  },
  binary: {
    label: 'Binaires',
    description: 'Exactement 2 categories',
    color: 'text-emerald-600',
    bgColor: 'bg-emerald-50 dark:bg-emerald-950/30',
  },
  ternary: {
    label: 'Ternaires',
    description: 'Exactement 3 categories',
    color: 'text-amber-600',
    bgColor: 'bg-amber-50 dark:bg-amber-950/30',
  },
  multi_category: {
    label: 'Multi-categories',
    description: 'Entre 4 et 15 categories',
    color: 'text-violet-600',
    bgColor: 'bg-violet-50 dark:bg-violet-950/30',
  },
  numeric_bins: {
    label: 'Series numeriques',
    description: 'Distributions par classes numeriques',
    color: 'text-teal-600',
    bgColor: 'bg-teal-50 dark:bg-teal-950/30',
  },
  large_category: {
    label: 'Grandes categories',
    description: 'Plus de 15 categories',
    color: 'text-orange-600',
    bgColor: 'bg-orange-50 dark:bg-orange-950/30',
  },
}

/**
 * Plugin display information (generic descriptions)
 */
export const PLUGIN_INFO: Record<
  string,
  { label: string; description: string }
> = {
  class_object_field_aggregator: {
    label: 'Agregateur de champs',
    description: 'Regroupe plusieurs metriques scalaires',
  },
  class_object_series_extractor: {
    label: 'Extracteur de series',
    description: 'Extrait une serie de valeurs numeriques',
  },
  class_object_categories_extractor: {
    label: 'Extracteur de categories',
    description: 'Extrait des categories avec leurs valeurs',
  },
  class_object_binary_aggregator: {
    label: 'Agregateur binaire',
    description: 'Calcule des ratios entre 2 categories',
  },
  class_object_series_ratio_aggregator: {
    label: 'Comparaison de distributions',
    description: 'Compare deux distributions (total vs subset)',
  },
  class_object_categories_mapper: {
    label: 'Comparaison de categories',
    description: 'Compare des categories entre groupes',
  },
  class_object_series_matrix_extractor: {
    label: 'Matrice de series',
    description: 'Multiple series sur le meme axe',
  },
  class_object_series_by_axis_extractor: {
    label: 'Series par axe',
    description: 'Plusieurs types sur un axe commun',
  },
}

/**
 * Fetch widget suggestions for a group
 */
export async function getWidgetSuggestions(
  groupBy: string,
  sourceName?: string
): Promise<WidgetSuggestionsResponse> {
  const params = sourceName ? `?source_name=${encodeURIComponent(sourceName)}` : ''
  const response = await apiClient.get(`/templates/widget-suggestions/${groupBy}${params}`)
  return response.data
}

/**
 * Hook to fetch class_object suggestions for a group
 */
export function useClassObjectSuggestions(groupBy: string, sourceName?: string) {
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['class-object-suggestions', groupBy, sourceName],
    queryFn: () => getWidgetSuggestions(groupBy, sourceName),
    enabled: !!groupBy,
    staleTime: 60_000,
  })

  return {
    data: data ?? null,
    classObjects: data?.class_objects ?? [],
    pluginSchemas: data?.plugin_schemas ?? {},
    patternGroups: data?.pattern_groups ?? {},
    categoriesSummary: data?.categories_summary ?? {},
    loading: isLoading,
    error: error?.message ?? null,
    refetch: () => { refetch() },
  }
}

// =============================================================================
// MULTI-FIELD COMBINED WIDGET SUGGESTIONS
// =============================================================================

/**
 * Multi-field pattern types
 */
export type MultiFieldPatternType =
  | 'phenology'
  | 'allometry'
  | 'temporal_series'
  | 'categorical_comparison'
  | 'boolean_comparison'
  | 'numeric_correlation'
  | 'trait_comparison'

/**
 * A combined widget suggestion for multiple fields
 */
export interface CombinedWidgetSuggestion {
  pattern_type: MultiFieldPatternType
  name: string
  description: string
  fields: string[]
  field_roles: Record<string, string>
  confidence: number
  is_recommended: boolean
  transformer_config: Record<string, unknown>
  widget_config: Record<string, unknown>
}

/**
 * Semantic group detected proactively
 */
export interface SemanticGroup {
  group_name: string
  display_name: string
  description: string
  fields: string[]
  pattern_type: MultiFieldPatternType
}

/**
 * Response from combined-suggestions endpoint
 */
export interface CombinedWidgetResponse {
  suggestions: CombinedWidgetSuggestion[]
  semantic_groups: SemanticGroup[]
}

/**
 * Response from semantic-groups endpoint
 */
export interface SemanticGroupsResponse {
  groups: SemanticGroup[]
}

/**
 * Multi-field pattern display info
 * icon: Lucide icon name (see PATTERN_ICONS in CombinedWidgetModal)
 */
export const PATTERN_INFO: Record<
  MultiFieldPatternType,
  { label: string; description: string; icon: string; color: string }
> = {
  phenology: {
    label: 'Phénologie',
    description: 'Distribution temporelle des états (floraison, fructification)',
    icon: 'Flower2',
    color: 'text-pink-600',
  },
  allometry: {
    label: 'Allométrie',
    description: 'Relation entre dimensions (diamètre, hauteur)',
    icon: 'Ruler',
    color: 'text-blue-600',
  },
  temporal_series: {
    label: 'Série temporelle',
    description: 'Évolution de mesures dans le temps',
    icon: 'TrendingUp',
    color: 'text-green-600',
  },
  categorical_comparison: {
    label: 'Comparaison catégorielle',
    description: 'Comparaison de plusieurs catégories',
    icon: 'BarChart3',
    color: 'text-purple-600',
  },
  boolean_comparison: {
    label: 'Comparaison d\'états',
    description: 'Comparaison de variables booléennes',
    icon: 'ToggleLeft',
    color: 'text-amber-600',
  },
  numeric_correlation: {
    label: 'Corrélation',
    description: 'Relation entre deux variables numériques',
    icon: 'GitCompareArrows',
    color: 'text-teal-600',
  },
  trait_comparison: {
    label: 'Traits fonctionnels',
    description: 'Comparaison de traits écologiques (feuilles, bois, écorce)',
    icon: 'Leaf',
    color: 'text-emerald-600',
  },
}

/**
 * Fetch combined widget suggestions for selected fields
 */
export async function getCombinedWidgetSuggestions(
  referenceName: string,
  selectedFields: string[],
  sourceName: string = 'occurrences'
): Promise<CombinedWidgetResponse> {
  const response = await apiClient.post(
    `/templates/${referenceName}/combined-suggestions`,
    {
      selected_fields: selectedFields,
      source_name: sourceName,
    }
  )
  return response.data
}

/**
 * Fetch semantic groups for proactive suggestions
 */
export async function getSemanticGroups(
  referenceName: string,
  entity: string = 'occurrences'
): Promise<SemanticGroupsResponse> {
  const response = await apiClient.get(
    `/templates/${referenceName}/semantic-groups?entity=${encodeURIComponent(entity)}`
  )
  return response.data
}

/**
 * Hook for combined widget suggestions.
 * Auto-fetch quand selectedFields >= 2 et enabled est true.
 */
export function useCombinedWidgetSuggestions(
  referenceName: string,
  selectedFields: string[],
  sourceName: string = 'occurrences'
) {
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['combined-suggestions', referenceName, selectedFields, sourceName],
    queryFn: () => getCombinedWidgetSuggestions(referenceName, selectedFields, sourceName),
    enabled: !!referenceName && selectedFields.length >= 2,
    staleTime: 30_000,
  })

  return {
    data: data ?? null,
    suggestions: data?.suggestions ?? [],
    semanticGroups: data?.semantic_groups ?? [],
    loading: isLoading,
    error: error?.message ?? null,
    fetchSuggestions: () => { refetch() },
  }
}

/**
 * Hook for semantic groups (proactive detection)
 */
export function useSemanticGroups(
  referenceName: string,
  entity: string = 'occurrences',
  enabled: boolean = true
) {
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['semantic-groups', referenceName, entity],
    queryFn: () => getSemanticGroups(referenceName, entity),
    enabled: enabled && !!referenceName,
    staleTime: 60_000,
  })

  return {
    groups: data?.groups ?? [],
    loading: isLoading,
    error: error?.message ?? null,
    refetch: () => { refetch() },
  }
}

// =============================================================================
// SAVE COMBINED WIDGET
// =============================================================================

/**
 * Request to save a combined widget recipe
 */
export interface SaveCombinedWidgetRequest {
  group_by: string
  recipe: {
    widget_id: string
    transformer: {
      plugin: string
      params: Record<string, unknown>
    }
    widget: {
      plugin: string
      title: string
      params: Record<string, unknown>
      layout: {
        colspan: number
        order: number
      }
    }
  }
}

/**
 * Response after saving a combined widget
 */
export interface SaveCombinedWidgetResponse {
  success: boolean
  message: string
  widget_id: string
  data_source_id: string
}

/**
 * Save a combined widget recipe to transform.yml and export.yml
 */
export async function saveCombinedWidget(
  request: SaveCombinedWidgetRequest
): Promise<SaveCombinedWidgetResponse> {
  const response = await apiClient.post('/recipes/save', request)
  return response.data
}

/**
 * Convert combined widget modal output to API request format
 */
export function createCombinedWidgetRequest(
  groupBy: string,
  config: {
    pattern_type: string
    name: string
    fields: string[]
    transformer: { plugin: string; params: Record<string, unknown> }
    widget: { plugin: string; params: Record<string, unknown> }
  },
  existingWidgetCount: number = 0
): SaveCombinedWidgetRequest {
  // Generate a unique widget ID from the pattern and fields
  const fieldsSuffix = config.fields.slice(0, 2).join('_').replace(/[^a-z0-9_]/gi, '_')
  const widgetId = `${config.pattern_type}_${fieldsSuffix}`.toLowerCase()

  return {
    group_by: groupBy,
    recipe: {
      widget_id: widgetId,
      transformer: {
        plugin: config.transformer.plugin,
        params: config.transformer.params,
      },
      widget: {
        plugin: config.widget.plugin,
        title: config.name,
        params: config.widget.params,
        layout: {
          colspan: 1,
          order: existingWidgetCount, // Add at the end
        },
      },
    },
  }
}
