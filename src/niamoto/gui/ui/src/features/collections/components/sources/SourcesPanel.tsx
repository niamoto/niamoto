import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Loader2, Plus } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { useSources, useRemoveSource } from '@/features/collections/hooks/useSources'
import { SourcesList } from './SourcesList'
import { AddSourceDialog } from './AddSourceDialog'
import type { ReferenceInfo } from '@/hooks/useReferences'

interface SourcesPanelProps {
  reference: ReferenceInfo
}

export function SourcesPanel({ reference }: SourcesPanelProps) {
  const { t } = useTranslation(['sources', 'common'])
  const [addDialogOpen, setAddDialogOpen] = useState(false)

  const { data: sourcesData, isLoading: sourcesLoading } = useSources(reference.name)
  const sources = sourcesData?.sources ?? []
  const removeMutation = useRemoveSource(reference.name)

  const customSourceCount = sources.filter((source) => !source.is_builtin).length

  return (
    <div className="h-full overflow-auto p-4">
      <div className="space-y-4">
        <Card>
          <CardHeader className="pb-2">
            <div className="flex items-center justify-between gap-3">
              <div>
                <CardTitle className="text-sm">
                  {t('collectionPanel.sourcesTab.title', 'Data sources')}
                </CardTitle>
                <CardDescription className="text-xs">
                  {t('collectionPanel.sourcesTab.description', { name: reference.name })}
                </CardDescription>
              </div>
              {customSourceCount > 0 && (
                <Badge variant="secondary" className="text-[10px]">
                  {customSourceCount}
                </Badge>
              )}
            </div>
          </CardHeader>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">
              {t('collectionPanel.sourcesTab.primarySource')}
            </CardTitle>
            <CardDescription className="text-xs">
              {t('collectionPanel.sourcesTab.primarySourceDesc')}
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="rounded-md bg-muted p-2.5">
              <p className="font-mono text-sm">
                {t('collectionPanel.sourcesTab.occurrences')}
              </p>
              <p className="mt-0.5 text-xs text-muted-foreground">
                {t('collectionPanel.sourcesTab.relation')}:{' '}
                {reference.kind === 'hierarchical'
                  ? t('collectionPanel.sourcesTab.nestedSet')
                  : t('collectionPanel.sourcesTab.directReference')}
              </p>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <div>
              <CardTitle className="text-sm">
                {t('collectionPanel.sourcesTab.precomputed')}
              </CardTitle>
              <CardDescription className="text-xs">
                {t('collectionPanel.sourcesTab.precomputedDesc')}
              </CardDescription>
            </div>
            <Button variant="outline" size="sm" onClick={() => setAddDialogOpen(true)}>
              <Plus className="mr-1 h-3 w-3" />
              {t('common:actions.add')}
            </Button>
          </CardHeader>
          <CardContent>
            {sourcesLoading ? (
              <div className="flex min-h-[60px] items-center justify-center">
                <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
              </div>
            ) : (
              <SourcesList
                sources={sources}
                onRemove={(name) => removeMutation.mutate(name)}
                isRemoving={removeMutation.isPending}
              />
            )}
          </CardContent>
        </Card>

        {reference.schema_fields.length > 0 && (
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm">
                {t('collectionPanel.sourcesTab.schemaFields')}
              </CardTitle>
              <CardDescription className="text-xs">
                {t('collectionPanel.sourcesTab.schemaFieldsDesc')}
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid gap-1.5 md:grid-cols-3">
                {reference.schema_fields.map((field) => (
                  <div
                    key={field.name}
                    className="flex items-center justify-between rounded-md bg-muted p-1.5"
                  >
                    <span className="font-mono text-xs">{field.name}</span>
                    {field.type && (
                      <Badge variant="outline" className="text-[10px]">
                        {field.type}
                      </Badge>
                    )}
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        )}
      </div>

      <AddSourceDialog
        open={addDialogOpen}
        onOpenChange={setAddDialogOpen}
        referenceName={reference.name}
        onSuccess={() => setAddDialogOpen(false)}
      />
    </div>
  )
}
