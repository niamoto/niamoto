/**
 * Group Panel - Widget Configuration for a Reference
 *
 * Three tabs:
 * - Sources de données: Configure data sources (occurrences + stats files)
 * - Widgets: Gallery of available widgets (SmartSetup generalized)
 * - Mise en page: Widget layout configuration (future)
 */

import { useState, useMemo, useCallback } from 'react'
import type { ReferenceInfo } from '@/hooks/useReferences'
import { Database, LayoutGrid, Package, Loader2, AlertCircle, Save, Plus, GripVertical, Layout, ListChecks, Wand2, ListOrdered, Sparkles, FileSpreadsheet, Code2 } from 'lucide-react'
import { Panel, PanelGroup, PanelResizeHandle } from 'react-resizable-panels'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { ScrollArea } from '@/components/ui/scroll-area'
import {
  WidgetGallery,
  WidgetPreviewPanel,
  ConfiguredWidgetsList,
  ClassObjectSelector,
  WidgetWizard,
  RecipeEditor,
  useSuggestions,
  useTemplateSelection,
  useConfiguredWidgets,
  useGenerateConfig,
  useSaveConfig,
  useWidgetConfig,
  type TemplateSuggestion,
  type ConfiguredWidget,
} from '@/components/widgets'
import { useClassObjectSuggestions } from '@/lib/api/widget-suggestions'
import { apiClient } from '@/lib/api/client'
import { useSources, useRemoveSource } from '@/hooks/useSources'
import { SourcesList, AddSourceDialog } from '@/components/sources'
import { LayoutEditor } from '@/components/layout-editor'
import { IndexConfigEditor } from '@/components/index-config'

interface GroupPanelProps {
  reference: ReferenceInfo
}

export function GroupPanel({ reference }: GroupPanelProps) {
  const [activeTab, setActiveTab] = useState('sources')

  // Kind display mapping
  const kindLabels: Record<string, string> = {
    hierarchical: 'Hiérarchique',
    flat: 'Plat',
    spatial: 'Spatial',
  }

  return (
    <div className="flex h-full flex-col">
      {/* Header */}
      <div className="border-b bg-background px-6 py-4">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
            <Package className="h-5 w-5 text-primary" />
          </div>
          <div>
            <h1 className="text-xl font-bold">{reference.name}</h1>
            <p className="text-sm text-muted-foreground">
              {reference.entity_count ?? '?'} entités
              <span className="mx-2">·</span>
              <Badge variant="outline" className="text-xs">
                {kindLabels[reference.kind] || reference.kind}
              </Badge>
              {reference.description && (
                <>
                  <span className="mx-2">·</span>
                  {reference.description}
                </>
              )}
            </p>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab} className="flex-1">
        <div className="border-b px-6">
          <TabsList className="h-10 w-fit gap-1 bg-muted/50 p-1 rounded-lg">
            <TabsTrigger
              value="sources"
              className="px-3 data-[state=active]:bg-background data-[state=active]:shadow-sm rounded-md"
            >
              <Database className="mr-2 h-4 w-4" />
              Sources de donnees
            </TabsTrigger>
            <TabsTrigger
              value="widgets"
              className="px-3 data-[state=active]:bg-background data-[state=active]:shadow-sm rounded-md"
            >
              <LayoutGrid className="mr-2 h-4 w-4" />
              Widgets
            </TabsTrigger>
            <TabsTrigger
              value="layout"
              className="px-3 data-[state=active]:bg-background data-[state=active]:shadow-sm rounded-md"
            >
              <Layout className="mr-2 h-4 w-4" />
              Mise en page
            </TabsTrigger>
            <TabsTrigger
              value="index"
              className="px-3 data-[state=active]:bg-background data-[state=active]:shadow-sm rounded-md"
            >
              <ListOrdered className="mr-2 h-4 w-4" />
              Index
            </TabsTrigger>
          </TabsList>
        </div>

        {/* Tab Content */}
        <div className="flex-1 overflow-auto p-6">
          <TabsContent value="sources" className="m-0">
            <SourcesTab reference={reference} />
          </TabsContent>

          <TabsContent value="widgets" className="m-0">
            <WidgetsTab reference={reference} />
          </TabsContent>

          <TabsContent value="layout" className="m-0">
            <LayoutTab reference={reference} />
          </TabsContent>

          <TabsContent value="index" className="m-0">
            <IndexTab reference={reference} />
          </TabsContent>
        </div>
      </Tabs>
    </div>
  )
}

