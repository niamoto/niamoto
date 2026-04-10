/**
 * WidgetPreviewPanel - Live widget preview using API
 *
 * Supports two modes:
 * 1. Template preview mode (TemplateSuggestion) - for widget gallery
 * 2. Configured widget mode (ConfiguredWidget) - with edit capability
 *
 * Renders actual widgets via iframe from the preview endpoint
 */
import { useState, useEffect, useCallback, useMemo } from 'react'
import { useTranslation } from 'react-i18next'
import { useQueryClient } from '@tanstack/react-query'
import yaml from 'js-yaml'
import {
  Info,
  Map,
  BarChart3,
  Activity,
  PieChart,
  Layers,
  RefreshCw,
  Mountain,
  Leaf,
  Trophy,
  CloudRain,
  Thermometer,
  Box,
  ArrowUp,
  Maximize2,
  CircleDot,
  Sparkles,
  FileCode,
  FileOutput,
  FolderTree,
  Pencil,
  Eye,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import type { TemplateSuggestion, WidgetCategory } from './types'
import { CATEGORY_INFO, getPluginLabel, getPluginDescription } from './types'
import type { ConfiguredWidget } from './useWidgetConfig'
import { WidgetConfigForm } from './WidgetConfigForm'
import type { LocalizedString } from '@/components/ui/localized-input'
import { PreviewPane } from '@/components/preview'
import type { PreviewDescriptor } from '@/lib/preview/types'
import { invalidateAllPreviews } from '@/lib/preview/usePreviewFrame'

// Helper to resolve LocalizedString for display
function resolveLocalizedString(value: LocalizedString | undefined, defaultLang = 'fr'): string {
  if (!value) return ''
  if (typeof value === 'string') return value
  return value[defaultLang] || Object.values(value)[0] || ''
}

// Icon mapping
const ICON_MAP: Record<string, React.ElementType> = {
  Info,
  Map,
  BarChart3,
  Activity,
  PieChart,
  Mountain,
  Layers,
  Leaf,
  Trophy,
  CloudRain,
  Thermometer,
  Box,
  ArrowUp,
  Maximize2,
  CircleDot,
}

const CATEGORY_ICONS: Record<WidgetCategory, React.ElementType> = {
  navigation: FolderTree,
  info: Info,
  map: Map,
  chart: BarChart3,
  gauge: Activity,
  donut: PieChart,
  table: Layers,
}

// Known transformer plugins - used to extract transformer type from template_id
const KNOWN_TRANSFORMERS = [
  'top_ranking',
  'categorical_distribution',
  'binned_distribution',
  'statistical_summary',
  'binary_counter',
  'geospatial_extractor',
  'field_aggregator',
  'time_series_analysis',
  'categories_extractor',
  'class_object_series_extractor',
] as const

interface WidgetPreviewPanelProps {
  // Template mode (for widget gallery)
  template?: TemplateSuggestion | null
  // Configured widget mode (for editing)
  configuredWidget?: ConfiguredWidget | null
  groupBy?: string  // Reference name for correct data filtering
  availableFields?: string[]  // For field-select widgets
  onUpdateWidget?: (widgetId: string, config: Partial<ConfiguredWidget>) => Promise<boolean>
  className?: string
}

export function WidgetPreviewPanel({
  template,
  configuredWidget,
  groupBy,
  availableFields = [],
  onUpdateWidget,
  className,
}: WidgetPreviewPanelProps) {
  const { t } = useTranslation('widgets')
  const queryClient = useQueryClient()
  const [editMode, setEditMode] = useState(false)

  // Determine which mode we're in
  const isConfiguredMode = !!configuredWidget && !template
  const activeWidget = configuredWidget
  const activeTemplate = template
  const activeItemKey = activeTemplate?.template_id ?? activeWidget?.id ?? null

  // Build PreviewDescriptor
  const previewDescriptor: PreviewDescriptor | null = useMemo(() => {
    if (isConfiguredMode && activeWidget) {
      return {
        templateId: activeWidget.dataSource || activeWidget.id,
        groupBy,
        mode: 'full' as const,
      }
    }
    if (activeTemplate) {
      return {
        templateId: activeTemplate.template_id,
        groupBy,
        mode: 'full' as const,
      }
    }
    return null
  }, [isConfiguredMode, activeWidget, activeTemplate, groupBy])

  // Reload preview (manual refresh only)
  const handleRefresh = useCallback(() => {
    invalidateAllPreviews(queryClient)
  }, [queryClient])

  // Reset edit mode when switching items
  useEffect(() => {
    if (activeItemKey) {
      const frameId = window.requestAnimationFrame(() => {
        setEditMode(false)
      })
      return () => window.cancelAnimationFrame(frameId)
    }
  }, [activeItemKey])

  // Extract transformer from template_id (format: column_transformer_widget)
  const transformer = useMemo(() => {
    // For configured widgets, use the transformer plugin directly
    if (isConfiguredMode && activeWidget) {
      return activeWidget.transformerPlugin
    }

    // For templates, extract from template_id
    if (!activeTemplate) return ''
    let result = activeTemplate.plugin
    for (const t of KNOWN_TRANSFORMERS) {
      if (activeTemplate.template_id.includes(t)) {
        result = t
        break
      }
    }
    return result
  }, [isConfiguredMode, activeWidget, activeTemplate])

  const transformerLabel = activeTemplate ? getPluginLabel(transformer, activeTemplate.config) : transformer
  const transformerDescription = transformer ? getPluginDescription(transformer) : ''

  // Handle save from edit form
  const handleSave = useCallback(async (config: Partial<ConfiguredWidget>): Promise<boolean> => {
    if (!activeWidget || !onUpdateWidget) return false
    const success = await onUpdateWidget(activeWidget.id, config)
    if (success) {
      invalidateAllPreviews(queryClient)
      setEditMode(false)
    }
    return success
  }, [activeWidget, onUpdateWidget, queryClient])

  // Handle cancel edit
  const handleCancelEdit = useCallback(() => {
    setEditMode(false)
  }, [])

  // Generate realistic YAML previews for transform.yml and export.yml
  // Based on niamoto-nc reference format
  const yamlPreviews = useMemo(() => {
    // For configured widgets, show actual config
    if (isConfiguredMode && activeWidget) {
      const transformConfig: Record<string, unknown> = {
        [activeWidget.id]: {
          plugin: activeWidget.transformerPlugin,
          params: activeWidget.transformerParams,
        },
      }

      const exportWidget: Record<string, unknown> = {
        plugin: activeWidget.widgetPlugin,
        data_source: activeWidget.dataSource,
        title: activeWidget.title,
        layout: {
          colspan: 1,
          order: 0,
        },
        ...(activeWidget.description && { description: activeWidget.description }),
        ...(Object.keys(activeWidget.widgetParams).length > 0 && { params: activeWidget.widgetParams }),
      }

      return {
        transform: yaml.dump(transformConfig, { indent: 2, lineWidth: -1 }),
        export: yaml.dump([exportWidget], { indent: 2, lineWidth: -1 }),
      }
    }

    // For templates, use the config from the backend suggestion
    if (!activeTemplate) return { transform: '', export: '' }

    // Use template_id as widget name (this is what gets saved)
    const widgetName = activeTemplate.template_id

    // Build transform.yml section using the config from the backend
    // The backend provides the correct transformer params in activeTemplate.config
    const transformConfig: Record<string, unknown> = {
      [widgetName]: {
        plugin: transformer,
        params: activeTemplate.config || {},
      },
    }

    // Build export.yml section
    // Map category to actual widget plugin name
    const categoryToPlugin: Record<string, string> = {
      info: 'info_grid',
      map: 'interactive_map',
      chart: 'bar_plot',
      gauge: 'radial_gauge',
      donut: 'donut_chart',
      table: 'info_grid',
      navigation: 'hierarchical_nav_widget',
    }
    const widgetPlugin = categoryToPlugin[activeTemplate.category] || activeTemplate.category

    // Generate export widget params matching backend's _generate_widget_params
    let exportParams: Record<string, unknown> = {}

    if (widgetPlugin === 'bar_plot') {
      if (transformer === 'top_ranking') {
        exportParams = {
          orientation: 'h',
          x_axis: 'counts',
          y_axis: 'tops',
          sort_order: 'ascending',
          auto_color: true,
        }
      } else if (transformer === 'categorical_distribution' || transformer === 'binned_distribution') {
        exportParams = {
          orientation: 'v',
          x_axis: 'labels',
          y_axis: 'counts',
          gradient_color: '#10b981',
          gradient_mode: 'luminance',
          show_legend: false,
        }
        if (transformer === 'binned_distribution') {
          exportParams.transform = 'bins_to_df'
          exportParams.transform_params = {
            bin_field: 'bins',
            count_field: 'counts',
            use_percentages: true,
            percentage_field: 'percentages',
            x_field: 'bin',
            y_field: 'count',
          }
        }
      }
    } else if (widgetPlugin === 'donut_chart') {
      exportParams = {
        labels_field: 'labels',
        values_field: 'counts',
        show_legend: false,
      }
    } else if (widgetPlugin === 'radial_gauge') {
      if (transformer === 'statistical_summary') {
        // Use new stat_to_display params for statistical_summary
        exportParams = {
          stat_to_display: 'mean',
          show_range: true,
          auto_range: true,
        }
      } else {
        exportParams = {
          auto_range: true,
        }
      }
    } else if (widgetPlugin === 'interactive_map') {
      exportParams = {
        map_style: 'carto-voyager',
        zoom: 7,
        layers: [{
          id: 'occurrences',
          source: 'coordinates',
          type: 'circle_markers',
          style: {
            color: '#1fb99d',
            weight: 1,
            fillColor: '#00716b',
            fillOpacity: 0.5,
            radius: 8,
          },
        }],
      }
    }

    const exportWidget: Record<string, unknown> = {
      plugin: widgetPlugin,
      data_source: widgetName,
      title: activeTemplate.name,
      layout: {
        colspan: 1,
        order: 0,  // Will be set based on position when saved
      },
      ...(Object.keys(exportParams).length > 0 && { params: exportParams }),
    }

    return {
      transform: yaml.dump(transformConfig, { indent: 2, lineWidth: -1 }),
      export: yaml.dump([exportWidget], { indent: 2, lineWidth: -1 }),
    }
  }, [isConfiguredMode, activeWidget, activeTemplate, transformer])

  // Early return for empty state - AFTER all hooks
  if (!activeTemplate && !activeWidget) {
    return (
      <div className={cn('h-full flex flex-col', className)}>
        <div className="flex-1 flex flex-col items-center justify-center text-center p-8">
          <div className="w-20 h-20 rounded-2xl bg-muted/50 flex items-center justify-center mb-4">
            <Sparkles className="h-10 w-10 text-muted-foreground/50" />
          </div>
          <h3 className="text-lg font-medium text-muted-foreground">
            {t('preview.selectWidget')}
          </h3>
          <p className="text-sm text-muted-foreground/70 mt-2 max-w-[240px]">
            {t('preview.selectWidgetHint')}
          </p>
        </div>
      </div>
    )
  }

  // Determine display info based on mode
  const displayInfo = isConfiguredMode && activeWidget
    ? {
        name: resolveLocalizedString(activeWidget.title),
        description: resolveLocalizedString(activeWidget.description) || `Widget ${activeWidget.id}`,
        category: (activeWidget.category || 'chart') as WidgetCategory,
        icon: 'BarChart3',
      }
    : activeTemplate
    ? {
        name: activeTemplate.name,
        description: activeTemplate.description,
        category: activeTemplate.category,
        icon: activeTemplate.icon,
      }
    : null

  if (!displayInfo) return null

  const IconComponent = ICON_MAP[displayInfo.icon] || CATEGORY_ICONS[displayInfo.category] || Info
  const categoryInfo = CATEGORY_INFO[displayInfo.category] ?? { label: displayInfo.category, color: 'text-gray-600', bgColor: 'bg-gray-50' }

  return (
    <div className={cn('h-full flex flex-col', className)}>
      {/* Header */}
      <div className="shrink-0 p-4 border-b">
        <div className="flex items-start gap-3">
          <div className={cn(
            'h-12 w-12 rounded-xl flex items-center justify-center flex-shrink-0',
            categoryInfo.bgColor
          )}>
            <IconComponent className={cn('h-6 w-6', categoryInfo.color)} />
          </div>
          <div className="flex-1 min-w-0">
            <h3 className="font-semibold truncate">{displayInfo.name}</h3>
            <p className="text-sm text-muted-foreground line-clamp-2">
              {displayInfo.description}
            </p>
          </div>

          {/* Action buttons */}
          <div className="flex items-center gap-1 flex-shrink-0">
            {/* Edit/Preview toggle for configured widgets */}
            {isConfiguredMode && onUpdateWidget && (
              <Button
                variant={editMode ? 'default' : 'outline'}
                size="sm"
                className="h-8"
                onClick={() => setEditMode(!editMode)}
              >
                {editMode ? (
                  <>
                    <Eye className="h-4 w-4 mr-1" />
                    Preview
                  </>
                ) : (
                  <>
                    <Pencil className="h-4 w-4 mr-1" />
                    {t('preview.edit')}
                  </>
                )}
              </Button>
            )}
            <Button
              variant="ghost"
              size="icon"
              className="h-8 w-8"
              onClick={handleRefresh}
            >
              <RefreshCw className="h-4 w-4" />
            </Button>
          </div>
        </div>

        {/* Badges - User-friendly descriptions */}
        <div className="flex flex-wrap gap-1.5 mt-3">
          {/* Main badge: What this template does */}
          <Badge
            variant="outline"
            className="text-xs border-success/50 bg-success/10 text-success"
          >
            {transformerLabel}
          </Badge>

          {/* Widget type */}
          <Badge variant="secondary" className="text-xs">
            {categoryInfo.label}
          </Badge>

          {/* Source: occurrences vs CSV (only for templates) */}
          {activeTemplate?.config?.source !== undefined && (
            <Badge variant="outline" className="text-xs">
              Source: {String(activeTemplate.config.source)}
            </Badge>
          )}

          {/* CSV source indicator (only for templates) */}
          {activeTemplate?.source === 'class_object' && (
            <Badge variant="outline" className="text-xs border-data-source-secondary/50 bg-data-source-secondary/10 text-data-source-secondary">
              {t('preview.precomputedCsv')}
            </Badge>
          )}

          {/* Configured widget indicator */}
          {isConfiguredMode && (
            <Badge variant="outline" className="text-xs border-primary/50 bg-primary/10 text-primary">
              {t('preview.configured')}
            </Badge>
          )}
        </div>

        {/* Transformer description */}
        {transformerDescription && !editMode && (
          <p className="text-xs text-muted-foreground mt-2">
            {transformerDescription}
          </p>
        )}

        {activeTemplate?.match_reason && !editMode && (
          <p className="text-xs text-muted-foreground mt-2">
            {activeTemplate.match_reason}
            {activeTemplate.matched_column && (
              <span className="font-mono ml-1 px-1 py-0.5 rounded bg-muted">
                {activeTemplate.matched_column}
              </span>
            )}
          </p>
        )}
      </div>

      {/* Main content area - Edit form or Preview */}
      {editMode && activeWidget ? (
        /* Edit form for configured widgets */
        <div className="flex-1 min-h-0 overflow-auto">
          <WidgetConfigForm
            widget={activeWidget}
            groupBy={groupBy || ''}
            availableFields={availableFields}
            onSave={handleSave}
            onCancel={handleCancelEdit}
          />
        </div>
      ) : (
        /* Preview area */
        <div className="flex-1 min-h-0 p-4 overflow-hidden">
          <div className="h-full rounded-xl border bg-card overflow-hidden">
            {previewDescriptor && (
              <PreviewPane descriptor={previewDescriptor} className="w-full h-full" />
            )}
          </div>
        </div>
      )}

      {/* YAML Config preview - hidden in edit mode */}
      {!editMode && (
      <div className="shrink-0 p-4 border-t">
        <details className="group" open>
          <summary className="text-sm font-medium cursor-pointer list-none flex items-center justify-between">
            <span className="flex items-center gap-2">
              <FileCode className="h-4 w-4 text-muted-foreground" />
              {t('preview.yamlConfig')}
            </span>
            <span className="text-xs text-muted-foreground group-open:hidden">{t('preview.show')}</span>
            <span className="text-xs text-muted-foreground hidden group-open:inline">{t('preview.hide')}</span>
          </summary>

          <Tabs defaultValue="transform" className="mt-3">
            <TabsList className="grid w-full grid-cols-2 h-8">
              <TabsTrigger value="transform" className="text-xs gap-1">
                <FileCode className="h-3 w-3" />
                transform.yml
              </TabsTrigger>
              <TabsTrigger value="export" className="text-xs gap-1">
                <FileOutput className="h-3 w-3" />
                export.yml
              </TabsTrigger>
            </TabsList>

            <TabsContent value="transform" className="mt-2">
              <div className="relative">
                <pre className="p-3 rounded-lg bg-slate-950 text-slate-50 text-xs overflow-auto max-h-36 font-mono">
                  <code>{yamlPreviews.transform}</code>
                </pre>
                <div className="absolute top-1 right-1">
                  <Badge variant="outline" className="text-[10px] bg-warning/10 text-warning border-warning/30">
                    {t('preview.transformation')}
                  </Badge>
                </div>
              </div>
            </TabsContent>

            <TabsContent value="export" className="mt-2">
              <div className="relative">
                <pre className="p-3 rounded-lg bg-slate-950 text-slate-50 text-xs overflow-auto max-h-36 font-mono">
                  <code>{yamlPreviews.export}</code>
                </pre>
                <div className="absolute top-1 right-1">
                  <Badge variant="outline" className="text-[10px] bg-success/10 text-success border-success/30">
                    {t('preview.widget')}
                  </Badge>
                </div>
              </div>
            </TabsContent>
          </Tabs>
        </details>
      </div>
      )}
    </div>
  )
}
