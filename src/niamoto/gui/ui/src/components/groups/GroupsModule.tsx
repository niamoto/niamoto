/**
 * GroupsModule - Orchestrator for the Groups section
 *
 * Sidebar + content layout using ModuleLayout.
 * Reads URL to determine initial selection:
 *   /groups       -> overview
 *   /groups/:name -> group detail
 *
 * Overview shows a card grid of all reference groups.
 * Group detail delegates to GroupPanel.
 */

import { useState, useEffect } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useReferences } from '@/hooks/useReferences'
import { useNavigationStore } from '@/stores/navigationStore'
import { ModuleLayout } from '@/components/layout/ModuleLayout'
import { StalenessBanner } from '@/components/pipeline/StalenessBanner'
import { GroupsTree, type GroupsSelection } from './GroupsTree'
import { GroupPanel } from '@/components/panels/GroupPanel'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Layers, ArrowRight } from 'lucide-react'

// =============================================================================
// URL HELPERS
// =============================================================================

function selectionFromPath(pathname: string): GroupsSelection {
  const match = pathname.match(/^\/groups\/(.+)$/)
  if (match) {
    return { type: 'group', name: decodeURIComponent(match[1]) }
  }
  return { type: 'overview' }
}

// =============================================================================
// COMPONENT
// =============================================================================

export function GroupsModule() {
  const { t } = useTranslation(['sources', 'common'])
  const location = useLocation()
  const navigate = useNavigate()
  const setBreadcrumbs = useNavigationStore((s) => s.setBreadcrumbs)

  const { data: referencesData, isLoading } = useReferences()
  const references = referencesData?.references ?? []

  // Selection state — initialized from URL
  const [selection, setSelection] = useState<GroupsSelection>(() =>
    selectionFromPath(location.pathname)
  )

  // Sync selection when URL changes externally (e.g. browser back/forward)
  useEffect(() => {
    const newSelection = selectionFromPath(location.pathname)
    setSelection(newSelection)
  }, [location.pathname])

  // Update URL when selection changes
  const handleSelect = (newSelection: GroupsSelection) => {
    setSelection(newSelection)
    if (newSelection.type === 'overview') {
      navigate('/groups')
    } else {
      navigate(`/groups/${encodeURIComponent(newSelection.name)}`)
    }
  }

  // Update breadcrumbs
  useEffect(() => {
    const crumbs: { label: string; path?: string }[] = [
      { label: t('groups.title', 'Groupes'), path: '/groups' },
    ]

    if (selection.type === 'group') {
      crumbs.push({ label: selection.name })
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
              {t('groups.noGroups', 'Aucun groupe')}
            </h2>
            <p className="mt-2 text-muted-foreground">
              {t('groups.noGroupsHint', "Importez des données pour créer des groupes.")}
            </p>
            <button
              className="mt-4 text-primary hover:underline"
              onClick={() => navigate('/sources/import')}
            >
              {t('groups.importData', 'Importer des données')}
            </button>
          </div>
        </div>
      )
    }

    // Overview — card grid
    if (selection.type === 'overview') {
      return (
        <div className="space-y-6 p-6">
          <div>
            <h1 className="text-2xl font-bold">{t('groups.title', 'Groupes')}</h1>
            <p className="mt-1 text-muted-foreground">
              {t('groups.description', 'Configurez les widgets et les sources de données pour chaque groupe.')}
            </p>
          </div>
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {references.map((ref) => (
              <Card
                key={ref.name}
                className="cursor-pointer transition-colors hover:border-primary"
                onClick={() => handleSelect({ type: 'group', name: ref.name })}
              >
                <CardHeader className="pb-2">
                  <div className="flex items-center justify-between">
                    <CardTitle className="text-lg">{ref.name}</CardTitle>
                    <ArrowRight className="h-4 w-4 text-muted-foreground" />
                  </div>
                  <CardDescription>
                    {t('groups.table', 'Table')}: {ref.table_name}
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="flex items-center gap-2">
                    <Badge variant="outline">{ref.kind}</Badge>
                    {ref.entity_count !== undefined && (
                      <Badge variant="secondary">
                        {ref.entity_count} {t('reference.entities', 'entités')}
                      </Badge>
                    )}
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      )
    }

    // Group detail
    const reference = references.find((r) => r.name === selection.name)
    if (reference) {
      return <GroupPanel reference={reference} />
    }

    // Group not found
    return (
      <div className="flex h-full items-center justify-center">
        <div className="text-center">
          <h2 className="text-lg font-medium">
            {t('groups.notFound', 'Groupe introuvable')}
          </h2>
          <p className="mt-1 text-muted-foreground">
            {t('groups.notFoundDesc', "Le groupe « {{name}} » n'existe pas.", {
              name: selection.name,
            })}
          </p>
          <button
            className="mt-4 text-primary hover:underline"
            onClick={() => handleSelect({ type: 'overview' })}
          >
            {t('groups.backToGroups', 'Retour aux groupes')}
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
          <GroupsTree
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
