/**
 * ReferenceDetailPanel - Detailed view of a reference entity with tabs
 *
 * Tabs:
 * - Summary: Identity, readiness cues, next actions
 * - Hierarchy: Hierarchical reference inspection (conditional)
 * - Preview: Data preview
 * - Enrichment: API enrichment management (conditional)
 * - Configuration: Reference settings
 */

import { useState, useEffect, useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { useQueryClient } from '@tanstack/react-query'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Checkbox } from '@/components/ui/checkbox'
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { PanelTransition } from '@/components/motion/PanelTransition'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from '@/components/ui/alert-dialog'
import {
  ArrowLeft,
  ExternalLink,
  Leaf,
  Map,
  MapPin,
  Trash2,
  Loader2,
  Zap,
  Settings,
  Eye,
  GitBranch,
} from 'lucide-react'
import { TableBrowser } from '@/features/import/components/data-preview/TableBrowser'
import { ReferenceConfigEditor } from '@/features/import/components/editors/ReferenceConfigEditor'
import { EnrichmentTab } from '@/features/import/components/enrichment/EnrichmentTab'
import { HierarchyView } from '@/features/import/components/hierarchy/HierarchyView'
import { SourceSummary } from '@/features/import/components/panels/SourceSummary'
import { deleteEntity } from '@/features/import/api/import'
import { apiClient } from '@/shared/lib/api/client'
import { importQueryKeys } from '@/features/import/queryKeys'
import { removeImportEntityFromCache } from '@/features/import/queryUtils'

interface EnrichmentConfigSource {
  id: string
  label: string
  enabled: boolean
}

interface EnrichmentConfigResponse {
  enabled: boolean
  sources: EnrichmentConfigSource[]
}

interface ReferenceDetailPanelProps {
  referenceName: string
  tableName: string
  kind?: string
  entityCount?: number
  onBack?: () => void
}

