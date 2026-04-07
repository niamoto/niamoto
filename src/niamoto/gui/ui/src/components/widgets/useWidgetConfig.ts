/**
 * Hook pour la gestion des widgets configurés dans transform.yml et export.yml
 *
 * Architecture React Query :
 * - `useQuery` pour le fetch parallèle des deux configs (staleTime: 30s)
 * - `useMutation` + `invalidateQueries` pour les opérations CRUD
 * - Dérivation client-side de `configuredWidgets` via `useMemo`
 */
import { useMemo, useCallback } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import type { LocalizedString } from '@/components/ui/localized-input'

const API_BASE = '/api/config'

/**
 * Represents a configured widget with both transform and export params
 */
export interface ConfiguredWidget {
  id: string                           // Widget name in transform.yml (e.g., "dbh_distribution")
  transformerPlugin: string            // Transformer plugin name (e.g., "binned_distribution")
  widgetPlugin: string                 // Widget plugin name (e.g., "bar_plot")
  title: LocalizedString               // Display title from export config (supports i18n)
  description?: LocalizedString        // Optional description (supports i18n)
  dataSource: string                   // Data source key (usually same as id)
  transformerParams: Record<string, unknown>  // Params from transform.yml
  widgetParams: Record<string, unknown>       // Params from export.yml
  category?: string                    // Widget category (chart, gauge, etc.)
  hasTransformConfig: boolean          // Whether this widget has a transform.yml entry
}

interface TransformConfig {
  group_by: string
  sources?: Array<{
    name: string
    data: string
    grouping: string
    relation?: Record<string, unknown>
  }>
  widgets_data?: Record<string, {
    plugin: string
    params?: Record<string, unknown>
  }>
}

interface ExportWidgetConfig {
  plugin: string
  data_source: string
  title?: LocalizedString
  description?: LocalizedString
  params?: Record<string, unknown>
  layout?: {
    colspan?: number
    order?: number
  }
}

function getNavigationWidgetId(groupBy: string): string {
  return `${groupBy}_hierarchical_nav_widget`
}

function getExportWidgetId(groupBy: string, widget: ExportWidgetConfig): string | null {
  if (widget.data_source) return widget.data_source
  if (widget.plugin === 'hierarchical_nav_widget') return getNavigationWidgetId(groupBy)
  return null
}

interface ExportGroupConfig {
  group_by: string
  widgets?: ExportWidgetConfig[]
  index_generator?: Record<string, unknown>
}

interface ExportConfig {
  exports?: Array<{
    name: string
    exporter: string
    params?: {
      groups?: ExportGroupConfig[]
    }
    groups?: ExportGroupConfig[]
    static_pages?: unknown[]
  }>
}

export interface UseWidgetConfigReturn {
  configuredWidgets: ConfiguredWidget[]
  loading: boolean
  error: string | null

  updateWidget: (widgetId: string, config: Partial<ConfiguredWidget>) => Promise<boolean>
  deleteWidget: (widgetId: string) => Promise<boolean>
  duplicateWidget: (widgetId: string, newId: string) => Promise<boolean>
  reorderWidgets: (widgetIds: string[]) => Promise<boolean>
  refetch: () => void
}

/** Données brutes retournées par le fetch parallèle */
interface RawConfigs {
  transformData: TransformConfig[]
  exportData: ExportConfig
}

/**
 * Parse transform.yml to extract widgets for a specific group
 */
function parseTransformWidgets(
  transformData: TransformConfig[] | Record<string, unknown>,
  groupBy: string
): Map<string, { plugin: string; params: Record<string, unknown> }> {
  const widgets = new Map<string, { plugin: string; params: Record<string, unknown> }>()

  // Handle both array format (list of groups) and object format
  let groups: TransformConfig[] = []

  if (Array.isArray(transformData)) {
    groups = transformData
  } else if (transformData && typeof transformData === 'object') {
    // Check if it's a single group object or has groups array
    const data = transformData as Record<string, unknown>
    if ('group_by' in data && typeof data.group_by === 'string') {
      groups = [data as unknown as TransformConfig]
    }
  }

  // Find the group matching our groupBy
  const group = groups.find(g => g.group_by === groupBy)
  if (group?.widgets_data) {
    Object.entries(group.widgets_data).forEach(([widgetId, widgetConfig]) => {
      if (widgetConfig.plugin === 'hierarchical_nav_widget') {
        return
      }
      widgets.set(widgetId, {
        plugin: widgetConfig.plugin,
        params: widgetConfig.params || {}
      })
    })
  }

  return widgets
}

