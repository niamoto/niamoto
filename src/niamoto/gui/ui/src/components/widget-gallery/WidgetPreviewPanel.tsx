/**
 * WidgetPreviewPanel - Live widget preview using API
 * Renders actual widgets via iframe from the preview endpoint
 */
import { useState, useEffect, useCallback, useMemo } from 'react'
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
  AlertTriangle,
  FileCode,
  FileOutput,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import type { TemplateSuggestion, WidgetCategory } from './types'
import { CATEGORY_INFO, getPluginLabel, getPluginDescription } from './types'

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
  info: Info,
  map: Map,
  chart: BarChart3,
  gauge: Activity,
  donut: PieChart,
  table: Layers,
}

interface WidgetPreviewPanelProps {
  template: TemplateSuggestion | null
  className?: string
}

export function WidgetPreviewPanel({ template, className }: WidgetPreviewPanelProps) {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [refreshCounter, setRefreshCounter] = useState(0)

  // Build preview URL
  const previewUrl = template
    ? `/api/templates/preview/${template.template_id}`
    : null

  // Unique key for iframe: template_id + refresh counter
  // This ensures single load on template change, and reload on manual refresh
  const iframeKey = template ? `${template.template_id}-${refreshCounter}` : 'empty'

  // Handle iframe load
  const handleIframeLoad = useCallback(() => {
    setLoading(false)
    setError(null)
  }, [])

  // Handle iframe error
  const handleIframeError = useCallback(() => {
    setLoading(false)
    setError('Impossible de charger la preview')
  }, [])

  // Reload preview (manual refresh only)
  const handleRefresh = useCallback(() => {
    setLoading(true)
    setError(null)
    setRefreshCounter(prev => prev + 1)
  }, [])

  // Reset loading state when template changes
  useEffect(() => {
    if (template) {
      setLoading(true)
      setError(null)
    }
  }, [template?.template_id])

  // Extract transformer from template_id (format: column_transformer_widget)
  // Must be computed before early return for hooks consistency
  const knownTransformers = ['top_ranking', 'categorical_distribution', 'binned_distribution', 'statistical_summary', 'binary_counter', 'geospatial_extractor', 'field_aggregator', 'time_series_analysis', 'categories_extractor', 'class_object_series_extractor']

  const transformer = useMemo(() => {
    if (!template) return ''
    let result = template.plugin
    for (const t of knownTransformers) {
      if (template.template_id.includes(t)) {
        result = t
        break
      }
    }
    return result
  }, [template])

  const transformerLabel = template ? getPluginLabel(transformer, template.config) : ''
  const transformerDescription = transformer ? getPluginDescription(transformer) : ''

  // Generate realistic YAML previews for transform.yml and export.yml
  // Based on niamoto-nc reference format
  const yamlPreviews = useMemo(() => {
    if (!template) return { transform: '', export: '' }

    const column = template.matched_column || 'field'
    const config = template.config || {}
    const source = String(config.source || 'occurrences')

    // Generate short, descriptive widget name like niamoto-nc
    // e.g., "top_species", "distribution_dbh", "map_occurrences"
    let widgetName: string
    if (transformer === 'top_ranking') {
      widgetName = `top_${column}`
    } else if (transformer === 'categorical_distribution') {
      widgetName = `distribution_${column}`
    } else if (transformer === 'binned_distribution') {
      widgetName = `distribution_${column}`
    } else if (transformer === 'geospatial_extractor') {
      widgetName = `distribution_map`
    } else if (transformer === 'binary_counter') {
      widgetName = `distribution_${column}`
    } else {
      widgetName = `${column}_stats`
    }

    // Build transform.yml section (format: widgets_data in transform.yml)
    const transformConfig: Record<string, unknown> = {
      [widgetName]: {
        plugin: transformer,
        params: {},
      },
    }

    // Add transformer-specific params (matching niamoto-nc format)
    if (transformer === 'top_ranking') {
      (transformConfig[widgetName] as Record<string, unknown>).params = {
        source,
        field: column,
        count: config.count || 10,
      }
    } else if (transformer === 'categorical_distribution') {
      (transformConfig[widgetName] as Record<string, unknown>).params = {
        source,
        field: column,
      }
    } else if (transformer === 'binned_distribution') {
      (transformConfig[widgetName] as Record<string, unknown>).params = {
        source,
        field: column,
        bins: config.bins || 10,
      }
    } else if (transformer === 'statistical_summary') {
      (transformConfig[widgetName] as Record<string, unknown>).params = {
        source,
        field: column,
        stats: ['count', 'mean', 'min', 'max', 'std'],
      }
    } else if (transformer === 'binary_counter') {
      (transformConfig[widgetName] as Record<string, unknown>).params = {
        source,
        field: column,
        true_label: 'oui',
        false_label: 'non',
        include_percentages: true,
      }
    } else if (transformer === 'geospatial_extractor') {
      (transformConfig[widgetName] as Record<string, unknown>).params = {
        source,
        field: 'geo_pt',
        format: 'geojson',
      }
    } else {
      (transformConfig[widgetName] as Record<string, unknown>).params = {
        source,
        field: column,
      }
    }

    // Build export.yml section (format: list of widgets in export.yml groups)
    // Map category to actual widget plugin name
    const categoryToPlugin: Record<string, string> = {
      info: 'info_grid',
      map: 'interactive_map',
      chart: 'bar_plot',
      gauge: 'radial_gauge',
      donut: 'donut_chart',
      table: 'info_grid',
    }
    const widgetPlugin = categoryToPlugin[template.category] || template.category
    let exportWidget: Record<string, unknown> = {
      plugin: widgetPlugin,
      data_source: widgetName,
      title: template.name,
      params: {},
    }

    // Add widget-specific params (matching niamoto-nc format)
    if (widgetPlugin === 'bar_plot') {
      if (transformer === 'top_ranking') {
        exportWidget.params = {
          orientation: 'h',
          x_axis: 'counts',
          y_axis: 'tops',
          sort_order: 'ascending',
          auto_color: true,
        }
      } else if (transformer === 'categorical_distribution' || transformer === 'binned_distribution') {
        exportWidget.params = {
          orientation: 'v',
          x_axis: 'labels',
          y_axis: 'counts',
          gradient_color: '#10b981',
          gradient_mode: 'luminance',
        }
      }
    } else if (widgetPlugin === 'donut_chart') {
      exportWidget.params = {
        labels_field: 'labels',
        values_field: 'counts',
      }
    } else if (widgetPlugin === 'radial_gauge') {
      exportWidget.params = {
        value_field: 'percentage',
      }
    } else if (widgetPlugin === 'interactive_map') {
      exportWidget.params = {
        center: [-21.5, 165.5],
        zoom: 7,
      }
    } else if (widgetPlugin === 'info_grid') {
      exportWidget = {
        plugin: widgetPlugin,
        data_source: widgetName,
        title: template.name,
      }
    }

    return {
      transform: yaml.dump(transformConfig, { indent: 2, lineWidth: -1 }),
      export: yaml.dump([exportWidget], { indent: 2, lineWidth: -1 }),
    }
  }, [template, transformer])

  // Early return for empty state - AFTER all hooks
  if (!template) {
    return (
      <div className={cn('h-full flex flex-col', className)}>
        <div className="flex-1 flex flex-col items-center justify-center text-center p-8">
          <div className="w-20 h-20 rounded-2xl bg-muted/50 flex items-center justify-center mb-4">
            <Sparkles className="h-10 w-10 text-muted-foreground/50" />
          </div>
          <h3 className="text-lg font-medium text-muted-foreground">
            Selectionnez un template
          </h3>
          <p className="text-sm text-muted-foreground/70 mt-2 max-w-[240px]">
            Cliquez sur un widget pour visualiser son rendu
          </p>
        </div>
      </div>
    )
  }

  // These are safe now since template is guaranteed to exist
  const IconComponent = ICON_MAP[template.icon] || CATEGORY_ICONS[template.category] || Info
  const categoryInfo = CATEGORY_INFO[template.category] ?? { label: template.category, color: 'text-gray-600', bgColor: 'bg-gray-50' }

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
            <h3 className="font-semibold truncate">{template.name}</h3>
            <p className="text-sm text-muted-foreground line-clamp-2">
              {template.description}
            </p>
          </div>
          <Button
            variant="ghost"
            size="icon"
            className="h-8 w-8 flex-shrink-0"
            onClick={handleRefresh}
            disabled={loading}
          >
            <RefreshCw className={cn('h-4 w-4', loading && 'animate-spin')} />
          </Button>
        </div>

        {/* Badges - User-friendly descriptions */}
        <div className="flex flex-wrap gap-1.5 mt-3">
          {/* Main badge: What this template does */}
          <Badge
            variant="outline"
            className="text-xs border-emerald-300 bg-emerald-50 text-emerald-700 dark:border-emerald-800 dark:bg-emerald-950/50 dark:text-emerald-400"
          >
            {transformerLabel}
          </Badge>

          {/* Widget type */}
          <Badge variant="secondary" className="text-xs">
            {categoryInfo.label}
          </Badge>

          {/* Source: occurrences vs CSV */}
          {template.config?.source !== undefined && (
            <Badge variant="outline" className="text-xs">
              Source: {String(template.config.source)}
            </Badge>
          )}

          {/* CSV source indicator */}
          {template.source === 'class_object' && (
            <Badge variant="outline" className="text-xs border-blue-300 bg-blue-50 text-blue-700 dark:border-blue-800 dark:bg-blue-950/50 dark:text-blue-400">
              CSV pré-calculé
            </Badge>
          )}
        </div>

        {/* Transformer description */}
        {transformerDescription && (
          <p className="text-xs text-muted-foreground mt-2">
            {transformerDescription}
          </p>
        )}

        {template.match_reason && (
          <p className="text-xs text-muted-foreground mt-2">
            {template.match_reason}
            {template.matched_column && (
              <span className="font-mono ml-1 px-1 py-0.5 rounded bg-muted">
                {template.matched_column}
              </span>
            )}
          </p>
        )}
      </div>

      {/* Preview area with iframe */}
      <div className="flex-1 min-h-0 p-4 overflow-hidden">
        <div className="h-full rounded-xl border bg-card overflow-hidden relative">
          {loading && (
            <div className="absolute inset-0 flex items-center justify-center bg-background/80 z-10">
              <div className="flex flex-col items-center gap-2">
                <RefreshCw className="h-8 w-8 animate-spin text-muted-foreground" />
                <span className="text-sm text-muted-foreground">Chargement...</span>
              </div>
            </div>
          )}

          {error && (
            <div className="absolute inset-0 flex flex-col items-center justify-center bg-background z-10">
              <AlertTriangle className="h-10 w-10 text-amber-500 mb-2" />
              <span className="text-sm text-muted-foreground">{error}</span>
              <Button
                variant="outline"
                size="sm"
                className="mt-3"
                onClick={handleRefresh}
              >
                <RefreshCw className="h-4 w-4 mr-2" />
                Reessayer
              </Button>
            </div>
          )}

          {previewUrl && (
            <iframe
              key={iframeKey}
              src={previewUrl}
              className="w-full h-full border-0"
              onLoad={handleIframeLoad}
              onError={handleIframeError}
              title={`Preview: ${template.name}`}
            />
          )}
        </div>
      </div>

      {/* YAML Config preview */}
      <div className="shrink-0 p-4 border-t">
        <details className="group" open>
          <summary className="text-sm font-medium cursor-pointer list-none flex items-center justify-between">
            <span className="flex items-center gap-2">
              <FileCode className="h-4 w-4 text-muted-foreground" />
              Configuration YAML
            </span>
            <span className="text-xs text-muted-foreground group-open:hidden">Voir</span>
            <span className="text-xs text-muted-foreground hidden group-open:inline">Masquer</span>
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
                  <Badge variant="outline" className="text-[10px] bg-amber-500/10 text-amber-500 border-amber-500/30">
                    Transformation
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
                  <Badge variant="outline" className="text-[10px] bg-emerald-500/10 text-emerald-500 border-emerald-500/30">
                    Widget
                  </Badge>
                </div>
              </div>
            </TabsContent>
          </Tabs>
        </details>
      </div>
    </div>
  )
}