function SourcesTab({ reference }: { reference: ReferenceInfo }) {
  const [addDialogOpen, setAddDialogOpen] = useState(false)

  // Fetch configured sources
  const { data: sourcesData, isLoading: sourcesLoading } = useSources(reference.name)
  const sources = sourcesData?.sources ?? []

  // Remove source mutation
  const removeMutation = useRemoveSource(reference.name)

  const handleRemoveSource = (sourceName: string) => {
    removeMutation.mutate(sourceName)
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-lg font-medium">Sources de donnees</h2>
        <p className="text-sm text-muted-foreground">
          Configurez les sources de donnees pour le groupe "{reference.name}".
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        {/* Primary source - occurrences */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Source principale</CardTitle>
            <CardDescription>
              Table de donnees liee a cette reference
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="rounded-md bg-muted p-3">
              <p className="font-mono text-sm">occurrences</p>
              <p className="mt-1 text-xs text-muted-foreground">
                Relation: {reference.kind === 'hierarchical' ? 'nested_set' : 'direct_reference'}
              </p>
            </div>
          </CardContent>
        </Card>

        {/* Pre-calculated sources */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0">
            <div>
              <CardTitle className="text-base">Donnees pre-calculees</CardTitle>
              <CardDescription>
                Fichiers CSV de statistiques supplementaires
              </CardDescription>
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setAddDialogOpen(true)}
            >
              <Plus className="mr-1 h-3 w-3" />
              Ajouter
            </Button>
          </CardHeader>
          <CardContent>
            {sourcesLoading ? (
              <div className="flex min-h-[60px] items-center justify-center">
                <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
              </div>
            ) : (
              <SourcesList
                sources={sources}
                onRemove={handleRemoveSource}
                isRemoving={removeMutation.isPending}
              />
            )}
          </CardContent>
        </Card>
      </div>

      {/* Schema fields */}
      {reference.schema_fields.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Champs du schema</CardTitle>
            <CardDescription>
              Colonnes disponibles pour cette reference
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid gap-2 md:grid-cols-3">
              {reference.schema_fields.map((field) => (
                <div
                  key={field.name}
                  className="flex items-center justify-between rounded-md bg-muted p-2"
                >
                  <span className="font-mono text-sm">{field.name}</span>
                  {field.type && (
                    <Badge variant="outline" className="text-xs">
                      {field.type}
                    </Badge>
                  )}
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Add Source Dialog */}
      <AddSourceDialog
        open={addDialogOpen}
        onOpenChange={setAddDialogOpen}
        referenceName={reference.name}
        onSuccess={() => setAddDialogOpen(false)}
      />
    </div>
  )
}

function WidgetsTab({ reference }: { reference: ReferenceInfo }) {
  // Sub-tab state - default to "available" (Colonnes)
  const [widgetSubTab, setWidgetSubTab] = useState('available')

  // Fetch configured widgets using the new hook
  const {
    configuredWidgets,
    loading: configuredLoading,
    updateWidget,
    deleteWidget,
    duplicateWidget,
    refetch: refetchConfigured,
  } = useWidgetConfig(reference.name)

  // Fetch configured widget IDs for template selection
  const { configuredIds, hasConfig, loading: configLoading } = useConfiguredWidgets(reference.name)

  // Convert to Set for useTemplateSelection
  const existingIds = useMemo(() => new Set(configuredIds), [configuredIds])

  // Fetch widget suggestions for this reference
  const { suggestions, loading, error, refetch } = useSuggestions(
    reference.name,
    'occurrences'
  )

  // Fetch class_object suggestions (new API)
  const {
    classObjects,
    pluginSchemas,
    data: suggestionsData,
    loading: classObjectsLoading,
    error: classObjectsError,
    refetch: refetchClassObjects,
  } = useClassObjectSuggestions(reference.name)

  // Class object selection state
  const [selectedClassObjects, setSelectedClassObjects] = useState<Set<string>>(new Set())
  const [_selectedConfigs, setSelectedConfigs] = useState<Map<string, Record<string, unknown>>>(new Map())

  // Wizard state
  const [wizardOpen, setWizardOpen] = useState(false)

  // Handle class_object selection
  const handleSelectClassObject = useCallback((name: string, config: Record<string, unknown>) => {
    setSelectedClassObjects(prev => new Set([...prev, name]))
    setSelectedConfigs(prev => new Map([...prev, [name, config]]))
  }, [])

  const handleDeselectClassObject = useCallback((name: string) => {
    setSelectedClassObjects(prev => {
      const next = new Set(prev)
      next.delete(name)
      return next
    })
    setSelectedConfigs(prev => {
      const next = new Map(prev)
      next.delete(name)
      return next
    })
  }, [])

  // Map transformer plugins to widget plugins for export
  const TRANSFORMER_TO_WIDGET: Record<string, string> = {
    class_object_field_aggregator: 'info_grid',
    class_object_binary_aggregator: 'bar_plot',
    class_object_categories_extractor: 'bar_plot',
    class_object_series_extractor: 'bar_plot',
    class_object_series_ratio_aggregator: 'bar_plot',
    class_object_categories_mapper: 'bar_plot',
    class_object_series_matrix_extractor: 'bar_plot',
    class_object_series_by_axis_extractor: 'bar_plot',
  }

  // Handle wizard completion
  const handleWizardComplete = useCallback(async (config: Record<string, unknown>, widgetId: string, pluginName: string) => {
    try {
      // 1. Save widget to transform.yml
      await apiClient.put(`/config/transform/${reference.name}/widgets/${widgetId}`, {
        plugin: pluginName,
        params: config,
      })

      // 2. Save corresponding widget to export.yml
      const widgetPlugin = TRANSFORMER_TO_WIDGET[pluginName] || 'info_grid'
      await apiClient.put(`/config/export/${reference.name}/widgets/${widgetId}`, {
        plugin: widgetPlugin,
        data_source: widgetId,
        title: widgetId.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase()),
      })

      console.log('Widget saved to transform.yml and export.yml:', widgetId, pluginName, widgetPlugin)
      refetchConfigured()
      setWizardOpen(false)
    } catch (error) {
      console.error('Error saving widget:', error)
    }
  }, [reference.name, refetchConfigured])

  // Selection management: use existing config if available, otherwise auto-select
  const selection = useTemplateSelection(suggestions, hasConfig ? existingIds : undefined)

  // Preview state - can be either a template or a configured widget
  const [previewTemplate, setPreviewTemplate] = useState<TemplateSuggestion | null>(null)
  const [previewWidget, setPreviewWidget] = useState<ConfiguredWidget | null>(null)

  // Key to force re-render of preview on resize
  const [previewKey, setPreviewKey] = useState(0)

  // Handle panel resize to refresh preview dimensions
  const handlePanelResize = useCallback(() => {
    setPreviewKey(k => k + 1)
  }, [])

  // Generate and save config hooks
  const { generate, loading: generating, error: generateError } = useGenerateConfig()
  const { save, loading: saving, error: saveError } = useSaveConfig()

  // Combined loading state
  const isSaving = generating || saving

  // Get selected templates with full config
  const selectedTemplates = useMemo(() => {
    return suggestions
      .filter(s => selection.selectedSet.has(s.template_id))
      .map(s => ({
        template_id: s.template_id,
        plugin: s.plugin,
        config: s.config
      }))
  }, [suggestions, selection.selectedSet])

  // Save result state for success message
  const [saveResult, setSaveResult] = useState<{ added: number; updated: number } | null>(null)

  // Handle save config: generate then save to transform.yml
  const handleSaveConfig = async () => {
    if (selectedTemplates.length === 0) return
    setSaveResult(null)

    // Step 1: Generate config
    const generatedConfig = await generate(selectedTemplates, reference.name, reference.kind)
    if (!generatedConfig) return

    // Step 2: Save to transform.yml
    const result = await save(generatedConfig)
    if (result?.success) {
      setSaveResult({ added: result.widgets_added, updated: result.widgets_updated })
      // Clear success message after 3 seconds
      setTimeout(() => setSaveResult(null), 3000)
      // Refetch configured widgets
      refetchConfigured()
    }
  }

  // Handle selecting a template for preview
  const handleSelectTemplate = useCallback((template: TemplateSuggestion) => {
    setPreviewTemplate(template)
    setPreviewWidget(null)
  }, [])

  // Handle selecting a configured widget for preview/edit
  const handleSelectWidget = useCallback((widget: ConfiguredWidget) => {
    setPreviewWidget(widget)
    setPreviewTemplate(null)
  }, [])

  // Handle widget update (from edit form)
  const handleUpdateWidget = useCallback(async (widgetId: string, config: Partial<ConfiguredWidget>): Promise<boolean> => {
    const success = await updateWidget(widgetId, config)
    if (success) {
      refetchConfigured()
    }
    return success
  }, [updateWidget, refetchConfigured])

  // Handle widget delete
  const handleDeleteWidget = useCallback(async (widgetId: string): Promise<boolean> => {
    const success = await deleteWidget(widgetId)
    if (success) {
      // Clear preview if deleted widget was selected
      if (previewWidget?.id === widgetId) {
        setPreviewWidget(null)
      }
      refetchConfigured()
    }
    return success
  }, [deleteWidget, previewWidget, refetchConfigured])

  // Handle widget duplicate
  const handleDuplicateWidget = useCallback(async (widgetId: string, newId: string): Promise<boolean> => {
    const success = await duplicateWidget(widgetId, newId)
    if (success) {
      refetchConfigured()
    }
    return success
  }, [duplicateWidget, refetchConfigured])

  // Loading state - wait for both config and suggestions
  if (loading || configLoading) {
    return (
      <div className="flex min-h-[400px] flex-col items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        <p className="mt-4 text-sm text-muted-foreground">
          Analyse des colonnes pour {reference.name}...
        </p>
      </div>
    )
  }

  // Error state
  if (error) {
    return (
      <div className="flex min-h-[400px] flex-col items-center justify-center">
        <AlertCircle className="h-12 w-12 text-destructive/50" />
        <h3 className="mt-4 font-medium">Erreur de chargement</h3>
        <p className="mt-2 text-sm text-muted-foreground">{error}</p>
        <Button variant="outline" className="mt-4" onClick={refetch}>
          Reessayer
        </Button>
      </div>
    )
  }

  return (
    <Tabs value={widgetSubTab} onValueChange={setWidgetSubTab} className="h-[calc(100vh-280px)] flex flex-col">
      {/* Sub-tabs header */}
      <div className="shrink-0 mb-4">
        <TabsList className="h-9 w-fit gap-1 bg-muted p-1">
          <TabsTrigger value="available" className="px-3 data-[state=active]:bg-background data-[state=active]:shadow-sm">
            <Wand2 className="mr-2 h-4 w-4" />
            Colonnes
            {suggestions.length > 0 && (
              <Badge variant="outline" className="ml-2 h-5 px-1.5 text-xs">
                {suggestions.length}
              </Badge>
            )}
          </TabsTrigger>
          {classObjects.length > 0 && (
            <TabsTrigger value="class_objects" className="px-3 data-[state=active]:bg-background data-[state=active]:shadow-sm">
              <FileSpreadsheet className="mr-2 h-4 w-4" />
              Class Objects
              <Badge variant="outline" className="ml-2 h-5 px-1.5 text-xs bg-emerald-50 text-emerald-700 border-emerald-200">
                {classObjects.length}
              </Badge>
            </TabsTrigger>
          )}
          <TabsTrigger value="expert" className="px-3 data-[state=active]:bg-background data-[state=active]:shadow-sm">
            <Code2 className="mr-2 h-4 w-4" />
            Expert
          </TabsTrigger>
          <TabsTrigger value="configured" className="px-3 data-[state=active]:bg-background data-[state=active]:shadow-sm">
            <ListChecks className="mr-2 h-4 w-4" />
            Configures
            {configuredWidgets.length > 0 && (
              <Badge variant="secondary" className="ml-2 h-5 px-1.5 text-xs">
                {configuredWidgets.length}
              </Badge>
            )}
          </TabsTrigger>
        </TabsList>
      </div>

      {/* Main content - using TabsContent for proper accessibility */}

      {/* Class Objects tab - New feature */}
      <TabsContent value="class_objects" className="flex-1 min-h-0 m-0 data-[state=inactive]:hidden">
        {classObjectsLoading ? (
          <div className="flex min-h-[400px] flex-col items-center justify-center">
            <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
            <p className="mt-4 text-sm text-muted-foreground">
              Analyse des class_objects...
            </p>
          </div>
        ) : classObjectsError ? (
          <div className="flex min-h-[400px] flex-col items-center justify-center">
            <AlertCircle className="h-12 w-12 text-destructive/50" />
            <h3 className="mt-4 font-medium">Erreur de chargement</h3>
            <p className="mt-2 text-sm text-muted-foreground">{classObjectsError}</p>
            <Button variant="outline" className="mt-4" onClick={refetchClassObjects}>
              Reessayer
            </Button>
          </div>
        ) : classObjects.length === 0 ? (
          <div className="flex min-h-[400px] flex-col items-center justify-center text-center p-8">
            <FileSpreadsheet className="h-12 w-12 text-muted-foreground/50" />
            <h3 className="mt-4 font-medium">Aucun class_object disponible</h3>
            <p className="mt-2 text-sm text-muted-foreground max-w-md">
              Ajoutez une source de donnees pre-calculee (fichier CSV avec colonnes id, label, class_object, class_name, class_value) dans l'onglet "Sources de donnees".
            </p>
          </div>
        ) : (
          <PanelGroup direction="horizontal" className="h-full" onLayout={handlePanelResize}>
            {/* Left panel - Class Object Selector */}
            <Panel defaultSize={40} minSize={25} maxSize={60}>
              <div className="h-full rounded-lg border bg-card overflow-hidden">
                <ClassObjectSelector
                  classObjects={classObjects}
                  selectedNames={selectedClassObjects}
                  onSelect={handleSelectClassObject}
                  onDeselect={handleDeselectClassObject}
                />
              </div>
            </Panel>

            {/* Resize handle */}
            <PanelResizeHandle className="w-2 mx-1 flex items-center justify-center group">
              <div className="w-1 h-12 rounded-full bg-border group-hover:bg-primary/50 group-active:bg-primary transition-colors flex items-center justify-center">
                <GripVertical className="h-4 w-4 text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity" />
              </div>
            </PanelResizeHandle>

            {/* Right panel - Actions & Summary */}
            <Panel defaultSize={60} minSize={40} maxSize={75}>
              <div className="h-full rounded-lg border bg-card overflow-hidden flex flex-col">
                <ScrollArea className="flex-1">
                  {/* Wizard launcher */}
                  <div className="p-4 border-b">
                    <div className="flex items-center gap-2 mb-2">
                      <Wand2 className="h-4 w-4 text-primary" />
                      <h4 className="text-sm font-medium">Creer un widget avance</h4>
                    </div>
                    <p className="text-xs text-muted-foreground mb-3">
                      Utilisez l'assistant pour configurer des widgets complexes
                      (comparaisons, distributions, matrices).
                    </p>
                    <Button
                      onClick={() => setWizardOpen(true)}
                      className="w-full"
                      disabled={Object.keys(pluginSchemas).length === 0}
                    >
                      <Plus className="mr-2 h-4 w-4" />
                      Ouvrir l'assistant
                    </Button>
                  </div>

                  {/* Selection summary */}
                  {selectedClassObjects.size > 0 && (
                    <div className="p-4 border-t">
                      <div className="flex items-center gap-2 mb-3">
                        <Sparkles className="h-4 w-4 text-primary" />
                        <h4 className="text-sm font-medium">
                          {selectedClassObjects.size} class_object{selectedClassObjects.size > 1 ? 's' : ''} selectionne{selectedClassObjects.size > 1 ? 's' : ''}
                        </h4>
                      </div>
                      <div className="flex flex-wrap gap-2 mb-4">
                        {Array.from(selectedClassObjects).map(name => (
                          <Badge key={name} variant="secondary" className="text-xs">
                            {name}
                          </Badge>
                        ))}
                      </div>
                      <p className="text-xs text-muted-foreground">
                        Les class_objects selectionnes peuvent etre utilises
                        pour creer des widgets simples (agregateurs de champs).
                      </p>
                    </div>
                  )}

                  {/* Plugin schemas summary */}
                  {Object.keys(pluginSchemas).length > 0 && (
                    <div className="p-4 border-t">
                      <h4 className="text-sm font-medium mb-2">Plugins disponibles</h4>
                      <div className="space-y-2">
                        {Object.entries(pluginSchemas).map(([name, schema]) => (
                          <div key={name} className="flex items-center justify-between text-xs">
                            <span>{schema.name}</span>
                            <Badge variant="outline" className="text-[10px]">
                              {schema.complexity}
                            </Badge>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </ScrollArea>
              </div>
            </Panel>
          </PanelGroup>
        )}

        {/* Widget Wizard */}
        <WidgetWizard
          open={wizardOpen}
          onOpenChange={setWizardOpen}
          classObjects={classObjects}
          pluginSchemas={pluginSchemas}
          sourceName={suggestionsData?.source_name || 'stats'}
          onComplete={handleWizardComplete}
        />
      </TabsContent>

      <TabsContent value="available" className="flex-1 min-h-0 m-0 data-[state=inactive]:hidden">
        <PanelGroup direction="horizontal" className="h-full" onLayout={handlePanelResize}>
          {/* Left panel - Widget Gallery */}
          <Panel defaultSize={40} minSize={25} maxSize={60}>
            <div className="h-full rounded-lg border bg-card overflow-hidden">
              <WidgetGallery
                suggestions={suggestions}
                selectedIds={selection.selectedSet}
                groupBy={reference.name}
                onSelect={selection.toggle}
                onPreview={handleSelectTemplate}
                onSelectAll={() => selection.selectAll(suggestions.map(s => s.template_id))}
                onDeselectAll={selection.deselectAll}
              />
            </div>
          </Panel>

          {/* Resize handle */}
          <PanelResizeHandle className="w-2 mx-1 flex items-center justify-center group">
            <div className="w-1 h-12 rounded-full bg-border group-hover:bg-primary/50 group-active:bg-primary transition-colors flex items-center justify-center">
              <GripVertical className="h-4 w-4 text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity" />
            </div>
          </PanelResizeHandle>

          {/* Right panel - Preview */}
          <Panel defaultSize={60} minSize={40} maxSize={75}>
            <div className="h-full rounded-lg border bg-card overflow-hidden">
              <WidgetPreviewPanel
                key={`available-${previewKey}`}
                template={previewTemplate}
                groupBy={reference.name}
              />
            </div>
          </Panel>
        </PanelGroup>
      </TabsContent>

      <TabsContent value="configured" className="flex-1 min-h-0 m-0 data-[state=inactive]:hidden">
        <PanelGroup direction="horizontal" className="h-full" onLayout={handlePanelResize}>
          {/* Left panel - Configured List */}
          <Panel defaultSize={40} minSize={25} maxSize={60}>
            <div className="h-full rounded-lg border bg-card overflow-hidden">
              <ConfiguredWidgetsList
                widgets={configuredWidgets}
                selectedId={previewWidget?.id}
                loading={configuredLoading}
                onSelect={handleSelectWidget}
                onDelete={handleDeleteWidget}
                onDuplicate={handleDuplicateWidget}
              />
            </div>
          </Panel>

          {/* Resize handle */}
          <PanelResizeHandle className="w-2 mx-1 flex items-center justify-center group">
            <div className="w-1 h-12 rounded-full bg-border group-hover:bg-primary/50 group-active:bg-primary transition-colors flex items-center justify-center">
              <GripVertical className="h-4 w-4 text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity" />
            </div>
          </PanelResizeHandle>

          {/* Right panel - Preview/Edit */}
          <Panel defaultSize={60} minSize={40} maxSize={75}>
            <div className="h-full rounded-lg border bg-card overflow-hidden">
              <WidgetPreviewPanel
                key={`configured-${previewKey}`}
                configuredWidget={previewWidget}
                groupBy={reference.name}
                onUpdateWidget={handleUpdateWidget}
              />
            </div>
          </Panel>
        </PanelGroup>
      </TabsContent>

      {/* Expert Mode - Recipe Editor */}
      <TabsContent value="expert" className="flex-1 min-h-0 m-0 data-[state=inactive]:hidden">
        <div className="h-full rounded-lg border bg-card overflow-hidden">
          <RecipeEditor
            groupBy={reference.name}
            onSave={() => {
              refetchConfigured()
            }}
          />
        </div>
      </TabsContent>

      {/* Floating action button - only for available widgets tab */}
      {widgetSubTab === 'available' && selectedTemplates.length > 0 && (
        <div className="fixed bottom-6 right-6 z-50 flex flex-col items-end gap-2">
          {/* Success message */}
          {saveResult && (
            <div className="bg-success text-success-foreground px-4 py-2 rounded-lg shadow-lg text-sm animate-in fade-in slide-in-from-bottom-2">
              {saveResult.added > 0 && <span>{saveResult.added} widget{saveResult.added > 1 ? 's' : ''} ajoute{saveResult.added > 1 ? 's' : ''}</span>}
              {saveResult.added > 0 && saveResult.updated > 0 && <span>, </span>}
              {saveResult.updated > 0 && <span>{saveResult.updated} mis a jour</span>}
            </div>
          )}

          {/* Error message */}
          {(generateError || saveError) && (
            <div className="bg-destructive text-destructive-foreground px-4 py-2 rounded-lg shadow-lg text-sm max-w-sm">
              {generateError || saveError}
            </div>
          )}

          {/* Save button */}
          <Button
            size="lg"
            className="shadow-lg"
            onClick={handleSaveConfig}
            disabled={isSaving}
          >
            {isSaving ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                {generating ? 'Generation...' : 'Sauvegarde...'}
              </>
            ) : (
              <>
                <Save className="mr-2 h-4 w-4" />
                Sauvegarder {selectedTemplates.length} widget{selectedTemplates.length > 1 ? 's' : ''}
              </>
            )}
          </Button>
        </div>
      )}
    </Tabs>
  )
}

function LayoutTab({ reference }: { reference: ReferenceInfo }) {
  return (
    <div className="h-[calc(100vh-280px)]">
      <LayoutEditor groupBy={reference.name} />
    </div>
  )
}

function IndexTab({ reference }: { reference: ReferenceInfo }) {
  return (
    <div className="h-[calc(100vh-280px)]">
      <IndexConfigEditor groupBy={reference.name} />
    </div>
  )
}
