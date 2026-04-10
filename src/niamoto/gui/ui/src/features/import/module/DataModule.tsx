/**
 * DataModule - Orchestrator for the Data (Sources) module
 *
 * Manages sidebar tree + content panel layout:
 * - Overview: SourcesOverview with readiness-oriented source summary
 * - Verification: Dedicated diagnostics workspace
 * - Enrichment: Dedicated API enrichment workspace
 * - Dataset detail: DatasetDetailPanel
 * - Reference detail: ReferenceDetailPanel
 * - Import wizard: ImportWizard
 */

import { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { useLocation, useNavigate } from 'react-router-dom'
import { ModuleLayout } from '@/components/layout/ModuleLayout'
import { PanelTransition } from '@/components/motion/PanelTransition'
import { DataTree, type DataSelection } from './DataTree'
import { ImportWizard } from '@/features/import/components/ImportWizard'
import { EnrichmentView } from '@/features/import/components/dashboard/EnrichmentView'
import { SourcesEmptyState } from '@/features/import/components/dashboard/SourcesEmptyState'
import { SourcesOverview } from '@/features/import/components/dashboard/SourcesOverview'
import { VerificationView } from '@/features/import/components/dashboard/VerificationView'
import { DatasetDetailPanel } from '@/features/import/components/panels/DatasetDetailPanel'
import { ReferenceDetailPanel } from '@/features/import/components/panels/ReferenceDetailPanel'
import { useDatasets } from '@/features/import/hooks/useDatasets'
import { useImportSummary } from '@/features/import/hooks/useImportSummary'
import { useReferences } from '@/features/import/hooks/useReferences'
import { useNavigationStore } from '@/stores/navigationStore'
import type { UploadedFileInfo } from '@/features/import/api/upload'

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function selectionFromLocation(pathname: string): DataSelection {
  if (pathname === '/sources/import') return { type: 'import' }
  if (pathname === '/sources/verification') return { type: 'verification' }
  if (pathname === '/sources/enrichment') return { type: 'enrichment' }

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
  const { data: importSummary } = useImportSummary()

  const datasets = datasetsData?.datasets ?? []
  const references = referencesData?.references ?? []
  const layerCount = importSummary?.layer_count ?? 0
  const hasImportedData = datasets.length > 0 || references.length > 0 || layerCount > 0

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
      case 'verification':
        navigate('/sources/verification')
        break
      case 'enrichment':
        navigate('/sources/enrichment')
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
      case 'verification':
        crumbs.push({ label: t('dashboard.verification.title', 'Verification tools') })
        break
      case 'enrichment':
        crumbs.push({ label: t('dashboard.enrichmentView.title', 'API enrichment') })
        break
    }

    setBreadcrumbs(crumbs)
    return () => setBreadcrumbs([])
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

      case 'verification':
        return <VerificationView />

      case 'enrichment':
        return <EnrichmentView />

      case 'overview':
      default: {
        if (!hasImportedData) {
          return (
            <SourcesEmptyState
              onFilesReady={(files: UploadedFileInfo[], paths: string[]) =>
                navigate('/sources/import', {
                  state: {
                    autoStart: true,
                    filePaths: paths,
                    uploadedFiles: files.map((file) => ({
                      name: file.filename,
                      path: file.path,
                      size: file.size,
                    })),
                  },
                })
              }
              onOpenImportWorkspace={() => handleSelect({ type: 'import' })}
            />
          )
        }

        return (
          <div className="h-full overflow-auto p-6">
            <SourcesOverview
              onExploreDataset={(name) => handleSelect({ type: 'dataset', name })}
              onExploreReference={(name) => handleSelect({ type: 'reference', name })}
              onOpenGroups={() => navigate('/groups')}
              onOpenGroup={(name) => navigate(`/groups/${encodeURIComponent(name)}`)}
              onReimport={() => handleSelect({ type: 'import' })}
              onOpenVerification={() => handleSelect({ type: 'verification' })}
              onOpenEnrichment={() => handleSelect({ type: 'enrichment' })}
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
    <ModuleLayout
      sidebar={
        <DataTree
          datasets={datasets}
          references={references}
          datasetsLoading={datasetsLoading}
          referencesLoading={referencesLoading}
          selection={selection}
          onSelect={handleSelect}
          hasImportedData={hasImportedData}
        />
      }
    >
      <PanelTransition transitionKey={`${selection.type}:${'name' in selection ? selection.name ?? '' : ''}`}>
        {renderContent()}
      </PanelTransition>
    </ModuleLayout>
  )
}