/**
 * Parse export.yml to extract widgets for a specific group
 * Returns both a map for quick lookup and an ordered array sorted by layout.order
 */
function parseExportWidgets(
  exportData: ExportConfig,
  groupBy: string
): { map: Map<string, ExportWidgetConfig>; order: string[] } {
  const widgetMap = new Map<string, ExportWidgetConfig>()
  const widgetsWithOrder: Array<{ dataSource: string; order: number }> = []

  if (!exportData?.exports) return { map: widgetMap, order: [] }

  // Find the web_pages export (or first export with groups)
  for (const exportConfig of exportData.exports) {
    const groups = exportConfig.groups || exportConfig.params?.groups
    if (!groups) continue

    const group = groups.find(g => g.group_by === groupBy)
    if (group?.widgets) {
      group.widgets.forEach((widget, arrayIndex) => {
        const widgetId = getExportWidgetId(groupBy, widget)
        if (!widgetId) return

        widgetMap.set(widgetId, widget)
        // Use layout.order if available, otherwise use array index
        const order = widget.layout?.order ?? arrayIndex
        widgetsWithOrder.push({ dataSource: widgetId, order })
      })
    }
  }

  // Sort by layout.order
  widgetsWithOrder.sort((a, b) => a.order - b.order)
  const order = widgetsWithOrder.map(w => w.dataSource)

  return { map: widgetMap, order }
}

/**
 * Map widget plugin to category
 */
function getWidgetCategory(plugin: string): string {
  const categoryMap: Record<string, string> = {
    bar_plot: 'chart',
    donut_chart: 'donut',
    radial_gauge: 'gauge',
    interactive_map: 'map',
    info_grid: 'info',
    hierarchical_nav_widget: 'navigation',
    stacked_area_plot: 'chart',
    concentric_rings: 'chart',
  }
  return categoryMap[plugin] || 'chart'
}

/**
 * Merge transform and export widget data
 * Preserves order from export.yml
 */
function mergeWidgetData(
  transformWidgets: Map<string, { plugin: string; params: Record<string, unknown> }>,
  exportWidgets: { map: Map<string, ExportWidgetConfig>; order: string[] }
): ConfiguredWidget[] {
  const merged: ConfiguredWidget[] = []
  const processedIds = new Set<string>()

  // First, add widgets in export.yml order (this preserves user's custom order)
  for (const widgetId of exportWidgets.order) {
    const transformConfig = transformWidgets.get(widgetId)
    const exportConfig = exportWidgets.map.get(widgetId)

    if (!exportConfig) continue

    if (!transformConfig && exportConfig.plugin === 'hierarchical_nav_widget') {
      processedIds.add(widgetId)
      merged.push({
        id: widgetId,
        transformerPlugin: exportConfig.plugin,
        widgetPlugin: exportConfig.plugin,
        title: exportConfig.title || 'Navigation',
        description: exportConfig.description,
        dataSource: exportConfig.data_source || '',
        transformerParams: {},
        widgetParams: exportConfig.params || {},
        category: getWidgetCategory(exportConfig.plugin),
        hasTransformConfig: false,
      })
      continue
    }

    if (!transformConfig) continue // Skip if not in transform.yml
    processedIds.add(widgetId)

    merged.push({
      id: widgetId,
      transformerPlugin: transformConfig.plugin,
      widgetPlugin: exportConfig?.plugin || 'bar_plot',
      title: exportConfig?.title || widgetId.replace(/_/g, ' '),
      description: exportConfig?.description,
      dataSource: widgetId,
      transformerParams: transformConfig.params,
      widgetParams: exportConfig?.params || {},
      category: exportConfig ? getWidgetCategory(exportConfig.plugin) : 'chart',
      hasTransformConfig: true,
    })
  }

  return merged
}

