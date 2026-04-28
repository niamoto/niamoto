/**
 * DatasetDetailPanel - Detailed view of a dataset entity with tabs
 *
 * Tabs:
 * - Summary: Identity, readiness cues, next actions
 * - Preview: Data preview
 * - Configuration: Edit dataset settings
 */

import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router-dom'
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
  Trash2,
  Loader2,
  Table2,
  Settings,
  Eye,
} from 'lucide-react'
import { TableBrowser } from '@/features/import/components/data-preview/TableBrowser'
import { DatasetConfigEditor } from '@/features/import/components/editors/DatasetConfigEditor'
import { SourceSummary } from '@/features/import/components/panels/SourceSummary'
import { deleteEntity } from '@/features/import/api/import'
import { importQueryKeys } from '@/features/import/queryKeys'
import { removeImportEntityFromCache } from '@/features/import/queryUtils'

interface DatasetDetailPanelProps {
  datasetName: string
  tableName: string
  entityCount?: number
  connectorType?: string
  path?: string
  onBack?: () => void
}

export function DatasetDetailPanel({
  datasetName,
  tableName,
  entityCount,
  connectorType,
  path,
  onBack,
}: DatasetDetailPanelProps) {
  const { t } = useTranslation(['common', 'sources'])
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [isDeleting, setIsDeleting] = useState(false)
  const [deleteTable, setDeleteTable] = useState(false)
  const [dialogOpen, setDialogOpen] = useState(false)
  const [activeTab, setActiveTab] = useState('summary')

  const openInDataExplorer = () => {
    navigate(`/tools/explorer?table=${encodeURIComponent(tableName)}`)
  }

  const handleDelete = async () => {
    setIsDeleting(true)
    try {
      await deleteEntity('dataset', datasetName, deleteTable)
      removeImportEntityFromCache(queryClient, {
        entityType: 'dataset',
        entityName: datasetName,
        tableName,
      })
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: importQueryKeys.all() }),
        queryClient.invalidateQueries({ queryKey: ['pipeline-status'] }),
      ])
      setDialogOpen(false)
      onBack?.()
    } catch (error) {
      console.error('Error deleting dataset:', error)
    } finally {
      setIsDeleting(false)
    }
  }

  return (
    <div className="flex h-full min-h-0 flex-col overflow-hidden">
      {/* Header */}
      <div className="flex shrink-0 items-center justify-between border-b p-4 pb-3">
        <div className="flex items-center gap-4">
          {onBack && (
            <Button variant="ghost" size="sm" onClick={onBack}>
              <ArrowLeft className="h-4 w-4" />
            </Button>
          )}
          <div>
            <h1 className="flex items-center gap-2 text-xl font-semibold">
              <Table2 className="h-5 w-5 text-primary" />
              {datasetName}
            </h1>
            <div className="flex items-center gap-2 text-muted-foreground">
              <span>Dataset</span>
              {entityCount != null && (
                <Badge variant="outline">
                  {entityCount.toLocaleString()} {t('file.rows')}
                </Badge>
              )}
              {connectorType && (
                <Badge variant="secondary">
                  {connectorType}
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
                {t('actions.delete')}
              </Button>
            </AlertDialogTrigger>
            <AlertDialogContent>
              <AlertDialogHeader>
                <AlertDialogTitle>{t('sources:dataset.deleteDataset', { name: datasetName })}</AlertDialogTitle>
                <AlertDialogDescription>
                  {t('sources:reference.deleteReferenceDescription')}
                </AlertDialogDescription>
              </AlertDialogHeader>
              <div className="flex items-center space-x-2 py-4">
                <Checkbox
                  id="delete-table"
                  checked={deleteTable}
                  onCheckedChange={(checked) => setDeleteTable(checked === true)}
                />
                <label
                  htmlFor="delete-table"
                  className="text-sm font-medium leading-none"
                >
                  {t('sources:dataset.deleteTableToo')}
                </label>
              </div>
              <AlertDialogFooter>
                <AlertDialogCancel>{t('actions.cancel')}</AlertDialogCancel>
                <AlertDialogAction
                  onClick={handleDelete}
                  disabled={isDeleting}
                  className="bg-destructive text-destructive-foreground"
                >
                  {isDeleting ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      {t('status.deleting')}
                    </>
                  ) : (
                    t('actions.delete')
                  )}
                </AlertDialogAction>
              </AlertDialogFooter>
            </AlertDialogContent>
          </AlertDialog>
        </div>
      </div>

      {/* Tabs */}
      <div className="min-h-0 flex-1 overflow-hidden p-4">
        <Tabs value={activeTab} onValueChange={setActiveTab} className="h-full min-h-0 gap-4">
          <TabsList className="shrink-0">
            <TabsTrigger value="summary" className="gap-1">
              <Table2 className="h-4 w-4" />
              {t('sources:reference.summary')}
            </TabsTrigger>
            <TabsTrigger value="preview" className="gap-1">
              <Eye className="h-4 w-4" />
              {t('sources:reference.preview')}
            </TabsTrigger>
            <TabsTrigger value="config" className="gap-1">
              <Settings className="h-4 w-4" />
              {t('sources:reference.configuration')}
            </TabsTrigger>
          </TabsList>

          <PanelTransition transitionKey={activeTab} className="min-h-0 flex-1 overflow-hidden">
            {activeTab === 'summary' ? (
              <div className="h-full overflow-auto overscroll-contain pr-1">
                <SourceSummary
                  entityType="dataset"
                  name={datasetName}
                  tableName={tableName}
                  rowCount={entityCount}
                  connectorType={connectorType}
                  path={path}
                  onPreview={() => setActiveTab('preview')}
                  onConfigure={() => setActiveTab('config')}
                  onOpenExplorer={openInDataExplorer}
                />
              </div>
            ) : activeTab === 'preview' ? (
              <div className="h-full overflow-auto overscroll-contain pr-1">
                <Card>
                  <CardHeader className="pb-3">
                    <CardTitle className="text-base">{t('sources:reference.dataPreview')}</CardTitle>
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
            ) : (
              <div className="h-full overflow-auto overscroll-contain pr-1">
                <DatasetConfigEditor datasetName={datasetName} />
              </div>
            )}
          </PanelTransition>
        </Tabs>
      </div>
    </div>
  )
}
