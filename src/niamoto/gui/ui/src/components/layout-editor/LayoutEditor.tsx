/**
 * LayoutEditor - Main component for widget layout editing
 *
 * Features:
 * - Visual preview of widget layout
 * - Drag & drop reordering
 * - Column span toggle (1 or 2 columns)
 * - Inline title editing
 * - Navigation sidebar preview
 */
import { useState, useCallback, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  Loader2,
  Save,
  RefreshCw,
  AlertCircle,
  Settings2,
  Columns,
  Columns2,
  Eye,
  EyeOff,
  Leaf,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { WidgetGrid } from './WidgetGrid'
import { LayoutSidebar } from './LayoutSidebar'
import type {
  LayoutResponse,
  LayoutUpdateRequest,
  WidgetLayout,
  WidgetLayoutUpdate,
} from './types'

interface LayoutEditorProps {
  groupBy: string
}

interface RepresentativeEntity {
  id: string
  name: string
  count: number
}

interface RepresentativesResponse {
  group_by: string
  default_entity: RepresentativeEntity | null
  entities: RepresentativeEntity[]
  total: number
}

async function fetchLayout(groupBy: string): Promise<LayoutResponse> {
  const response = await fetch(`/api/layout/${groupBy}`)
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Unknown error' }))
    throw new Error(error.detail || `HTTP error ${response.status}`)
  }
  return response.json()
}

