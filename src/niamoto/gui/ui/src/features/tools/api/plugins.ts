import { apiClient } from '@/shared/lib/api/client'
import { getApiErrorMessage } from '@/shared/lib/api/errors'

export type PluginType = 'loader' | 'transformer' | 'exporter' | 'widget'

export interface ParameterSchema {
  name: string
  type: string
  required?: boolean
  default?: unknown
  description?: string
  enum?: unknown[]
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
  example_config?: Record<string, unknown>
}

export interface PluginCategoriesResponse {
  categories: string[]
}

export async function listPlugins(
  type?: PluginType,
  category?: string
): Promise<Plugin[]> {
  try {
    const response = await apiClient.get<Plugin[]>('/plugins/', {
      params: {
        ...(type ? { type } : {}),
        ...(category ? { category } : {}),
      },
    })
    return response.data
  } catch (error) {
    throw new Error(getApiErrorMessage(error, 'Failed to fetch plugins'))
  }
}

export async function getPlugin(pluginId: string): Promise<Plugin> {
  try {
    const response = await apiClient.get<Plugin>(`/plugins/${pluginId}/`)
    return response.data
  } catch (error) {
    throw new Error(getApiErrorMessage(error, 'Failed to fetch plugin'))
  }
}

export async function listPluginCategories(): Promise<string[]> {
  try {
    const response = await apiClient.get<PluginCategoriesResponse>(
      '/plugins/categories/list'
    )
    return response.data.categories || []
  } catch (error) {
    throw new Error(getApiErrorMessage(error, 'Failed to fetch categories'))
  }
}
