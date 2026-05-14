import { FileCode, Loader2, Package } from 'lucide-react'
import { useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader } from '@/components/ui/card'
import {
  type StandardProfileConfig,
  type StandardProfileOutputResult,
  type StandardProfileOutputType,
  type StandardValidationReport,
  useExecuteStandardProfileOutput,
  useExecuteStandardProfileOutputDraft,
  useStandardProfileOutputPreview,
} from '@/features/collections/hooks/useStandardProfiles'

interface ProfileOutputsPanelProps {
  profile: StandardProfileConfig
  validation?: StandardValidationReport
  draftMode?: boolean
}

const outputIcon = {
  api_json: FileCode,
  dwc_archive: Package,
  standard_files: Package,
} as const

export function ProfileOutputsPanel({
  profile,
  validation,
  draftMode = false,
}: ProfileOutputsPanelProps) {
  const { t } = useTranslation(['sources'])
  const executePublicationOutput = useExecuteStandardProfileOutput(profile.name)
  const executeDraftOutput = useExecuteStandardProfileOutputDraft(profile.name)
  const executeOutput = draftMode ? executeDraftOutput : executePublicationOutput
  const outputContextKey = `${profile.name}:${draftMode ? 'draft' : 'publication'}`
  const [lastOutputState, setLastOutputState] = useState<{
    contextKey: string
    result: StandardProfileOutputResult
  } | null>(null)
  const [errorState, setErrorState] = useState<{
    contextKey: string
    message: string
  } | null>(null)
  const runRequestRef = useRef(0)
  const validationStatus = validation?.status ?? profile.validation_status
  const hasCritical = (validation?.summary.critical ?? 0) > 0
  const lastOutput =
    lastOutputState?.contextKey === outputContextKey ? lastOutputState.result : null
  const error = errorState?.contextKey === outputContextKey ? errorState.message : null
  const retentionLocation = lastOutput
    ? draftRetentionLocation(lastOutput)
    : null

  const runOutput = async (outputType: StandardProfileOutputType) => {
    const requestId = runRequestRef.current + 1
    runRequestRef.current = requestId
    const profileName = profile.name
    const contextKey = outputContextKey
    setErrorState(null)
    setLastOutputState(null)
    try {
      const result = await executeOutput.mutateAsync(outputType)
      if (
        requestId !== runRequestRef.current ||
        (result.profile_name && result.profile_name !== profileName)
      ) {
        return
      }
      setLastOutputState({ contextKey, result })
    } catch (runError) {
      if (requestId !== runRequestRef.current) {
        return
      }
      setErrorState({
        contextKey,
        message:
          runError instanceof Error
            ? runError.message
            : t('collections.standards.outputFailed'),
      })
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
                (!draftMode && publicationFile && hasCritical)
              const actionLabel = draftMode
                ? publicationFile
                  ? t('collections.standards.generateDraftOutput')
                  : t('collections.standards.generateDraftJson')
                : publicationFile
                  ? t('collections.standards.generatePublicationFile')
                  : t('collections.standards.generatePublicationJson')

              return (
                <div
                  key={output.type}
                  className="space-y-3 rounded-md border p-3"
                >
                  <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
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
                      {actionLabel}
                    </Button>
                  </div>
                  {output.type === 'api_json' && output.enabled && (
                    <ProfileJsonOutputPreview profileName={profile.name} />
                  )}
                </div>
              )
            })}
          </div>
        )}

        {lastOutput?.output_path && (
          <div className="space-y-2 rounded-md border bg-muted/20 p-3 text-xs">
            <div className="flex flex-wrap items-center gap-2">
              <Badge variant={draftMode ? 'outline' : 'success'}>
                {draftMode
                  ? t('collections.standards.testOutput')
                  : t('collections.standards.publicationOutput')}
              </Badge>
              <span>
                {t('collections.standards.lastOutput')}: {lastOutput.output_path}
              </span>
            </div>
            {retentionLocation && (
              <p className="text-muted-foreground">
                {t('collections.standards.draftRetention', {
                  location: retentionLocation,
                })}
              </p>
            )}
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

function draftRetentionLocation(result: StandardProfileOutputResult) {
  const retentionPolicy = result.metadata?.retention_policy
  if (
    typeof retentionPolicy === 'object' &&
    retentionPolicy !== null &&
    'location' in retentionPolicy
  ) {
    return String(retentionPolicy.location)
  }
  return null
}

function ProfileJsonOutputPreview({ profileName }: { profileName: string }) {
  const { t } = useTranslation(['sources'])
  const preview = useStandardProfileOutputPreview(profileName, 'api_json')
  const previewLabel = t('collections.standards.outputJsonPreview')
  const previewText = JSON.stringify(preview.data?.preview ?? null, null, 2)

  if (preview.isLoading || preview.isFetching) {
    return (
      <div className="rounded-md border bg-muted/20 p-3 text-xs text-muted-foreground">
        {t('collections.standards.outputJsonPreviewLoading')}
      </div>
    )
  }

  if (preview.error) {
    return (
      <div className="rounded-md border border-destructive/30 bg-destructive/5 p-3 text-xs text-destructive">
        {preview.error instanceof Error
          ? preview.error.message
          : t('collections.standards.outputJsonPreviewFailed')}
      </div>
    )
  }

  return (
    <div className="min-w-0 rounded-md border bg-muted/20 p-3">
      <div className="mb-2 flex flex-wrap items-center justify-between gap-2 text-xs text-muted-foreground">
        <span className="font-medium">{previewLabel}</span>
        {preview.data?.item_id !== null && preview.data?.item_id !== undefined && (
          <span>
            {t('collections.standards.outputJsonPreviewItem', {
              id: preview.data.item_id,
            })}
          </span>
        )}
      </div>
      <pre
        aria-label={previewLabel}
        className="max-h-[24rem] overflow-auto whitespace-pre-wrap break-words rounded bg-background p-3 font-mono text-xs leading-relaxed text-foreground"
      >
        {previewText}
      </pre>
    </div>
  )
}
