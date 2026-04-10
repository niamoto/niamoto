import { useQuery } from '@tanstack/react-query'
import {
  getPlugin,
  listPluginCategories,
  listPlugins,
  type ParameterSchema,
  type Plugin,
  type PluginType,
} from '@/features/tools/api/plugins'
import { toolsQueryKeys } from '@/features/tools/queryKeys'
export type { ParameterSchema, Plugin, PluginType }

export function usePlugins(type?: PluginType, category?: string) {
  const query = useQuery({
    queryKey: toolsQueryKeys.plugins(type, category),
    queryFn: () => listPlugins(type, category),
  })

  return {
    plugins: query.data ?? [],
    loading: query.isLoading,
    error: query.error?.message ?? null,
  }
}

export function usePlugin(pluginId: string) {
  const query = useQuery({
    queryKey: toolsQueryKeys.plugin(pluginId),
    queryFn: () => getPlugin(pluginId),
    enabled: pluginId.length > 0,
  })

  return {
    plugin: query.data ?? null,
    loading: query.isLoading,
    error: query.error?.message ?? null,
  }
}

export function usePluginCategories() {
  const query = useQuery({
    queryKey: toolsQueryKeys.pluginCategories(),
    queryFn: listPluginCategories,
  })

  return {
    categories: query.data ?? [],
    loading: query.isLoading,
    error: query.error?.message ?? null,
  }
}
