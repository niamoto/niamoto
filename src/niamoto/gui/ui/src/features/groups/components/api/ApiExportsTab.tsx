import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { Loader2, RotateCcw, Save, Settings2 } from 'lucide-react'
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
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Switch } from '@/components/ui/switch'
import {
  useApiExportGroupConfig,
  useApiExportSuggestions,
  useApiExportTargets,
  useUpdateApiExportGroupConfig,
  type ApiExportGroupConfig,
  type ApiExportTargetSummary,
} from '@/features/groups/hooks/useApiExportConfigs'

import { ApiFieldMappingsEditor } from './ApiFieldMappingsEditor'
import { DwcMappingEditor } from './DwcMappingEditor'

interface ApiExportsTabProps {
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

function ApiExportGroupCard({
  exportTarget,
  groupBy,
}: {
  exportTarget: ApiExportTargetSummary
  groupBy: string
}) {
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
    JSON.stringify(buildDefaultLocalConfig(serverConfig)) !==
      JSON.stringify(localConfig)
  const isDwcTransformer =
    localConfig?.transformer_plugin === 'niamoto_to_dwc_occurrence'

  const serverFormKey = JSON.stringify(serverConfig?.transformer_params ?? {})

  const updateLocalConfig = (
    updater: (current: ApiExportGroupConfig) => ApiExportGroupConfig
  ) => {
    setLocalConfig((current) => (current ? updater(current) : current))
  }

  const handleSave = async () => {
    if (!localConfig) {
      return
    }

    try {
      await saveMutation.mutateAsync(localConfig)
      toast.success(
        t('groupPanel.api.groupConfigSaved', {
          exportName: exportTarget.name,
          groupBy,
        })
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
    }
  }

  if (isLoading || !localConfig) {
    return (
      <Card>
        <CardContent className="flex min-h-[180px] items-center justify-center">
          <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
        </CardContent>
      </Card>
    )
  }

  if (error) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>{exportTarget.name}</CardTitle>
          <CardDescription className="text-destructive">
            {error instanceof Error ? error.message : t('groupPanel.api.loadFailed')}
          </CardDescription>
        </CardHeader>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader className="border-b bg-muted/20">
        <div className="flex items-start justify-between gap-4">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <CardTitle className="text-base">{exportTarget.name}</CardTitle>
              {!exportTarget.enabled && (
                <Badge variant="outline">
                  {t('groupPanel.api.globallyDisabled')}
                </Badge>
              )}
              {isDirty && (
                <Badge variant="outline">
                  {t('groupPanel.api.unsaved')}
                </Badge>
              )}
            </div>
            <CardDescription>
              {t('groupPanel.api.targetDescription', {
                exportName: exportTarget.name,
                groupBy,
              })}
            </CardDescription>
          </div>

          <div className="flex items-center gap-3">
            <Label className="text-sm">{t('groupPanel.api.enabledForGroup')}</Label>
            <Switch
              checked={localConfig.enabled}
              onCheckedChange={(enabled) =>
                updateLocalConfig((current) => ({ ...current, enabled }))
              }
            />
          </div>
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={handleReset}
            disabled={!isDirty || saveMutation.isPending}
          >
            <RotateCcw className="mr-2 h-4 w-4" />
            {t('common:actions.reset')}
          </Button>
          <Button
            size="sm"
            onClick={handleSave}
            disabled={!isDirty || saveMutation.isPending}
          >
            {saveMutation.isPending ? (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            ) : (
              <Save className="mr-2 h-4 w-4" />
            )}
            {t('common:actions.save')}
          </Button>
        </div>
      </CardHeader>

      <CardContent className="space-y-6 p-6">
        {!localConfig.enabled ? (
          <div className="rounded-lg border border-dashed p-6 text-sm text-muted-foreground">
            {t('groupPanel.api.disabledForGroup')}
          </div>
        ) : (
          <>
            <div className="grid gap-4 md:grid-cols-2">
              <div className="space-y-2 rounded-lg border p-4">
                <Label htmlFor={`${exportTarget.name}-${groupBy}-data-source`}>
                  {t('groupPanel.api.dataSource')}
                </Label>
                <Input
                  id={`${exportTarget.name}-${groupBy}-data-source`}
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

              {!localConfig.transformer_plugin && (
                <div className="space-y-2 rounded-lg border p-4">
                  <div className="flex items-center justify-between gap-2">
                    <div>
                      <Label>{t('groupPanel.api.passThrough')}</Label>
                      <p className="text-xs text-muted-foreground">
                        {t('groupPanel.api.passThroughHelp')}
                      </p>
                    </div>
                    <Switch
                      checked={localConfig.detail?.pass_through ?? true}
                      onCheckedChange={(passThrough) =>
                        updateLocalConfig((current) => ({
                          ...current,
                          detail: {
                            ...current.detail,
                            pass_through: passThrough,
                          },
                        }))
                      }
                    />
                  </div>
                </div>
              )}
            </div>

            {!localConfig.transformer_plugin && localConfig.detail?.pass_through === false && (
              <JsonField
                name={`${exportTarget.name}-${groupBy}-detail-fields`}
                label={t('groupPanel.api.detailFields')}
                description={t('groupPanel.api.detailFieldsHelp')}
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

            <ApiFieldMappingsEditor
              title={t('groupPanel.api.indexFields')}
              description={t('groupPanel.api.indexFieldsHelp')}
              value={localConfig.index?.fields ?? []}
              suggestions={suggestionsQuery.data?.display_fields ?? []}
              onChange={(fields) =>
                updateLocalConfig((current) => ({
                  ...current,
                  index: { fields },
                }))
              }
            />

            <Accordion type="multiple" className="space-y-4">
              {localConfig.transformer_plugin && (
                <AccordionItem value="transformer" className="rounded-lg border px-4">
                  <AccordionTrigger className="text-sm font-medium hover:no-underline">
                    {t('groupPanel.api.transformerParams')}
                  </AccordionTrigger>
                  <AccordionContent className="pb-4">
                    <JsonSchemaForm
                      key={`${exportTarget.name}-${groupBy}-${serverFormKey}`}
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
                    {isDwcTransformer && (
                      <div className="mt-4">
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
                      </div>
                    )}
                  </AccordionContent>
                </AccordionItem>
              )}

              <AccordionItem value="json-options" className="rounded-lg border px-4">
                <AccordionTrigger className="text-sm font-medium hover:no-underline">
                  {t('groupPanel.api.jsonOverrides')}
                </AccordionTrigger>
                <AccordionContent className="pb-4">
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
          </>
        )}
      </CardContent>
    </Card>
  )
}

export function ApiExportsTab({ groupBy }: ApiExportsTabProps) {
  const navigate = useNavigate()
  const { t } = useTranslation(['sources', 'common'])
  const { data: targets, isLoading, error } = useApiExportTargets()

  if (isLoading) {
    return (
      <div className="flex h-full items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    )
  }

  if (error) {
    return (
      <div className="rounded-lg border border-dashed p-6 text-sm text-destructive">
        {error instanceof Error ? error.message : t('groupPanel.api.loadFailed')}
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h2 className="text-lg font-medium">{t('groupPanel.api.title')}</h2>
          <p className="text-sm text-muted-foreground">
            {t('groupPanel.api.description', { groupBy })}
          </p>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={() => navigate('/groups/api-settings')}
        >
          <Settings2 className="mr-2 h-4 w-4" />
          {t('groupPanel.api.globalSettings')}
        </Button>
      </div>

      {!targets || targets.length === 0 ? (
        <div className="rounded-lg border border-dashed p-6 text-sm text-muted-foreground">
          {t('groupPanel.api.empty')}
        </div>
      ) : (
        targets.map((target) => (
          <ApiExportGroupCard
            key={`${target.name}-${groupBy}`}
            exportTarget={target}
            groupBy={groupBy}
          />
        ))
      )}
    </div>
  )
}
