import { useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'
import {
  ChevronRight,
  Database,
  FileJson,
  Leaf,
  Loader2,
  RotateCcw,
  Save,
  Settings,
  Sparkles,
} from 'lucide-react'
import { toast } from 'sonner'

import { JsonSchemaForm } from '@/components/forms'
import type { FormValues } from '@/components/forms/formSchemaTypes'
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from '@/components/ui/accordion'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Switch } from '@/components/ui/switch'
import { cn } from '@/lib/utils'
import {
  useApiExportAutoConfig,
  useApiExportGroupConfig,
  useApiExportPreview,
  useApiExportSuggestions,
  useUpdateApiExportGroupConfig,
  type ApiExportGroupConfig,
  type ApiExportTargetSummary,
} from '@/features/collections/hooks/useApiExportConfigs'

import {
  applyApiExportAutoConfigProposal,
  isJsonArray,
  isJsonObject,
  normalizeApiExportGroupConfig,
} from './apiExportConfigUtils'
import { ApiFieldMappingsEditor } from './ApiFieldMappingsEditor'
import { AutoConfigReviewDialog } from './AutoConfigReviewDialog'
import { DwcMappingEditor } from './DwcMappingEditor'
import { JsonOptionsEditor } from './JsonOptionsEditor'
import { SynchronizedJsonConfigSection } from './SynchronizedJsonConfigSection'

interface ExportCardProps {
  exportTarget: ApiExportTargetSummary
  groupBy: string
}

function buildAvailableFields(
  suggestions: ReturnType<typeof useApiExportSuggestions>['data']
) {
  const values = new Set<string>(['occurrences'])
  const fields = suggestions?.available_fields ?? suggestions?.display_fields ?? []
  fields.forEach((field) => {
    values.add(field.source)
    values.add(field.name)
  })
  return Array.from(values).sort()
}

function buildDefaultLocalConfig(config: ApiExportGroupConfig): ApiExportGroupConfig {
  return normalizeApiExportGroupConfig(config)
}

function omitEmptyJsonOptions(value: Record<string, unknown>) {
  return Object.keys(value).length > 0 ? value : undefined
}

/** Generate a natural language summary for this export. */
function formatExportSummary(
  config: ApiExportGroupConfig | null,
  suggestions: ReturnType<typeof useApiExportSuggestions>['data'],
  t: (key: string, opts?: Record<string, unknown>) => string
): string {
  if (!config) return ''
  if (!config.enabled) return t('collectionPanel.api.exportSummary.disabled')

  const count = suggestions?.total_entities ?? 0
  const isDwc = config.transformer_plugin === 'niamoto_to_dwc_occurrence'

  if (isDwc) {
    const termCount = Object.keys(
      (config.transformer_params?.mapping as Record<string, unknown>) ?? {}
    ).length
    return t('collectionPanel.api.exportSummary.dwc', { termCount, count })
  }

  if (config.detail?.pass_through !== false) {
    return t('collectionPanel.api.exportSummary.simplePassThrough', { count })
  }

  const fieldCount = config.detail?.fields?.length ?? 0
  return t('collectionPanel.api.exportSummary.simpleFields', { fieldCount, count })
}

export function ExportCard({ exportTarget, groupBy }: ExportCardProps) {
  const { t } = useTranslation(['sources', 'common'])
  const {
    data: serverConfig,
    isLoading,
    error,
    refetch,
  } = useApiExportGroupConfig(exportTarget.name, groupBy)
  const suggestionsQuery = useApiExportSuggestions(exportTarget.name, groupBy)

  if (isLoading || !serverConfig) {
    return (
      <Card>
        <CardContent className="flex min-h-[100px] items-center justify-center">
          <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
        </CardContent>
      </Card>
    )
  }

  if (error) {
    return (
      <Card>
        <CardHeader>
          <div className="text-sm font-medium">{exportTarget.name}</div>
          <p className="text-xs text-destructive">
            {error instanceof Error ? error.message : t('collectionPanel.api.loadFailed')}
          </p>
        </CardHeader>
      </Card>
    )
  }

  return (
    <ExportCardForm
      key={`${exportTarget.name}:${groupBy}:${JSON.stringify(serverConfig)}`}
      exportTarget={exportTarget}
      groupBy={groupBy}
      serverConfig={serverConfig}
      suggestions={suggestionsQuery.data}
      onRefetch={refetch}
    />
  )
}

interface ExportCardFormProps {
  exportTarget: ApiExportTargetSummary
  groupBy: string
  serverConfig: ApiExportGroupConfig
  suggestions: ReturnType<typeof useApiExportSuggestions>['data']
  onRefetch: () => Promise<unknown>
}

