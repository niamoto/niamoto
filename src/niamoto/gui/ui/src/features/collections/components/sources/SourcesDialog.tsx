/**
 * SourcesDialog - Overlay for managing auxiliary data sources
 *
 * Wraps SourcesList + AddSourceDialog in a Dialog overlay,
 * triggered by a button in the Blocs tab header.
 */

import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Database, Loader2, Plus } from 'lucide-react'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { useSources, useRemoveSource } from '@/features/collections/hooks/useSources'
import { SourcesList } from './SourcesList'
import { AddSourceDialog } from './AddSourceDialog'
import type { ReferenceInfo } from '@/hooks/useReferences'

interface SourcesDialogProps {
  reference: ReferenceInfo
}

export function SourcesDialog({ reference }: SourcesDialogProps) {
  const { t } = useTranslation(['sources', 'common'])
  const [addDialogOpen, setAddDialogOpen] = useState(false)

  const { data: sourcesData, isLoading: sourcesLoading } = useSources(reference.name)
  const sources = sourcesData?.sources ?? []
  const removeMutation = useRemoveSource(reference.name)

  const customSourceCount = sources.filter(s => !s.is_builtin).length

  return (
    <Dialog>
      <DialogTrigger asChild>
        <Button variant="outline" size="sm" className="gap-1.5">
          <Database className="h-3.5 w-3.5" />
          {t('collectionPanel.sourcesTab.title', 'Sources')}
          {customSourceCount > 0 && (
            <Badge variant="secondary" className="ml-1 text-[10px]">
              {customSourceCount}
            </Badge>
          )}
        </Button>
      </DialogTrigger>
      <DialogContent className="max-w-2xl max-h-[80vh] overflow-auto">
        <DialogHeader>
          <DialogTitle>{t('collectionPanel.sourcesTab.title', 'Data sources')}</DialogTitle>
          <DialogDescription>
            {t('collectionPanel.sourcesTab.description', { name: reference.name })}
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 mt-4">
          {/* Primary source - read only */}
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm">{t('collectionPanel.sourcesTab.primarySource')}</CardTitle>
              <CardDescription className="text-xs">
                {t('collectionPanel.sourcesTab.primarySourceDesc')}
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="rounded-md bg-muted p-2.5">
                <p className="font-mono text-sm">{t('collectionPanel.sourcesTab.occurrences')}</p>
                <p className="mt-0.5 text-xs text-muted-foreground">
                  {t('collectionPanel.sourcesTab.relation')}: {reference.kind === 'hierarchical' ? t('collectionPanel.sourcesTab.nestedSet') : t('collectionPanel.sourcesTab.directReference')}
                </p>
              </div>
            </CardContent>
          </Card>

          {/* Pre-calculated sources */}
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <div>
                <CardTitle className="text-sm">{t('collectionPanel.sourcesTab.precomputed')}</CardTitle>
                <CardDescription className="text-xs">
                  {t('collectionPanel.sourcesTab.precomputedDesc')}
                </CardDescription>
              </div>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setAddDialogOpen(true)}
              >
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

          {/* Schema fields */}
          {reference.schema_fields.length > 0 && (
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm">{t('collectionPanel.sourcesTab.schemaFields')}</CardTitle>
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

        {/* Add Source Dialog (nested) */}
        <AddSourceDialog
          open={addDialogOpen}
          onOpenChange={setAddDialogOpen}
          referenceName={reference.name}
          onSuccess={() => setAddDialogOpen(false)}
        />
      </DialogContent>
    </Dialog>
  )
}
