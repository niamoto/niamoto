import { useEffect, useState } from 'react'

export type PluginType = 'loader' | 'transformer' | 'exporter' | 'widget'

export interface ParameterSchema {
  name: string
  type: string
  required?: boolean
  default?: any
  description?: string
  enum?: any[]
  min?: number
  max?: number
}

export interface Plugin {
  id: string
  name: string
  type: PluginType
  description: string
  version?: string
  author?: string
  category?: string
  parameters_schema: ParameterSchema[]
  compatible_inputs: string[]
  output_format?: string
  example_config?: Record<string, any>
}

export function usePlugins(type?: PluginType, category?: string) {
  const [plugins, setPlugins] = useState<Plugin[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const fetchPlugins = async () => {
      try {
        setLoading(true)
        setError(null)

        const params = new URLSearchParams()
        if (type) params.append('type', type)
        if (category) params.append('category', category)

        const response = await fetch(`/api/plugins/${params.toString() ? `?${params.toString()}` : ''}`)
        if (!response.ok) {
          throw new Error(`Failed to fetch plugins: ${response.statusText}`)
        }

        const data = await response.json()
        setPlugins(data)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to fetch plugins')
        console.error('Error fetching plugins:', err)
      } finally {
        setLoading(false)
      }
    }

    fetchPlugins()
  }, [type, category])

  return { plugins, loading, error }
}

export function usePlugin(pluginId: string) {
  const [plugin, setPlugin] = useState<Plugin | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!pluginId) {
      setPlugin(null)
      setLoading(false)
      return
    }

    const fetchPlugin = async () => {
      try {
        setLoading(true)
        setError(null)

        const response = await fetch(`/api/plugins/${pluginId}/`)
        if (!response.ok) {
          throw new Error(`Failed to fetch plugin: ${response.statusText}`)
        }

        const data = await response.json()
        setPlugin(data)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to fetch plugin')
        console.error('Error fetching plugin:', err)
      } finally {
        setLoading(false)
      }
    }

    fetchPlugin()
  }, [pluginId])

  return { plugin, loading, error }
}

export function usePluginCategories() {
  const [categories, setCategories] = useState<string[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const fetchCategories = async () => {
      try {
        setLoading(true)
        setError(null)

        const response = await fetch('/api/plugins/categories/list')
        if (!response.ok) {
          throw new Error(`Failed to fetch categories: ${response.statusText}`)
        }

        const data = await response.json()
        setCategories(data.categories || [])
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to fetch categories')
        console.error('Error fetching categories:', err)
      } finally {
        setLoading(false)
      }
    }

    fetchCategories()
  }, [])

  return { categories, loading, error }
}
