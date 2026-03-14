/**
 * PublishModule - Orchestrator for the Publish section
 *
 * Manages sidebar navigation (PublishTree) + content rendering
 * inside a shared ModuleLayout with resizable panels.
 */

import { useState, useEffect } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useNavigationStore } from '@/stores/navigationStore'
import { usePublishStore } from '@/stores/publishStore'
import { ModuleLayout } from '@/components/layout/ModuleLayout'
import { PublishTree, type PublishSelection } from './PublishTree'

import PublishOverviewContent from '@/pages/publish/index'
import PublishBuildContent from '@/pages/publish/build'
import PublishDeployContent from '@/pages/publish/deploy'
import PublishHistoryContent from '@/pages/publish/history'

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Derive initial selection from the current URL pathname. */
function selectionFromPath(pathname: string): PublishSelection {
  if (pathname.includes('/publish/build')) return { type: 'build' }
  if (pathname.includes('/publish/deploy')) return { type: 'deploy' }
  if (pathname.includes('/publish/history')) return { type: 'history' }
  return { type: 'overview' }
}

/** Map a selection back to a URL path. */
function pathFromSelection(sel: PublishSelection): string {
  switch (sel.type) {
    case 'build':
      return '/publish/build'
    case 'deploy':
      return '/publish/deploy'
    case 'history':
      return '/publish/history'
    case 'overview':
    default:
      return '/publish'
  }
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function PublishModule() {
  const location = useLocation()
  const navigate = useNavigate()
  const { t } = useTranslation('publish')
  const { setBreadcrumbs } = useNavigationStore()

  const { buildHistory, deployHistory } = usePublishStore()
  const lastBuild = buildHistory[0]
  const lastDeploy = deployHistory[0]

  const [selection, setSelection] = useState<PublishSelection>(() =>
    selectionFromPath(location.pathname)
  )

  // Keep selection in sync when the URL changes externally
  useEffect(() => {
    setSelection(selectionFromPath(location.pathname))
  }, [location.pathname])

  // Update breadcrumbs when selection changes
  useEffect(() => {
    const labels: Record<PublishSelection['type'], string> = {
      overview: t('overview.title', 'Overview'),
      build: t('build.title', 'Build'),
      deploy: t('deploy.title', 'Deploy'),
      history: t('history.title', 'History'),
    }

    setBreadcrumbs([
      { label: t('title', 'Publish'), path: '/publish' },
      { label: labels[selection.type] },
    ])
  }, [selection.type, setBreadcrumbs, t])

  const handleSelect = (sel: PublishSelection) => {
    setSelection(sel)
    navigate(pathFromSelection(sel), { replace: true })
  }

  // -------------------------------------------------------------------------
  // Content
  // -------------------------------------------------------------------------

  function renderContent() {
    switch (selection.type) {
      case 'build':
        return <PublishBuildContent />
      case 'deploy':
        return <PublishDeployContent />
      case 'history':
        return <PublishHistoryContent />
      case 'overview':
      default:
        return <PublishOverviewContent />
    }
  }

  // -------------------------------------------------------------------------
  // Render
  // -------------------------------------------------------------------------

  return (
    <ModuleLayout
      sidebar={
        <PublishTree
          selection={selection}
          lastBuildStatus={lastBuild?.status}
          lastDeployStatus={lastDeploy?.status}
          buildCount={buildHistory.length}
          deployCount={deployHistory.length}
          onSelect={handleSelect}
        />
      }
    >
      {renderContent()}
    </ModuleLayout>
  )
}
