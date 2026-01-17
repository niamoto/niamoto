/**
 * Hook for fetching and managing widget templates
 */
import { useState, useEffect, useCallback } from 'react'
import type {
  TemplatesListResponse,
  SuggestionsResponse,
  GenerateConfigResponse,
  TemplateSuggestion
} from './types'

const API_BASE = '/api/templates'

interface UseTemplatesReturn {
  templates: TemplatesListResponse | null
  loading: boolean
  error: string | null
  refetch: () => void
}

interface UseSuggestionsReturn {
  suggestions: TemplateSuggestion[]
  loading: boolean
  error: string | null
  columnsAnalyzed: number
  refetch: () => void
}

interface SelectedTemplate {
  template_id: string
  plugin: string
  config: Record<string, unknown>
}

interface UseGenerateConfigReturn {
  generate: (templates: SelectedTemplate[], groupBy?: string, referenceKind?: string) => Promise<GenerateConfigResponse | null>
  loading: boolean
  error: string | null
}

interface SaveConfigResponse {
  success: boolean
  message: string
  file_path: string
  widgets_added: number
  widgets_updated: number
}

interface UseSaveConfigReturn {
  save: (config: GenerateConfigResponse, mode?: 'merge' | 'replace') => Promise<SaveConfigResponse | null>
  loading: boolean
  error: string | null
}

/**
 * Fetch all available templates
 */
export function useTemplates(): UseTemplatesReturn {
  const [templates, setTemplates] = useState<TemplatesListResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchTemplates = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const response = await fetch(`${API_BASE}/taxons`)
      if (!response.ok) {
        throw new Error(`Failed to fetch templates: ${response.statusText}`)
      }
      const data = await response.json()
      setTemplates(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchTemplates()
  }, [fetchTemplates])

  return { templates, loading, error, refetch: fetchTemplates }
}

/**
 * Fetch template suggestions based on data analysis
 * @param groupBy - The reference/group to get suggestions for (e.g., 'taxons', 'plots', 'shapes')
 * @param entity - The data source entity (default: 'occurrences')
 */
export function useSuggestions(
  groupBy: string = 'taxons',
  entity: string = 'occurrences'
): UseSuggestionsReturn {
  const [suggestions, setSuggestions] = useState<TemplateSuggestion[]>([])
  const [columnsAnalyzed, setColumnsAnalyzed] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchSuggestions = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      // Use dynamic groupBy in the API path (no max_suggestions = use API default of 50)
      const response = await fetch(
        `${API_BASE}/${groupBy}/suggestions?entity=${entity}`
      )
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}))
        throw new Error(errorData.detail || `Failed to fetch suggestions: ${response.statusText}`)
      }
      const data: SuggestionsResponse = await response.json()
      setSuggestions(data.suggestions)
      setColumnsAnalyzed(data.columns_analyzed)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error')
      setSuggestions([])
    } finally {
      setLoading(false)
    }
  }, [groupBy, entity])

  useEffect(() => {
    fetchSuggestions()
  }, [fetchSuggestions])

  return { suggestions, columnsAnalyzed, loading, error, refetch: fetchSuggestions }
}

/**
 * Generate transform config from selected templates
 */
export function useGenerateConfig(): UseGenerateConfigReturn {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const generate = useCallback(async (
    templates: SelectedTemplate[],
    groupBy: string = 'taxons',
    referenceKind: string = 'flat'
  ): Promise<GenerateConfigResponse | null> => {
    setLoading(true)
    setError(null)
    try {
      const response = await fetch(`${API_BASE}/generate-config`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          templates: templates,
          group_by: groupBy,
          reference_kind: referenceKind
        })
      })
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}))
        throw new Error(errorData.detail || `Failed to generate config: ${response.statusText}`)
      }
      return await response.json()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error')
      return null
    } finally {
      setLoading(false)
    }
  }, [])

  return { generate, loading, error }
}

