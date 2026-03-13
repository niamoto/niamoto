/**
 * DataModule - Orchestrator for the Data (Sources) module
 *
 * Manages sidebar tree + content panel layout:
 * - Overview: ImportDashboard with data quality stats
 * - Dataset detail: DatasetDetailPanel
 * - Reference detail: ReferenceDetailPanel
 * - Import wizard: ImportWizard
 */

import { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { useLocation, useNavigate } from 'react-router-dom'
import { Upload, Database } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { ModuleLayout } from '@/components/layout/ModuleLayout'
import { StalenessBanner } from '@/components/pipeline/StalenessBanner'
import { DataTree, type DataSelection } from './DataTree'
import { ImportDashboard } from '@/components/sources/dashboard'
import { ImportWizard } from '@/components/sources'
import { DatasetDetailPanel } from '@/components/panels/DatasetDetailPanel'
import { ReferenceDetailPanel } from '@/components/panels/ReferenceDetailPanel'
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
      { label: t('breadcrumb.data', 'Données'), path: '/sources' },
    ]

    switch (selection.type) {
      case 'dataset':
        crumbs.push({ label: selection.name })
        break
      case 'reference':
        crumbs.push({ label: selection.name })
        break
      case 'import':
        crumbs.push({ label: t('breadcrumb.import', 'Import') })
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
                {t('detail.datasetNotFound', 'Dataset introuvable')}
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
                {t('detail.referenceNotFound', 'Référence introuvable')}
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
                  <CardTitle>{t('dashboard.noData', 'Aucune donnée')}</CardTitle>
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
                    {t('dashboard.importData', 'Importer des données')}
                  </Button>
                </CardContent>
              </Card>
            </div>
          )
        }

        return (
          <div className="space-y-6 p-6">
            {/* Header */}
            <div className="flex items-center justify-between">
              <div>
                <h1 className="text-2xl font-bold">
                  {t('dashboard.title', 'Tableau de bord des données')}
                </h1>
                <p className="text-muted-foreground">
                  {t(
                    'dashboard.description',
                    'Vue d\'ensemble de la qualité et de la complétude des données importées.'
                  )}
                </p>
              </div>
              <div className="flex gap-2">
                <Button
                  variant="outline"
                  onClick={() => handleSelect({ type: 'import' })}
                >
                  <Upload className="mr-2 h-4 w-4" />
                  {t('dashboard.import', 'Importer')}
                </Button>
              </div>
            </div>

            {/* Dashboard Content */}
            <ImportDashboard
              onExploreEntity={(name) => handleSelect({ type: 'dataset', name })}
              onEnrich={(name) => handleSelect({ type: 'reference', name })}
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
