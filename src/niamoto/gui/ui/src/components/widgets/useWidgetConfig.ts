/**
 * Hook for managing configured widgets in transform.yml and export.yml
 *
 * Provides CRUD operations for widgets:
 * - Fetch all configured widgets for a group
 * - Update widget parameters (transform + export)
 * - Delete widgets
 * - Duplicate widgets
 */
import { useState, useEffect, useCallback, useMemo } from 'react'

const API_BASE = '/api/config'

/**
 * Represents a configured widget with both transform and export params
 */
export interface ConfiguredWidget {
  id: string                           // Widget name in transform.yml (e.g., "dbh_distribution")
  transformerPlugin: string            // Transformer plugin name (e.g., "binned_distribution")
  widgetPlugin: string                 // Widget plugin name (e.g., "bar_plot")
  title: string                        // Display title from export config
  description?: string                 // Optional description
  dataSource: string                   // Data source key (usually same as id)
  transformerParams: Record<string, unknown>  // Params from transform.yml
  widgetParams: Record<string, unknown>       // Params from export.yml
  category?: string                    // Widget category (chart, gauge, etc.)
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
  title?: string
  description?: string
  params?: Record<string, unknown>
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
  refetch: () => void
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
 */
function parseExportWidgets(
  exportData: ExportConfig,
  groupBy: string
): Map<string, ExportWidgetConfig> {
  const widgets = new Map<string, ExportWidgetConfig>()

  if (!exportData?.exports) return widgets

  // Find the web_pages export (or first export with groups)
  for (const exportConfig of exportData.exports) {
    const groups = exportConfig.groups || exportConfig.params?.groups
    if (!groups) continue

    const group = groups.find(g => g.group_by === groupBy)
    if (group?.widgets) {
      group.widgets.forEach(widget => {
        if (widget.data_source) {
          widgets.set(widget.data_source, widget)
        }
      })
    }
  }

  return widgets
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
 */
function mergeWidgetData(
  transformWidgets: Map<string, { plugin: string; params: Record<string, unknown> }>,
  exportWidgets: Map<string, ExportWidgetConfig>
): ConfiguredWidget[] {
  const merged: ConfiguredWidget[] = []

  // Start from transform widgets (they define the data source)
  transformWidgets.forEach((transformConfig, widgetId) => {
    const exportConfig = exportWidgets.get(widgetId)

    merged.push({
      id: widgetId,
      transformerPlugin: transformConfig.plugin,
      widgetPlugin: exportConfig?.plugin || 'bar_plot', // Default widget
      title: exportConfig?.title || widgetId.replace(/_/g, ' '),
      description: exportConfig?.description,
      dataSource: widgetId,
      transformerParams: transformConfig.params,
      widgetParams: exportConfig?.params || {},
      category: exportConfig ? getWidgetCategory(exportConfig.plugin) : 'chart'
    })
  })

  return merged
}

/**
 * Hook for managing configured widgets
 */
export function useWidgetConfig(groupBy: string): UseWidgetConfigReturn {
  const [transformData, setTransformData] = useState<TransformConfig[] | null>(null)
  const [exportData, setExportData] = useState<ExportConfig | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Fetch both configs
  const fetchConfigs = useCallback(async () => {
    setLoading(true)
    setError(null)

    try {
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

      // Extract content from response (API returns { content: {...} })
      setTransformData(transformJson.content || transformJson)
      setExportData(exportJson.content || exportJson)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchConfigs()
  }, [fetchConfigs, groupBy])

  // Compute configured widgets from both configs
  const configuredWidgets = useMemo(() => {
    if (!transformData) return []

    const transformWidgets = parseTransformWidgets(transformData, groupBy)
    const exportWidgets = exportData ? parseExportWidgets(exportData, groupBy) : new Map()

    return mergeWidgetData(transformWidgets, exportWidgets)
  }, [transformData, exportData, groupBy])

  // Update a widget's configuration
  const updateWidget = useCallback(async (
    widgetId: string,
    config: Partial<ConfiguredWidget>
  ): Promise<boolean> => {
    try {
      // Build updated transform config
      if (config.transformerParams !== undefined || config.transformerPlugin !== undefined) {
        const currentWidget = configuredWidgets.find(w => w.id === widgetId)
        if (!currentWidget) {
          throw new Error(`Widget ${widgetId} not found`)
        }

        // Update transform.yml via dedicated endpoint
        const transformPayload = {
          plugin: config.transformerPlugin || currentWidget.transformerPlugin,
          params: config.transformerParams !== undefined
            ? config.transformerParams
            : currentWidget.transformerParams
        }

        const transformRes = await fetch(
          `${API_BASE}/transform/${groupBy}/widgets/${widgetId}`,
          {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(transformPayload)
          }
        )

        if (!transformRes.ok) {
          const errorData = await transformRes.json().catch(() => ({}))
          throw new Error(errorData.detail || `Failed to update transform config`)
        }
      }

      // Update export.yml if export params changed
      if (config.widgetParams !== undefined || config.widgetPlugin !== undefined ||
          config.title !== undefined || config.description !== undefined) {
        const currentWidget = configuredWidgets.find(w => w.id === widgetId)
        if (!currentWidget) {
          throw new Error(`Widget ${widgetId} not found`)
        }

        const exportPayload = {
          plugin: config.widgetPlugin || currentWidget.widgetPlugin,
          data_source: widgetId,
          title: config.title !== undefined ? config.title : currentWidget.title,
          description: config.description !== undefined ? config.description : currentWidget.description,
          params: config.widgetParams !== undefined
            ? config.widgetParams
            : currentWidget.widgetParams
        }

        const exportRes = await fetch(
          `${API_BASE}/export/${groupBy}/widgets/${widgetId}`,
          {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(exportPayload)
          }
        )

        if (!exportRes.ok) {
          const errorData = await exportRes.json().catch(() => ({}))
          throw new Error(errorData.detail || `Failed to update export config`)
        }
      }

      // Refetch to sync state
      await fetchConfigs()
      return true
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error')
      return false
    }
  }, [configuredWidgets, groupBy, fetchConfigs])

  // Delete a widget from both configs
  const deleteWidget = useCallback(async (widgetId: string): Promise<boolean> => {
    try {
      // Delete from transform.yml
      const transformRes = await fetch(
        `${API_BASE}/transform/${groupBy}/widgets/${widgetId}`,
        { method: 'DELETE' }
      )

      if (!transformRes.ok && transformRes.status !== 404) {
        const errorData = await transformRes.json().catch(() => ({}))
        throw new Error(errorData.detail || `Failed to delete from transform config`)
      }

      // Delete from export.yml
      const exportRes = await fetch(
        `${API_BASE}/export/${groupBy}/widgets/${widgetId}`,
        { method: 'DELETE' }
      )

      if (!exportRes.ok && exportRes.status !== 404) {
        const errorData = await exportRes.json().catch(() => ({}))
        throw new Error(errorData.detail || `Failed to delete from export config`)
      }

      // Refetch to sync state
      await fetchConfigs()
      return true
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error')
      return false
    }
  }, [groupBy, fetchConfigs])

  // Duplicate a widget with a new ID
  const duplicateWidget = useCallback(async (
    widgetId: string,
    newId: string
  ): Promise<boolean> => {
    const sourceWidget = configuredWidgets.find(w => w.id === widgetId)
    if (!sourceWidget) {
      setError(`Widget ${widgetId} not found`)
      return false
    }

    try {
      // Create new widget in transform.yml
      const transformPayload = {
        plugin: sourceWidget.transformerPlugin,
        params: { ...sourceWidget.transformerParams }
      }

      const transformRes = await fetch(
        `${API_BASE}/transform/${groupBy}/widgets/${newId}`,
        {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(transformPayload)
        }
      )

      if (!transformRes.ok) {
        const errorData = await transformRes.json().catch(() => ({}))
        throw new Error(errorData.detail || `Failed to create transform config`)
      }

      // Create new widget in export.yml
      const exportPayload = {
        plugin: sourceWidget.widgetPlugin,
        data_source: newId,
        title: `${sourceWidget.title} (copie)`,
        description: sourceWidget.description,
        params: { ...sourceWidget.widgetParams }
      }

      const exportRes = await fetch(
        `${API_BASE}/export/${groupBy}/widgets/${newId}`,
        {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(exportPayload)
        }
      )

      if (!exportRes.ok) {
        const errorData = await exportRes.json().catch(() => ({}))
        throw new Error(errorData.detail || `Failed to create export config`)
      }

      // Refetch to sync state
      await fetchConfigs()
      return true
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error')
      return false
    }
  }, [configuredWidgets, groupBy, fetchConfigs])

  return {
    configuredWidgets,
    loading,
    error,
    updateWidget,
    deleteWidget,
    duplicateWidget,
    refetch: fetchConfigs
  }
}
