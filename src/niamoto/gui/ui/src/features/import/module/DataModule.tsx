/**
 * DataModule - Orchestrator for the Data (Sources) module
 *
 * Manages sidebar tree + content panel layout:
 * - Overview: ImportDashboard with exploration-oriented data stats
 * - Dataset detail: DatasetDetailPanel
 * - Reference detail: ReferenceDetailPanel
 * - Import wizard: ImportWizard
 */

import { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { useLocation, useNavigate } from 'react-router-dom'
import { Database, Upload } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { ModuleLayout } from '@/components/layout/ModuleLayout'
import { StalenessBanner } from '@/components/pipeline/StalenessBanner'
import { DataTree, type DataSelection } from './DataTree'
import { ImportWizard } from '@/features/import/components/ImportWizard'
import { ImportDashboard } from '@/features/import/components/dashboard/ImportDashboard'
import { DatasetDetailPanel } from '@/features/import/components/panels/DatasetDetailPanel'
import { ReferenceDetailPanel } from '@/features/import/components/panels/ReferenceDetailPanel'
import { useDatasets } from '@/hooks/useDatasets'
import { useReferences } from '@/hooks/useReferences'
import { useNavigationStore } from '@/stores/navigationStore'

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function selectionFromLocation(pathname: string): DataSelection {
  if (pathname === '/sources/import') return { type: 'import' }

  const datasetMatch = pathname.match(/^\/sources\/dataset\/(.+)$/)
  if (datasetMatch) return { type: 'dataset', name: decodeURIComponent(datasetMatch[1]) }

  const referenceMatch = pathname.match(/^\/sources\/reference\/(.+)$/)
  if (referenceMatch) return { type: 'reference', name: decodeURIComponent(referenceMatch[1]) }

  return { type: 'overview' }
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function DataModule() {
  const { t } = useTranslation(['sources', 'common'])
  const location = useLocation()
  const navigate = useNavigate()
  const setBreadcrumbs = useNavigationStore((s) => s.setBreadcrumbs)

  const { data: datasetsData, isLoading: datasetsLoading } = useDatasets()
  const { data: referencesData, isLoading: referencesLoading } = useReferences()

  const datasets = datasetsData?.datasets ?? []
  const references = referencesData?.references ?? []

  const [selection, setSelection] = useState<DataSelection>(() =>
    selectionFromLocation(location.pathname)
  )

  // Sync selection from URL on navigation (back/forward)
  useEffect(() => {
    setSelection(selectionFromLocation(location.pathname))
  }, [location.pathname])

  // Update URL when selection changes via sidebar
  const handleSelect = (sel: DataSelection) => {
    setSelection(sel)
    switch (sel.type) {
      case 'dataset':
        navigate(`/sources/dataset/${encodeURIComponent(sel.name)}`)
        break
      case 'reference':
        navigate(`/sources/reference/${encodeURIComponent(sel.name)}`)
        break
      case 'import':
        navigate('/sources/import')
        break
      case 'overview':
      default:
        navigate('/sources')
        break
    }
  }

  // Update breadcrumbs based on selection
  useEffect(() => {
    const crumbs: { label: string; path?: string }[] = [
      { label: t('common:breadcrumb.data', 'Data'), path: '/sources' },
    ]

    switch (selection.type) {
      case 'dataset':
        crumbs.push({ label: selection.name })
        break
      case 'reference':
        crumbs.push({ label: selection.name })
        break
      case 'import':
        crumbs.push({ label: t('common:breadcrumb.import', 'Import') })
        break
    }

    setBreadcrumbs(crumbs)
  }, [selection, setBreadcrumbs, t])

  // ---------------------------------------------------------------------------
  // Content rendering
  // ---------------------------------------------------------------------------

  const renderContent = () => {
    switch (selection.type) {
      case 'dataset': {
        const dataset = datasets.find((d) => d.name === selection.name)
        if (!dataset) {
          return (
            <div className="flex items-center justify-center h-full p-6">
              <p className="text-muted-foreground">
                {t('detail.datasetNotFound', 'Dataset not found')}
              </p>
            </div>
          )
        }
        return (
          <DatasetDetailPanel
            datasetName={dataset.name}
            tableName={dataset.table_name}
            entityCount={dataset.entity_count}
            onBack={() => handleSelect({ type: 'overview' })}
          />
        )
      }

      case 'reference': {
        const reference = references.find((r) => r.name === selection.name)
        if (!reference) {
          return (
            <div className="flex items-center justify-center h-full p-6">
              <p className="text-muted-foreground">
                {t('detail.referenceNotFound', 'Reference not found')}
              </p>
            </div>
          )
        }
        return (
          <ReferenceDetailPanel
            referenceName={reference.name}
            tableName={reference.table_name}
            kind={reference.kind}
            entityCount={reference.entity_count}
            onBack={() => handleSelect({ type: 'overview' })}
          />
        )
      }

      case 'import':
        return <ImportWizard />

      case 'overview':
      default: {
        const hasData = datasets.length > 0 || references.length > 0

        if (!hasData) {
          return (
            <div className="flex items-center justify-center h-full p-6">
              <Card className="max-w-md text-center">
                <CardHeader>
                  <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-muted">
                    <Database className="h-8 w-8 text-muted-foreground" />
                  </div>
                  <CardTitle>{t('dashboard.noData', 'No data')}</CardTitle>
                  <CardDescription>
                    {t(
                      'dashboard.noDataHint',
                      'Importez vos données pour commencer à explorer et analyser.'
                    )}
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <Button
                    onClick={() => handleSelect({ type: 'import' })}
                    size="lg"
                    className="gap-2"
                  >
                    <Upload className="h-4 w-4" />
                    {t('dashboard.importData', 'Import data')}
                  </Button>
                </CardContent>
              </Card>
            </div>
          )
        }

        return (
          <div className="p-6">
            <ImportDashboard
              onExploreEntity={(name) => handleSelect({ type: 'dataset', name })}
              onExploreReference={(name) => handleSelect({ type: 'reference', name })}
              onOpenGroup={(name) => navigate(`/groups/${encodeURIComponent(name)}`)}
              onEnrich={(name) =>
                navigate(`/sources/reference/${encodeURIComponent(name)}?tab=enrichment`)
              }
              onReimport={() => handleSelect({ type: 'import' })}
            />
          </div>
        )
      }
    }
  }

  // ---------------------------------------------------------------------------
  // Render
  // ---------------------------------------------------------------------------

  return (
    <>
      <StalenessBanner stage="data" />
      <ModuleLayout
        sidebar={
          <DataTree
            datasets={datasets}
            references={references}
            datasetsLoading={datasetsLoading}
            referencesLoading={referencesLoading}
            selection={selection}
            onSelect={handleSelect}
          />
        }
      >
        {renderContent()}
      </ModuleLayout>
    </>
  )
}
