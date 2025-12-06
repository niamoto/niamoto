import { useState, useEffect, useCallback } from 'react'
import { API_BASE_URL } from '@/lib/api-config'
import type {
  TransformerSuggestionsResponse,
  TransformerSuggestion,
  SuggestionSelection,
  TransformerConfig,
} from '@/types/suggestions'

interface UseTransformerSuggestionsResult {
  suggestions: TransformerSuggestionsResponse | null
  loading: boolean
  error: string | null
  selections: SuggestionSelection[]
  toggleSelection: (columnName: string, transformerName: string) => void
  selectAll: () => void
  deselectAll: () => void
  getSelectedConfigs: () => TransformerConfig[]
  refetch: () => Promise<void>
}

export function useTransformerSuggestions(
  entityName: string | null
): UseTransformerSuggestionsResult {
  const [suggestions, setSuggestions] =
    useState<TransformerSuggestionsResponse | null>(null)
  const [loading, setLoading] = useState(!!entityName)
  const [error, setError] = useState<string | null>(null)
  const [selections, setSelections] = useState<SuggestionSelection[]>([])

  const fetchSuggestions = useCallback(async () => {
    if (!entityName) {
      setSuggestions(null)
      setSelections([])
      return
    }

    setLoading(true)
    setError(null)

    try {
      const response = await fetch(
        `${API_BASE_URL}/transformer-suggestions/${entityName}`
      )

      if (!response.ok) {
        if (response.status === 404) {
          const data = await response.json()
          throw new Error(data.detail || `Aucune suggestion pour ${entityName}`)
        }
        throw new Error(`Erreur lors de la récupération des suggestions`)
      }

      const data: TransformerSuggestionsResponse = await response.json()
      setSuggestions(data)

      // Initialize selections with top suggestion per column selected by default
      const initialSelections: SuggestionSelection[] = []
      for (const [columnName, columnSuggestions] of Object.entries(
        data.suggestions
      )) {
        columnSuggestions.forEach(
          (suggestion: TransformerSuggestion, index: number) => {
            initialSelections.push({
              columnName,
              transformerName: suggestion.transformer,
              config: suggestion.config,
              selected: index === 0 && suggestion.confidence >= 0.7,
            })
          }
        )
      }
      setSelections(initialSelections)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erreur inconnue')
      setSuggestions(null)
      setSelections([])
    } finally {
      setLoading(false)
    }
  }, [entityName])

  useEffect(() => {
    fetchSuggestions()
  }, [fetchSuggestions])

  const toggleSelection = useCallback(
    (columnName: string, transformerName: string) => {
      setSelections((prev) =>
        prev.map((s) =>
          s.columnName === columnName && s.transformerName === transformerName
            ? { ...s, selected: !s.selected }
            : s
        )
      )
    },
    []
  )

  const selectAll = useCallback(() => {
    setSelections((prev) => prev.map((s) => ({ ...s, selected: true })))
  }, [])

  const deselectAll = useCallback(() => {
    setSelections((prev) => prev.map((s) => ({ ...s, selected: false })))
  }, [])

  const getSelectedConfigs = useCallback(() => {
    return selections.filter((s) => s.selected).map((s) => s.config)
  }, [selections])

  return {
    suggestions,
    loading,
    error,
    selections,
    toggleSelection,
    selectAll,
    deselectAll,
    getSelectedConfigs,
    refetch: fetchSuggestions,
  }
}

// Hook to list entities with available suggestions
export function useEntitiesWithSuggestions() {
  const [entities, setEntities] = useState<string[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchEntities = useCallback(async () => {
    setLoading(true)
    setError(null)

    try {
      const response = await fetch(`${API_BASE_URL}/transformer-suggestions/`)

      if (!response.ok) {
        throw new Error('Erreur lors de la récupération des entités')
      }

      const data: string[] = await response.json()
      setEntities(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erreur inconnue')
      setEntities([])
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchEntities()
  }, [fetchEntities])

  return {
    entities,
    loading,
    error,
    refetch: fetchEntities,
  }
}
