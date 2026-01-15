/**
 * Group Panel - Widget Configuration for a Reference
 *
 * Three tabs (Option A: Hybride):
 * - Sources de donnees: Configure data sources (occurrences + stats files)
 * - Contenu: Widget management with contextual panel (list + layout/details)
 * - Index: Index configuration
 */

import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import type { ReferenceInfo } from '@/hooks/useReferences'
import { Database, Package, Loader2, ListOrdered, Plus, LayoutGrid } from 'lucide-react'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { useSources, useRemoveSource } from '@/hooks/useSources'
import { SourcesList, AddSourceDialog } from '@/components/sources'
import { IndexConfigEditor } from '@/components/index-config'
import { ContentTab } from '@/components/content'

interface GroupPanelProps {
  reference: ReferenceInfo
}

export function GroupPanel({ reference }: GroupPanelProps) {
  const { t } = useTranslation(['sources', 'common'])
  const [activeTab, setActiveTab] = useState('sources')

  // Kind display mapping using i18n
  const kindLabels: Record<string, string> = {
    hierarchical: t('groupPanel.kinds.hierarchical'),
    flat: t('groupPanel.kinds.flat'),
    spatial: t('groupPanel.kinds.spatial'),
  }

  return (
    <div className="flex h-full flex-col">
      {/* Header */}
      <div className="border-b bg-background px-6 py-4">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
            <Package className="h-5 w-5 text-primary" />
          </div>
          <div>
            <h1 className="text-xl font-bold">{reference.name}</h1>
            <p className="text-sm text-muted-foreground">
              {reference.entity_count ?? '?'} {t('reference.entities')}
              <span className="mx-2">·</span>
              <Badge variant="outline" className="text-xs">
                {kindLabels[reference.kind] || reference.kind}
              </Badge>
              {reference.description && (
                <>
                  <span className="mx-2">·</span>
                  {reference.description}
                </>
              )}
            </p>
          </div>
        </div>
      </div>

      {/* Tabs - Option A: Hybride (3 onglets) */}
      <Tabs value={activeTab} onValueChange={setActiveTab} className="flex-1 flex flex-col">
        <div className="border-b px-6">
          <TabsList className="h-10 w-fit gap-1 bg-muted/50 p-1 rounded-lg">
            <TabsTrigger
              value="sources"
              className="px-3 data-[state=active]:bg-background data-[state=active]:shadow-sm rounded-md"
            >
              <Database className="mr-2 h-4 w-4" />
              {t('groupPanel.tabs.sources')}
            </TabsTrigger>
            <TabsTrigger
              value="content"
              className="px-3 data-[state=active]:bg-background data-[state=active]:shadow-sm rounded-md"
            >
              <LayoutGrid className="mr-2 h-4 w-4" />
              {t('groupPanel.tabs.content')}
            </TabsTrigger>
            <TabsTrigger
              value="index"
              className="px-3 data-[state=active]:bg-background data-[state=active]:shadow-sm rounded-md"
            >
              <ListOrdered className="mr-2 h-4 w-4" />
              {t('groupPanel.tabs.index')}
            </TabsTrigger>
          </TabsList>
        </div>

        {/* Tab Content */}
        <TabsContent value="sources" className="flex-1 m-0 p-6 overflow-auto">
          <SourcesTab reference={reference} />
        </TabsContent>

        <TabsContent value="content" className="flex-1 m-0 overflow-hidden">
          <ContentTab reference={reference} />
        </TabsContent>

        <TabsContent value="index" className="flex-1 m-0 p-6 overflow-auto">
          <IndexTab reference={reference} />
        </TabsContent>
      </Tabs>
    </div>
  )
}

function SourcesTab({ reference }: { reference: ReferenceInfo }) {
  const { t } = useTranslation(['sources', 'common'])
  const [addDialogOpen, setAddDialogOpen] = useState(false)

  // Fetch configured sources
  const { data: sourcesData, isLoading: sourcesLoading } = useSources(reference.name)
  const sources = sourcesData?.sources ?? []

  // Remove source mutation
  const removeMutation = useRemoveSource(reference.name)

  const handleRemoveSource = (sourceName: string) => {
    removeMutation.mutate(sourceName)
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-lg font-medium">{t('groupPanel.sourcesTab.title')}</h2>
        <p className="text-sm text-muted-foreground">
          {t('groupPanel.sourcesTab.description', { name: reference.name })}
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        {/* Primary source - occurrences */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">{t('groupPanel.sourcesTab.primarySource')}</CardTitle>
            <CardDescription>
              {t('groupPanel.sourcesTab.primarySourceDesc')}
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="rounded-md bg-muted p-3">
              <p className="font-mono text-sm">{t('groupPanel.sourcesTab.occurrences')}</p>
              <p className="mt-1 text-xs text-muted-foreground">
                {t('groupPanel.sourcesTab.relation')}: {reference.kind === 'hierarchical' ? t('groupPanel.sourcesTab.nestedSet') : t('groupPanel.sourcesTab.directReference')}
              </p>
            </div>
          </CardContent>
        </Card>

        {/* Pre-calculated sources */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0">
            <div>
              <CardTitle className="text-base">{t('groupPanel.sourcesTab.precomputed')}</CardTitle>
              <CardDescription>
                {t('groupPanel.sourcesTab.precomputedDesc')}
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
                onRemove={handleRemoveSource}
                isRemoving={removeMutation.isPending}
              />
            )}
          </CardContent>
        </Card>
      </div>

      {/* Schema fields */}
      {reference.schema_fields.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">{t('groupPanel.sourcesTab.schemaFields')}</CardTitle>
            <CardDescription>
              {t('groupPanel.sourcesTab.schemaFieldsDesc')}
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid gap-2 md:grid-cols-3">
              {reference.schema_fields.map((field) => (
                <div
                  key={field.name}
                  className="flex items-center justify-between rounded-md bg-muted p-2"
                >
                  <span className="font-mono text-sm">{field.name}</span>
                  {field.type && (
                    <Badge variant="outline" className="text-xs">
                      {field.type}
                    </Badge>
                  )}
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Add Source Dialog */}
      <AddSourceDialog
        open={addDialogOpen}
        onOpenChange={setAddDialogOpen}
        referenceName={reference.name}
        onSuccess={() => setAddDialogOpen(false)}
      />
    </div>
  )
}

function IndexTab({ reference }: { reference: ReferenceInfo }) {
  return (
    <div className="h-[calc(100vh-280px)]">
      <IndexConfigEditor groupBy={reference.name} />
    </div>
  )
}
