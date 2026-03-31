import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { ExternalLink, Loader2, RotateCcw, Save } from 'lucide-react'
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
  const navigate = useNavigate()
  const {
    data: serverSettings,
    isLoading,
    error,
    refetch,
  } = useApiExportTargetSettings(target.name)
  const saveMutation = useUpdateApiExportTargetSettings(target.name)
  const [localSettings, setLocalSettings] = useState<ApiExportTargetSettings | null>(null)
  const [resetCounter, setResetCounter] = useState(0)

  useEffect(() => {
    if (serverSettings) {
      setLocalSettings(serverSettings)
    }
  }, [serverSettings])

  const isDirty =
    serverSettings !== undefined &&
    localSettings !== null &&
    JSON.stringify(serverSettings) !== JSON.stringify(localSettings)

  const activeGroups = target.groups.filter((g) => g.enabled)

  const handleSave = async () => {
    if (!localSettings) return
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

  const handleReset = () => {
    if (serverSettings) {
      setLocalSettings(serverSettings)
      setResetCounter((c) => c + 1)
    }
  }

  if (isLoading || !localSettings) {
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
            {error instanceof Error ? error.message : t('groupPanel.api.loadFailed')}
          </CardDescription>
        </CardHeader>
      </Card>
    )
  }

  // Build a short summary
  const outputDir = (localSettings.params as Record<string, string>)?.output_dir ?? ''
  const summaryParts = [
    outputDir ? `→ ${outputDir}` : '',
    t('groupPanel.api.groupsCount', { count: activeGroups.length }),
  ].filter(Boolean)

  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between gap-4">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <CardTitle className="text-base">{target.name}</CardTitle>
              <Badge variant="secondary" className="text-[10px]">
                {t('groupPanel.api.groupsCount', { count: activeGroups.length })}
              </Badge>
              {isDirty && (
                <Badge variant="outline" className="text-[10px] border-amber-300 text-amber-700">
                  {t('groupPanel.api.unsaved')}
                </Badge>
              )}
            </div>
            <CardDescription className="text-xs">
              {summaryParts.join(' · ')}
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
          initialValues={localSettings.params}
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
              {t('groupPanel.api.groupsCount', { count: activeGroups.length })}
            </p>
            <div className="flex flex-wrap gap-1.5">
              {activeGroups.map((g) => (
                <Button
                  key={g.group_by}
                  variant="outline"
                  size="sm"
                  className="h-6 gap-1 px-2 text-xs"
                  onClick={() => navigate(`/groups/${g.group_by}`)}
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