async function saveLayout(
  groupBy: string,
  updates: LayoutUpdateRequest
): Promise<{ success: boolean; message: string; widgets_updated: number }> {
  const response = await fetch(`/api/layout/${groupBy}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(updates),
  })
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Unknown error' }))
    throw new Error(error.detail || `HTTP error ${response.status}`)
  }
  return response.json()
}

async function fetchRepresentatives(groupBy: string): Promise<RepresentativesResponse> {
  const response = await fetch(`/api/layout/${groupBy}/representatives`)
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Unknown error' }))
    throw new Error(error.detail || `HTTP error ${response.status}`)
  }
  return response.json()
}

export function LayoutEditor({ groupBy }: LayoutEditorProps) {
  const { t } = useTranslation(['widgets', 'common'])
  const queryClient = useQueryClient()

  // Fetch layout data
  const {
    data: layout,
    isLoading,
    error,
    refetch,
  } = useQuery({
    queryKey: ['layout', groupBy],
    queryFn: () => fetchLayout(groupBy),
  })

  // Fetch representative entities for preview selector
  const { data: representatives } = useQuery({
    queryKey: ['representatives', groupBy],
    queryFn: () => fetchRepresentatives(groupBy),
  })

  // Local state for editing
  const [localWidgets, setLocalWidgets] = useState<WidgetLayout[]>([])
  const [hasChanges, setHasChanges] = useState(false)
  const [showPreviews, setShowPreviews] = useState(true) // Previews on by default
  const [selectedEntityId, setSelectedEntityId] = useState<string | null>(null)

  // Set default entity when representatives are loaded
  useEffect(() => {
    if (representatives?.default_entity && !selectedEntityId) {
      setSelectedEntityId(representatives.default_entity.id)
    }
  }, [representatives, selectedEntityId])

  // Initialize local widgets from fetched data
  useEffect(() => {
    if (layout?.widgets) {
      setLocalWidgets([...layout.widgets])
      setHasChanges(false)
    }
  }, [layout])

  // Save mutation
  const saveMutation = useMutation({
    mutationFn: (updates: LayoutUpdateRequest) => saveLayout(groupBy, updates),
    onSuccess: () => {
      setHasChanges(false)
      queryClient.invalidateQueries({ queryKey: ['layout', groupBy] })
    },
  })

  // Handle reorder - preserve navigation widget
  const handleReorder = useCallback((newOrder: WidgetLayout[]) => {
    setLocalWidgets((prev) => {
      // Keep navigation widget(s) separate
      const navWidgets = prev.filter((w) => w.is_navigation)

      // Update order values for content widgets based on new positions
      const updatedContent = newOrder.map((widget, idx) => ({
        ...widget,
        order: idx,
      }))

      // Combine: navigation widgets first, then content widgets
      return [...navWidgets, ...updatedContent]
    })
    setHasChanges(true)
  }, [])

  // Handle colspan toggle
  const handleColspanToggle = useCallback((widgetIndex: number) => {
    setLocalWidgets((prev) =>
      prev.map((w) =>
        w.index === widgetIndex
          ? { ...w, colspan: w.colspan === 1 ? 2 : 1 }
          : w
      )
    )
    setHasChanges(true)
  }, [])

  // Handle title change
  const handleTitleChange = useCallback((widgetIndex: number, newTitle: string) => {
    setLocalWidgets((prev) =>
      prev.map((w) =>
        w.index === widgetIndex ? { ...w, title: newTitle } : w
      )
    )
    setHasChanges(true)
  }, [])

  // Handle save
  const handleSave = useCallback(() => {
    const updates: WidgetLayoutUpdate[] = localWidgets.map((w) => ({
      index: w.index,
      title: w.title,
      description: w.description,
      colspan: w.colspan,
      order: w.order,
    }))
    saveMutation.mutate({ widgets: updates })
  }, [localWidgets, saveMutation])

  // Loading state
  if (isLoading) {
    return (
      <div className="flex min-h-[400px] flex-col items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        <p className="mt-4 text-sm text-muted-foreground">
          {t('layout.loadingLayout')}
        </p>
      </div>
    )
  }

  // Error state
  if (error) {
    return (
      <div className="flex min-h-[400px] flex-col items-center justify-center">
        <AlertCircle className="h-12 w-12 text-destructive/50" />
        <h3 className="mt-4 font-medium">{t('layout.loadError')}</h3>
        <p className="mt-2 text-sm text-muted-foreground">
          {error instanceof Error ? error.message : t('layout.unknownError')}
        </p>
        <Button variant="outline" className="mt-4" onClick={() => refetch()}>
          <RefreshCw className="mr-2 h-4 w-4" />
          {t('common:actions.retry')}
        </Button>
      </div>
    )
  }

  // No widgets state
  if (!layout || layout.widgets.length === 0) {
    return (
      <div className="flex min-h-[400px] flex-col items-center justify-center rounded-lg border-2 border-dashed border-muted-foreground/25 p-8">
        <Settings2 className="mb-4 h-12 w-12 text-muted-foreground" />
        <h3 className="mb-2 font-medium">{t('layout.noWidgets')}</h3>
        <p className="text-center text-sm text-muted-foreground max-w-md">
          {t('layout.noWidgetsHint')}
        </p>
      </div>
    )
  }

  // Separate navigation widget from content widgets
  const navigationWidget = localWidgets.find((w) => w.is_navigation)
  const contentWidgets = localWidgets.filter((w) => !w.is_navigation)

  return (
    <div className="h-full flex flex-col">
      {/* Header with actions */}
      <div className="flex items-center justify-between mb-4">
        <div>
          <h2 className="text-lg font-medium">{t('layout.title')}</h2>
          <p className="text-sm text-muted-foreground">
            {t('layout.widgetsConfigured', { count: layout.total_widgets })}
            {hasChanges && (
              <Badge variant="outline" className="ml-2 text-warning border-warning">
                {t('layout.unsavedChanges')}
              </Badge>
            )}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant={showPreviews ? 'secondary' : 'outline'}
            size="sm"
            onClick={() => setShowPreviews(!showPreviews)}
            title={showPreviews ? t('layout.hidePreviews') : t('layout.showPreviews')}
          >
            {showPreviews ? (
              <>
                <Eye className="mr-2 h-4 w-4" />
                {t('layout.previews')}
              </>
            ) : (
              <>
                <EyeOff className="mr-2 h-4 w-4" />
                {t('layout.previews')}
              </>
            )}
          </Button>

          {/* Entity selector for previews */}
          {showPreviews && representatives && representatives.entities.length > 0 && (
            <Select
              value={selectedEntityId || ''}
              onValueChange={(value) => setSelectedEntityId(value)}
            >
              <SelectTrigger className="w-[200px] h-8">
                <Leaf className="mr-2 h-4 w-4 text-muted-foreground" />
                <SelectValue placeholder={t('layout.selectEntity')} />
              </SelectTrigger>
              <SelectContent>
                {representatives.entities.map((entity) => (
                  <SelectItem key={entity.id} value={entity.id}>
                    {entity.name} ({entity.count})
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          )}

          <Button
            variant="outline"
            size="sm"
            onClick={() => refetch()}
            disabled={saveMutation.isPending}
          >
            <RefreshCw className="mr-2 h-4 w-4" />
            {t('layout.refresh')}
          </Button>
          <Button
            size="sm"
            onClick={handleSave}
            disabled={!hasChanges || saveMutation.isPending}
          >
            {saveMutation.isPending ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                {t('layout.saving')}
              </>
            ) : (
              <>
                <Save className="mr-2 h-4 w-4" />
                {t('layout.save')}
              </>
            )}
          </Button>
        </div>
      </div>

      {/* Success/Error messages */}
      {saveMutation.isSuccess && (
        <div className="mb-4 bg-success/10 text-success border border-success/30 px-4 py-2 rounded-lg text-sm">
          {t('layout.saveSuccess')}
        </div>
      )}
      {saveMutation.error && (
        <div className="mb-4 bg-destructive/10 text-destructive border border-destructive/30 px-4 py-2 rounded-lg text-sm">
          {saveMutation.error instanceof Error
            ? saveMutation.error.message
            : t('layout.saveError')}
        </div>
      )}

      {/* Layout preview */}
      <div className="flex-1 flex gap-4 min-h-0">
        {/* Navigation sidebar (if exists) */}
        {navigationWidget && layout.navigation_widget && (
          <div className="w-72 flex-shrink-0">
            <LayoutSidebar
              groupBy={groupBy}
              navigationWidget={layout.navigation_widget}
            />
          </div>
        )}

        {/* Main content grid */}
        <div className="flex-1 overflow-auto">
          <WidgetGrid
            groupBy={groupBy}
            widgets={contentWidgets}
            showPreviews={showPreviews}
            entityId={selectedEntityId}
            onReorder={handleReorder}
            onColspanToggle={handleColspanToggle}
            onTitleChange={handleTitleChange}
          />
        </div>
      </div>

      {/* Legend */}
      <div className="mt-4 pt-4 border-t flex items-center gap-4 text-xs text-muted-foreground">
        <div className="flex items-center gap-1">
          <Columns className="h-3.5 w-3.5" />
          <span>{t('layout.columns.one')}</span>
        </div>
        <div className="flex items-center gap-1">
          <Columns2 className="h-3.5 w-3.5" />
          <span>{t('layout.columns.two')}</span>
        </div>
        <span className="text-muted-foreground/50">|</span>
        <span>{t('layout.dragDrop')}</span>
      </div>
    </div>
  )
}
