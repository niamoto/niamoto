/**
 * Hooks pour les templates et suggestions de widgets.
 *
 * Architecture React Query :
 * - `useTemplates` — cache des templates disponibles (staleTime: 60s)
 * - `useSuggestions` — suggestions par groupe/entité (staleTime: 60s)
 * - `useConfiguredWidgets` — IDs déjà configurés (staleTime: 30s)
 * - `useGenerateConfig` / `useSaveConfig` — actions impératives (useMutation)
 */
import { useState, useEffect, useCallback } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
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
  widget_plugin?: string
  widget_params?: Record<string, unknown> | null
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

/** Fetch des templates disponibles */
async function fetchTemplates({ signal }: { signal: AbortSignal }): Promise<TemplatesListResponse> {
  const response = await fetch(`${API_BASE}/taxons`, { signal })
  if (!response.ok) {
    throw new Error(`Failed to fetch templates: ${response.statusText}`)
  }
  return response.json()
}

/**
 * Fetch all available templates
 */
export function useTemplates(): UseTemplatesReturn {
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['templates'],
    queryFn: fetchTemplates,
    staleTime: 60_000,
  })

  return {
    templates: data ?? null,
    loading: isLoading,
    error: error?.message ?? null,
    refetch: () => { refetch() }
  }
}

/** Fetch des suggestions par groupe et entité */
async function fetchSuggestions(
  groupBy: string,
  entity: string,
  signal: AbortSignal
): Promise<SuggestionsResponse> {
  const response = await fetch(
    `${API_BASE}/${groupBy}/suggestions?entity=${entity}`,
    { signal }
  )
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}))
    throw new Error(errorData.detail || `Failed to fetch suggestions: ${response.statusText}`)
  }
  return response.json()
}

/**
 * Fetch template suggestions based on data analysis
 */
export function useSuggestions(
  groupBy: string = 'taxons',
  entity: string = 'occurrences',
  enabled: boolean = true
): UseSuggestionsReturn {
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['suggestions', groupBy, entity],
    queryFn: ({ signal }) => fetchSuggestions(groupBy, entity, signal),
    enabled: enabled && !!groupBy,
    staleTime: 60_000,
  })

  return {
    suggestions: data?.suggestions ?? [],
    columnsAnalyzed: data?.columns_analyzed ?? 0,
    loading: isLoading,
    error: error?.message ?? null,
    refetch: () => { refetch() }
  }
}

/**
 * Generate transform config from selected templates
 */
export function useGenerateConfig(): UseGenerateConfigReturn {
  const [error, setError] = useState<string | null>(null)

  const mutation = useMutation({
    mutationFn: async (vars: {
      templates: SelectedTemplate[]
      groupBy: string
      referenceKind: string
    }) => {
      const response = await fetch(`${API_BASE}/generate-config`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          templates: vars.templates,
          group_by: vars.groupBy,
          reference_kind: vars.referenceKind
        })
      })
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}))
        throw new Error(errorData.detail || `Failed to generate config: ${response.statusText}`)
      }
      return response.json() as Promise<GenerateConfigResponse>
    },
    onError: (err: Error) => setError(err.message),
  })

  const generate = useCallback(async (
    templates: SelectedTemplate[],
    groupBy: string = 'taxons',
    referenceKind: string = 'generic'
  ): Promise<GenerateConfigResponse | null> => {
    setError(null)
    try {
      return await mutation.mutateAsync({ templates, groupBy, referenceKind })
    } catch {
      return null
    }
  }, [mutation])

  return { generate, loading: mutation.isPending, error }
}

/**
 * Save generated config to transform.yml
 */
export function useSaveConfig(): UseSaveConfigReturn {
  const [error, setError] = useState<string | null>(null)
  const queryClient = useQueryClient()

  const mutation = useMutation({
    mutationFn: async (vars: {
      config: GenerateConfigResponse
      mode: 'merge' | 'replace'
    }) => {
      const response = await fetch(`${API_BASE}/save-config`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          group_by: vars.config.group_by,
          sources: vars.config.sources,
          widgets_data: vars.config.widgets_data,
          mode: vars.mode
        })
      })
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}))
        throw new Error(errorData.detail || `Failed to save config: ${response.statusText}`)
      }
      return response.json() as Promise<SaveConfigResponse>
    },
    onSuccess: () => {
      // Invalider les configs après sauvegarde
      queryClient.invalidateQueries({ queryKey: ['widget-config'] })
      queryClient.invalidateQueries({ queryKey: ['configured-widgets'] })
    },
    onError: (err: Error) => setError(err.message),
  })

  const save = useCallback(async (
    config: GenerateConfigResponse,
    mode: 'merge' | 'replace' = 'replace'
  ): Promise<SaveConfigResponse | null> => {
    setError(null)
    try {
      return await mutation.mutateAsync({ config, mode })
    } catch {
      return null
    }
  }, [mutation])

  return { save, loading: mutation.isPending, error }
}

/** Fetch des widgets configurés */
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

async function fetchConfiguredWidgets(
  groupBy: string
): Promise<ConfiguredWidgetsResponse> {
  const response = await fetch(`${API_BASE}/${groupBy}/configured`)
  if (!response.ok) {
    throw new Error(`Failed to fetch configured widgets: ${response.statusText}`)
  }
  return response.json()
}

export function useConfiguredWidgets(groupBy: string): UseConfiguredWidgetsReturn {
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['configured-widgets', groupBy],
    queryFn: () => fetchConfiguredWidgets(groupBy),
    staleTime: 30_000,
  })

  return {
    configuredIds: data?.configured_ids ?? [],
    hasConfig: data?.has_config ?? false,
    loading: isLoading,
    error: error?.message ?? null,
    refetch: () => { refetch() }
  }
}

/**
 * Selection management hook
 */
export function useTemplateSelection(
  initialSuggestions: TemplateSuggestion[] = [],
  existingIds?: Set<string>
) {
  const [selected, setSelected] = useState<Set<string>>(new Set())

  // Select based on existing config or auto-select high-confidence suggestions
  useEffect(() => {
    const nextSelected = existingIds && existingIds.size > 0
      ? new Set(
          Array.from(existingIds).filter(id =>
            initialSuggestions.some(s => s.template_id === id)
          )
        )
      : new Set(
          initialSuggestions
            .filter(s => s.confidence >= 0.7 || s.is_recommended)
            .map(s => s.template_id)
        )

    const frameId = window.requestAnimationFrame(() => {
      setSelected(nextSelected)
    })

    return () => window.cancelAnimationFrame(frameId)
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
