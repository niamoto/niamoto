/**
 * ReferenceDetailPanel - Detailed view of a reference entity with tabs
 *
 * Tabs:
 * - Overview: Stats, hierarchy, data preview
 * - Enrichment: API enrichment management (conditional)
 * - Configuration: Reference settings
 */

import { useState, useEffect } from 'react'
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
  Database,
  Zap,
  Settings,
  LayoutDashboard,
} from 'lucide-react'
import { TableBrowser } from '@/features/import/components/data-preview/TableBrowser'
import { TableStats } from '@/features/import/components/data-preview/TableStats'
import { ReferenceConfigEditor } from '@/features/import/components/editors/ReferenceConfigEditor'
import { EnrichmentTab } from '@/features/import/components/enrichment/EnrichmentTab'
import { deleteEntity } from '@/features/import/api/import'
import { apiClient } from '@/shared/lib/api/client'

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
  hierarchyLevels?: string[]
  onBack?: () => void
}

export function ReferenceDetailPanel({
  referenceName,
  tableName,
  kind,
  entityCount,
  hierarchyLevels,
  onBack,
}: ReferenceDetailPanelProps) {
  const { t } = useTranslation(['sources', 'common'])
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const queryClient = useQueryClient()
  const [isDeleting, setIsDeleting] = useState(false)
  const [deleteTable, setDeleteTable] = useState(false)
  const [dialogOpen, setDialogOpen] = useState(false)
  const [activeTab, setActiveTab] = useState('overview')
  const requestedTab = searchParams.get('tab')

  // Check if enrichment is configured for this reference
  const [enrichmentConfig, setEnrichmentConfig] = useState<EnrichmentConfigResponse | null>(null)

  // Reset to overview tab when reference changes
  useEffect(() => {
    if (requestedTab === 'enrichment' || requestedTab === 'config') {
      setActiveTab(requestedTab)
      return
    }
    setActiveTab('overview')
  }, [referenceName, requestedTab])

  // Function to reload enrichment config (called after config changes)
  const reloadEnrichmentConfig = async () => {
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
  }

  useEffect(() => {
    reloadEnrichmentConfig()
  }, [referenceName])

  const hasEnrichment = Boolean(enrichmentConfig?.sources?.some((source) => source.enabled))

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
      queryClient.invalidateQueries({ queryKey: ['entities'] })
      queryClient.invalidateQueries({ queryKey: ['references'] })
      queryClient.invalidateQueries({ queryKey: ['datasets'] })
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
      <div className="flex items-center justify-between p-6 pb-4 border-b">
        <div className="flex items-center gap-4">
          {onBack && (
            <Button variant="ghost" size="sm" onClick={onBack}>
              <ArrowLeft className="h-4 w-4" />
            </Button>
          )}
          <div>
            <h1 className="flex items-center gap-2 text-2xl font-bold">
              {getKindIcon()}
              {referenceName}
            </h1>
            <div className="flex items-center gap-2 text-muted-foreground">
              <span>{t('reference.referenceKind', { kind: kind || 'generic' })}</span>
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
      <div className="flex-1 overflow-auto p-6">
        <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-4">
          <TabsList>
            <TabsTrigger value="overview" className="gap-1">
              <LayoutDashboard className="h-4 w-4" />
              {t('reference.overview')}
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
            {activeTab === 'overview' ? (
              <div className="space-y-6">
                {kind === 'hierarchical' && hierarchyLevels && hierarchyLevels.length > 0 && (
                  <Card>
                    <CardHeader className="pb-3">
                      <CardTitle className="flex items-center gap-2 text-base">
                        <Leaf className="h-4 w-4" />
                        {t('reference.hierarchy')}
                      </CardTitle>
                      <CardDescription>
                        {t('reference.hierarchyLevels', { count: hierarchyLevels.length })}
                      </CardDescription>
                    </CardHeader>
                    <CardContent>
                      <div className="flex items-center gap-2 flex-wrap">
                        {hierarchyLevels.map((level, idx) => (
                          <div key={level} className="flex items-center gap-2">
                            <Badge variant="outline">{level}</Badge>
                            {idx < hierarchyLevels.length - 1 && (
                              <span className="text-muted-foreground">→</span>
                            )}
                          </div>
                        ))}
                      </div>
                    </CardContent>
                  </Card>
                )}

                <Card>
                  <CardHeader className="pb-3">
                    <CardTitle className="flex items-center gap-2 text-base">
                      <Database className="h-4 w-4" />
                      {t('reference.statistics')}
                    </CardTitle>
                    <CardDescription>Table: {tableName}</CardDescription>
                  </CardHeader>
                  <CardContent>
                    <TableStats
                      tableName={tableName}
                      kind={kind}
                      hierarchyLevels={hierarchyLevels}
                    />
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader className="pb-3">
                    <CardTitle className="text-base">{t('reference.dataPreview')}</CardTitle>
                    <CardDescription>
                      {t('reference.firstRows')}
                    </CardDescription>
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
              <div className="space-y-6">
                <EnrichmentTab
                  referenceName={referenceName}
                  hasEnrichment={hasEnrichment}
                  onConfigSaved={handleConfigSaved}
                />
              </div>
            ) : (
              <div className="space-y-6">
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
