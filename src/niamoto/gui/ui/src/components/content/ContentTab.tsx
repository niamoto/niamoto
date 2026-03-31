/**
 * ContentTab - Main content tab for hybrid widget management
 *
 * Combines widget list (left) with contextual right panel:
 * - No selection: Shows layout overview (grid preview)
 * - Widget selected: Shows widget detail panel (preview + params + YAML)
 */

import { useState, useCallback, useMemo, useEffect, useRef } from 'react'
import { useTranslation } from 'react-i18next'
import { PanelLeft, Plus } from 'lucide-react'
import type { ImperativePanelHandle } from 'react-resizable-panels'
import {
  ResizableHandle,
  ResizablePanel,
  ResizablePanelGroup,
} from '@/components/ui/resizable'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
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
  // Selection state
  const [selectedWidgetId, setSelectedWidgetId] = useState<string | null>(null)

  // Reset selection when reference changes (group switch)
  useEffect(() => {
    setSelectedWidgetId(null)
  }, [reference.name])

  // Modal state
  const [addModalOpen, setAddModalOpen] = useState(false)
  const [addModalTab, setAddModalTab] = useState<'suggestions' | 'combined' | 'custom'>('suggestions')

  // Search state
  const [searchQuery, setSearchQuery] = useState('')

  const {
    configuredIds,
    loading: configuredWidgetsLoading,
  } = useConfiguredWidgets(reference.name)
  const hasConfiguredWidgets = configuredIds.length > 0

  // Fetch configured widgets
  const {
    configuredWidgets,
    loading: widgetsLoading,
    updateWidget,
    deleteWidget,
    duplicateWidget,
    reorderWidgets,
    refetch: refetchWidgets,
  } = useWidgetConfig(reference.name, hasConfiguredWidgets)

  // Fetch suggestions only when the add-widget modal is opened
  const { suggestions, loading: suggestionsLoading } = useSuggestions(
    reference.name,
    'occurrences',
    addModalOpen
  )

  // Extract available fields from suggestions (for field-select widgets)
  const availableFields = useMemo(() => {
    const fields = new Set<string>()
    suggestions.forEach((s) => {
      if (s.matched_column) fields.add(s.matched_column)
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

  // Get selected widget data
  const selectedWidget = useMemo(() => {
    if (!selectedWidgetId) return null
    return configuredWidgets.find(w => w.id === selectedWidgetId) || null
  }, [configuredWidgets, selectedWidgetId])

  // Handle widget selection
  const handleSelectWidget = useCallback((widget: ConfiguredWidget | null) => {
    setSelectedWidgetId(widget?.id || null)
  }, [])

  // Handle back to layout overview
  const handleBackToLayout = useCallback(() => {
    setSelectedWidgetId(null)
  }, [])

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
      setSelectedWidgetId(null)
    }
    return success
  }, [deleteWidget, selectedWidgetId])

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

  // Handle open add modal with specific tab — invalidate cache to force fresh fetch
  const handleOpenAddModal = useCallback((tab: 'suggestions' | 'combined' | 'custom') => {
    setAddModalTab(tab)
    setAddModalOpen(true)
  }, [])

  // Handle widget added from modal
  const handleWidgetAdded = useCallback(() => {
    refetchWidgets()
    setAddModalOpen(false)
    setSelectedWidgetId(null)
  }, [refetchWidgets])

  const leftPanelRef = useRef<ImperativePanelHandle>(null)
  const [isCollapsed, setIsCollapsed] = useState(false)

  const togglePanel = useCallback(() => {
    const panel = leftPanelRef.current
    if (!panel) return
    if (isCollapsed) {
      panel.expand()
    } else {
      panel.collapse()
    }
  }, [isCollapsed])

  return (
    <div className="h-full flex flex-col">
      <ResizablePanelGroup direction="horizontal" className="flex-1">
        {/* Left Panel - Widget List */}
        <ResizablePanel
          ref={leftPanelRef}
          defaultSize={28}
          minSize={15}
          maxSize={40}
          collapsible
          collapsedSize={0}
          onCollapse={() => setIsCollapsed(true)}
          onExpand={() => setIsCollapsed(false)}
        >
          <div className="h-full flex flex-col overflow-hidden">
            {/* Header with Add button + collapse toggle */}
            <div className="px-2 py-1.5 border-b flex items-center gap-1">
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button size="sm" className="gap-1">
                    <Plus className="h-4 w-4" />
                    {t('widgets:actions.addWidget')}
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="start">
                  <DropdownMenuItem onClick={() => handleOpenAddModal('suggestions')}>
                    {t('widgets:actions.addFromSuggestions')}
                  </DropdownMenuItem>
                  <DropdownMenuItem onClick={() => handleOpenAddModal('combined')}>
                    {t('widgets:actions.addCombinedWidget')}
                  </DropdownMenuItem>
                  <DropdownMenuItem onClick={() => handleOpenAddModal('custom')}>
                    {t('widgets:modal.custom')}
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
              <Button variant="ghost" size="icon" className="h-7 w-7 shrink-0 ml-auto" onClick={togglePanel} title="Hide widget list">
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
            <WidgetListPanel
              widgets={filteredWidgets}
              selectedId={selectedWidgetId}
              loading={configuredWidgetsLoading || (hasConfiguredWidgets && widgetsLoading)}
              onSelect={handleSelectWidget}
              onDelete={handleDeleteWidget}
              onDuplicate={handleDuplicateWidget}
              onReorder={handleReorderWidgets}
            />

            {/* Footer */}
            <div className="p-2 border-t text-xs text-muted-foreground text-center">
              {configuredWidgets.length} widget{configuredWidgets.length !== 1 ? 's' : ''} configure{configuredWidgets.length !== 1 ? 's' : ''}
            </div>
          </div>
        </ResizablePanel>

        {/* Resize Handle */}
        <ResizableHandle />

        {/* Right Panel - Contextual */}
        <ResizablePanel defaultSize={72} minSize={55}>
          {/* Collapsed toolbar: toggle + add widget */}
          {isCollapsed && (
            <div className="flex items-center gap-1 border-b px-2 py-1">
              <Button variant="ghost" size="icon" className="h-7 w-7" onClick={togglePanel} title="Show widget list">
                <PanelLeft className="h-4 w-4" />
              </Button>
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button variant="ghost" size="icon" className="h-7 w-7">
                    <Plus className="h-4 w-4" />
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="start">
                  <DropdownMenuItem onClick={() => handleOpenAddModal('suggestions')}>
                    {t('widgets:actions.addFromSuggestions')}
                  </DropdownMenuItem>
                  <DropdownMenuItem onClick={() => handleOpenAddModal('combined')}>
                    {t('widgets:actions.addCombinedWidget')}
                  </DropdownMenuItem>
                  <DropdownMenuItem onClick={() => handleOpenAddModal('custom')}>
                    {t('widgets:modal.custom')}
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
              <span className="text-xs text-muted-foreground ml-1">
                {configuredWidgets.length} widget{configuredWidgets.length !== 1 ? 's' : ''}
              </span>
            </div>
          )}
          <ContentRightPanel
            selectedWidget={selectedWidget}
            allWidgets={configuredWidgets}
            groupBy={reference.name}
            availableFields={availableFields}
            onSelectWidget={handleSelectWidget}
            onBack={handleBackToLayout}
            onUpdateWidget={handleUpdateWidget}
            onDeleteWidget={handleDeleteWidget}
            onLayoutSaved={refetchWidgets}
          />
        </ResizablePanel>
      </ResizablePanelGroup>

      {/* Add Widget Modal */}
      {addModalOpen ? (
        <AddWidgetModal
          open={addModalOpen}
          onOpenChange={setAddModalOpen}
          defaultTab={addModalTab}
          reference={reference}
          suggestions={suggestions}
          suggestionsLoading={suggestionsLoading}
          onWidgetAdded={handleWidgetAdded}
        />
      ) : null}
    </div>
  )
}
