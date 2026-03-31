import { useEffect, useMemo, useState } from 'react'
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
} from 'lucide-react'
import { toast } from 'sonner'

import { JsonSchemaForm } from '@/components/forms'
import JsonField from '@/components/forms/fields/JsonField'
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
import {
  useApiExportGroupConfig,
  useApiExportSuggestions,
  useUpdateApiExportGroupConfig,
  type ApiExportGroupConfig,
  type ApiExportTargetSummary,
} from '@/features/groups/hooks/useApiExportConfigs'

import { ApiFieldMappingsEditor } from './ApiFieldMappingsEditor'
import { DwcMappingEditor } from './DwcMappingEditor'

interface ExportCardProps {
  exportTarget: ApiExportTargetSummary
  groupBy: string
}

function buildAvailableFields(
  suggestions: ReturnType<typeof useApiExportSuggestions>['data']
) {
  const values = new Set<string>(['occurrences'])
  suggestions?.display_fields.forEach((field) => {
    values.add(field.source)
    values.add(field.name)
  })
  return Array.from(values).sort()
}

function buildDefaultLocalConfig(config: ApiExportGroupConfig): ApiExportGroupConfig {
  return {
    ...config,
    detail: config.detail ?? { pass_through: true },
    index: config.index ?? { fields: [] },
  }
}

