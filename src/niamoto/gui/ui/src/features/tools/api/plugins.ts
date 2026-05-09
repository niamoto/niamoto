import { apiClient } from '@/shared/lib/api/client'
import { getApiErrorMessage } from '@/shared/lib/api/errors'

export type PluginType = 'loader' | 'transformer' | 'exporter' | 'widget'

interface ParameterSchema {
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
