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
import { Database, LayoutGrid, Package, Loader2, AlertCircle, Sparkles, Save, Plus, GripVertical, Layout } from 'lucide-react'
import { Panel, PanelGroup, PanelResizeHandle } from 'react-resizable-panels'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  WidgetGallery,
  WidgetPreviewPanel,
  useSuggestions,
  useTemplateSelection,
  useConfiguredWidgets,
  useGenerateConfig,
  useSaveConfig,
  type TemplateSuggestion,
} from '@/components/widgets'
import { useSources, useRemoveSource } from '@/hooks/useSources'
import { SourcesList, AddSourceDialog } from '@/components/sources'
import { LayoutEditor } from '@/components/layout-editor'

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
              Sources de données
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
  // Fetch configured widgets from transform.yml
  const { configuredIds, hasConfig, loading: configLoading } = useConfiguredWidgets(reference.name)

  // Convert to Set for useTemplateSelection
  const existingIds = useMemo(() => new Set(configuredIds), [configuredIds])

  // Fetch widget suggestions for this reference
  const { suggestions, columnsAnalyzed, loading, error, refetch } = useSuggestions(
    reference.name,
    'occurrences'
  )

  // Selection management: use existing config if available, otherwise auto-select
  const selection = useTemplateSelection(suggestions, hasConfig ? existingIds : undefined)

  // Preview state
  const [previewTemplate, setPreviewTemplate] = useState<TemplateSuggestion | null>(null)

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
    }
  }

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
          Réessayer
        </Button>
      </div>
    )
  }

  // No suggestions state
  if (suggestions.length === 0) {
    return (
      <div className="flex min-h-[400px] flex-col items-center justify-center">
        <Sparkles className="h-12 w-12 text-muted-foreground/50" />
        <h3 className="mt-4 font-medium">Aucun widget disponible</h3>
        <p className="mt-2 text-center text-sm text-muted-foreground max-w-md">
          Importez des données avec des colonnes analysables pour obtenir des suggestions de widgets.
        </p>
        {columnsAnalyzed > 0 && (
          <p className="mt-2 text-xs text-muted-foreground">
            {columnsAnalyzed} colonnes analysées
          </p>
        )}
      </div>
    )
  }

  return (
    <div className="h-[calc(100vh-280px)]">
      <PanelGroup direction="horizontal" className="h-full" onLayout={handlePanelResize}>
        {/* Gallery panel - left side */}
        <Panel defaultSize={50} minSize={30} maxSize={70}>
          <div className="h-full rounded-lg border bg-card overflow-hidden">
            <WidgetGallery
              suggestions={suggestions}
              selectedIds={selection.selectedSet}
              groupBy={reference.name}
              onSelect={selection.toggle}
              onPreview={setPreviewTemplate}
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

        {/* Preview panel - right side */}
        <Panel defaultSize={50} minSize={30} maxSize={70}>
          <div className="h-full rounded-lg border bg-card overflow-hidden">
            <WidgetPreviewPanel key={previewKey} template={previewTemplate} groupBy={reference.name} />
          </div>
        </Panel>
      </PanelGroup>

      {/* Floating action button */}
      {selectedTemplates.length > 0 && (
        <div className="fixed bottom-6 right-6 z-50 flex flex-col items-end gap-2">
          {/* Success message */}
          {saveResult && (
            <div className="bg-success text-success-foreground px-4 py-2 rounded-lg shadow-lg text-sm animate-in fade-in slide-in-from-bottom-2">
              {saveResult.added > 0 && <span>{saveResult.added} widget{saveResult.added > 1 ? 's' : ''} ajouté{saveResult.added > 1 ? 's' : ''}</span>}
              {saveResult.added > 0 && saveResult.updated > 0 && <span>, </span>}
              {saveResult.updated > 0 && <span>{saveResult.updated} mis à jour</span>}
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
                {generating ? 'Génération...' : 'Sauvegarde...'}
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
    </div>
  )
}

function LayoutTab({ reference }: { reference: ReferenceInfo }) {
  return (
    <div className="h-[calc(100vh-280px)]">
      <LayoutEditor groupBy={reference.name} />
    </div>
  )
}
