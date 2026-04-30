import { FileCode, Loader2, Package } from 'lucide-react'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader } from '@/components/ui/card'
import {
  type StandardProfileConfig,
  type StandardProfileOutputType,
  type StandardValidationReport,
  useExecuteStandardProfileOutput,
} from '@/features/collections/hooks/useStandardProfiles'

interface ProfileOutputsPanelProps {
  profile: StandardProfileConfig
  validation?: StandardValidationReport
}

const outputIcon = {
  api_json: FileCode,
  dwc_archive: Package,
  standard_files: Package,
} as const

export function ProfileOutputsPanel({
  profile,
  validation,
}: ProfileOutputsPanelProps) {
  const { t } = useTranslation(['sources'])
  const executeOutput = useExecuteStandardProfileOutput(profile.name)
  const [lastOutputPath, setLastOutputPath] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const validationStatus = validation?.status ?? profile.validation_status
  const hasCritical = (validation?.summary.critical ?? 0) > 0

  const runOutput = async (outputType: StandardProfileOutputType) => {
    setError(null)
    try {
      const result = await executeOutput.mutateAsync(outputType)
      setLastOutputPath(result.output_path ?? null)
    } catch (runError) {
      setError(
        runError instanceof Error
          ? runError.message
          : t('collections.standards.outputFailed'),
      )
    }
  }

  return (
    <Card>
      <CardHeader className="space-y-2 pb-3">
        <div className="flex flex-wrap items-center gap-2">
          <h3 className="text-sm font-semibold">
            {t('collections.standards.outputs')}
          </h3>
          <Badge variant={validationStatus === 'conformant' ? 'success' : 'outline'}>
            {t(`collections.standards.validationStatus.${validationStatus}`)}
          </Badge>
        </div>
        {hasCritical && (
          <p className="text-xs text-muted-foreground">
            {t('collections.standards.publicationBlocked')}
          </p>
        )}
      </CardHeader>
      <CardContent className="space-y-3">
        {profile.outputs.length === 0 ? (
          <div className="rounded-md border border-dashed p-3 text-sm text-muted-foreground">
            {t('collections.standards.noOutputs')}
          </div>
        ) : (
          <div className="grid gap-2">
            {profile.outputs.map((output) => {
              const Icon = outputIcon[output.type]
              const publicationFile = output.type !== 'api_json'
              const disabled =
                !output.enabled ||
                executeOutput.isPending ||
                (publicationFile && hasCritical)

              return (
                <div
                  key={output.type}
                  className="flex flex-col gap-2 rounded-md border p-3 sm:flex-row sm:items-center sm:justify-between"
                >
                  <div className="flex min-w-0 items-center gap-2">
                    <Icon className="h-4 w-4 text-muted-foreground" />
                    <div className="min-w-0">
                      <div className="text-sm font-medium">
                        {t(`collections.standards.outputTypes.${output.type}`)}
                      </div>
                      <div className="text-xs text-muted-foreground">
                        {output.enabled
                          ? t('collections.standards.outputEnabled')
                          : t('collections.standards.outputDisabled')}
                      </div>
                    </div>
                  </div>
                  <Button
                    size="sm"
                    variant={publicationFile ? 'default' : 'outline'}
                    disabled={disabled}
                    onClick={() => runOutput(output.type)}
                  >
                    {executeOutput.isPending ? (
                      <Loader2 className="h-3.5 w-3.5 animate-spin" />
                    ) : null}
                    {publicationFile
                      ? t('collections.standards.generatePublicationFile')
                      : t('collections.standards.generateDraftJson')}
                  </Button>
                </div>
              )
            })}
          </div>
        )}

        {lastOutputPath && (
          <div className="rounded-md border bg-muted/20 p-3 text-xs">
            {t('collections.standards.lastOutput')}: {lastOutputPath}
          </div>
        )}
        {error && (
          <div className="rounded-md border border-destructive/30 bg-destructive/5 p-3 text-xs text-destructive">
            {error}
          </div>
        )}
      </CardContent>
    </Card>
  )
}