function ExportCardForm({
  exportTarget,
  groupBy,
  serverConfig,
  suggestions,
  onRefetch,
}: ExportCardFormProps) {
  const { t } = useTranslation(['sources', 'common'])
  const saveMutation = useUpdateApiExportGroupConfig(exportTarget.name, groupBy)
  const autoConfigQuery = useApiExportAutoConfig(exportTarget.name, groupBy, false)
  const [localConfig, setLocalConfig] = useState<ApiExportGroupConfig>(
    buildDefaultLocalConfig(serverConfig)
  )
  const [resetCounter, setResetCounter] = useState(0)
  const [autoConfigOpen, setAutoConfigOpen] = useState(false)

  const availableFields = useMemo(
    () => buildAvailableFields(suggestions),
    [suggestions]
  )

  const isDirty =
    JSON.stringify(buildDefaultLocalConfig(serverConfig)) !== JSON.stringify(localConfig)

  const isDwcTransformer =
    localConfig.transformer_plugin === 'niamoto_to_dwc_occurrence'
  const isPassThrough = localConfig.detail?.pass_through !== false
  const dwcMapping =
    (localConfig.transformer_params?.mapping as Record<string, unknown> | undefined) ??
    {}
  const hasDwcMapping = Object.keys(dwcMapping).length > 0

  const indexPreviewQuery = useApiExportPreview(
    exportTarget.name,
    groupBy,
    'index',
    localConfig,
    localConfig.enabled
  )
  const detailPreviewQuery = useApiExportPreview(
    exportTarget.name,
    groupBy,
    'detail',
    localConfig,
    localConfig.enabled && (isDwcTransformer ? hasDwcMapping : !isPassThrough)
  )

  const summary = formatExportSummary(localConfig, suggestions, t)

  const updateLocalConfig = (
    updater: (current: ApiExportGroupConfig) => ApiExportGroupConfig
  ) => {
    setLocalConfig((current) => (current ? updater(current) : current))
  }

  const handleSave = async () => {
    try {
      await saveMutation.mutateAsync(localConfig)
      toast.success(
        t('collectionPanel.api.groupConfigSaved', { exportName: exportTarget.name, groupBy })
      )
      await onRefetch()
    } catch (mutationError) {
      toast.error(
        mutationError instanceof Error
          ? mutationError.message
          : t('collectionPanel.api.saveFailed')
      )
    }
  }

  const handleReset = () => {
    setLocalConfig(buildDefaultLocalConfig(serverConfig))
    setResetCounter((c) => c + 1)
  }

  const handleOpenAutoConfig = () => {
    setAutoConfigOpen(true)
    void autoConfigQuery.refetch()
  }

  const handleApplyAutoConfig = (sectionKeys: string[]) => {
    if (!autoConfigQuery.data) return
    setLocalConfig((current) =>
      applyApiExportAutoConfigProposal(current, autoConfigQuery.data, sectionKeys)
    )
    setAutoConfigOpen(false)
  }

  const indexFieldCount = localConfig.index?.fields?.length ?? 0
  const dwcTermCount = Object.keys(dwcMapping).length

  return (
    <Card className="gap-0 py-0">
      {/* ── Header: name + summary + toggle ── */}
      <CardHeader className="sticky top-0 z-20 rounded-t-theme-lg border-b bg-card/95 px-4 py-3 shadow-sm backdrop-blur supports-[backdrop-filter]:bg-card/90">
        <div className="flex items-start justify-between gap-4">
          <div className="min-w-0 flex-1 space-y-1">
            <div className="flex items-center gap-2">
              {isDwcTransformer ? (
                <Leaf className="h-4 w-4 text-green-600" />
              ) : (
                <FileJson className="h-4 w-4 text-blue-500" />
              )}
              <span className="text-sm font-semibold">{exportTarget.name}</span>
              {localConfig.enabled && (
                <Badge variant="success" className="text-[10px]">
                  {t('collectionPanel.api.enabledForGroup')}
                </Badge>
              )}
              {!exportTarget.enabled && (
                <Badge variant="outline" className="text-[10px]">
                  {t('collectionPanel.api.globallyDisabled')}
                </Badge>
              )}
              {isDirty && (
                <Badge variant="outline" className="text-[10px] border-amber-300 text-amber-700">
                  {t('collectionPanel.api.unsaved')}
                </Badge>
              )}
            </div>
            <p className="text-xs text-muted-foreground">{summary}</p>
          </div>

          <Switch
            checked={localConfig.enabled}
            onCheckedChange={(enabled) =>
              updateLocalConfig((current) => ({ ...current, enabled }))
            }
          />
        </div>

        {/* Save / Cancel — only when dirty */}
        {isDirty && (
          <div className="flex flex-wrap items-center gap-2 pt-2">
            <Button
              variant="outline"
              size="sm"
              onClick={handleReset}
              disabled={saveMutation.isPending}
            >
              <RotateCcw className="mr-1.5 h-3.5 w-3.5" />
              {t('common:actions.reset')}
            </Button>
            <Button
              size="sm"
              onClick={handleSave}
              disabled={saveMutation.isPending}
              className={cn(
                'relative',
                !saveMutation.isPending &&
                  'animate-pulse bg-amber-500 text-white shadow-lg shadow-amber-500/25 hover:bg-amber-600 focus-visible:ring-amber-300'
              )}
            >
              {saveMutation.isPending ? (
                <Loader2 className="mr-1.5 h-3.5 w-3.5 animate-spin" />
              ) : (
                <Save className="mr-1.5 h-3.5 w-3.5" />
              )}
              {t('common:actions.save')}
            </Button>
          </div>
        )}
        {localConfig.enabled && (
          <div className="pt-2">
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={handleOpenAutoConfig}
              disabled={autoConfigQuery.isFetching}
            >
              {autoConfigQuery.isFetching ? (
                <Loader2 className="mr-1.5 h-3.5 w-3.5 animate-spin" />
              ) : (
                <Sparkles className="mr-1.5 h-3.5 w-3.5" />
              )}
              {t('collectionPanel.api.autoConfig.button')}
            </Button>
          </div>
        )}
      </CardHeader>

      {/* ── Body: collapsible sections ── */}
      {localConfig.enabled && (
        <CardContent className="px-4 py-4">
          <Accordion type="multiple" className="space-y-2">
            {/* ── Main: Index fields ── */}
            <AccordionItem value="index" className="rounded-lg border">
              <AccordionTrigger className="px-3 py-2 text-sm hover:no-underline">
                <div className="flex items-center gap-2">
                  <ChevronRight className="h-3.5 w-3.5 shrink-0 transition-transform duration-200" />
                  <span className="font-medium">
                    {t('collectionPanel.api.indexFields')}
                  </span>
                  <Badge variant="secondary" className="text-[10px]">
                    {indexFieldCount > 0
                      ? t('collectionPanel.api.fieldCount', { count: indexFieldCount })
                      : t('collectionPanel.api.sectionDefault')}
                  </Badge>
                </div>
              </AccordionTrigger>
              <AccordionContent className="px-3 pb-3">
                <p className="mb-3 text-xs text-muted-foreground">
                  {t('collectionPanel.api.sectionHelp.indexFields', {
                    groupBy,
                  })}
                </p>
                <SynchronizedJsonConfigSection
                  name={`${exportTarget.name}-${groupBy}-index-fields`}
                  value={localConfig.index?.fields ?? []}
                  validate={isJsonArray}
                  jsonLabel={t('collectionPanel.api.indexFields')}
                  showJsonPreview
                  jsonPreviewValue={indexPreviewQuery.data?.preview}
                  jsonPreviewLoading={indexPreviewQuery.isFetching}
                  jsonPreviewError={
                    indexPreviewQuery.error instanceof Error
                      ? indexPreviewQuery.error.message
                      : null
                  }
                  onChange={(fields) =>
                    updateLocalConfig((current) => ({
                      ...current,
                      index: { fields: fields as Array<string | Record<string, unknown>> },
                    }))
                  }
                >
                  <ApiFieldMappingsEditor
                    value={localConfig.index?.fields ?? []}
                    suggestions={suggestions?.display_fields ?? []}
                    sourceFields={
                      suggestions?.available_fields ?? suggestions?.display_fields ?? []
                    }
                    onChange={(fields) =>
                      updateLocalConfig((current) => ({
                        ...current,
                        index: { fields },
                      }))
                    }
                  />
                </SynchronizedJsonConfigSection>
              </AccordionContent>
            </AccordionItem>

            {/* ── Main: Detail / pass-through ── */}
            {!localConfig.transformer_plugin && (
              <AccordionItem value="detail" className="rounded-lg border">
                <AccordionTrigger className="px-3 py-2 text-sm hover:no-underline">
                  <div className="flex items-center gap-2">
                    <ChevronRight className="h-3.5 w-3.5 shrink-0 transition-transform duration-200" />
                    <span className="font-medium">
                      {t('collectionPanel.api.detailFields')}
                    </span>
                    <Badge variant="secondary" className="text-[10px]">
                      {isPassThrough
                        ? t('collectionPanel.api.passThrough')
                        : t('collectionPanel.api.fieldCount', {
                            count: localConfig.detail?.fields?.length ?? 0,
                          })}
                    </Badge>
                  </div>
                </AccordionTrigger>
                <AccordionContent className="px-3 pb-3">
                  <p className="mb-3 text-xs text-muted-foreground">
                    {t('collectionPanel.api.sectionHelp.detailFields', { groupBy })}
                  </p>
                  <div className="mb-3 flex items-center justify-between gap-2">
                    <Label className="text-sm">{t('collectionPanel.api.passThrough')}</Label>
                    <Switch
                      checked={localConfig.detail?.pass_through ?? true}
                      onCheckedChange={(passThrough) =>
                        updateLocalConfig((current) => ({
                          ...current,
                          detail: { ...current.detail, pass_through: passThrough },
                        }))
                      }
                    />
                  </div>
                  {!isPassThrough && (
                    <SynchronizedJsonConfigSection
                      name={`${exportTarget.name}-${groupBy}-detail-fields`}
                      value={localConfig.detail?.fields ?? []}
                      validate={isJsonArray}
                      jsonLabel={t('collectionPanel.api.detailFields')}
                      showJsonPreview
                      jsonPreviewValue={detailPreviewQuery.data?.preview}
                      jsonPreviewLoading={detailPreviewQuery.isFetching}
                      jsonPreviewError={
                        detailPreviewQuery.error instanceof Error
                          ? detailPreviewQuery.error.message
                          : null
                      }
                      onChange={(fields) =>
                        updateLocalConfig((current) => ({
                          ...current,
                          detail: {
                            ...current.detail,
                            fields: fields as Array<string | Record<string, unknown>>,
                          },
                        }))
                      }
                    >
                      <ApiFieldMappingsEditor
                        value={localConfig.detail?.fields ?? []}
                        suggestions={suggestions?.display_fields ?? []}
                        sourceFields={
                          suggestions?.available_fields ?? suggestions?.display_fields ?? []
                        }
                        onChange={(fields) =>
                          updateLocalConfig((current) => ({
                            ...current,
                            detail: {
                              ...current.detail,
                              fields,
                            },
                          }))
                        }
                      />
                    </SynchronizedJsonConfigSection>
                  )}
                </AccordionContent>
              </AccordionItem>
            )}

            {/* ── Main: DwC mapping ── */}
            {isDwcTransformer && (
              <AccordionItem value="dwc" className="rounded-lg border">
                <AccordionTrigger className="px-3 py-2 text-sm hover:no-underline">
                  <div className="flex items-center gap-2">
                    <ChevronRight className="h-3.5 w-3.5 shrink-0 transition-transform duration-200" />
                    <span className="font-medium">
                      {t('collectionPanel.api.dwcMapping')}
                    </span>
                    <Badge variant="secondary" className="text-[10px]">
                      {dwcTermCount > 0
                        ? t('collectionPanel.api.termCount', { count: dwcTermCount })
                        : t('collectionPanel.api.sectionDefault')}
                    </Badge>
                  </div>
                </AccordionTrigger>
                <AccordionContent className="px-3 pb-3">
                  <p className="mb-3 text-xs text-muted-foreground">
                    {t('collectionPanel.api.sectionHelp.dwcMapping')}
                  </p>
                  <SynchronizedJsonConfigSection
                    name={`${exportTarget.name}-${groupBy}-dwc-mapping`}
                    value={
                      dwcMapping
                    }
                    validate={isJsonObject}
                    jsonLabel={t('collectionPanel.api.dwcMapping')}
                    showJsonPreview
                    jsonPreviewLabel={t('collectionPanel.api.dwcJsonPreview')}
                    jsonPreviewValue={
                      hasDwcMapping ? detailPreviewQuery.data?.preview : []
                    }
                    jsonPreviewLoading={detailPreviewQuery.isFetching}
                    jsonPreviewError={
                      detailPreviewQuery.error instanceof Error
                        ? detailPreviewQuery.error.message
                        : null
                    }
                    onChange={(mapping) =>
                      updateLocalConfig((current) => ({
                        ...current,
                        transformer_plugin:
                          current.transformer_plugin || 'niamoto_to_dwc_occurrence',
                        transformer_params: {
                          ...(current.transformer_params ?? {}),
                          mapping: mapping as Record<string, unknown>,
                        },
                      }))
                    }
                  >
                    <DwcMappingEditor
                      value={dwcMapping}
                      sourceFields={availableFields}
                      onChange={(mapping) =>
                        updateLocalConfig((current) => ({
                          ...current,
                          transformer_plugin:
                            current.transformer_plugin || 'niamoto_to_dwc_occurrence',
                          transformer_params: {
                            ...(current.transformer_params ?? {}),
                            mapping,
                          },
                        }))
                      }
                    />
                  </SynchronizedJsonConfigSection>
                </AccordionContent>
              </AccordionItem>
            )}

            {/* ── Advanced: Transformer params ── */}
            {localConfig.transformer_plugin && (
              <AccordionItem
                value="transformer"
                className="rounded-lg border border-dashed opacity-70"
              >
                <AccordionTrigger className="px-3 py-2 text-sm hover:no-underline">
                  <div className="flex items-center gap-2">
                    <Settings className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
                    <span className="font-medium text-muted-foreground">
                      {t('collectionPanel.api.transformerParams')}
                    </span>
                  </div>
                </AccordionTrigger>
                <AccordionContent className="px-3 pb-3">
                  <JsonSchemaForm
                    key={`transformer-${exportTarget.name}-${groupBy}-${resetCounter}`}
                    pluginId={localConfig.transformer_plugin}
                    groupBy={groupBy}
                    showTitle={false}
                    hiddenFields={isDwcTransformer ? ['mapping'] : []}
                    initialValues={(localConfig.transformer_params ?? {}) as FormValues}
                    availableFields={availableFields}
                    onChange={(transformerParams) =>
                      updateLocalConfig((current) => ({
                        ...current,
                        transformer_plugin:
                          current.transformer_plugin || 'niamoto_to_dwc_occurrence',
                        transformer_params: {
                          ...(current.transformer_params ?? {}),
                          ...transformerParams,
                        },
                      }))
                    }
                  />
                </AccordionContent>
              </AccordionItem>
            )}

            {/* ── Advanced: Data source + JSON overrides ── */}
            <AccordionItem
              value="advanced"
              className="rounded-lg border border-dashed opacity-70"
            >
              <AccordionTrigger className="px-3 py-2 text-sm hover:no-underline">
                <div className="flex items-center gap-2">
                  <Database className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
                  <span className="font-medium text-muted-foreground">
                    {t('collectionPanel.api.jsonOverrides')}
                  </span>
                </div>
              </AccordionTrigger>
              <AccordionContent className="space-y-4 px-3 pb-3">
                <p className="text-xs text-muted-foreground">
                  {t('collectionPanel.api.sectionHelp.advancedOptions')}
                </p>
                <div className="space-y-2">
                  <Label>{t('collectionPanel.api.dataSource')}</Label>
                  <Input
                    value={localConfig.data_source || ''}
                    onChange={(event) =>
                      updateLocalConfig((current) => ({
                        ...current,
                        data_source: event.target.value || undefined,
                      }))
                    }
                    placeholder={t('collectionPanel.api.dataSourcePlaceholder')}
                  />
                  <p className="text-xs text-muted-foreground">
                    {t('collectionPanel.api.dataSourceHelp')}
                  </p>
                </div>
                <SynchronizedJsonConfigSection
                  name={`${exportTarget.name}-${groupBy}-json-options`}
                  value={localConfig.json_options ?? {}}
                  validate={isJsonObject}
                  jsonLabel={t('collectionPanel.api.jsonOverrides')}
                  jsonDescription={t('collectionPanel.api.jsonOverridesHelp')}
                  onChange={(value) =>
                    updateLocalConfig((current) => ({
                      ...current,
                      json_options: omitEmptyJsonOptions(
                        value as Record<string, unknown>
                      ),
                    }))
                  }
                >
                  <JsonOptionsEditor
                    value={localConfig.json_options ?? {}}
                    onChange={(value) =>
                      updateLocalConfig((current) => ({
                        ...current,
                        json_options: omitEmptyJsonOptions(value),
                      }))
                    }
                  />
                </SynchronizedJsonConfigSection>
              </AccordionContent>
            </AccordionItem>
          </Accordion>
        </CardContent>
      )}
      <AutoConfigReviewDialog
        open={autoConfigOpen}
        onOpenChange={setAutoConfigOpen}
        proposal={autoConfigQuery.data}
        isLoading={autoConfigQuery.isFetching}
        error={autoConfigQuery.error instanceof Error ? autoConfigQuery.error : null}
        onApply={handleApplyAutoConfig}
      />
    </Card>
  )
}
