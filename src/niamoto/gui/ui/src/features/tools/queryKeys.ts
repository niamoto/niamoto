import type { PluginType } from '@/features/tools/hooks/usePlugins'

export const toolsQueryKeys = {
  plugins: (type?: PluginType, category?: string) =>
    ['tools', 'plugins', type ?? 'all', category ?? 'all'] as const,
  plugin: (pluginId: string) => ['tools', 'plugin', pluginId] as const,
  pluginCategories: () => ['tools', 'plugin-categories'] as const,
}
