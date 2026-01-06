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
  AlertTriangle,
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

interface WidgetDetailPanelProps {
  widget: ConfiguredWidget
  groupBy: string
  onBack: () => void
  onUpdate: (config: Partial<ConfiguredWidget>) => Promise<boolean>
  onDelete: () => Promise<boolean>
}

export function WidgetDetailPanel({
  widget,
  groupBy,
  onBack,
  onUpdate,
  onDelete,
}: WidgetDetailPanelProps) {
  const [activeTab, setActiveTab] = useState<'preview' | 'params' | 'yaml'>('preview')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [refreshCounter, setRefreshCounter] = useState(0)
  const [isDeleting, setIsDeleting] = useState(false)
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false)

  // Category info
  const category = widget.category || 'chart'
  const Icon = CATEGORY_ICONS[category] || BarChart3
  const colors = CATEGORY_COLORS[category] || CATEGORY_COLORS.chart

  // Build preview URL
  const previewUrl = useMemo(() => {
    const baseUrl = `/api/templates/preview/${widget.dataSource || widget.id}`
    if (groupBy) {
      return `${baseUrl}?group_by=${encodeURIComponent(groupBy)}`
    }
    return baseUrl
  }, [widget.id, widget.dataSource, groupBy])

  // Unique key for iframe refresh
  const iframeKey = `${widget.id}-${refreshCounter}`

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

  // Reset loading state when widget changes
  useEffect(() => {
    setLoading(true)
    setError(null)
    setActiveTab('preview')
  }, [widget.id])

  // Handlers
  const handleIframeLoad = useCallback(() => {
    setLoading(false)
    setError(null)
  }, [])

  const handleIframeError = useCallback(() => {
    setLoading(false)
    setError('Impossible de charger la preview')
  }, [])

  const handleRefresh = useCallback(() => {
    setLoading(true)
    setError(null)
    setRefreshCounter((prev) => prev + 1)
  }, [])

  const handleSave = useCallback(async (config: Partial<ConfiguredWidget>): Promise<boolean> => {
    const success = await onUpdate(config)
    if (success) {
      handleRefresh()
    }
    return success
  }, [onUpdate, handleRefresh])

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
            <h2 className="font-semibold truncate">{widget.title}</h2>
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
              disabled={loading}
            >
              <RefreshCw className={cn('h-4 w-4', loading && 'animate-spin')} />
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
            {widget.description}
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
                  <AlertTriangle className="h-10 w-10 text-warning mb-2" />
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

              <iframe
                key={iframeKey}
                src={previewUrl}
                className="w-full h-full border-0"
                onLoad={handleIframeLoad}
                onError={handleIframeError}
                title={`Preview: ${widget.title}`}
              />
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
              Cela supprimera <strong>"{widget.title}"</strong> de la configuration.
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
                  Suppression...
                </>
              ) : (
                'Supprimer'
              )}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  )
}
