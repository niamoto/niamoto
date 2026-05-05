/**
 * CollectionsModule - Orchestrator for the Collections section
 *
 * Reads URL to determine initial selection:
 *   /groups       -> overview
 *   /groups/:name -> collection detail
 *
 * Overview shows a card grid of all reference collections.
 * Collection detail delegates to CollectionPanel.
 */

import { useEffect, useMemo } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useReferences } from '@/hooks/useReferences'
import { useNavigationStore } from '@/stores/navigationStore'
import type { CollectionsSelection } from './CollectionsTree'
import { CollectionPanel } from './CollectionPanel'
import { CollectionsOverview } from './CollectionsOverview'
import { ApiSettingsPanel } from './api/ApiSettingsPanel'
import { CollectionReviewPanel } from './review/CollectionReviewPanel'
import { Layers } from 'lucide-react'
import { buildCollectionsPath, normalizeCollectionTab, selectionFromPath } from '../routing'
import { useCollectionsCatalog } from '../hooks/useCollectionsCatalog'
import {
  buildCollectionDisplayItems,
  defaultCollectionTab,
} from '../utils/collectionDisplay'

// =============================================================================
// COMPONENT
// =============================================================================

export function CollectionsModule() {
  const { t } = useTranslation(['sources', 'common'])
  const { pathname, search } = useLocation()
  const navigate = useNavigate()
  const setBreadcrumbs = useNavigationStore((s) => s.setBreadcrumbs)

  const { data: referencesData, isLoading } = useReferences()
  const { data: catalogData, isLoading: catalogLoading } = useCollectionsCatalog()
  const references = referencesData?.references ?? []
  const catalogCollections = catalogData?.collections ?? []
  const collectionItems = useMemo(
    () => buildCollectionDisplayItems(references, catalogCollections),
    [catalogCollections, references],
  )
  const isInitialLoading = (isLoading && !referencesData) || (catalogLoading && !catalogData)
  const pendingReviewCount = catalogCollections.filter(
    (collection) => collection.review_status === 'pending',
  ).length

  const selection = useMemo(() => selectionFromPath(pathname), [pathname])
  const initialTab = useMemo(
    () => normalizeCollectionTab(new URLSearchParams(search).get('tab')),
    [search]
  )

  // Update URL when selection changes
  const handleSelect = (newSelection: CollectionsSelection, tab?: string) => {
    const selectedCollection = newSelection.type === 'collection'
      ? collectionItems.find((item) => item.name === newSelection.name)
      : undefined
    navigate(
      buildCollectionsPath(newSelection, tab, {
        defaultTab: selectedCollection
          ? defaultCollectionTab(selectedCollection)
          : undefined,
      })
    )
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
    if (isInitialLoading) {
      return (
        <div className="flex h-full items-center justify-center">
          <div className="animate-pulse text-muted-foreground">
            {t('common:status.loading')}
          </div>
        </div>
      )
    }

    // API settings — always accessible regardless of collections
    if (selection.type === 'api-settings') {
      return <ApiSettingsPanel />
    }

    if (selection.type === 'review') {
      return <CollectionReviewPanel />
    }

    // Empty state
    if (collectionItems.length === 0 && catalogCollections.length === 0) {
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
          collectionItems={collectionItems}
          catalog={catalogData}
          pendingReviewCount={pendingReviewCount}
          onSelect={handleSelect}
        />
      )
    }

    const reference = collectionItems.find((r) => r.name === selection.name)
    if (reference) {
      const defaultTab = defaultCollectionTab(reference)
      return (
        <CollectionPanel
          reference={reference}
          initialTab={initialTab ?? defaultTab}
          collectionOptions={collectionItems}
          collectionMetadata={reference.collectionMetadata}
        />
      )
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

  const isScrollablePage =
    selection.type === 'overview'
    || selection.type === 'review'
    || selection.type === 'api-settings'

  return (
    <div className={isScrollablePage ? 'h-full overflow-y-auto' : 'h-full overflow-hidden'}>
      {renderContent()}
    </div>
  )
}
