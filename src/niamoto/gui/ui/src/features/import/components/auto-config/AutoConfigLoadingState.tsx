import { useTranslation } from 'react-i18next'
import { AlertCircle, CheckCircle2, Loader2, Sparkles } from 'lucide-react'
import type { AutoConfigureProgressEvent } from '@/features/import/api/smart-config'

interface AutoConfigLoadingStateProps {
  analysisEvents: AutoConfigureProgressEvent[]
  analysisStage?: string | null
}

export function AutoConfigLoadingState({
  analysisEvents,
  analysisStage,
}: AutoConfigLoadingStateProps) {
  const { t } = useTranslation('sources')
  const latestEvents = analysisEvents.slice(-8)

  return (
    <div className="space-y-6 py-8">
      <div className="flex flex-col items-center justify-center">
        <div className="relative mb-4">
          <Sparkles className="h-12 w-12 animate-pulse text-primary" />
        </div>
        <h3 className="mb-2 text-lg font-semibold">{t('autoConfig.loading.title')}</h3>
        <p className="text-center text-sm text-muted-foreground">
          {analysisStage || t('autoConfig.loading.description')}
        </p>
      </div>

      <div className="mx-auto w-full max-w-2xl rounded-lg border bg-muted/30 p-4">
        <div className="mb-3 flex items-center justify-between">
          <div className="text-sm font-medium">{t('autoConfig.loading.liveFeed')}</div>
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <Loader2 className="h-3.5 w-3.5 animate-spin" />
            {t('autoConfig.loading.step')}
          </div>
        </div>
        <div className="space-y-2">
          {latestEvents.length > 0 ? (
            latestEvents.map((event, index) => (
              <div
                key={`${event.timestamp}-${index}`}
                className="flex items-start gap-3 rounded-md bg-background/80 px-3 py-2 text-sm"
              >
                <div className="pt-0.5">
                  {event.kind === 'finding' ? (
                    <CheckCircle2 className="h-4 w-4 text-green-600" />
                  ) : event.kind === 'error' ? (
                    <AlertCircle className="h-4 w-4 text-destructive" />
                  ) : (
                    <Loader2 className="h-4 w-4 animate-spin text-primary" />
                  )}
                </div>
                <div className="min-w-0 flex-1">
                  <div className="text-foreground">{event.message}</div>
                  {(event.file || event.entity) && (
                    <div className="text-xs text-muted-foreground">
                      {[event.entity, event.file].filter(Boolean).join(' • ')}
                    </div>
                  )}
                </div>
              </div>
            ))
          ) : (
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <Loader2 className="h-4 w-4 animate-spin" />
              {t('autoConfig.loading.waitingForEvents')}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
