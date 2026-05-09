import { useQuery } from '@tanstack/react-query'
import {
  listPlugins,
  type Plugin,
  type PluginType,
} from '@/features/tools/api/plugins'
import { toolsQueryKeys } from '@/features/tools/queryKeys'
export type { Plugin, PluginType }

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