export function ReferenceDetailPanel({
  referenceName,
  tableName,
  kind,
  entityCount,
  onBack,
}: ReferenceDetailPanelProps) {
  const { t } = useTranslation(['sources', 'common'])
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const queryClient = useQueryClient()
  const [isDeleting, setIsDeleting] = useState(false)
  const [deleteTable, setDeleteTable] = useState(false)
  const [dialogOpen, setDialogOpen] = useState(false)
  const [activeTab, setActiveTab] = useState('summary')
  const requestedTab = searchParams.get('tab')
  const requestedSource = searchParams.get('source')

  // Check if enrichment is configured for this reference
  const [enrichmentConfig, setEnrichmentConfig] = useState<EnrichmentConfigResponse | null>(null)

  // Reset to summary tab when reference changes
  useEffect(() => {
    if (requestedTab === 'enrichment' || requestedTab === 'config' || requestedTab === 'preview') {
      setActiveTab(requestedTab)
      return
    }
    if (requestedTab === 'hierarchy' && kind === 'hierarchical') {
      setActiveTab('hierarchy')
      return
    }
    setActiveTab('summary')
  }, [kind, referenceName, requestedTab])

  // Function to reload enrichment config (called after config changes)
  const reloadEnrichmentConfig = useCallback(async () => {
    try {
      const response = await apiClient.get(`/enrichment/config/${referenceName}`)
      if (response.data) {
        setEnrichmentConfig(response.data)
        return Boolean(response.data.sources?.some((source: EnrichmentConfigSource) => source.enabled))
      }
      setEnrichmentConfig(null)
      return false
    } catch {
      setEnrichmentConfig(null)
      return false
    }
  }, [referenceName])

  useEffect(() => {
    reloadEnrichmentConfig()
  }, [reloadEnrichmentConfig])

  const hasEnrichment = Boolean(enrichmentConfig?.sources?.some((source) => source.enabled))
  const referenceKindLabel =
    kind === 'hierarchical'
      ? t('reference.hierarchical')
      : kind === 'spatial'
        ? t('reference.spatial')
        : kind
          ? t('reference.file')
          : t('reference.file')

  const handleConfigSaved = async () => {
    await reloadEnrichmentConfig()
  }

  const openInDataExplorer = () => {
    navigate(`/tools/explorer?table=${encodeURIComponent(tableName)}`)
  }

  const handleDelete = async () => {
    setIsDeleting(true)
    try {
      await deleteEntity('reference', referenceName, deleteTable)
      removeImportEntityFromCache(queryClient, {
        entityType: 'reference',
        entityName: referenceName,
        tableName,
      })
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: importQueryKeys.all() }),
        queryClient.invalidateQueries({ queryKey: ['pipeline-status'] }),
      ])
      setDialogOpen(false)
      onBack?.()
    } catch (error) {
      console.error('Error deleting reference:', error)
    } finally {
      setIsDeleting(false)
    }
  }

  // Get icon based on kind
  const getKindIcon = () => {
    switch (kind) {
      case 'hierarchical':
        return <Leaf className="h-6 w-6 text-success" />
      case 'spatial':
        return <Map className="h-6 w-6 text-primary" />
      default:
        return <MapPin className="h-6 w-6 text-warning" />
    }
  }

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between border-b p-4 pb-3">
        <div className="flex items-center gap-4">
          {onBack && (
            <Button variant="ghost" size="sm" onClick={onBack}>
              <ArrowLeft className="h-4 w-4" />
            </Button>
          )}
          <div>
            <h1 className="flex items-center gap-2 text-xl font-semibold">
              {getKindIcon()}
              {referenceName}
            </h1>
            <div className="flex items-center gap-2 text-muted-foreground">
              <span>{t('reference.referenceKind', { kind: referenceKindLabel })}</span>
              {entityCount != null && (
                <Badge variant="outline">
                  {entityCount.toLocaleString()} {t('reference.entities')}
                </Badge>
              )}
              {hasEnrichment && (
                <Badge variant="secondary" className="gap-1">
                  <Zap className="h-3 w-3" />
                  {t('reference.apiEnrichment')}
                </Badge>
              )}
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <Button variant="outline" onClick={openInDataExplorer}>
            <ExternalLink className="mr-2 h-4 w-4" />
            Data Explorer
          </Button>

          <AlertDialog open={dialogOpen} onOpenChange={setDialogOpen}>
            <AlertDialogTrigger asChild>
              <Button variant="outline" className="text-destructive hover:bg-destructive/10">
                <Trash2 className="mr-2 h-4 w-4" />
                {t('common:actions.delete')}
              </Button>
            </AlertDialogTrigger>
            <AlertDialogContent>
              <AlertDialogHeader>
                <AlertDialogTitle>{t('reference.deleteReference', { name: referenceName })}</AlertDialogTitle>
                <AlertDialogDescription>
                  {t('reference.deleteReferenceDescription')}
                  {kind === 'hierarchical' && (
                    <span className="mt-2 block text-warning">
                      {t('reference.deleteWarningHierarchical')}
                    </span>
                  )}
                </AlertDialogDescription>
              </AlertDialogHeader>
              <div className="flex items-center space-x-2 py-4">
                <Checkbox
                  id="delete-table-ref"
                  checked={deleteTable}
                  onCheckedChange={(checked) => setDeleteTable(checked === true)}
                />
                <label htmlFor="delete-table-ref" className="text-sm font-medium leading-none">
                  {t('dataset.deleteTableToo')}
                </label>
              </div>
              <AlertDialogFooter>
                <AlertDialogCancel>{t('common:actions.cancel')}</AlertDialogCancel>
                <AlertDialogAction
                  onClick={handleDelete}
                  disabled={isDeleting}
                  className="bg-destructive text-destructive-foreground"
                >
                  {isDeleting ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      {t('common:status.deleting')}
                    </>
                  ) : (
                    t('common:actions.delete')
                  )}
                </AlertDialogAction>
              </AlertDialogFooter>
            </AlertDialogContent>
          </AlertDialog>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex-1 overflow-auto p-4">
        <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-4">
          <TabsList>
            <TabsTrigger value="summary" className="gap-1">
              <MapPin className="h-4 w-4" />
              {t('reference.summary')}
            </TabsTrigger>
            {kind === 'hierarchical' && (
              <TabsTrigger value="hierarchy" className="gap-1">
                <GitBranch className="h-4 w-4" />
                {t('reference.hierarchy')}
              </TabsTrigger>
            )}
            <TabsTrigger value="preview" className="gap-1">
              <Eye className="h-4 w-4" />
              {t('reference.preview')}
            </TabsTrigger>
            <TabsTrigger value="config" className="gap-1">
              <Settings className="h-4 w-4" />
              {t('reference.configuration')}
            </TabsTrigger>
            <TabsTrigger value="enrichment" className="gap-1">
              <Zap className="h-4 w-4" />
              {t('reference.apiEnrichment')}
            </TabsTrigger>
          </TabsList>

          <PanelTransition transitionKey={activeTab} className="min-h-0">
            {activeTab === 'summary' ? (
              <div className="space-y-4">
                <SourceSummary
                  entityType="reference"
                  name={referenceName}
                  tableName={tableName}
                  rowCount={entityCount}
                  kind={kind}
                  hasEnrichment={hasEnrichment}
                  hasHierarchy={kind === 'hierarchical'}
                  onPreview={() => setActiveTab('preview')}
                  onConfigure={() => setActiveTab('config')}
                  onOpenExplorer={openInDataExplorer}
                  onOpenHierarchy={
                    kind === 'hierarchical' ? () => setActiveTab('hierarchy') : undefined
                  }
                  onOpenEnrichment={() => setActiveTab('enrichment')}
                />
              </div>
            ) : activeTab === 'hierarchy' && kind === 'hierarchical' ? (
              <div className="space-y-4">
                <HierarchyView referenceName={referenceName} />
              </div>
            ) : activeTab === 'preview' ? (
              <div className="space-y-4">
                <Card>
                  <CardHeader className="pb-3">
                    <CardTitle className="text-base">{t('reference.dataPreview')}</CardTitle>
                    <CardDescription>Table: {tableName}</CardDescription>
                  </CardHeader>
                  <CardContent>
                    <TableBrowser
                      tableName={tableName}
                      pageSize={15}
                      maxColumns={6}
                      onOpenInExplorer={openInDataExplorer}
                    />
                  </CardContent>
                </Card>
              </div>
            ) : activeTab === 'enrichment' ? (
              <div className="space-y-4">
                <EnrichmentTab
                  referenceName={referenceName}
                  hasEnrichment={hasEnrichment}
                  onConfigSaved={handleConfigSaved}
                  initialSourceId={requestedSource}
                />
              </div>
            ) : (
              <div className="space-y-4">
                <ReferenceConfigEditor
                  referenceName={referenceName}
                  onSaved={handleConfigSaved}
                />
              </div>
            )}
          </PanelTransition>
        </Tabs>
      </div>
    </div>
  )
}
