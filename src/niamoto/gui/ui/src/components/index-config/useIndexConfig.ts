/**
 * Hook for managing index generator configuration
 *
 * Provides CRUD operations for index_generator in export.yml:
 * - Fetch current config for a group
 * - Update config (page, filters, display_fields, views)
 * - Local state management with save/reset
 * - Auto-detect fields from data
 */
import { useState, useEffect, useCallback, useMemo } from 'react'

const API_BASE = '/api/config'

/**
 * Suggested display field from auto-detection
 */
export interface SuggestedDisplayField {
  name: string
  source: string
  type: 'text' | 'select' | 'boolean' | 'json_array' | 'number'
  label: string
  searchable: boolean
  cardinality?: number
  sample_values?: string[]
  suggested_as_filter: boolean
  format?: string
  dynamic_options: boolean
  priority: 'high' | 'low'  // high = extra_data/field_aggregator, low = other transformers
}

/**
 * Suggested filter from auto-detection
 */
export interface SuggestedFilter {
  field: string
  source: string
  label: string
  type: string
  values: (string | number | boolean)[]
  operator: string
}

/**
 * Response from suggestions endpoint
 */
export interface IndexFieldSuggestions {
  display_fields: SuggestedDisplayField[]
  filters: SuggestedFilter[]
  total_entities: number
}

/**
 * Display field configuration
 */
export interface IndexDisplayField {
  name: string
  source: string  // JSON path like "general_info.name.value"
  fallback?: string
  type: 'text' | 'select' | 'boolean' | 'json_array'
  label?: string
  searchable: boolean
  format?: 'badge' | 'map' | 'number' | 'link'
  mapping?: Record<string, string>
  filter_options?: Array<{ value: string; label: string }>
  dynamic_options: boolean
  display: 'normal' | 'hidden' | 'image_preview' | 'link'

  // Badge-specific
  inline_badge: boolean
  badge_color?: string
  badge_style?: string
  badge_colors?: Record<string, string>
  badge_styles?: Record<string, string>
  true_label?: string
  false_label?: string
  tooltip_mapping?: Record<string, string>

  // Link-specific
  link_template?: string
  link_label?: string
  link_title?: string
  link_target?: string
  css_class?: string
  css_style?: string

  // Image-specific
  image_fields?: Record<string, string>
}

/**
 * Filter configuration
 */
export interface IndexFilterConfig {
  field: string
  values: Array<string | number | boolean>
  operator: 'in' | 'not_in' | 'equals'
}

/**
 * Page configuration
 */
export interface IndexPageConfig {
  title: string
  description?: string
  items_per_page: number
}

/**
 * View configuration
 */
export interface IndexViewConfig {
  type: 'grid' | 'list'
  template?: string
  default: boolean
}

/**
 * Complete index generator configuration
 */
export interface IndexGeneratorConfig {
  enabled: boolean
  template: string
  page_config: IndexPageConfig
  filters?: IndexFilterConfig[]
  display_fields: IndexDisplayField[]
  views?: IndexViewConfig[]
}

/**
 * Default empty configuration (disabled until user enables it)
 */
const DEFAULT_CONFIG: IndexGeneratorConfig = {
  enabled: false,
  template: 'group_index.html',
  page_config: {
    title: 'Index',
    description: '',
    items_per_page: 24,
  },
  filters: [],
  display_fields: [],
  views: [
    { type: 'grid', default: true },
    { type: 'list', default: false },
  ],
}

export interface UseIndexConfigReturn {
  // Current config (local state)
  config: IndexGeneratorConfig
  loading: boolean
  error: string | null
  isDirty: boolean

  // Global mutations
  setEnabled: (enabled: boolean) => void
  setPageConfig: (config: Partial<IndexPageConfig>) => void
  setTemplate: (template: string) => void

  // Filter mutations
  addFilter: (filter: IndexFilterConfig) => void
  updateFilter: (index: number, filter: IndexFilterConfig) => void
  removeFilter: (index: number) => void

  // Display field mutations
  addDisplayField: (field: IndexDisplayField) => void
  updateDisplayField: (index: number, field: Partial<IndexDisplayField>) => void
  removeDisplayField: (index: number) => void
  reorderDisplayFields: (fromIndex: number, toIndex: number) => void

  // View mutations
  setViews: (views: IndexViewConfig[]) => void

  // Persistence
  save: () => Promise<boolean>
  reset: () => void
  refetch: () => void

  // Auto-detection
  fetchSuggestions: () => Promise<IndexFieldSuggestions | null>
  applySuggestions: (suggestions: IndexFieldSuggestions) => void
}

/**
 * Create default display field
 */
export function createDefaultDisplayField(partial: Partial<IndexDisplayField> = {}): IndexDisplayField {
  return {
    name: '',
    source: '',
    type: 'text',
    searchable: false,
    dynamic_options: false,
    display: 'normal',
    inline_badge: false,
    ...partial,
  }
}

/**
 * Hook for managing index generator configuration
 */
