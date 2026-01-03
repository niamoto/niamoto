import { useState, useEffect, useCallback } from 'react'
import { apiClient } from './client'

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
  const [data, setData] = useState<WidgetSuggestionsResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchSuggestions = useCallback(async () => {
    if (!groupBy) {
      setLoading(false)
      return
    }

    setLoading(true)
    setError(null)

    try {
      const response = await getWidgetSuggestions(groupBy, sourceName)
      setData(response)
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Erreur lors du chargement'
      setError(message)
    } finally {
      setLoading(false)
    }
  }, [groupBy, sourceName])

  useEffect(() => {
    fetchSuggestions()
  }, [fetchSuggestions])

  return {
    data,
    classObjects: data?.class_objects ?? [],
    pluginSchemas: data?.plugin_schemas ?? {},
    patternGroups: data?.pattern_groups ?? {},
    categoriesSummary: data?.categories_summary ?? {},
    loading,
    error,
    refetch: fetchSuggestions,
  }
}