/** Fetch parallèle des deux configs */
async function fetchWidgetConfigs(): Promise<RawConfigs> {
  const [transformRes, exportRes] = await Promise.all([
    fetch(`${API_BASE}/transform`),
    fetch(`${API_BASE}/export`)
  ])

  if (!transformRes.ok) {
    throw new Error(`Failed to fetch transform config: ${transformRes.statusText}`)
  }
  if (!exportRes.ok) {
    throw new Error(`Failed to fetch export config: ${exportRes.statusText}`)
  }

  const transformJson = await transformRes.json()
  const exportJson = await exportRes.json()

  return {
    transformData: transformJson.content || transformJson,
    exportData: exportJson.content || exportJson
  }
}

/** Mutation : mise à jour d'un widget (transform + export) */
async function performUpdate(
  widgetId: string,
  config: Partial<ConfiguredWidget>,
  currentWidgets: ConfiguredWidget[],
  groupBy: string
): Promise<void> {
  const currentWidget = currentWidgets.find(w => w.id === widgetId)
  if (!currentWidget) throw new Error(`Widget ${widgetId} not found`)

  if (currentWidget.hasTransformConfig &&
      (config.transformerParams !== undefined || config.transformerPlugin !== undefined)) {

    const transformPayload = {
      plugin: config.transformerPlugin || currentWidget.transformerPlugin,
      params: config.transformerParams !== undefined
        ? config.transformerParams
        : currentWidget.transformerParams
    }

    const res = await fetch(
      `${API_BASE}/transform/${groupBy}/widgets/${widgetId}`,
      {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(transformPayload)
      }
    )
    if (!res.ok) {
      const errorData = await res.json().catch(() => ({}))
      throw new Error(errorData.detail || 'Failed to update transform config')
    }
  }

  if (config.widgetParams !== undefined || config.widgetPlugin !== undefined ||
      config.title !== undefined || config.description !== undefined) {
    const exportPayload = {
      plugin: config.widgetPlugin || currentWidget.widgetPlugin,
      data_source: currentWidget.widgetPlugin === 'hierarchical_nav_widget'
        ? ''
        : currentWidget.dataSource,
      title: config.title !== undefined ? config.title : currentWidget.title,
      description: config.description !== undefined ? config.description : currentWidget.description,
      params: config.widgetParams !== undefined
        ? config.widgetParams
        : currentWidget.widgetParams
    }

    const res = await fetch(
      `${API_BASE}/export/${groupBy}/widgets/${widgetId}`,
      {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(exportPayload)
      }
    )
    if (!res.ok) {
      const errorData = await res.json().catch(() => ({}))
      throw new Error(errorData.detail || 'Failed to update export config')
    }
  }
}

/** Mutation : suppression d'un widget (transform + export) */
async function performDelete(widgetId: string, groupBy: string): Promise<void> {
  const transformRes = await fetch(
    `${API_BASE}/transform/${groupBy}/widgets/${widgetId}`,
    { method: 'DELETE' }
  )
  if (!transformRes.ok && transformRes.status !== 404) {
    const errorData = await transformRes.json().catch(() => ({}))
    throw new Error(errorData.detail || 'Failed to delete from transform config')
  }

  const exportRes = await fetch(
    `${API_BASE}/export/${groupBy}/widgets/${widgetId}`,
    { method: 'DELETE' }
  )
  if (!exportRes.ok && exportRes.status !== 404) {
    const errorData = await exportRes.json().catch(() => ({}))
    throw new Error(errorData.detail || 'Failed to delete from export config')
  }
}

/** Mutation : duplication d'un widget */
async function performDuplicate(
  widgetId: string,
  newId: string,
  currentWidgets: ConfiguredWidget[],
  groupBy: string
): Promise<void> {
  const sourceWidget = currentWidgets.find(w => w.id === widgetId)
  if (!sourceWidget) throw new Error(`Widget ${widgetId} not found`)
  if (!sourceWidget.hasTransformConfig) {
    throw new Error(`Widget ${widgetId} cannot be duplicated`)
  }

  const transformRes = await fetch(
    `${API_BASE}/transform/${groupBy}/widgets/${newId}`,
    {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        plugin: sourceWidget.transformerPlugin,
        params: { ...sourceWidget.transformerParams }
      })
    }
  )
  if (!transformRes.ok) {
    const errorData = await transformRes.json().catch(() => ({}))
    throw new Error(errorData.detail || 'Failed to create transform config')
  }

  const exportRes = await fetch(
    `${API_BASE}/export/${groupBy}/widgets/${newId}`,
    {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        plugin: sourceWidget.widgetPlugin,
        data_source: newId,
        title: `${sourceWidget.title} (copie)`,
        description: sourceWidget.description,
        params: { ...sourceWidget.widgetParams }
      })
    }
  )
  if (!exportRes.ok) {
    const errorData = await exportRes.json().catch(() => ({}))
    throw new Error(errorData.detail || 'Failed to create export config')
  }
}