export function useIndexConfig(groupBy: string): UseIndexConfigReturn {
  const [serverConfig, setServerConfig] = useState<IndexGeneratorConfig | null>(null)
  const [localConfig, setLocalConfig] = useState<IndexGeneratorConfig>(DEFAULT_CONFIG)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Fetch config from server
  const fetchConfig = useCallback(async () => {
    setLoading(true)
    setError(null)

    try {
      const response = await fetch(`${API_BASE}/export/${groupBy}/index-generator`)

      if (response.status === 404) {
        // No config exists yet, use defaults
        setServerConfig(null)
        setLocalConfig({ ...DEFAULT_CONFIG, page_config: { ...DEFAULT_CONFIG.page_config, title: `Liste des ${groupBy}` } })
        setLoading(false)
        return
      }

      if (!response.ok) {
        throw new Error(`Failed to fetch index config: ${response.statusText}`)
      }

      const data = await response.json()
      setServerConfig(data)
      setLocalConfig(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error')
    } finally {
      setLoading(false)
    }
  }, [groupBy])

  useEffect(() => {
    fetchConfig()
  }, [fetchConfig])

  // Check if config has changed from server state
  const isDirty = useMemo(() => {
    if (!serverConfig && localConfig !== DEFAULT_CONFIG) return true
    return JSON.stringify(serverConfig) !== JSON.stringify(localConfig)
  }, [serverConfig, localConfig])

  // Global mutations
  const setEnabled = useCallback((enabled: boolean) => {
    setLocalConfig(prev => ({ ...prev, enabled }))
  }, [])

  const setPageConfig = useCallback((config: Partial<IndexPageConfig>) => {
    setLocalConfig(prev => ({
      ...prev,
      page_config: { ...prev.page_config, ...config },
    }))
  }, [])

  const setTemplate = useCallback((template: string) => {
    setLocalConfig(prev => ({ ...prev, template }))
  }, [])

  // Filter mutations
  const addFilter = useCallback((filter: IndexFilterConfig) => {
    setLocalConfig(prev => ({
      ...prev,
      filters: [...(prev.filters || []), filter],
    }))
  }, [])

  const updateFilter = useCallback((index: number, filter: IndexFilterConfig) => {
    setLocalConfig(prev => ({
      ...prev,
      filters: (prev.filters || []).map((f, i) => (i === index ? filter : f)),
    }))
  }, [])

  const removeFilter = useCallback((index: number) => {
    setLocalConfig(prev => ({
      ...prev,
      filters: (prev.filters || []).filter((_, i) => i !== index),
    }))
  }, [])

  // Display field mutations
  const addDisplayField = useCallback((field: IndexDisplayField) => {
    setLocalConfig(prev => ({
      ...prev,
      display_fields: [...prev.display_fields, field],
    }))
  }, [])

  const updateDisplayField = useCallback((index: number, field: Partial<IndexDisplayField>) => {
    setLocalConfig(prev => ({
      ...prev,
      display_fields: prev.display_fields.map((f, i) =>
        i === index ? { ...f, ...field } : f
      ),
    }))
  }, [])

  const removeDisplayField = useCallback((index: number) => {
    setLocalConfig(prev => ({
      ...prev,
      display_fields: prev.display_fields.filter((_, i) => i !== index),
    }))
  }, [])

  const reorderDisplayFields = useCallback((fromIndex: number, toIndex: number) => {
    setLocalConfig(prev => {
      const fields = [...prev.display_fields]
      const [removed] = fields.splice(fromIndex, 1)
      fields.splice(toIndex, 0, removed)
      return { ...prev, display_fields: fields }
    })
  }, [])

  // View mutations
  const setViews = useCallback((views: IndexViewConfig[]) => {
    setLocalConfig(prev => ({ ...prev, views }))
  }, [])

  // Save to server
  const save = useCallback(async (): Promise<boolean> => {
    try {
      setError(null)

      const response = await fetch(`${API_BASE}/export/${groupBy}/index-generator`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(localConfig),
      })

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}))
        throw new Error(errorData.detail || 'Failed to save index config')
      }

      const savedConfig = await response.json()
      setServerConfig(savedConfig)
      setLocalConfig(savedConfig)
      return true
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error')
      return false
    }
  }, [groupBy, localConfig])

  // Reset to server state
  const reset = useCallback(() => {
    if (serverConfig) {
      setLocalConfig(serverConfig)
    } else {
      setLocalConfig({ ...DEFAULT_CONFIG, page_config: { ...DEFAULT_CONFIG.page_config, title: `Liste des ${groupBy}` } })
    }
  }, [serverConfig, groupBy])

  // Fetch suggestions from auto-detection
  const fetchSuggestions = useCallback(async (): Promise<IndexFieldSuggestions | null> => {
    try {
      const response = await fetch(`${API_BASE}/export/${groupBy}/index-generator/suggestions`)
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}))
        throw new Error(errorData.detail || 'Failed to fetch suggestions')
      }
      return await response.json()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error')
      return null
    }
  }, [groupBy])

  // Apply suggestions to local config
  const applySuggestions = useCallback((suggestions: IndexFieldSuggestions) => {
    // Convert suggested display fields to IndexDisplayField format
    const displayFields: IndexDisplayField[] = suggestions.display_fields.map(sf => ({
      name: sf.name,
      source: sf.source,
      type: sf.type === 'number' ? 'text' : sf.type,
      label: sf.label,
      searchable: sf.searchable,
      dynamic_options: sf.dynamic_options,
      display: 'normal',
      inline_badge: false,
      format: sf.format as IndexDisplayField['format'],
    }))

    // Convert suggested filters to IndexFilterConfig format
    const filters: IndexFilterConfig[] = suggestions.filters.map(sf => ({
      field: sf.source,
      values: sf.values,
      operator: sf.operator as 'in' | 'not_in' | 'equals',
    }))

    setLocalConfig(prev => ({
      ...prev,
      display_fields: displayFields,
      filters: filters.length > 0 ? filters : prev.filters,
    }))
  }, [])

  return {
    config: localConfig,
    loading,
    error,
    isDirty,

    setEnabled,
    setPageConfig,
    setTemplate,

    addFilter,
    updateFilter,
    removeFilter,

    addDisplayField,
    updateDisplayField,
    removeDisplayField,
    reorderDisplayFields,

    setViews,

    save,
    reset,
    refetch: fetchConfig,

    fetchSuggestions,
    applySuggestions,
  }
}
