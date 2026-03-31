/**
 * CollectionsModule - Orchestrator for the Collections section
 *
 * Sidebar + content layout using ModuleLayout.
 * Reads URL to determine initial selection:
 *   /groups       -> overview
 *   /groups/:name -> collection detail
 *
 * Overview shows a card grid of all reference collections.
 * Collection detail delegates to CollectionPanel.
 */

import { useState, useEffect } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useReferences } from '@/hooks/useReferences'
import { useNavigationStore } from '@/stores/navigationStore'
import { ModuleLayout } from '@/components/layout/ModuleLayout'
import { StalenessBanner } from '@/components/pipeline/StalenessBanner'
import { CollectionsTree, type CollectionsSelection } from './CollectionsTree'
import { CollectionPanel } from './CollectionPanel'
import { CollectionsOverview } from './CollectionsOverview'
import { ApiSettingsPanel } from './api/ApiSettingsPanel'
import { Layers } from 'lucide-react'

// =============================================================================
// URL HELPERS
// =============================================================================

function selectionFromPath(pathname: string): CollectionsSelection {
  if (pathname === '/groups/api-settings') {
    return { type: 'api-settings' }
  }
  const match = pathname.match(/^\/groups\/(.+)$/)
  if (match) {
    return { type: 'collection', name: decodeURIComponent(match[1]) }
  }
  return { type: 'overview' }
}

// =============================================================================
// COMPONENT
// =============================================================================

export function CollectionsModule() {
  const { t } = useTranslation(['sources', 'common'])
  const location = useLocation()
  const navigate = useNavigate()
  const setBreadcrumbs = useNavigationStore((s) => s.setBreadcrumbs)

  const { data: referencesData, isLoading } = useReferences()
  const references = referencesData?.references ?? []

  // Selection state — initialized from URL
  const [selection, setSelection] = useState<CollectionsSelection>(() =>
    selectionFromPath(location.pathname)
  )
  const [initialTab, setInitialTab] = useState<string | undefined>()

  // Sync selection when URL changes externally (e.g. browser back/forward)
  useEffect(() => {
    const newSelection = selectionFromPath(location.pathname)
    setSelection(newSelection)
  }, [location.pathname])

  // Update URL when selection changes
  const handleSelect = (newSelection: CollectionsSelection, tab?: string) => {
    setSelection(newSelection)
    setInitialTab(tab)
    if (newSelection.type === 'overview') {
      navigate('/groups')
    } else if (newSelection.type === 'api-settings') {
      navigate('/groups/api-settings')
    } else {
      navigate(`/groups/${encodeURIComponent(newSelection.name)}`)
    }
  }

  // Update breadcrumbs
  useEffect(() => {
    const crumbs: { label: string; path?: string }[] = [
      { label: t('collections.title', 'Collections'), path: '/groups' },
    ]

    if (selection.type === 'collection') {
      crumbs.push({ label: selection.name })
    } else if (selection.type === 'api-settings') {
      crumbs.push({ label: t('collections.apiSettings', 'API settings') })
    }

    setBreadcrumbs(crumbs)
    return () => setBreadcrumbs([])
  }, [selection, setBreadcrumbs, t])

  // ---------------------------------------------------------------------------
  // Content rendering
  // ---------------------------------------------------------------------------

  const renderContent = () => {
    // Loading state
    if (isLoading) {
      return (
        <div className="flex h-full items-center justify-center">
          <div className="animate-pulse text-muted-foreground">
            {t('common:status.loading')}
          </div>
        </div>
      )
    }

    // Empty state
    if (references.length === 0) {
      return (
        <div className="flex h-full items-center justify-center">
          <div className="max-w-md text-center">
            <Layers className="mx-auto mb-4 h-12 w-12 text-muted-foreground" />
            <h2 className="text-lg font-medium">
              {t('collections.noCollections', 'No collections')}
            </h2>
            <p className="mt-2 text-muted-foreground">
              {t('collections.noCollectionsHint', "Import data to create collections.")}
            </p>
            <button
              className="mt-4 text-primary hover:underline"
              onClick={() => navigate('/sources/import')}
            >
              {t('collections.importData', 'Import data')}
            </button>
          </div>
        </div>
      )
    }

    // Overview — enriched card grid
    if (selection.type === 'overview') {
      return (
        <CollectionsOverview
          references={references}
          onSelect={handleSelect}
        />
      )
    }

    // Collection detail
    if (selection.type === 'api-settings') {
      return <ApiSettingsPanel />
    }

    const reference = references.find((r) => r.name === selection.name)
    if (reference) {
      return <CollectionPanel reference={reference} initialTab={initialTab} />
    }

    // Collection not found
    return (
      <div className="flex h-full items-center justify-center">
        <div className="text-center">
          <h2 className="text-lg font-medium">
            {t('collections.notFound', 'Collection not found')}
          </h2>
          <p className="mt-1 text-muted-foreground">
            {t('collections.notFoundDesc', "La collection « {{name}} » n'existe pas.", {
              name: selection.name,
            })}
          </p>
          <button
            className="mt-4 text-primary hover:underline"
            onClick={() => handleSelect({ type: 'overview' })}
          >
            {t('collections.backToCollections', 'Back to collections')}
          </button>
        </div>
      </div>
    )
  }

  // ---------------------------------------------------------------------------
  // Render
  // ---------------------------------------------------------------------------

  return (
    <>
      <StalenessBanner stage="groups" />
      <ModuleLayout
        sidebar={
          <CollectionsTree
            references={references}
            referencesLoading={isLoading}
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
