import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Loader2, RotateCcw, Save } from 'lucide-react'
import { toast } from 'sonner'

import { JsonSchemaForm } from '@/components/forms'
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
} from '@/features/groups/hooks/useApiExportConfigs'

function ApiTargetSettingsCard({ target }: { target: ApiExportTargetSummary }) {
  const { t } = useTranslation(['sources', 'common'])
  const {
    data: serverSettings,
    isLoading,
    error,
    refetch,
  } = useApiExportTargetSettings(target.name)
  const saveMutation = useUpdateApiExportTargetSettings(target.name)
  const [localSettings, setLocalSettings] = useState<ApiExportTargetSettings | null>(null)

  useEffect(() => {
    if (serverSettings) {
      setLocalSettings(serverSettings)
    }
  }, [serverSettings])

  const isDirty =
    serverSettings !== undefined &&
    localSettings !== null &&
    JSON.stringify(serverSettings) !== JSON.stringify(localSettings)

  const handleSave = async () => {
    if (!localSettings) {
      return
    }

    try {
      await saveMutation.mutateAsync(localSettings)
      toast.success(
        t('groupPanel.api.globalConfigSaved', { exportName: target.name })
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

  if (isLoading || !localSettings) {
    return (
      <Card>
        <CardContent className="flex min-h-[200px] items-center justify-center">
          <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
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
              <CardTitle className="text-base">{target.name}</CardTitle>
              <Badge variant="outline">
                {t('groupPanel.api.groupsCount', {
                  count: target.group_names.length,
                })}
              </Badge>
              {isDirty && (
                <Badge variant="outline">
                  {t('groupPanel.api.unsaved')}
                </Badge>
              )}
            </div>
            <CardDescription>
              {t('groupPanel.api.globalTargetDescription', {
                exportName: target.name,
              })}
            </CardDescription>
          </div>

          <div className="flex items-center gap-3">
            <Label className="text-sm">{t('groupPanel.api.enabledGlobally')}</Label>
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

        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => setLocalSettings(serverSettings ?? null)}
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

      <CardContent className="p-6">
        <JsonSchemaForm
          key={`${target.name}-${JSON.stringify(serverSettings?.params ?? {})}`}
          pluginId="json_api_exporter"
          showTitle={false}
          initialValues={localSettings.params}
          onChange={(params) =>
            setLocalSettings((current) =>
              current ? { ...current, params } : current
            )
          }
        />
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
        {error instanceof Error ? error.message : t('groupPanel.api.loadFailed')}
      </div>
    )
  }

  return (
    <div className="space-y-6 p-6">
      <div>
        <h1 className="text-2xl font-bold">{t('groupPanel.api.globalSettings')}</h1>
        <p className="mt-1 text-muted-foreground">
          {t('groupPanel.api.globalSettingsDescription')}
        </p>
      </div>

      {!targets || targets.length === 0 ? (
        <div className="rounded-lg border border-dashed p-6 text-sm text-muted-foreground">
          {t('groupPanel.api.empty')}
        </div>
      ) : (
        targets.map((target) => (
          <ApiTargetSettingsCard key={target.name} target={target} />
        ))
      )}
    </div>
  )
}
