import { useQuery } from '@tanstack/react-query'
import { apiClient } from '@/shared/lib/api/client'

/**
 * Multi-field pattern types
 */
type MultiFieldPatternType =
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
 * Fetch combined widget suggestions for selected fields
 */
async function getCombinedWidgetSuggestions(
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
async function getSemanticGroups(
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
