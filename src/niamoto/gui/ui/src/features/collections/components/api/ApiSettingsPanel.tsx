import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { ExternalLink, Loader2, RotateCcw, Save } from 'lucide-react'
import { toast } from 'sonner'

import { JsonSchemaForm } from '@/components/forms'
import type { FormValues } from '@/components/forms/formSchemaTypes'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Label } from '@/components/ui/label'
import { Switch } from '@/components/ui/switch'
import {
  useApiExportTargetSettings,
  useApiExportTargets,
  useUpdateApiExportTargetSettings,
  type ApiExportTargetSummary,
  type ApiExportTargetSettings,
} from '@/features/collections/hooks/useApiExportConfigs'

function ApiTargetSettingsCard({ target }: { target: ApiExportTargetSummary }) {
  const { t } = useTranslation(['sources', 'common'])
  const navigate = useNavigate()
  const {
    data: serverSettings,
    isLoading,
    error,
    refetch,
  } = useApiExportTargetSettings(target.name)
  const activeGroups = target.groups.filter((g) => g.enabled)

  if (isLoading || !serverSettings) {
    return (
      <Card>
        <CardContent className="flex min-h-[120px] items-center justify-center">
          <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
        </CardContent>
      </Card>
    )
  }

  if (error) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>{target.name}</CardTitle>
          <CardDescription className="text-destructive">
            {error instanceof Error ? error.message : t('collectionPanel.api.loadFailed')}
          </CardDescription>
        </CardHeader>
      </Card>
    )
  }

  return (
    <ApiTargetSettingsCardForm
      key={`${target.name}:${JSON.stringify(serverSettings)}`}
      target={target}
      serverSettings={serverSettings}
      activeGroups={activeGroups}
      onRefetch={refetch}
      onNavigate={navigate}
    />
  )
}

interface ApiTargetSettingsCardFormProps {
  target: ApiExportTargetSummary
  serverSettings: ApiExportTargetSettings
  activeGroups: ApiExportTargetSummary['groups']
  onRefetch: () => Promise<unknown>
  onNavigate: ReturnType<typeof useNavigate>
}

function ApiTargetSettingsCardForm({
  target,
  serverSettings,
  activeGroups,
  onRefetch,
  onNavigate,
}: ApiTargetSettingsCardFormProps) {
  const { t } = useTranslation(['sources', 'common'])
  const saveMutation = useUpdateApiExportTargetSettings(target.name)
  const [localSettings, setLocalSettings] = useState<ApiExportTargetSettings>(serverSettings)
  const [resetCounter, setResetCounter] = useState(0)

  const isDirty = JSON.stringify(serverSettings) !== JSON.stringify(localSettings)

  const handleSave = async () => {
    try {
      await saveMutation.mutateAsync(localSettings)
      toast.success(
        t('collectionPanel.api.globalConfigSaved', { exportName: target.name })
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
    setLocalSettings(serverSettings)
    setResetCounter((c) => c + 1)
  }

  // Build a short summary
  const outputDir = (localSettings.params as Record<string, string>)?.output_dir ?? ''
  const summaryParts = [
    outputDir ? `→ ${outputDir}` : '',
    t('collectionPanel.api.groupsCount', { count: activeGroups.length }),
  ].filter(Boolean)

  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between gap-4">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <CardTitle className="text-base">{target.name}</CardTitle>
              <Badge variant="secondary" className="text-[10px]">
                {t('collectionPanel.api.groupsCount', { count: activeGroups.length })}
              </Badge>
              {isDirty && (
                <Badge variant="outline" className="text-[10px] border-amber-300 text-amber-700">
                  {t('collectionPanel.api.unsaved')}
                </Badge>
              )}
            </div>
            <CardDescription className="text-xs">
              {summaryParts.join(' · ')}
            </CardDescription>
          </div>

          <div className="flex items-center gap-3">
            <Label className="text-sm">{t('collectionPanel.api.enabledGlobally')}</Label>
            <Switch
              checked={localSettings.enabled}
              onCheckedChange={(enabled) =>
                setLocalSettings((current) =>
                  current ? { ...current, enabled } : current
                )
              }
            />
          </div>
        </div>

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

      <CardContent className="space-y-4 pt-0">
        <JsonSchemaForm
          key={`settings-${target.name}-${resetCounter}`}
          pluginId="json_api_exporter"
          showTitle={false}
          initialValues={localSettings.params as FormValues}
          onChange={(params) =>
            setLocalSettings((current) =>
              current ? { ...current, params } : current
            )
          }
        />

        {/* Groups using this target */}
        {activeGroups.length > 0 && (
          <div className="rounded-lg border border-dashed p-3">
            <p className="mb-2 text-xs font-medium text-muted-foreground">
              {t('collectionPanel.api.groupsCount', { count: activeGroups.length })}
            </p>
            <div className="flex flex-wrap gap-1.5">
              {activeGroups.map((g) => (
                <Button
                  key={g.group_by}
                  variant="outline"
                  size="sm"
                  className="h-6 gap-1 px-2 text-xs"
                  onClick={() => onNavigate(`/groups/${g.group_by}`)}
                >
                  {g.group_by}
                  <ExternalLink className="h-3 w-3" />
                </Button>
              ))}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  )
}

export function ApiSettingsPanel() {
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
        {error instanceof Error ? error.message : t('collectionPanel.api.loadFailed')}
      </div>
    )
  }

  return (
    <div className="space-y-6 p-6">
      <div>
        <h1 className="text-2xl font-bold">{t('collectionPanel.api.globalSettings')}</h1>
        <p className="mt-1 text-muted-foreground">
          {t('collectionPanel.api.globalSettingsDescription')}
        </p>
      </div>

      {!targets || targets.length === 0 ? (
        <div className="rounded-lg border border-dashed p-6 text-sm text-muted-foreground">
          {t('collectionPanel.api.empty')}
        </div>
      ) : (
        targets.map((target) => (
          <ApiTargetSettingsCard key={target.name} target={target} />
        ))
      )}
    </div>
  )
}
