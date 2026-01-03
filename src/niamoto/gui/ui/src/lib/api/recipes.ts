import { useState, useEffect, useCallback } from 'react'
import { apiClient } from './client'

/**
 * Source types
 */
export type SourceType = 'occurrences' | 'csv_stats' | 'csv_direct'

/**
 * Information about an available data source
 */
export interface SourceInfo {
  type: SourceType
  name?: string
  columns: string[]
  transformers: string[]
}

/**
 * Response from sources endpoint
 */
export interface SourcesResponse {
  group_by: string
  sources: SourceInfo[]
}

/**
 * Schema for a plugin parameter
 */
export interface ParamSchema {
  type: string
  required: boolean
  default?: unknown
  description?: string
  enum?: string[]
  // Extended schema info for complex types
  items_type?: string  // For arrays
  additional_properties_type?: string  // For dicts
  min_items?: number
  max_items?: number
  // UI hints from Pydantic
  ui_widget?: string
  ui_depends?: string
  ui_condition?: string
  ui_options?: Array<string | { value: string; label: string }>  // Options for select widgets
  ui_min?: number  // Min value for number inputs
  ui_max?: number  // Max value for number inputs
  ui_step?: number  // Step for number inputs
  ui_item_widget?: string  // Widget type for array items
}

/**
 * Schema for a transformer plugin
 */
export interface TransformerSchema {
  name: string
  description: string
  params: Record<string, ParamSchema>
  suggested_widgets: string[]
  source_types: string[]
}

/**
 * Schema for a widget plugin
 */
export interface WidgetSchema {
  name: string
  description: string
  params: Record<string, ParamSchema>
  compatible_transformers: string[]
}

/**
 * Configuration for a transformer in a recipe
 */
export interface TransformerConfig {
  plugin: string
  params: Record<string, unknown>
}

/**
 * Layout configuration for a widget
 */
export interface WidgetLayoutConfig {
  colspan: number
  order: number
}

/**
 * Configuration for widget output in a recipe
 */
export interface WidgetOutputConfig {
  plugin: string
  title?: string
  params: Record<string, unknown>
  layout: WidgetLayoutConfig
}

/**
 * A complete widget recipe
 */
export interface WidgetRecipe {
  widget_id: string
  transformer: TransformerConfig
  widget: WidgetOutputConfig
}

/**
 * Request to save a recipe
 */
export interface SaveRecipeRequest {
  group_by: string
  recipe: WidgetRecipe
}

/**
 * Response from save recipe
 */
export interface SaveRecipeResponse {
  success: boolean
  message: string
  widget_id: string
  data_source_id: string
}

/**
 * Validation error
 */
export interface ValidationError {
  field: string
  message: string
}

/**
 * Response from validate recipe
 */
export interface ValidateRecipeResponse {
  valid: boolean
  errors: ValidationError[]
  warnings: string[]
}

// =============================================================================
// API Functions
// =============================================================================

/**
 * Get available sources for a group
 */
export async function getAvailableSources(groupBy: string): Promise<SourcesResponse> {
  const response = await apiClient.get(`/recipes/sources/${groupBy}`)
  return response.data
}

/**
 * Get transformer schema
 */
export async function getTransformerSchema(pluginName: string): Promise<TransformerSchema> {
  const response = await apiClient.get(`/recipes/transformer-schema/${pluginName}`)
  return response.data
}

/**
 * List all transformers
 */
export async function listTransformers(): Promise<string[]> {
  const response = await apiClient.get('/recipes/transformers')
  return response.data
}

/**
 * List all widgets
 */
export async function listWidgets(): Promise<string[]> {
  const response = await apiClient.get('/recipes/widgets')
  return response.data
}

/**
 * Get widget schema
 */
export async function getWidgetSchema(pluginName: string): Promise<WidgetSchema> {
  const response = await apiClient.get(`/recipes/widget-schema/${pluginName}`)
  return response.data
}

/**
 * Validate a recipe without saving
 */
export async function validateRecipe(request: SaveRecipeRequest): Promise<ValidateRecipeResponse> {
  const response = await apiClient.post('/recipes/validate', request)
  return response.data
}

/**
 * Save a widget recipe
 */
export async function saveRecipe(request: SaveRecipeRequest): Promise<SaveRecipeResponse> {
  const response = await apiClient.post('/recipes/save', request)
  return response.data
}

/**
 * Delete a widget recipe
 */
export async function deleteRecipe(groupBy: string, widgetId: string): Promise<{ success: boolean; message: string }> {
  const response = await apiClient.delete(`/recipes/${groupBy}/${widgetId}`)
  return response.data
}

/**
 * Preview a recipe without saving - returns HTML blob URL
 */
export async function previewRecipe(request: SaveRecipeRequest): Promise<string> {
  const response = await apiClient.post('/recipes/preview', request, {
    responseType: 'text',
  })
  // Create a blob URL from the HTML response
  const blob = new Blob([response.data], { type: 'text/html' })
  return URL.createObjectURL(blob)
}

