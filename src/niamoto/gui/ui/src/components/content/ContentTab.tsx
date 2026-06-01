/**
 * ContentTab - Main content tab for hybrid widget management
 *
 * Combines widget list (left) with contextual right panel:
 * - No selection: Shows layout overview (grid preview)
 * - Widget selected: Shows widget detail panel (preview + params + YAML)
 */

import { useState, useCallback, useMemo, useRef } from 'react'
import { useTranslation } from 'react-i18next'
import { useLocation, useSearchParams } from 'react-router-dom'
import { PanelLeft, Plus } from 'lucide-react'
import type { PanelImperativeHandle, PanelSize } from 'react-resizable-panels'
import {
  ResizableHandle,
  ResizablePanel,
  ResizablePanelGroup,
} from '@/components/ui/resizable'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import {
  useConfiguredWidgets,
  useWidgetConfig,
  useSuggestions,
  type ConfiguredWidget,
} from '@/components/widgets'
import type { LocalizedString } from '@/components/ui/localized-input'
import { WidgetListPanel } from './WidgetListPanel'
import { ContentRightPanel } from './ContentRightPanel'
import { AddWidgetModal } from '@/components/widgets/AddWidgetModal'
import type { ReferenceInfo } from '@/hooks/useReferences'
import {
  readStoredCollectionsPreviewPreference,
  shouldAutoRefreshCollectionsDetailPreview,
  writeStoredCollectionsPreviewPreference,
  type CollectionsPreviewPreference,
} from './previewPolicy'
import { useDevListRenderMetric } from '@/shared/performance/devRenderMetrics'

// Helper to resolve LocalizedString for search
function resolveLocalizedString(value: LocalizedString | undefined, defaultLang = 'fr'): string {
  if (!value) return ''
  if (typeof value === 'string') return value
  return value[defaultLang] || Object.values(value)[0] || ''
}

interface ContentTabProps {
  reference: ReferenceInfo
}

