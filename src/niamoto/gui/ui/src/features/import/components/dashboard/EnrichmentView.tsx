import { useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'
import { AlertTriangle, Sparkles } from 'lucide-react'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { EnrichmentWorkspaceSheet } from './EnrichmentWorkspaceSheet'
import { useImportSummaryDetailed } from '@/hooks/useImportSummaryDetailed'
import { useReferences, type ReferenceInfo } from '@/hooks/useReferences'

export function EnrichmentView() {
  const { t } = useTranslation('sources')
  const queryClient = useQueryClient()
  const { data: referencesData, isLoading, error } = useReferences()
  const { data: summary } = useImportSummaryDetailed()
  const [activeReference, setActiveReference] = useState<ReferenceInfo | null>(null)

  const references = referencesData?.references ?? []
  const enrichableReferences = references.filter((reference) => reference.can_enrich)
  const unavailableReferences = references.filter((reference) => !reference.can_enrich)

  const entityRows = new Map(summary?.entities.map((entity) => [entity.name, entity]) ?? [])

  if (error) {
    return (
      <div className="p-6">
        <Alert variant="destructive">
          <AlertTriangle className="h-4 w-4" />
          <AlertTitle>{t('dashboard.errors.loadTitle')}</AlertTitle>
          <AlertDescription>
            {error instanceof Error ? error.message : t('dashboard.errors.loadSummary')}
          </AlertDescription>
        </Alert>
      </div>
    )
  }

  return (
    <div className="flex h-full flex-col overflow-auto p-6">
      <div className="space-y-4">
        <div className="space-y-2">
          <h1 className="text-2xl font-semibold tracking-tight">
            {t('dashboard.enrichmentView.title', 'API enrichment')}
          </h1>
          <p className="max-w-3xl text-sm text-muted-foreground">
            {t(
              'dashboard.enrichmentView.description',
              'Configure external enrichment for compatible references.'
            )}
          </p>
        </div>

        {!isLoading && enrichableReferences.length > 0 ? (
          <div className="flex flex-wrap gap-2">
            <Badge variant="secondary">
              {t('dashboard.enrichmentView.configuredCount', '{{count}} configured', {
                count: enrichableReferences.filter((reference) => reference.enrichment_enabled)
                  .length,
              })}
            </Badge>
            <Badge variant="outline">
              {t('dashboard.enrichmentView.availableCount', '{{count}} available', {
                count: enrichableReferences.filter((reference) => !reference.enrichment_enabled)
                  .length,
              })}
            </Badge>
          </div>
        ) : null}

        {isLoading ? (
          <div className="text-sm text-muted-foreground">
            {t('tree.loading', 'Loading...')}
          </div>
        ) : enrichableReferences.length === 0 ? (
          <Alert>
            <Sparkles className="h-4 w-4" />
            <AlertDescription>
              {t(
                'dashboard.enrichmentView.empty',
                'No enrichable references are currently available.'
              )}
            </AlertDescription>
          </Alert>
        ) : (
          <div className="space-y-3">
            {enrichableReferences.map((reference) => {
              const metrics =
                entityRows.get(reference.table_name) ?? entityRows.get(reference.name)
              return (
                <Card key={reference.name} className="border-border/70">
                  <CardContent className="flex flex-col gap-3 p-4 lg:flex-row lg:items-center lg:justify-between">
                    <div className="space-y-1">
                      <div className="flex flex-wrap items-center gap-2">
                        <div className="font-medium">{reference.name}</div>
                        <Badge variant="outline">
                          {t(`dashboard.referenceKinds.${reference.kind}`, {
                            defaultValue: reference.kind,
                          })}
                        </Badge>
                        <Badge variant={reference.enrichment_enabled ? 'secondary' : 'default'}>
                          {reference.enrichment_enabled
                            ? t('dashboard.status.enrichment_configured', 'Enrichment configured')
                            : t('dashboard.status.enrichment_available', 'Enrichment available')}
                        </Badge>
                      </div>
                      <div className="text-sm text-muted-foreground">
                        {t('dashboard.rows', '{{count}} rows', {
                          count: metrics?.row_count ?? reference.entity_count ?? 0,
                        })}
                      </div>
                    </div>
                    <Button type="button" onClick={() => setActiveReference(reference)}>
                      {reference.enrichment_enabled
                        ? t('dashboard.actions.manageEnrichment', 'Manage enrichment')
                        : t('dashboard.actions.configureEnrichment', 'Configure enrichment')}
                    </Button>
                  </CardContent>
                </Card>
              )
            })}
          </div>
        )}

        {unavailableReferences.length > 0 ? (
          <p className="text-sm text-muted-foreground">
            {t('dashboard.enrichmentView.unavailable', 'No enrichment available for: {{names}}', {
              names: unavailableReferences.map((reference) => reference.name).join(', '),
            })}
          </p>
        ) : null}
      </div>

      <EnrichmentWorkspaceSheet
        open={activeReference !== null}
        reference={activeReference}
        onOpenChange={(open) => !open && setActiveReference(null)}
        onConfigSaved={async () => {
          await Promise.all([
            queryClient.invalidateQueries({ queryKey: ['references'] }),
            queryClient.invalidateQueries({ queryKey: ['import-summary'] }),
          ])
        }}
      />
    </div>
  )
}