/**
 * Save generated config to transform.yml
 * @param mode - 'merge' to add widgets to existing config, 'replace' to overwrite all widgets
 */
export function useSaveConfig(): UseSaveConfigReturn {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const save = useCallback(async (
    config: GenerateConfigResponse,
    mode: 'merge' | 'replace' = 'replace'
  ): Promise<SaveConfigResponse | null> => {
    setLoading(true)
    setError(null)
    try {
      const response = await fetch(`${API_BASE}/save-config`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          group_by: config.group_by,
          sources: config.sources,
          widgets_data: config.widgets_data,
          mode: mode
        })
      })
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}))
        throw new Error(errorData.detail || `Failed to save config: ${response.statusText}`)
      }
      return await response.json()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error')
      return null
    } finally {
      setLoading(false)
    }
  }, [])

  return { save, loading, error }
}

/**
 * Fetch configured widgets from transform.yml
 * Returns the template_ids that are already saved in configuration
 */
interface ConfiguredWidgetsResponse {
  configured_ids: string[]
  has_config: boolean
}

interface UseConfiguredWidgetsReturn {
  configuredIds: string[]
  hasConfig: boolean
  loading: boolean
  error: string | null
  refetch: () => void
}

export function useConfiguredWidgets(groupBy: string): UseConfiguredWidgetsReturn {
  const [data, setData] = useState<ConfiguredWidgetsResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchConfigured = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const response = await fetch(`${API_BASE}/${groupBy}/configured`)
      if (!response.ok) {
        throw new Error(`Failed to fetch configured widgets: ${response.statusText}`)
      }
      const result: ConfiguredWidgetsResponse = await response.json()
      setData(result)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error')
      setData({ configured_ids: [], has_config: false })
    } finally {
      setLoading(false)
    }
  }, [groupBy])

  useEffect(() => {
    fetchConfigured()
  }, [fetchConfigured])

  return {
    configuredIds: data?.configured_ids || [],
    hasConfig: data?.has_config || false,
    loading,
    error,
    refetch: fetchConfigured
  }
}

/**
 * Selection management hook
 *
 * @param initialSuggestions - List of suggestions to select from
 * @param existingIds - Optional Set of template IDs already configured (from transform.yml)
 *                      If provided and non-empty, these will be pre-selected instead of auto-selection
 */
export function useTemplateSelection(
  initialSuggestions: TemplateSuggestion[] = [],
  existingIds?: Set<string>
) {
  const [selected, setSelected] = useState<Set<string>>(new Set())

  // Select based on existing config or auto-select high-confidence suggestions
  useEffect(() => {
    if (existingIds && existingIds.size > 0) {
      // Mode édition: use existing configured IDs
      // Only select IDs that are also in the suggestions list
      const validExisting = new Set(
        Array.from(existingIds).filter(id =>
          initialSuggestions.some(s => s.template_id === id)
        )
      )
      setSelected(validExisting)
    } else {
      // Mode création: auto-select high-confidence suggestions
      const autoSelected = new Set(
        initialSuggestions
          .filter(s => s.confidence >= 0.7 || s.is_recommended)
          .map(s => s.template_id)
      )
      setSelected(autoSelected)
    }
  }, [initialSuggestions, existingIds])

  const toggle = useCallback((templateId: string) => {
    setSelected(prev => {
      const next = new Set(prev)
      if (next.has(templateId)) {
        next.delete(templateId)
      } else {
        next.add(templateId)
      }
      return next
    })
  }, [])

  const selectAll = useCallback((templateIds: string[]) => {
    setSelected(new Set(templateIds))
  }, [])

  const deselectAll = useCallback(() => {
    setSelected(new Set())
  }, [])

  const isSelected = useCallback((templateId: string) => selected.has(templateId), [selected])

  return {
    selected: Array.from(selected),
    selectedSet: selected,
    toggle,
    selectAll,
    deselectAll,
    isSelected,
    count: selected.size
  }
}
