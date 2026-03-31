/**
 * IndexConfigEditor - Main component for configuring index generator
 *
 * Provides UI for:
 * - Enabling/disabling index page
 * - Page settings (title, description, items per page)
 * - Filters configuration
 * - Display fields configuration with drag-and-drop
 * - Views configuration (grid/list)
 * - Live preview panel
 */
import { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import {
  Loader2,
  Save,
  RotateCcw,
  Settings2,
  Filter,
  LayoutList,
  Eye,
  AlertCircle,
  CheckCircle2,
  Sparkles,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Switch } from '@/components/ui/switch'
import { Card, CardContent } from '@/components/ui/card'
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from '@/components/ui/accordion'
import { Alert, AlertDescription } from '@/components/ui/alert'
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
import { Badge } from '@/components/ui/badge'
import {
  ResizableHandle,
  ResizablePanel,
  ResizablePanelGroup,
} from '@/components/ui/resizable'
import { PreviewFrame, type DeviceSize } from '@/components/ui/preview-frame'
import { useGroupIndexPreview } from '@/shared/hooks/useSiteConfig'
import { useIndexConfig, createDefaultDisplayField } from './useIndexConfig'
import { IndexFiltersConfig } from './IndexFiltersConfig'
import { IndexDisplayFieldsConfig } from './IndexDisplayFieldsConfig'
import { DisplayFieldEditorPanel } from './DisplayFieldEditorPanel'

interface IndexConfigEditorProps {
  groupBy: string
  className?: string
}

export function IndexConfigEditor({ groupBy, className }: IndexConfigEditorProps) {
  const {
    config,
    loading,
    error,
    isDirty,
    setEnabled,
    setPageConfig,
    addFilter,
    updateFilter,
    removeFilter,
    addDisplayField,
    updateDisplayField,
    removeDisplayField,
    reorderDisplayFields,
    setViews,
    save,
    reset,
    fetchSuggestions,
    applySuggestions,
  } = useIndexConfig(groupBy)

  const { t } = useTranslation(['indexConfig', 'common'])
  const [saving, setSaving] = useState(false)
  const [saveSuccess, setSaveSuccess] = useState(false)
  const [detecting, setDetecting] = useState(false)
  const [showAutoDetectConfirm, setShowAutoDetectConfirm] = useState(false)
  const [showPreview, setShowPreview] = useState(false)
  const [previewDevice, setPreviewDevice] = useState<DeviceSize>('desktop')
  const [previewHtml, setPreviewHtml] = useState<string | null>(null)
  const [editingFieldIndex, setEditingFieldIndex] = useState<number | null>(null)
  const previewMutation = useGroupIndexPreview()

  // Load preview when enabled and showPreview is true
  useEffect(() => {
    if (showPreview && config.enabled) {
      loadPreview()
    }
  }, [showPreview, config.enabled, groupBy])

  // Function to load/refresh preview
  const loadPreview = () => {
    if (config.enabled) {
      previewMutation.mutate(
        { groupName: groupBy },
        {
          onSuccess: (data) => setPreviewHtml(data.html),
          onError: () => setPreviewHtml(null),
        }
      )
    }
  }

  // Handle save
  const handleSave = async () => {
    setSaving(true)
    setSaveSuccess(false)
    const success = await save()
    setSaving(false)
    if (success) {
      setSaveSuccess(true)
      setTimeout(() => setSaveSuccess(false), 3000)
      // Recharger la preview si elle est visible
      if (showPreview) {
        loadPreview()
      }
    }
  }

  // Handle enable toggle with auto-detection
  const handleEnableToggle = async (enabled: boolean) => {
    setEnabled(enabled)

    // If enabling and no display fields yet, auto-detect
    if (enabled && config.display_fields.length === 0) {
      await runAutoDetect()
    }
  }

  // Run auto-detection
  const runAutoDetect = async () => {
    setDetecting(true)
    const suggestions = await fetchSuggestions()
    setDetecting(false)
    if (suggestions) {
      applySuggestions(suggestions)
    }
  }

  // Handle auto-detect button click
  const handleAutoDetectClick = () => {
    // If config already has fields, show confirmation
    if (config.display_fields.length > 0 || (config.filters?.length ?? 0) > 0) {
      setShowAutoDetectConfirm(true)
    } else {
      runAutoDetect()
    }
  }

  // Confirm auto-detect (replaces existing config)
  const handleAutoDetectConfirm = () => {
    setShowAutoDetectConfirm(false)
    runAutoDetect()
  }

  // Handle add display field
  const handleAddDisplayField = () => {
    const newIndex = config.display_fields.length
    addDisplayField(createDefaultDisplayField({
      name: `field_${newIndex + 1}`,
      source: '',
    }))
    // Auto-select the new field for editing
    setEditingFieldIndex(newIndex)
    setShowPreview(false)
  }

  // Handle field selection
  const handleSelectField = (index: number) => {
    setEditingFieldIndex(index)
    setShowPreview(false)
  }

  // Handle field save from panel
  const handleSaveField = (field: Partial<typeof config.display_fields[0]>) => {
    if (editingFieldIndex !== null) {
      updateDisplayField(editingFieldIndex, field)
    }
  }

  // Handle field removal with index adjustment
  const handleRemoveField = (index: number) => {
    removeDisplayField(index)
    // If we're editing the removed field, close the editor
    if (editingFieldIndex === index) {
      setEditingFieldIndex(null)
    } else if (editingFieldIndex !== null && index < editingFieldIndex) {
      // Adjust index if a field before the edited one is removed
      setEditingFieldIndex(editingFieldIndex - 1)
    }
  }

  // Determine if side panel should be visible
  const showSidePanel = showPreview || editingFieldIndex !== null

  // Loading state or config not ready
  if (loading || !config) {
    return (
      <div className={cn('flex flex-col items-center justify-center py-12', className)}>
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        <p className="mt-4 text-sm text-muted-foreground">
          {t('loading')}
        </p>
      </div>
    )
  }

  return (
    <div className={cn('flex flex-col h-full', className)}>
      {/* Header with save button */}
      <div className="shrink-0 flex items-center justify-between p-4 border-b bg-muted/30">
        <div>
          <h2 className="text-lg font-semibold">{t('title')}</h2>
          <p className="text-sm text-muted-foreground">
            {t('collectionDescription', { groupBy })}
          </p>
        </div>
        <div className="flex items-center gap-2">
          {isDirty && (
            <Badge variant="outline" className="text-xs">
              {t('status.unsavedChanges')}
            </Badge>
          )}
          {config.enabled && (
            <>
              <Button
                variant={showPreview ? 'default' : 'outline'}
                size="sm"
                onClick={() => {
                  setShowPreview(!showPreview)
                  if (!showPreview) {
                    setEditingFieldIndex(null)
                  }
                }}
              >
                <Eye className="mr-2 h-4 w-4" />
                {t('common:actions.preview')}
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={handleAutoDetectClick}
                disabled={detecting || saving}
              >
                {detecting ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    {t('actions.detecting')}
                  </>
                ) : (
                  <>
                    <Sparkles className="mr-2 h-4 w-4" />
                    {t('actions.autoDetect')}
                  </>
                )}
              </Button>
            </>
          )}
          <Button
            variant="outline"
            size="sm"
            onClick={reset}
            disabled={!isDirty || saving}
          >
            <RotateCcw className="mr-2 h-4 w-4" />
            {t('common:actions.cancel')}
          </Button>
          <Button
            size="sm"
            onClick={handleSave}
            disabled={!isDirty || saving}
          >
            {saving ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                {t('actions.saving')}
              </>
            ) : (
              <>
                <Save className="mr-2 h-4 w-4" />
                {t('common:actions.save')}
              </>
            )}
          </Button>
        </div>
      </div>

      {/* Auto-detect confirmation dialog */}
      <AlertDialog open={showAutoDetectConfirm} onOpenChange={setShowAutoDetectConfirm}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>{t('replaceExisting')}</AlertDialogTitle>
            <AlertDialogDescription>
              {(config.filters?.length ?? 0) > 0
                ? t('confirm.replaceDescriptionWithFilters', {
                    fieldCount: config.display_fields.length,
                    filterCount: config.filters?.length ?? 0,
                  })
                : t('confirm.replaceDescription', {
                    fieldCount: config.display_fields.length,
                  })}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>{t('common:actions.cancel')}</AlertDialogCancel>
            <AlertDialogAction onClick={handleAutoDetectConfirm}>
              {t('actions.replace')}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* Success/Error messages */}
      {saveSuccess && (
        <Alert className="mx-4 mt-4 border-success/50 bg-success/10">
          <CheckCircle2 className="h-4 w-4 text-success" />
          <AlertDescription className="text-success">
            {t('status.saveSuccess')}
          </AlertDescription>
        </Alert>
      )}

      {error && (
        <Alert variant="destructive" className="mx-4 mt-4">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {/* Main content with optional side panel */}
      <ResizablePanelGroup direction="horizontal" className="flex-1">
        <ResizablePanel defaultSize={showSidePanel ? 55 : 100} minSize={40}>
          <div className="h-full overflow-auto p-4">
            <div className="space-y-4 max-w-4xl">
          {/* Enable/disable toggle */}
          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div className="space-y-0.5">
                  <Label className="text-base">{t('toggle.label')}</Label>
                  <p className="text-sm text-muted-foreground">
                    {detecting
                      ? t('toggle.descriptionDetecting')
                      : t('toggle.description')
                    }
                  </p>
                </div>
                {detecting ? (
                  <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
                ) : (
                  <Switch
                    checked={config.enabled}
                    onCheckedChange={handleEnableToggle}
                    disabled={detecting}
                  />
                )}
              </div>
            </CardContent>
          </Card>

          {/* Only show rest of config if enabled */}
          {config.enabled && (
            <Accordion type="multiple" defaultValue={['page', 'fields']} className="space-y-2">
              {/* Page settings */}
              <AccordionItem value="page" className="border rounded-lg">
                <AccordionTrigger className="px-4 py-3 hover:no-underline">
                  <div className="flex items-center gap-2">
                    <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-blue-50 border border-blue-200">
                      <Settings2 className="h-4 w-4 text-blue-600" />
                    </div>
                    <div className="text-left">
                      <span className="font-medium">{t('sections.page.title')}</span>
                      <p className="text-xs text-muted-foreground font-normal">
                        {t('sections.page.description')}
                      </p>
                    </div>
                  </div>
                </AccordionTrigger>
                <AccordionContent className="px-4 pb-4">
                  <div className="space-y-4">
                    <div className="space-y-2">
                      <Label htmlFor="page-title">{t('pageSettings.title')}</Label>
                      <Input
                        id="page-title"
                        value={config.page_config.title}
                        onChange={(e) => setPageConfig({ title: e.target.value })}
                        placeholder={t('pageSettings.titlePlaceholder')}
                      />
                    </div>

                    <div className="space-y-2">
                      <Label htmlFor="page-description">{t('pageSettings.description')}</Label>
                      <Textarea
                        id="page-description"
                        value={config.page_config.description || ''}
                        onChange={(e) => setPageConfig({ description: e.target.value || undefined })}
                        placeholder={t('pageSettings.descriptionPlaceholder')}
                        rows={2}
                      />
                    </div>

                    <div className="space-y-2">
                      <Label htmlFor="items-per-page">{t('pageSettings.itemsPerPage')}</Label>
                      <Input
                        id="items-per-page"
                        type="number"
                        min={1}
                        max={100}
                        value={config.page_config.items_per_page}
                        onChange={(e) => setPageConfig({ items_per_page: parseInt(e.target.value) || 24 })}
                      />
                    </div>
                  </div>
                </AccordionContent>
              </AccordionItem>

              {/* Filters */}
              <AccordionItem value="filters" className="border rounded-lg">
                <AccordionTrigger className="px-4 py-3 hover:no-underline">
                  <div className="flex items-center gap-2">
                    <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-amber-50 border border-amber-200">
                      <Filter className="h-4 w-4 text-amber-600" />
                    </div>
                    <div className="text-left">
                      <span className="font-medium">{t('sections.filters.title')}</span>
                      <p className="text-xs text-muted-foreground font-normal">
                        {t('sections.filters.description')}
                        {(config.filters?.length ?? 0) > 0 && (
                          <Badge variant="secondary" className="ml-2 h-5 px-1.5">
                            {config.filters?.length}
                          </Badge>
                        )}
                      </p>
                    </div>
                  </div>
                </AccordionTrigger>
                <AccordionContent className="px-4 pb-4">
                  <IndexFiltersConfig
                    filters={config.filters || []}
                    onAdd={addFilter}
                    onUpdate={updateFilter}
                    onRemove={removeFilter}
                  />
                </AccordionContent>
              </AccordionItem>

              {/* Display fields */}
              <AccordionItem value="fields" className="border rounded-lg">
                <AccordionTrigger className="px-4 py-3 hover:no-underline">
                  <div className="flex items-center gap-2">
                    <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-emerald-50 border border-emerald-200">
                      <LayoutList className="h-4 w-4 text-emerald-600" />
                    </div>
                    <div className="text-left">
                      <span className="font-medium">{t('sections.fields.title')}</span>
                      <p className="text-xs text-muted-foreground font-normal">
                        {t('sections.fields.description')}
                        {config.display_fields.length > 0 && (
                          <Badge variant="secondary" className="ml-2 h-5 px-1.5">
                            {config.display_fields.length}
                          </Badge>
                        )}
                      </p>
                    </div>
                  </div>
                </AccordionTrigger>
                <AccordionContent className="px-4 pb-4">
                  <IndexDisplayFieldsConfig
                    fields={config.display_fields}
                    selectedIndex={editingFieldIndex}
                    onAdd={handleAddDisplayField}
                    onSelect={handleSelectField}
                    onRemove={handleRemoveField}
                    onReorder={reorderDisplayFields}
                  />
                </AccordionContent>
              </AccordionItem>

              {/* Views */}
              <AccordionItem value="views" className="border rounded-lg">
                <AccordionTrigger className="px-4 py-3 hover:no-underline">
                  <div className="flex items-center gap-2">
                    <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-violet-50 border border-violet-200">
                      <Eye className="h-4 w-4 text-violet-600" />
                    </div>
                    <div className="text-left">
                      <span className="font-medium">{t('sections.views.title')}</span>
                      <p className="text-xs text-muted-foreground font-normal">
                        {t('sections.views.description')}
                      </p>
                    </div>
                  </div>
                </AccordionTrigger>
                <AccordionContent className="px-4 pb-4">
                  <div className="space-y-4">
                    <div className="flex items-center justify-between py-2">
                      <div className="space-y-0.5">
                        <Label>{t('views.grid.label')}</Label>
                        <p className="text-xs text-muted-foreground">
                          {t('views.grid.description')}
                        </p>
                      </div>
                      <Switch
                        checked={config.views?.some(v => v.type === 'grid') ?? true}
                        onCheckedChange={(checked) => {
                          const views = [...(config.views || [])].filter(v => v.type !== 'grid')
                          if (checked) {
                            views.push({ type: 'grid', default: views.length === 0 })
                          }
                          setViews(views.length > 0 ? views : [{ type: 'grid', default: true }])
                        }}
                      />
                    </div>

                    <div className="flex items-center justify-between py-2">
                      <div className="space-y-0.5">
                        <Label>{t('views.list.label')}</Label>
                        <p className="text-xs text-muted-foreground">
                          {t('views.list.description')}
                        </p>
                      </div>
                      <Switch
                        checked={config.views?.some(v => v.type === 'list') ?? false}
                        onCheckedChange={(checked) => {
                          const views = [...(config.views || [])].filter(v => v.type !== 'list')
                          if (checked) {
                            views.push({ type: 'list', default: views.length === 0 })
                          }
                          setViews(views.length > 0 ? views : [{ type: 'grid', default: true }])
                        }}
                      />
                    </div>

                    {(config.views?.length ?? 0) > 1 && (
                      <div className="space-y-2 pt-2 border-t">
                        <Label>{t('views.defaultLabel')}</Label>
                        <div className="flex gap-2">
                          {config.views?.map((view, index) => (
                            <Button
                              key={view.type}
                              variant={view.default ? 'default' : 'outline'}
                              size="sm"
                              onClick={() => {
                                const newViews = config.views?.map((v, i) => ({
                                  ...v,
                                  default: i === index,
                                })) || []
                                setViews(newViews)
                              }}
                            >
                              {view.type === 'grid' ? t('common:display.grid') : t('common:display.list')}
                            </Button>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                </AccordionContent>
              </AccordionItem>
            </Accordion>
          )}
            </div>
          </div>
        </ResizablePanel>

        {/* Side panel: Field editor or Preview */}
        {showSidePanel && (
          <>
            <ResizableHandle withHandle />
            <ResizablePanel defaultSize={45} minSize={30}>
              {editingFieldIndex !== null && config.display_fields[editingFieldIndex] ? (
                <DisplayFieldEditorPanel
                  field={config.display_fields[editingFieldIndex]}
                  fieldIndex={editingFieldIndex}
                  onSave={handleSaveField}
                  onClose={() => setEditingFieldIndex(null)}
                />
              ) : showPreview ? (
                <PreviewFrame
                  html={previewHtml}
                  isLoading={previewMutation.isPending}
                  device={previewDevice}
                  onDeviceChange={setPreviewDevice}
                  onRefresh={loadPreview}
                  onClose={() => setShowPreview(false)}
                  title={`${t('common:actions.preview')} - ${groupBy}`}
                  loadingMessage={t('indexConfig:preview.generating')}
                  emptyMessage={t('indexConfig:preview.noPreview')}
                />
              ) : null}
            </ResizablePanel>
          </>
        )}
      </ResizablePanelGroup>
    </div>
  )
}