export function ContentTab({ reference }: ContentTabProps) {
  const { t } = useTranslation(['widgets', 'common'])
  const location = useLocation()
  const [searchParams, setSearchParams] = useSearchParams()
  const requestedPanel = searchParams.get('panel')
  const routeRequestsAddWidget = requestedPanel === 'add-widget'
  const routeAddWidgetRequestKey = routeRequestsAddWidget
    ? `${reference.name}:${location.key}:${searchParams.toString()}`
    : null
  // Selection state is scoped to the current reference to avoid resetting it in an effect.
  const [selectedWidgetState, setSelectedWidgetState] = useState<{
    referenceName: string
    widgetId: string | null
  }>(() => ({
    referenceName: reference.name,
    widgetId: null,
  }))
  const selectedWidgetId =
    selectedWidgetState.referenceName === reference.name
      ? selectedWidgetState.widgetId
      : null

  const [addModalOpen, setAddModalOpen] = useState(false)
  const [dismissedRouteAddWidgetKey, setDismissedRouteAddWidgetKey] = useState<
    string | null
  >(null)
  const routeAddWidgetOpen =
    routeAddWidgetRequestKey !== null &&
    dismissedRouteAddWidgetKey !== routeAddWidgetRequestKey
  const addModalVisible = addModalOpen || routeAddWidgetOpen

  // Search state
  const [searchQuery, setSearchQuery] = useState('')
  const [previewPreference, setPreviewPreference] = useState<CollectionsPreviewPreference>(
    () => readStoredCollectionsPreviewPreference(),
  )

  const {
    loading: configuredWidgetsLoading,
  } = useConfiguredWidgets(reference.name)

  // Fetch configured widgets
  const {
    configuredWidgets,
    loading: widgetsLoading,
    updateWidget,
    deleteWidget,
    duplicateWidget,
    reorderWidgets,
    refetch: refetchWidgets,
  } = useWidgetConfig(reference.name, true)

  const { suggestions, loading: suggestionsLoading } = useSuggestions(
    reference.name,
    undefined,
    addModalVisible,
  )

  const availableFields = useMemo(() => {
    const fields = new Set<string>()
    suggestions.forEach((suggestion) => {
      if (suggestion.matched_column) fields.add(suggestion.matched_column)
    })
    return Array.from(fields).sort()
  }, [suggestions])

  // Filter widgets by search
  const filteredWidgets = useMemo(() => {
    if (!searchQuery.trim()) return configuredWidgets
    const query = searchQuery.toLowerCase()
    return configuredWidgets.filter(w =>
      resolveLocalizedString(w.title).toLowerCase().includes(query) ||
      w.id.toLowerCase().includes(query) ||
      w.widgetPlugin.toLowerCase().includes(query)
    )
  }, [configuredWidgets, searchQuery])

  const detailPreviewAutoRefresh = useMemo(
    () => shouldAutoRefreshCollectionsDetailPreview(previewPreference),
    [previewPreference],
  )

  useDevListRenderMetric('collections.content.configuredWidgets', configuredWidgets.length, {
    itemThreshold: 20,
    detail: {
      reference: reference.name,
      filteredCount: filteredWidgets.length,
      selected: selectedWidgetId !== null,
      autoRefreshPreview: detailPreviewAutoRefresh,
    },
  })

  // Get selected widget data
  const selectedWidget = useMemo(() => {
    if (!selectedWidgetId) return null
    return configuredWidgets.find(w => w.id === selectedWidgetId) || null
  }, [configuredWidgets, selectedWidgetId])

  // Handle widget selection
  const handleSelectWidget = useCallback((widget: ConfiguredWidget | null) => {
    const nextWidgetId = widget?.id || null
    setSelectedWidgetState((current) => {
      if (current.referenceName === reference.name && current.widgetId === nextWidgetId) {
        return current
      }

      return {
        referenceName: reference.name,
        widgetId: nextWidgetId,
      }
    })
  }, [reference.name])

  // Handle back to layout overview
  const handleBackToLayout = useCallback(() => {
    setSelectedWidgetState((current) => {
      if (current.referenceName === reference.name && current.widgetId === null) {
        return current
      }

      return {
        referenceName: reference.name,
        widgetId: null,
      }
    })
  }, [reference.name])

  // Handle widget update (updateWidget fait déjà fetchConfigs en interne)
  const handleUpdateWidget = useCallback(async (
    widgetId: string,
    config: Partial<ConfiguredWidget>
  ): Promise<boolean> => {
    return await updateWidget(widgetId, config)
  }, [updateWidget])

  // Handle widget delete (deleteWidget fait déjà fetchConfigs en interne)
  const handleDeleteWidget = useCallback(async (widgetId: string): Promise<boolean> => {
    const success = await deleteWidget(widgetId)
    if (success && selectedWidgetId === widgetId) {
      setSelectedWidgetState((current) => {
        if (current.referenceName === reference.name && current.widgetId === null) {
          return current
        }

        return {
          referenceName: reference.name,
          widgetId: null,
        }
      })
    }
    return success
  }, [deleteWidget, reference.name, selectedWidgetId])

  // Handle widget duplicate (duplicateWidget fait déjà fetchConfigs en interne)
  const handleDuplicateWidget = useCallback(async (
    widgetId: string,
    newId: string
  ): Promise<boolean> => {
    return await duplicateWidget(widgetId, newId)
  }, [duplicateWidget])

  // Handle widget reorder
  const handleReorderWidgets = useCallback(async (widgetIds: string[]): Promise<boolean> => {
    return await reorderWidgets(widgetIds)
  }, [reorderWidgets])

  const handleOpenAddModal = useCallback(() => {
    setAddModalOpen(true)
  }, [])

  const clearRouteAddWidgetPanel = useCallback(() => {
    if (!routeAddWidgetRequestKey || searchParams.get('panel') !== 'add-widget') {
      return
    }
    const nextSearchParams = new URLSearchParams(searchParams)
    nextSearchParams.delete('panel')
    setSearchParams(nextSearchParams, { replace: true })
  }, [routeAddWidgetRequestKey, searchParams, setSearchParams])

  const handleWidgetAdded = useCallback(() => {
    refetchWidgets()
    setAddModalOpen(false)
    if (routeAddWidgetRequestKey) {
      setDismissedRouteAddWidgetKey(routeAddWidgetRequestKey)
      clearRouteAddWidgetPanel()
    }
    setSelectedWidgetState((current) => {
      if (current.referenceName === reference.name && current.widgetId === null) {
        return current
      }

      return {
        referenceName: reference.name,
        widgetId: null,
      }
    })
  }, [
    clearRouteAddWidgetPanel,
    reference.name,
    refetchWidgets,
    routeAddWidgetRequestKey,
  ])

  const handleAddModalOpenChange = useCallback((isOpen: boolean) => {
    setAddModalOpen(isOpen)
    if (!isOpen && routeAddWidgetRequestKey) {
      setDismissedRouteAddWidgetKey(routeAddWidgetRequestKey)
      clearRouteAddWidgetPanel()
    }
  }, [clearRouteAddWidgetPanel, routeAddWidgetRequestKey])

  const leftPanelRef = useRef<PanelImperativeHandle>(null)
  const [isCollapsed, setIsCollapsed] = useState(false)

  const handleLeftPanelResize = useCallback((panelSize: PanelSize) => {
    const nextCollapsed = panelSize.asPercentage === 0
    setIsCollapsed((current) => current === nextCollapsed ? current : nextCollapsed)
  }, [])

  const togglePanel = useCallback(() => {
    const panel = leftPanelRef.current
    if (!panel) return
    if (isCollapsed) {
      panel.expand()
      setIsCollapsed(false)
    } else {
      panel.collapse()
      setIsCollapsed(true)
    }
  }, [isCollapsed])

  const handlePreviewPreferenceChange = useCallback(
    (preference: CollectionsPreviewPreference) => {
      setPreviewPreference(preference)
      writeStoredCollectionsPreviewPreference(preference)
    },
    [],
  )

  return (
    <div className="h-full flex flex-col">
      <ResizablePanelGroup direction="horizontal" className="flex-1">
          {/* Left Panel - Widget List */}
          <ResizablePanel
            panelRef={leftPanelRef}
            defaultSize="20%"
            minSize="14%"
            maxSize="26%"
            collapsible
            collapsedSize={0}
            onResize={handleLeftPanelResize}
          >
            <div className="relative h-full">
            <div className="absolute inset-0 flex flex-col">
              {/* Header with Add button + collapse toggle */}
              <div className="px-2 py-1.5 border-b flex items-center gap-1">
                <Button size="sm" className="gap-1" onClick={handleOpenAddModal}>
                  <Plus className="h-4 w-4" />
                  {t('widgets:actions.addWidget')}
                </Button>
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-7 w-7 shrink-0 ml-auto"
                  onClick={togglePanel}
                  title={t('widgets:layout.hideWidgetList')}
                >
                  <PanelLeft className="h-4 w-4" />
                </Button>
              </div>

              {/* Search */}
              <div className="px-2 py-1.5 border-b">
                <Input
                  placeholder={t('common:actions.search')}
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="h-7 text-xs"
                />
              </div>

              {/* Widget List */}
              <div className="flex-1 min-h-0">
                <WidgetListPanel
                  widgets={filteredWidgets}
                  selectedId={selectedWidgetId}
                  loading={configuredWidgetsLoading || widgetsLoading}
                  onSelect={handleSelectWidget}
                  onDelete={handleDeleteWidget}
                  onDuplicate={handleDuplicateWidget}
                  onReorder={handleReorderWidgets}
                />
              </div>

              {/* Footer */}
              <div className="shrink-0 p-2 border-t text-xs text-muted-foreground text-center">
                {t('widgets:layout.widgetsConfigured', { count: configuredWidgets.length })}
              </div>
            </div>
            </div>
          </ResizablePanel>

          {/* Resize Handle */}
          <ResizableHandle />

          {/* Right Panel - Contextual */}
          <ResizablePanel defaultSize="80%" minSize="55%">
            <div className="relative h-full">
            <div className="absolute inset-0 flex flex-col">
              {/* Collapsed toolbar: toggle + add widget */}
              {isCollapsed && (
                <div className="flex items-center gap-1 border-b px-2 py-1 shrink-0">
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-7 w-7"
                    onClick={togglePanel}
                    title={t('widgets:layout.showWidgetList')}
                  >
                    <PanelLeft className="h-4 w-4" />
                  </Button>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-7 w-7"
                    onClick={handleOpenAddModal}
                    aria-label={t('widgets:actions.addWidget')}
                  >
                    <Plus className="h-4 w-4" />
                  </Button>
                  <span className="text-xs text-muted-foreground ml-1">
                    {t('widgets:layout.widgetsConfigured', { count: configuredWidgets.length })}
                  </span>
                </div>
              )}
              <div className="flex-1 min-h-0">
                <ContentRightPanel
                  selectedWidget={selectedWidget}
                  allWidgets={configuredWidgets}
                  groupBy={reference.name}
                  availableFields={availableFields}
                  previewPreference={previewPreference}
                  onPreviewPreferenceChange={handlePreviewPreferenceChange}
                  detailPreviewAutoRefresh={detailPreviewAutoRefresh}
                  onSelectWidget={handleSelectWidget}
                  onBack={handleBackToLayout}
                  onUpdateWidget={handleUpdateWidget}
                  onDeleteWidget={handleDeleteWidget}
                  onLayoutSaved={refetchWidgets}
                />
              </div>
            </div>
            </div>
          </ResizablePanel>
      </ResizablePanelGroup>

      {addModalVisible ? (
        <AddWidgetModal
          open={addModalVisible}
          onOpenChange={handleAddModalOpenChange}
          defaultTab="suggestions"
          reference={reference}
          suggestions={suggestions}
          suggestionsLoading={suggestionsLoading}
          onWidgetAdded={handleWidgetAdded}
        />
      ) : null}
    </div>
  )
}
