/**
 * ContentTab - Main content tab for hybrid widget management
 *
 * Combines widget list (left) with contextual right panel:
 * - No selection: Shows layout overview (grid preview)
 * - Widget selected: Shows widget detail panel (preview + params + YAML)
 */

import { useState, useCallback, useMemo, useEffect } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { GripVertical, Plus } from 'lucide-react'
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

  // Fetch configured widgets
  const {
    configuredWidgets,
    loading: widgetsLoading,
    updateWidget,
    deleteWidget,
    duplicateWidget,
    reorderWidgets,
    refetch: refetchWidgets,
  } = useWidgetConfig(reference.name)

  // Fetch suggestions for the modal
  const queryClient = useQueryClient()
  const { suggestions, loading: suggestionsLoading } = useSuggestions(
    reference.name,
    'occurrences'
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
    queryClient.invalidateQueries({ queryKey: ['suggestions', reference.name] })
  }, [queryClient, reference.name])

  // Handle widget added from modal
  const handleWidgetAdded = useCallback(() => {
    refetchWidgets()
    setAddModalOpen(false)
    setSelectedWidgetId(null)
  }, [refetchWidgets])

  return (
    <div className="h-full flex flex-col">
      <ResizablePanelGroup direction="horizontal" className="flex-1">
        {/* Left Panel - Widget List */}
        <ResizablePanel defaultSize={30} minSize={20} maxSize={45}>
          <div className="h-full flex flex-col border-r">
            {/* Header with Add button */}
            <div className="p-3 border-b flex items-center justify-between gap-2">
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button size="sm" className="gap-1">
                    <Plus className="h-4 w-4" />
                    Ajouter un widget
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="start">
                  <DropdownMenuItem onClick={() => handleOpenAddModal('suggestions')}>
                    Depuis les suggestions
                  </DropdownMenuItem>
                  <DropdownMenuItem onClick={() => handleOpenAddModal('combined')}>
                    Widget combine
                  </DropdownMenuItem>
                  <DropdownMenuItem onClick={() => handleOpenAddModal('custom')}>
                    Widget personnalise
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            </div>

            {/* Search */}
            <div className="p-3 border-b">
              <Input
                placeholder="Rechercher..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="h-8"
              />
            </div>

            {/* Widget List */}
            <WidgetListPanel
              widgets={filteredWidgets}
              selectedId={selectedWidgetId}
              loading={widgetsLoading}
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
        <ResizableHandle className="w-2 flex items-center justify-center group">
          <div className="w-1 h-12 rounded-full bg-border group-hover:bg-primary/50 group-active:bg-primary transition-colors flex items-center justify-center">
            <GripVertical className="h-4 w-4 text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity" />
          </div>
        </ResizableHandle>

        {/* Right Panel - Contextual */}
        <ResizablePanel defaultSize={70} minSize={55}>
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
      <AddWidgetModal
        open={addModalOpen}
        onOpenChange={setAddModalOpen}
        defaultTab={addModalTab}
        reference={reference}
        suggestions={suggestions}
        suggestionsLoading={suggestionsLoading}
        onWidgetAdded={handleWidgetAdded}
      />
    </div>
  )
}
