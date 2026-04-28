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
import { useState, useEffect, useCallback, useRef } from 'react'
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
import { Switch } from '@/components/ui/switch'
import { LocalizedInput } from '@/components/ui/localized-input'
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
import type { IndexFieldSuggestions, SuggestedDisplayField } from './useIndexConfig'
import { IndexFiltersConfig } from './IndexFiltersConfig'
import { IndexDisplayFieldsConfig } from './IndexDisplayFieldsConfig'
import { DisplayFieldEditorPanel } from './DisplayFieldEditorPanel'

interface IndexConfigEditorProps {
  groupBy: string
  className?: string
}

export function IndexConfigEditor({ groupBy, className }: IndexConfigEditorProps) {
  return <IndexConfigEditorContent key={groupBy} groupBy={groupBy} className={className} />
}

function IndexConfigEditorContent({ groupBy, className }: IndexConfigEditorProps) {
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
  const [availableFields, setAvailableFields] = useState<SuggestedDisplayField[]>([])
  const [loadingAvailableFields, setLoadingAvailableFields] = useState(false)
  const [availableFieldsError, setAvailableFieldsError] = useState<string | null>(null)
  const [fieldEditorIsValid, setFieldEditorIsValid] = useState(true)
  const activeGroupRef = useRef(groupBy)
  const mountedRef = useRef(true)
  const {
    mutate: requestGroupIndexPreview,
    isPending: isPreviewPending,
  } = useGroupIndexPreview()
  const canSave = isDirty && !saving && fieldEditorIsValid
  const needsSaveAttention = canSave

  useEffect(() => {
    mountedRef.current = true
    activeGroupRef.current = groupBy

    return () => {
      mountedRef.current = false
    }
  }, [groupBy])

  const rememberAvailableFields = useCallback((suggestions: IndexFieldSuggestions) => {
    setAvailableFields(
      suggestions.available_fields?.length
        ? suggestions.available_fields
        : suggestions.display_fields
    )
    setAvailableFieldsError(null)
  }, [])

  const ensureAvailableFields = useCallback(async () => {
    if (availableFields.length > 0 || loadingAvailableFields) {
      return
    }

    const requestedGroup = groupBy
    setLoadingAvailableFields(true)
    setAvailableFieldsError(null)

    try {
      const suggestions = await fetchSuggestions()
      if (!mountedRef.current || activeGroupRef.current !== requestedGroup) {
        return
      }

      if (suggestions) {
        rememberAvailableFields(suggestions)
      } else {
        setAvailableFieldsError(t('fieldEditor.fieldPickerLoadError'))
      }
    } catch {
      if (mountedRef.current && activeGroupRef.current === requestedGroup) {
        setAvailableFieldsError(t('fieldEditor.fieldPickerLoadError'))
      }
    } finally {
      if (mountedRef.current && activeGroupRef.current === requestedGroup) {
        setLoadingAvailableFields(false)
      }
    }
  }, [
    availableFields.length,
    fetchSuggestions,
    groupBy,
    loadingAvailableFields,
    rememberAvailableFields,
    t,
  ])

  const loadPreview = useCallback(() => {
    if (!config.enabled) {
      return
    }

    requestGroupIndexPreview(
      {
        groupName: groupBy,
        request: {
          index_config: {
            ...config,
            filters: config.filters ?? [],
            views: config.views ?? [{ type: 'grid', default: true }],
          },
        },
      },
      {
        onSuccess: (data) => setPreviewHtml(data.html),
        onError: () => setPreviewHtml(null),
      }
    )
  }, [config, groupBy, requestGroupIndexPreview])

  // Load preview when enabled and showPreview is true
  useEffect(() => {
    if (showPreview && config.enabled) {
      loadPreview()
    }
  }, [config.enabled, loadPreview, showPreview])

  // Handle save
  const handleSave = async () => {
    if (!fieldEditorIsValid) return
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
    const requestedGroup = groupBy
    setDetecting(true)
    const suggestions = await fetchSuggestions()
    if (!mountedRef.current || activeGroupRef.current !== requestedGroup) {
      return
    }
    setDetecting(false)
    if (suggestions) {
      rememberAvailableFields(suggestions)
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
    setFieldEditorIsValid(true)
    setEditingFieldIndex(newIndex)
    setShowPreview(false)
    void ensureAvailableFields()
  }

  // Handle field selection
  const handleSelectField = (index: number) => {
    setFieldEditorIsValid(true)
    setEditingFieldIndex(index)
    setShowPreview(false)
    void ensureAvailableFields()
  }

  // Handle field changes from panel
  const handleChangeField = (field: Partial<typeof config.display_fields[0]>) => {
    if (editingFieldIndex !== null) {
      updateDisplayField(editingFieldIndex, field)
    }
  }

  // Handle field removal with index adjustment
  const handleRemoveField = (index: number) => {
    removeDisplayField(index)
    // If we're editing the removed field, close the editor
    if (editingFieldIndex === index) {
      setFieldEditorIsValid(true)
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
      <div className="shrink-0 flex items-center justify-between px-6 py-3 border-b">
        <div>
          <h2 className="text-base font-medium">{t('title')}</h2>
          <p className="text-xs text-muted-foreground">
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
                variant="outline"
                size="sm"
                className={cn(
                  showPreview &&
                    'border-primary bg-primary text-primary-foreground hover:bg-primary/90 hover:text-primary-foreground'
                )}
                onClick={() => {
                  setShowPreview(!showPreview)
                  if (!showPreview) {
                    setFieldEditorIsValid(true)
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
                <span className="grid items-center">
                  <span
                    aria-hidden="true"
                    className="invisible col-start-1 row-start-1 flex items-center"
                  >
                    <Sparkles className="mr-2 h-4 w-4" />
                    {t('actions.autoDetect')}
                  </span>
                  <span
                    aria-hidden="true"
                    className="invisible col-start-1 row-start-1 flex items-center"
                  >
                    <Loader2 className="mr-2 h-4 w-4" />
                    {t('actions.detecting')}
                  </span>
                  <span className="col-start-1 row-start-1 flex items-center justify-center">
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
                  </span>
                </span>
              </Button>
            </>
          )}
          <Button
            variant="outline"
            size="sm"
            onClick={() => {
              reset()
              setFieldEditorIsValid(true)
            }}
            disabled={!isDirty || saving}
          >
            <RotateCcw className="mr-2 h-4 w-4" />
            {t('common:actions.cancel')}
          </Button>
          <Button
            size="sm"
            onClick={handleSave}
            disabled={!canSave}
            className={cn(
              'relative',
              needsSaveAttention &&
                'animate-pulse bg-amber-500 text-white shadow-lg shadow-amber-500/25 hover:bg-amber-600 focus-visible:ring-amber-300'
            )}
          >
            <span className="grid items-center">
              <span
                aria-hidden="true"
                className="invisible col-start-1 row-start-1 flex items-center"
              >
                <Save className="mr-2 h-4 w-4" />
                {t('common:actions.save')}
              </span>
              <span
                aria-hidden="true"
                className="invisible col-start-1 row-start-1 flex items-center"
              >
                <Loader2 className="mr-2 h-4 w-4" />
                {t('actions.saving')}
              </span>
              <span className="col-start-1 row-start-1 flex items-center justify-center">
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
              </span>
            </span>
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
        <ResizablePanel defaultSize={showSidePanel ? "55%" : "100%"} minSize="40%">
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
                      <LocalizedInput
                        value={config.page_config.title}
                        onChange={(value) => setPageConfig({ title: value || '' })}
                        placeholder={t('pageSettings.titlePlaceholder')}
                      />
                    </div>

                    <div className="space-y-2">
                      <Label htmlFor="page-description">{t('pageSettings.description')}</Label>
                      <LocalizedInput
                        value={config.page_config.description || ''}
                        onChange={(value) => setPageConfig({ description: value || undefined })}
                        placeholder={t('pageSettings.descriptionPlaceholder')}
                        multiline
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
            <ResizablePanel defaultSize="45%" minSize="30%">
              {editingFieldIndex !== null && config.display_fields[editingFieldIndex] ? (
                <DisplayFieldEditorPanel
                  key={editingFieldIndex}
                  field={config.display_fields[editingFieldIndex]}
                  fieldIndex={editingFieldIndex}
                  availableFields={availableFields}
                  loadingAvailableFields={loadingAvailableFields}
                  availableFieldsError={availableFieldsError}
                  onLoadAvailableFields={ensureAvailableFields}
                  onChange={handleChangeField}
                  onValidityChange={setFieldEditorIsValid}
                  onClose={() => {
                    setFieldEditorIsValid(true)
                    setEditingFieldIndex(null)
                  }}
                />
              ) : showPreview ? (
                <PreviewFrame
                  html={previewHtml}
                  isLoading={isPreviewPending}
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