/** Mutation : réordonnancement des widgets */
async function performReorder(widgetIds: string[], groupBy: string): Promise<void> {
  const res = await fetch(`/api/recipes/${groupBy}/reorder`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ widget_ids: widgetIds })
  })
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}))
    throw new Error(errorData.detail || 'Failed to reorder widgets')
  }
}

/**
 * Hook pour la gestion des widgets configurés.
 * Utilise React Query pour le cache et la synchronisation.
 */
export function useWidgetConfig(groupBy: string, enabled: boolean = true): UseWidgetConfigReturn {
  const queryClient = useQueryClient()

  // Fetch parallèle des deux configs avec React Query
  const { data, isLoading, error } = useQuery({
    queryKey: ['widget-config'],
    queryFn: fetchWidgetConfigs,
    enabled,
    staleTime: 30_000,
  })

  // Dérivation client-side : fusionner transform + export pour le groupe courant
  const configuredWidgets = useMemo(() => {
    if (!data) return []
    const transformWidgets = parseTransformWidgets(data.transformData, groupBy)
    const exportWidgets = parseExportWidgets(data.exportData, groupBy)
    return mergeWidgetData(transformWidgets, exportWidgets)
  }, [data, groupBy])

  const invalidate = useCallback(
    () => queryClient.invalidateQueries({ queryKey: ['widget-config'] }),
    [queryClient]
  )

  const invalidateAll = useCallback(() => {
    invalidate()
    queryClient.invalidateQueries({ queryKey: ['layout'] })
  }, [invalidate, queryClient])

  // Mutations
  const updateMutation = useMutation({
    mutationFn: ({ widgetId, config }: { widgetId: string; config: Partial<ConfiguredWidget> }) =>
      performUpdate(widgetId, config, configuredWidgets, groupBy),
    onSuccess: invalidateAll,
  })

  const deleteMutation = useMutation({
    mutationFn: (widgetId: string) => performDelete(widgetId, groupBy),
    onSuccess: invalidateAll,
  })

  const duplicateMutation = useMutation({
    mutationFn: ({ widgetId, newId }: { widgetId: string; newId: string }) =>
      performDuplicate(widgetId, newId, configuredWidgets, groupBy),
    onSuccess: invalidateAll,
  })

  const reorderMutation = useMutation({
    mutationFn: (widgetIds: string[]) => performReorder(widgetIds, groupBy),
    onSuccess: invalidateAll,
  })

  // Wrappers conservant l'interface Promise<boolean>
  const updateWidget = useCallback(async (
    widgetId: string,
    config: Partial<ConfiguredWidget>
  ): Promise<boolean> => {
    try {
      await updateMutation.mutateAsync({ widgetId, config })
      return true
    } catch {
      return false
    }
  }, [updateMutation.mutateAsync])

  const deleteWidget = useCallback(async (widgetId: string): Promise<boolean> => {
    try {
      await deleteMutation.mutateAsync(widgetId)
      return true
    } catch {
      return false
    }
  }, [deleteMutation.mutateAsync])

  const duplicateWidget = useCallback(async (
    widgetId: string,
    newId: string
  ): Promise<boolean> => {
    try {
      await duplicateMutation.mutateAsync({ widgetId, newId })
      return true
    } catch {
      return false
    }
  }, [duplicateMutation.mutateAsync])

  const reorderWidgets = useCallback(async (widgetIds: string[]): Promise<boolean> => {
    try {
      await reorderMutation.mutateAsync(widgetIds)
      return true
    } catch {
      return false
    }
  }, [reorderMutation.mutateAsync])

  return {
    configuredWidgets,
    loading: isLoading,
    error: error?.message ?? null,
    updateWidget,
    deleteWidget,
    duplicateWidget,
    reorderWidgets,
    refetch: invalidateAll
  }
}