/** Generate a natural language summary for this export. */
function formatExportSummary(
  config: ApiExportGroupConfig | null,
  suggestions: ReturnType<typeof useApiExportSuggestions>['data'],
  t: (key: string, opts?: Record<string, unknown>) => string
): string {
  if (!config) return ''
  if (!config.enabled) return t('groupPanel.api.exportSummary.disabled')

  const count = suggestions?.total_entities ?? 0
  const isDwc = config.transformer_plugin === 'niamoto_to_dwc_occurrence'

  if (isDwc) {
    const termCount = Object.keys(
      (config.transformer_params?.mapping as Record<string, unknown>) ?? {}
    ).length
    return t('groupPanel.api.exportSummary.dwc', { termCount, count })
  }

  if (config.detail?.pass_through !== false) {
    return t('groupPanel.api.exportSummary.simplePassThrough', { count })
  }

  const fieldCount = config.detail?.fields?.length ?? 0
  return t('groupPanel.api.exportSummary.simpleFields', { fieldCount, count })
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
  const saveMutation = useUpdateApiExportGroupConfig(exportTarget.name, groupBy)
  const [localConfig, setLocalConfig] = useState<ApiExportGroupConfig | null>(null)
  const [resetCounter, setResetCounter] = useState(0)

  useEffect(() => {
    if (serverConfig) {
      setLocalConfig(buildDefaultLocalConfig(serverConfig))
    }
  }, [serverConfig])

  const availableFields = useMemo(
    () => buildAvailableFields(suggestionsQuery.data),
    [suggestionsQuery.data]
  )

  const isDirty =
    serverConfig !== undefined &&
    localConfig !== null &&
    JSON.stringify(buildDefaultLocalConfig(serverConfig)) !== JSON.stringify(localConfig)

  const isDwcTransformer =
    localConfig?.transformer_plugin === 'niamoto_to_dwc_occurrence'

  const summary = formatExportSummary(localConfig, suggestionsQuery.data, t)

  const updateLocalConfig = (
    updater: (current: ApiExportGroupConfig) => ApiExportGroupConfig
  ) => {
    setLocalConfig((current) => (current ? updater(current) : current))
  }

  const handleSave = async () => {
    if (!localConfig) return
    try {
      await saveMutation.mutateAsync(localConfig)
      toast.success(
        t('groupPanel.api.groupConfigSaved', { exportName: exportTarget.name, groupBy })
      )
      await refetch()
    } catch (mutationError) {
      toast.error(
        mutationError instanceof Error
          ? mutationError.message
          : t('groupPanel.api.saveFailed')
      )
    }
  }

  const handleReset = () => {
    if (serverConfig) {
      setLocalConfig(buildDefaultLocalConfig(serverConfig))
      setResetCounter((c) => c + 1)
    }
  }

  if (isLoading || !localConfig) {
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
            {error instanceof Error ? error.message : t('groupPanel.api.loadFailed')}
          </p>
        </CardHeader>
      </Card>
    )
  }

  const indexFieldCount = localConfig.index?.fields?.length ?? 0
  const dwcTermCount = Object.keys(
    (localConfig.transformer_params?.mapping as Record<string, unknown>) ?? {}
  ).length
  const isPassThrough = localConfig.detail?.pass_through !== false

  return (
    <Card>
      {/* ── Header: name + summary + toggle ── */}
      <CardHeader className="pb-3">
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
                  {t('groupPanel.api.enabledForGroup')}
                </Badge>
              )}
              {!exportTarget.enabled && (
                <Badge variant="outline" className="text-[10px]">
                  {t('groupPanel.api.globallyDisabled')}
                </Badge>
              )}
              {isDirty && (
                <Badge variant="outline" className="text-[10px] border-amber-300 text-amber-700">
                  {t('groupPanel.api.unsaved')}
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
          <div className="flex items-center gap-2 pt-2">
            <Button
              variant="outline"
              size="sm"
              onClick={handleReset}
              disabled={saveMutation.isPending}
            >
              <RotateCcw className="mr-1.5 h-3.5 w-3.5" />
              {t('common:actions.reset')}
            </Button>
            <Button size="sm" onClick={handleSave} disabled={saveMutation.isPending}>
              {saveMutation.isPending ? (
                <Loader2 className="mr-1.5 h-3.5 w-3.5 animate-spin" />
              ) : (
                <Save className="mr-1.5 h-3.5 w-3.5" />
              )}
              {t('common:actions.save')}
            </Button>
          </div>
        )}
      </CardHeader>

      {/* ── Body: collapsible sections ── */}
      {localConfig.enabled && (
        <CardContent className="pt-0 pb-4">
          <Accordion type="multiple" className="space-y-2">
            {/* ── Main: Index fields ── */}
            <AccordionItem value="index" className="rounded-lg border">
              <AccordionTrigger className="px-3 py-2 text-sm hover:no-underline">
                <div className="flex items-center gap-2">
                  <ChevronRight className="h-3.5 w-3.5 shrink-0 transition-transform duration-200" />
                  <span className="font-medium">
                    {t('groupPanel.api.indexFields')}
                  </span>
                  <Badge variant="secondary" className="text-[10px]">
                    {indexFieldCount > 0
                      ? t('groupPanel.api.fieldCount', { count: indexFieldCount })
                      : t('groupPanel.api.sectionDefault')}
                  </Badge>
                </div>
              </AccordionTrigger>
              <AccordionContent className="px-3 pb-3">
                <p className="mb-3 text-xs text-muted-foreground">
                  {t('groupPanel.api.sectionHelp.indexFields', {
                    groupBy,
                  })}
                </p>
                <ApiFieldMappingsEditor
                  value={localConfig.index?.fields ?? []}
                  suggestions={suggestionsQuery.data?.display_fields ?? []}
                  onChange={(fields) =>
                    updateLocalConfig((current) => ({
                      ...current,
                      index: { fields },
                    }))
                  }
                />
              </AccordionContent>
            </AccordionItem>

            {/* ── Main: Detail / pass-through ── */}
            {!localConfig.transformer_plugin && (
              <AccordionItem value="detail" className="rounded-lg border">
                <AccordionTrigger className="px-3 py-2 text-sm hover:no-underline">
                  <div className="flex items-center gap-2">
                    <ChevronRight className="h-3.5 w-3.5 shrink-0 transition-transform duration-200" />
                    <span className="font-medium">
                      {t('groupPanel.api.detailFields')}
                    </span>
                    <Badge variant="secondary" className="text-[10px]">
                      {isPassThrough
                        ? t('groupPanel.api.passThrough')
                        : t('groupPanel.api.fieldCount', {
                            count: localConfig.detail?.fields?.length ?? 0,
                          })}
                    </Badge>
                  </div>
                </AccordionTrigger>
                <AccordionContent className="px-3 pb-3">
                  <p className="mb-3 text-xs text-muted-foreground">
                    {t('groupPanel.api.sectionHelp.detailFields', { groupBy })}
                  </p>
                  <div className="mb-3 flex items-center justify-between gap-2">
                    <Label className="text-sm">{t('groupPanel.api.passThrough')}</Label>
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
                    <JsonField
                      name={`${exportTarget.name}-${groupBy}-detail-fields`}
                      label={t('groupPanel.api.detailFields')}
                      value={localConfig.detail?.fields}
                      onChange={(value) =>
                        updateLocalConfig((current) => ({
                          ...current,
                          detail: {
                            ...current.detail,
                            fields: Array.isArray(value)
                              ? (value as Array<string | Record<string, unknown>>)
                              : [],
                          },
                        }))
                      }
                    />
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
                      {t('groupPanel.api.dwcMapping')}
                    </span>
                    <Badge variant="secondary" className="text-[10px]">
                      {dwcTermCount > 0
                        ? t('groupPanel.api.termCount', { count: dwcTermCount })
                        : t('groupPanel.api.sectionDefault')}
                    </Badge>
                  </div>
                </AccordionTrigger>
                <AccordionContent className="px-3 pb-3">
                  <p className="mb-3 text-xs text-muted-foreground">
                    {t('groupPanel.api.sectionHelp.dwcMapping')}
                  </p>
                  <DwcMappingEditor
                    value={
                      (localConfig.transformer_params?.mapping as
                        | Record<string, unknown>
                        | undefined) ?? {}
                    }
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
                      {t('groupPanel.api.transformerParams')}
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
                    initialValues={localConfig.transformer_params ?? {}}
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
                    {t('groupPanel.api.jsonOverrides')}
                  </span>
                </div>
              </AccordionTrigger>
              <AccordionContent className="space-y-4 px-3 pb-3">
                <p className="text-xs text-muted-foreground">
                  {t('groupPanel.api.sectionHelp.advancedOptions')}
                </p>
                <div className="space-y-2">
                  <Label>{t('groupPanel.api.dataSource')}</Label>
                  <Input
                    value={localConfig.data_source || ''}
                    onChange={(event) =>
                      updateLocalConfig((current) => ({
                        ...current,
                        data_source: event.target.value || undefined,
                      }))
                    }
                    placeholder={t('groupPanel.api.dataSourcePlaceholder')}
                  />
                  <p className="text-xs text-muted-foreground">
                    {t('groupPanel.api.dataSourceHelp')}
                  </p>
                </div>
                <JsonField
                  name={`${exportTarget.name}-${groupBy}-json-options`}
                  label={t('groupPanel.api.jsonOverrides')}
                  description={t('groupPanel.api.jsonOverridesHelp')}
                  value={localConfig.json_options}
                  onChange={(value) =>
                    updateLocalConfig((current) => ({
                      ...current,
                      json_options:
                        value && typeof value === 'object'
                          ? (value as Record<string, unknown>)
                          : undefined,
                    }))
                  }
                />
              </AccordionContent>
            </AccordionItem>
          </Accordion>
        </CardContent>
      )}
    </Card>
  )
}