// =============================================================================
// Hooks
// =============================================================================

/**
 * Hook to fetch available sources for a group
 */
export function useAvailableSources(groupBy: string) {
  const [data, setData] = useState<SourcesResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchSources = useCallback(async () => {
    if (!groupBy) {
      setLoading(false)
      return
    }

    setLoading(true)
    setError(null)

    try {
      const response = await getAvailableSources(groupBy)
      setData(response)
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Error loading sources'
      setError(message)
    } finally {
      setLoading(false)
    }
  }, [groupBy])

  useEffect(() => {
    fetchSources()
  }, [fetchSources])

  return {
    data,
    sources: data?.sources ?? [],
    loading,
    error,
    refetch: fetchSources,
  }
}

/**
 * Hook to fetch transformer schema
 */
export function useTransformerSchema(pluginName: string | null) {
  const [schema, setSchema] = useState<TransformerSchema | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const fetchSchema = useCallback(async () => {
    if (!pluginName) {
      setSchema(null)
      return
    }

    setLoading(true)
    setError(null)

    try {
      const response = await getTransformerSchema(pluginName)
      setSchema(response)
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Error loading schema'
      setError(message)
    } finally {
      setLoading(false)
    }
  }, [pluginName])

  useEffect(() => {
    fetchSchema()
  }, [fetchSchema])

  return {
    schema,
    loading,
    error,
    refetch: fetchSchema,
  }
}

/**
 * Hook to list all transformers
 */
export function useTransformers() {
  const [transformers, setTransformers] = useState<string[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const fetch = async () => {
      try {
        const data = await listTransformers()
        setTransformers(data)
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Error loading transformers'
        setError(message)
      } finally {
        setLoading(false)
      }
    }
    fetch()
  }, [])

  return { transformers, loading, error }
}

/**
 * Hook to list all widgets
 */
export function useWidgets() {
  const [widgets, setWidgets] = useState<string[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const fetch = async () => {
      try {
        const data = await listWidgets()
        setWidgets(data)
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Error loading widgets'
        setError(message)
      } finally {
        setLoading(false)
      }
    }
    fetch()
  }, [])

  return { widgets, loading, error }
}

/**
 * Hook to fetch widget schema
 */
export function useWidgetSchema(pluginName: string | null) {
  const [schema, setSchema] = useState<WidgetSchema | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const fetchSchema = useCallback(async () => {
    if (!pluginName) {
      setSchema(null)
      return
    }

    setLoading(true)
    setError(null)

    try {
      const response = await getWidgetSchema(pluginName)
      setSchema(response)
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Error loading widget schema'
      setError(message)
    } finally {
      setLoading(false)
    }
  }, [pluginName])

  useEffect(() => {
    fetchSchema()
  }, [fetchSchema])

  return {
    schema,
    loading,
    error,
    refetch: fetchSchema,
  }
}

/**
 * Hook for recipe validation
 */
export function useRecipeValidation() {
  const [validating, setValidating] = useState(false)
  const [validation, setValidation] = useState<ValidateRecipeResponse | null>(null)
  const [error, setError] = useState<string | null>(null)

  const validate = useCallback(async (request: SaveRecipeRequest) => {
    setValidating(true)
    setError(null)

    try {
      const response = await validateRecipe(request)
      setValidation(response)
      return response
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Validation error'
      setError(message)
      return null
    } finally {
      setValidating(false)
    }
  }, [])

  return {
    validate,
    validation,
    validating,
    error,
  }
}

/**
 * Hook for saving recipes
 */
export function useSaveRecipe() {
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const save = useCallback(async (request: SaveRecipeRequest) => {
    setSaving(true)
    setError(null)

    try {
      const response = await saveRecipe(request)
      return response
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Error saving recipe'
      setError(message)
      return null
    } finally {
      setSaving(false)
    }
  }, [])

  return {
    save,
    saving,
    error,
  }
}

/**
 * Hook for previewing recipes
 */
export function useRecipePreview() {
  const [previewUrl, setPreviewUrl] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const preview = useCallback(async (request: SaveRecipeRequest) => {
    setLoading(true)
    setError(null)

    // Clean up previous blob URL
    if (previewUrl) {
      URL.revokeObjectURL(previewUrl)
    }

    try {
      const url = await previewRecipe(request)
      setPreviewUrl(url)
      return url
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Preview error'
      setError(message)
      setPreviewUrl(null)
      return null
    } finally {
      setLoading(false)
    }
  }, [previewUrl])

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (previewUrl) {
        URL.revokeObjectURL(previewUrl)
      }
    }
  }, [previewUrl])

  const clearPreview = useCallback(() => {
    if (previewUrl) {
      URL.revokeObjectURL(previewUrl)
    }
    setPreviewUrl(null)
    setError(null)
  }, [previewUrl])

  return {
    preview,
    previewUrl,
    loading,
    error,
    clearPreview,
  }
}
