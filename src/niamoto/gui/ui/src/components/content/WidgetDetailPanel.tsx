/**
 * WidgetDetailPanel - Detailed view of a selected widget
 *
 * Shows when a widget is selected in the content tab.
 * Provides:
 * - Header with back button, title, and actions
 * - Three tabs: Preview / Parameters / YAML
 * - Edit and delete capabilities
 */
import { useState, useCallback, useMemo } from 'react'
import { useTranslation } from 'react-i18next'
import { useQueryClient } from '@tanstack/react-query'
import yaml from 'js-yaml'
import {
  AlertTriangle,
  ArrowLeft,
  Info,
  Map,
  BarChart3,
  Activity,
  PieChart,
  Layers,
  FolderTree,
  RefreshCw,
  Trash2,
  FileCode,
  Settings,
  Loader2,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { ScrollArea } from '@/components/ui/scroll-area'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog'
import type { ConfiguredWidget } from '@/components/widgets'
import { WidgetConfigForm } from '@/components/widgets/WidgetConfigForm'
import type { LocalizedString } from '@/components/ui/localized-input'
import { PreviewPane, injectPreviewOverrides } from '@/components/preview'
import type { PreviewDescriptor } from '@/lib/preview/types'
import { invalidateAllPreviews } from '@/lib/preview/usePreviewFrame'
import { recordCollectionsPerf } from '@/features/collections/performance/collectionsPerf'

// La preview individuelle a besoin d'un rendu responsive, mais pas d'occuper
// toute la hauteur du panneau : on garde donc l'override Plotly, puis on borne
// la taille du conteneur côté layout.
function injectFullPreviewOverrides(html: string): string {
  return injectPreviewOverrides(html, { fullSize: true, allowScroll: true })
}

// Category icons
const CATEGORY_ICONS: Record<string, React.ElementType> = {
  navigation: FolderTree,
  info: Info,
  map: Map,
  chart: BarChart3,
  gauge: Activity,
  donut: PieChart,
  table: Layers,
}

// Category colors
const CATEGORY_COLORS: Record<string, { text: string; bg: string; border: string }> = {
  navigation: { text: 'text-violet-600', bg: 'bg-violet-50', border: 'border-violet-200' },
  info: { text: 'text-blue-600', bg: 'bg-blue-50', border: 'border-blue-200' },
  map: { text: 'text-emerald-600', bg: 'bg-emerald-50', border: 'border-emerald-200' },
  chart: { text: 'text-amber-600', bg: 'bg-amber-50', border: 'border-amber-200' },
  gauge: { text: 'text-teal-600', bg: 'bg-teal-50', border: 'border-teal-200' },
  donut: { text: 'text-orange-600', bg: 'bg-orange-50', border: 'border-orange-200' },
  table: { text: 'text-slate-600', bg: 'bg-slate-50', border: 'border-slate-200' },
}

// Helper to resolve LocalizedString for display
function resolveLocalizedString(value: LocalizedString | undefined, defaultLang = 'fr'): string {
  if (!value) return ''
  if (typeof value === 'string') return value
  return value[defaultLang] || Object.values(value)[0] || ''
}

interface WidgetDetailPanelProps {
  widget: ConfiguredWidget
  groupBy: string
  availableFields?: string[]
  autoRefreshPreview?: boolean
  onBack: () => void
  onUpdate: (config: Partial<ConfiguredWidget>) => Promise<boolean>
  onDelete: () => Promise<boolean>
}

export function WidgetDetailPanel({
  widget,
  groupBy,
  availableFields = [],
  autoRefreshPreview = true,
  onBack,
  onUpdate,
  onDelete,
}: WidgetDetailPanelProps) {
  const { t } = useTranslation(['widgets', 'common'])
  const queryClient = useQueryClient()
  const [panelState, setPanelState] = useState<{
    widgetId: string
    activeTab: 'params' | 'yaml'
    previewDraft: Partial<ConfiguredWidget> | null
    appliedPreviewDraft: Partial<ConfiguredWidget> | null
    formInstanceKey: number
  }>(() => ({
    widgetId: widget.id,
    activeTab: 'params',
    previewDraft: null,
    appliedPreviewDraft: null,
    formInstanceKey: 0,
  }))
  const [isDeleting, setIsDeleting] = useState(false)
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false)
  const activeTab = panelState.widgetId === widget.id ? panelState.activeTab : 'params'
  const previewDraft = panelState.widgetId === widget.id ? panelState.previewDraft : null
  const appliedPreviewDraft =
    panelState.widgetId === widget.id ? panelState.appliedPreviewDraft : null
  const formInstanceKey = panelState.widgetId === widget.id ? panelState.formInstanceKey : 0

  const updatePanelState = useCallback(
    (
      updater:
        | {
            activeTab: 'params' | 'yaml'
            previewDraft: Partial<ConfiguredWidget> | null
            appliedPreviewDraft: Partial<ConfiguredWidget> | null
            formInstanceKey: number
          }
        | ((prev: {
            activeTab: 'params' | 'yaml'
            previewDraft: Partial<ConfiguredWidget> | null
            appliedPreviewDraft: Partial<ConfiguredWidget> | null
            formInstanceKey: number
          }) => {
            activeTab: 'params' | 'yaml'
            previewDraft: Partial<ConfiguredWidget> | null
            appliedPreviewDraft: Partial<ConfiguredWidget> | null
            formInstanceKey: number
          }),
    ) => {
      setPanelState((prev) => {
        const base =
          prev.widgetId === widget.id
            ? prev
            : {
                widgetId: widget.id,
                activeTab: 'params' as const,
                previewDraft: null,
                appliedPreviewDraft: null,
                formInstanceKey: 0,
              }

        const next =
          typeof updater === 'function'
            ? updater({
                activeTab: base.activeTab,
                previewDraft: base.previewDraft,
                appliedPreviewDraft: base.appliedPreviewDraft,
                formInstanceKey: base.formInstanceKey,
              })
            : updater

        return {
          widgetId: widget.id,
          activeTab: next.activeTab,
          previewDraft: next.previewDraft,
          appliedPreviewDraft: next.appliedPreviewDraft,
          formInstanceKey: next.formInstanceKey,
        }
      })
    },
    [widget.id]
  )

  // Category info
  const category = widget.category || 'chart'
  const Icon = CATEGORY_ICONS[category] || BarChart3
  const colors = CATEGORY_COLORS[category] || CATEGORY_COLORS.chart

  const previewSourceDraft = useMemo(
    () => (autoRefreshPreview ? previewDraft : appliedPreviewDraft),
    [appliedPreviewDraft, autoRefreshPreview, previewDraft],
  )

  const previewTitle = useMemo(
    () => resolveLocalizedString(
      (previewSourceDraft?.title as LocalizedString | undefined) ?? widget.title,
    ),
    [previewSourceDraft?.title, widget.title],
  )

  // Build PreviewDescriptor
  const previewDescriptor: PreviewDescriptor = useMemo(() => {
    if (!widget.hasTransformConfig || widget.widgetPlugin === 'hierarchical_nav_widget') {
      return {
        templateId: widget.id,
        groupBy,
        mode: 'full' as const,
      }
    }

    return {
      groupBy,
      mode: 'full' as const,
      inline: {
        transformer_plugin: widget.transformerPlugin,
        transformer_params:
          (previewSourceDraft?.transformerParams as Record<string, unknown> | undefined) ??
          widget.transformerParams,
        widget_plugin: widget.widgetPlugin,
        widget_params:
          (previewSourceDraft?.widgetParams as Record<string, unknown> | undefined) ??
          widget.widgetParams,
        widget_title: previewTitle || widget.id,
      },
    }
  }, [
    groupBy,
    previewSourceDraft?.transformerParams,
    previewSourceDraft?.widgetParams,
    previewTitle,
    widget.hasTransformConfig,
    widget.id,
    widget.transformerPlugin,
    widget.transformerParams,
    widget.widgetParams,
    widget.widgetPlugin,
  ])

  // Generate YAML previews
  const yamlPreviews = useMemo(() => {
    const transformConfig: Record<string, unknown> | null = widget.hasTransformConfig
      ? {
          [widget.id]: {
            plugin: widget.transformerPlugin,
            params: widget.transformerParams,
          },
        }
      : null

    const exportWidget: Record<string, unknown> = {
      plugin: widget.widgetPlugin,
      data_source: widget.dataSource,
      title: widget.title,
      layout: {
        colspan: 1,
        order: 0,
      },
      ...(widget.description && { description: widget.description }),
      ...(Object.keys(widget.widgetParams).length > 0 && { params: widget.widgetParams }),
    }

    return {
      transform: transformConfig
        ? yaml.dump(transformConfig, { indent: 2, lineWidth: -1 })
        : '# No transform.yml entry for this export-only widget\n',
      export: yaml.dump([exportWidget], { indent: 2, lineWidth: -1 }),
    }
  }, [widget])

  const handleRefresh = useCallback(() => {
    updatePanelState((prev) => ({
      ...prev,
      appliedPreviewDraft: prev.previewDraft,
    }))
    invalidateAllPreviews(queryClient)
    recordCollectionsPerf('collections.detail.preview.refresh', {
      autoRefreshPreview,
      groupBy,
      widgetId: widget.id,
    })
  }, [autoRefreshPreview, groupBy, queryClient, updatePanelState, widget.id])

  const handleSave = useCallback(async (config: Partial<ConfiguredWidget>): Promise<boolean> => {
    const success = await onUpdate(config)
    if (success) {
      updatePanelState((prev) => ({
        ...prev,
        previewDraft: null,
        appliedPreviewDraft: null,
      }))
      invalidateAllPreviews(queryClient)
    }
    return success
  }, [onUpdate, queryClient, updatePanelState])

  const handleCancelEdit = useCallback(() => {
    updatePanelState((prev) => ({
      ...prev,
      activeTab: 'params',
      previewDraft: null,
      appliedPreviewDraft: null,
      formInstanceKey: prev.formInstanceKey + 1,
    }))
  }, [updatePanelState])

  const handleConfirmDelete = useCallback(async () => {
    setIsDeleting(true)
    const success = await onDelete()
    setIsDeleting(false)
    setDeleteDialogOpen(false)
    if (success) {
      onBack()
    }
  }, [onDelete, onBack])

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="px-4 py-3 border-b">
        <div className="flex items-center gap-3">
          {/* Back button */}
          <Button
            variant="ghost"
            size="icon"
            className="h-8 w-8 shrink-0"
            onClick={onBack}
          >
            <ArrowLeft className="h-4 w-4" />
          </Button>

          {/* Icon */}
          <div className={cn(
            'flex h-10 w-10 shrink-0 items-center justify-center rounded-lg',
            colors.bg,
            colors.border,
            'border'
          )}>
            <Icon className={cn('h-5 w-5', colors.text)} />
          </div>

          {/* Title and info */}
          <div className="flex-1 min-w-0">
            <h2 className="font-semibold truncate">{resolveLocalizedString(widget.title)}</h2>
            <div className="flex items-center gap-2 mt-0.5">
              <Badge variant="secondary" className="text-xs">
                {widget.widgetPlugin}
              </Badge>
              <Badge variant="outline" className="text-xs">
                {widget.transformerPlugin}
              </Badge>
            </div>
          </div>

          {/* Actions */}
          <div className="flex items-center gap-1.5 shrink-0">
            <Button
              variant="ghost"
              size="icon"
              className="h-8 w-8"
              onClick={handleRefresh}
            >
              <RefreshCw className="h-4 w-4" />
            </Button>
            <Button
              variant="ghost"
              size="icon"
              className="h-8 w-8 text-destructive hover:text-destructive hover:bg-destructive/10"
              onClick={() => setDeleteDialogOpen(true)}
            >
              <Trash2 className="h-4 w-4" />
            </Button>
          </div>
        </div>

        {/* Description if available */}
        {widget.description && (
          <p className="text-sm text-muted-foreground mt-2 ml-11">
            {resolveLocalizedString(widget.description)}
          </p>
        )}
      </div>

      {/* Tabs */}
      <Tabs
        value={activeTab}
        onValueChange={(value) =>
          updatePanelState((prev) => ({
            ...prev,
            activeTab: value as 'params' | 'yaml',
          }))
        }
        className="flex-1 flex flex-col min-h-0"
      >
        <div className="px-4 pt-2 border-b">
          <TabsList className="h-9">
            <TabsTrigger value="params" className="gap-1.5 text-sm">
              <Settings className="h-3.5 w-3.5" />
              {t('widgets:detailPanel.paramsTab')}
            </TabsTrigger>
            <TabsTrigger value="yaml" className="gap-1.5 text-sm">
              <FileCode className="h-3.5 w-3.5" />
              {t('widgets:detailPanel.yamlTab')}
            </TabsTrigger>
          </TabsList>
        </div>

        {/* Parameters Tab */}
        <TabsContent value="params" className="flex-1 m-0 min-h-0 overflow-hidden">
          <div className="flex h-full min-h-0 flex-col lg:flex-row">
            <div className="min-h-0 flex-1 lg:basis-[62%] lg:border-r">
              <WidgetConfigForm
                key={`${widget.id}-${formInstanceKey}`}
                widget={widget}
                groupBy={groupBy}
                availableFields={availableFields}
                onSave={handleSave}
                onCancel={handleCancelEdit}
                onChange={(config) =>
                  updatePanelState((prev) => ({
                    ...prev,
                    previewDraft: config,
                  }))
                }
              />
            </div>

            <div className="flex h-[38vh] shrink-0 flex-col border-t bg-muted/20 p-4 lg:h-full lg:basis-[38%] lg:border-l-0 lg:border-t-0">
              <div className="mb-3 flex items-center justify-between gap-3">
                <div className="min-w-0">
                  <p className="text-sm font-medium">{t('widgets:detailPanel.previewTitle')}</p>
                  <p className="text-xs text-muted-foreground">
                    {autoRefreshPreview
                      ? (previewDraft
                          ? t('widgets:detailPanel.livePreview')
                          : t('widgets:detailPanel.savedVersion'))
                      : (previewDraft
                          ? t('widgets:detailPanel.draftPendingRefresh')
                          : t('widgets:detailPanel.savedVersion'))}
                  </p>
                </div>
                {autoRefreshPreview ? (
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-8 w-8 shrink-0"
                    onClick={handleRefresh}
                  >
                    <RefreshCw className="h-4 w-4" />
                  </Button>
                ) : (
                  <Button
                    variant="outline"
                    size="sm"
                    className="shrink-0"
                    onClick={handleRefresh}
                  >
                    <RefreshCw className="mr-1.5 h-3.5 w-3.5" />
                    {t('widgets:detailPanel.refreshPreview')}
                  </Button>
                )}
              </div>

              <div className="mx-auto flex min-h-0 w-full max-w-[420px] flex-1 overflow-hidden rounded-xl border bg-card lg:h-[520px] lg:flex-none">
                <PreviewPane
                  descriptor={previewDescriptor}
                  className="h-full w-full"
                  transformHtml={injectFullPreviewOverrides}
                />
              </div>
            </div>
          </div>
        </TabsContent>

        {/* YAML Tab */}
        <TabsContent value="yaml" className="flex-1 m-0 min-h-0 overflow-hidden">
          <ScrollArea className="h-full">
            <div className="p-4 space-y-4">
              {/* Transform YAML */}
              <div>
                <div className="flex items-center gap-2 mb-2">
                  <FileCode className="h-4 w-4 text-muted-foreground" />
                  <span className="text-sm font-medium">transform.yml</span>
                  <Badge variant="outline" className="text-[10px] bg-warning/10 text-warning border-warning/30">
                    {t('widgets:preview.transformation')}
                  </Badge>
                </div>
                <pre className="p-3 rounded-lg bg-slate-950 text-slate-50 text-xs overflow-auto font-mono">
                  <code>{yamlPreviews.transform}</code>
                </pre>
              </div>

              {/* Export YAML */}
              <div>
                <div className="flex items-center gap-2 mb-2">
                  <FileCode className="h-4 w-4 text-muted-foreground" />
                  <span className="text-sm font-medium">export.yml</span>
                  <Badge variant="outline" className="text-[10px] bg-success/10 text-success border-success/30">
                    Widget
                  </Badge>
                </div>
                <pre className="p-3 rounded-lg bg-slate-950 text-slate-50 text-xs overflow-auto font-mono">
                  <code>{yamlPreviews.export}</code>
                </pre>
              </div>
            </div>
          </ScrollArea>
        </TabsContent>
      </Tabs>

      {/* Delete Confirmation Dialog */}
      <AlertDialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle className="flex items-center gap-2">
              <AlertTriangle className="h-5 w-5 text-destructive" />
              {t('widgets:detailPanel.deleteTitle')}
            </AlertDialogTitle>
            <AlertDialogDescription>
              {t('widgets:detailPanel.deleteDescription', {
                title: resolveLocalizedString(widget.title),
              })}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={isDeleting}>
              {t('common:actions.cancel')}
            </AlertDialogCancel>
            <AlertDialogAction
              onClick={handleConfirmDelete}
              disabled={isDeleting}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              {isDeleting ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  {t('common:status.deleting')}
                </>
              ) : (
                t('common:actions.delete')
              )}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  )
}
