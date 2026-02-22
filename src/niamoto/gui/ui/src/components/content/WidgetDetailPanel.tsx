/**
 * WidgetDetailPanel - Detailed view of a selected widget
 *
 * Shows when a widget is selected in the content tab.
 * Provides:
 * - Header with back button, title, and actions
 * - Three tabs: Preview / Parameters / YAML
 * - Edit and delete capabilities
 */
import { useState, useCallback, useMemo, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { useQueryClient } from '@tanstack/react-query'
import yaml from 'js-yaml'
import {
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
  Eye,
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
import { PreviewPane } from '@/components/preview'
import type { PreviewDescriptor } from '@/lib/preview/types'
import { invalidateAllPreviews } from '@/lib/preview/usePreviewFrame'

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
  onBack: () => void
  onUpdate: (config: Partial<ConfiguredWidget>) => Promise<boolean>
  onDelete: () => Promise<boolean>
}

export function WidgetDetailPanel({
  widget,
  groupBy,
  availableFields = [],
  onBack,
  onUpdate,
  onDelete,
}: WidgetDetailPanelProps) {
  const { t } = useTranslation()
  const queryClient = useQueryClient()
  const [activeTab, setActiveTab] = useState<'preview' | 'params' | 'yaml'>('preview')
  const [isDeleting, setIsDeleting] = useState(false)
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false)

  // Category info
  const category = widget.category || 'chart'
  const Icon = CATEGORY_ICONS[category] || BarChart3
  const colors = CATEGORY_COLORS[category] || CATEGORY_COLORS.chart

  // Build PreviewDescriptor
  const previewDescriptor: PreviewDescriptor = useMemo(() => ({
    templateId: widget.dataSource || widget.id,
    groupBy,
    mode: 'full' as const,
  }), [widget.id, widget.dataSource, groupBy])

  // Generate YAML previews
  const yamlPreviews = useMemo(() => {
    const transformConfig: Record<string, unknown> = {
      [widget.id]: {
        plugin: widget.transformerPlugin,
        params: widget.transformerParams,
      },
    }

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
      transform: yaml.dump(transformConfig, { indent: 2, lineWidth: -1 }),
      export: yaml.dump([exportWidget], { indent: 2, lineWidth: -1 }),
    }
  }, [widget])

  // Reset tab when widget changes
  useEffect(() => {
    setActiveTab('preview')
  }, [widget.id])

  const handleRefresh = useCallback(() => {
    invalidateAllPreviews(queryClient)
  }, [queryClient])

  const handleSave = useCallback(async (config: Partial<ConfiguredWidget>): Promise<boolean> => {
    const success = await onUpdate(config)
    if (success) {
      invalidateAllPreviews(queryClient)
    }
    return success
  }, [onUpdate, queryClient])

  const handleCancelEdit = useCallback(() => {
    setActiveTab('preview')
  }, [])

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
        onValueChange={(v) => setActiveTab(v as typeof activeTab)}
        className="flex-1 flex flex-col min-h-0"
      >
        <div className="px-4 pt-2 border-b">
          <TabsList className="h-9">
            <TabsTrigger value="preview" className="gap-1.5 text-sm">
              <Eye className="h-3.5 w-3.5" />
              Preview
            </TabsTrigger>
            <TabsTrigger value="params" className="gap-1.5 text-sm">
              <Settings className="h-3.5 w-3.5" />
              Parametres
            </TabsTrigger>
            <TabsTrigger value="yaml" className="gap-1.5 text-sm">
              <FileCode className="h-3.5 w-3.5" />
              YAML
            </TabsTrigger>
          </TabsList>
        </div>

        {/* Preview Tab */}
        <TabsContent value="preview" className="flex-1 m-0 min-h-0">
          <div className="h-full p-4">
            <div className="h-full rounded-xl border bg-card overflow-hidden">
              <PreviewPane descriptor={previewDescriptor} className="w-full h-full" />
            </div>
          </div>
        </TabsContent>

        {/* Parameters Tab */}
        <TabsContent value="params" className="flex-1 m-0 min-h-0 overflow-hidden">
          <ScrollArea className="h-full">
            <div className="p-4">
              <WidgetConfigForm
                widget={widget}
                groupBy={groupBy}
                availableFields={availableFields}
                onSave={handleSave}
                onCancel={handleCancelEdit}
              />
            </div>
          </ScrollArea>
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
                    Transformation
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
              Supprimer le widget ?
            </AlertDialogTitle>
            <AlertDialogDescription>
              Cela supprimera <strong>"{resolveLocalizedString(widget.title)}"</strong> de la configuration.
              Cette action est irreversible.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={isDeleting}>Annuler</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleConfirmDelete}
              disabled={isDeleting}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              {isDeleting ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  {t('status.deleting')}
                </>
              ) : (
                t('actions.delete')
              )}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  )
}
