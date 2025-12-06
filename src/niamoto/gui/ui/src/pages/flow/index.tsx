/**
 * Niamoto Flow - Unified Configuration Interface
 *
 * Main page for configuring the complete Niamoto pipeline:
 * - Import data (occurrences, references)
 * - Configure widgets per group (references from import.yml)
 * - Structure the output site
 *
 * No hardcoded entity names - everything is discovered dynamically.
 */

import { useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useReferences } from '@/hooks/useReferences'
import { getEntities } from '@/lib/api/import'
import { useNavigationStore } from '@/stores/navigationStore'
import { DataPanel } from './DataPanel'
import { DatasetViewPanel } from './DatasetViewPanel'
import { ReferenceViewPanel } from './ReferenceViewPanel'
import { GroupPanel } from './GroupPanel'
import { SitePanel } from './SitePanel'

export default function FlowPage() {
  const { data: referencesData } = useReferences()
  const references = referencesData?.references ?? []

  // Fetch entities (datasets)
  const { data: entities } = useQuery({
    queryKey: ['entities'],
    queryFn: getEntities,
    staleTime: 30000,
  })

  const datasets = entities?.datasets ?? []

  // Get active panel from navigation store
  const { activePanel, setActivePanel } = useNavigationStore()

  // Set default panel if none selected
  useEffect(() => {
    if (!activePanel) {
      setActivePanel('data')
    }
  }, [activePanel, setActivePanel])

  // Parse panel type and name
  const parsedPanel = parsePanel(activePanel)

  // Get current reference if on group panel
  const currentReference =
    parsedPanel.type === 'group'
      ? references.find((r) => r.name === parsedPanel.name)
      : undefined

  // Get current dataset if on dataset panel
  const currentDataset =
    parsedPanel.type === 'dataset'
      ? datasets.find((d) => d.name === parsedPanel.name)
      : undefined

  // Get current reference for reference-view panel
  const currentReferenceView =
    parsedPanel.type === 'reference-view'
      ? references.find((r) => r.name === parsedPanel.name)
      : undefined

  return (
    <div className="h-full overflow-auto">
      {/* Data overview panel */}
      {parsedPanel.type === 'data' && <DataPanel />}

      {/* Dataset detail panel */}
      {parsedPanel.type === 'dataset' && currentDataset && (
        <DatasetViewPanel
          datasetName={currentDataset.name}
          tableName={currentDataset.table_name}
          connectorType={currentDataset.connector_type}
          path={currentDataset.path}
          onBack={() => setActivePanel('data')}
        />
      )}

      {/* Reference detail panel */}
      {parsedPanel.type === 'reference-view' && currentReferenceView && (
        <ReferenceViewPanel
          referenceName={currentReferenceView.name}
          tableName={currentReferenceView.table_name}
          kind={currentReferenceView.kind}
          onBack={() => setActivePanel('data')}
        />
      )}

      {/* Group configuration panel */}
      {parsedPanel.type === 'group' && currentReference && (
        <GroupPanel reference={currentReference} />
      )}

      {/* Site panels */}
      {parsedPanel.type === 'site-structure' && (
        <SitePanel subSection="structure" />
      )}
      {parsedPanel.type === 'site-pages' && (
        <SitePanel subSection="pages" />
      )}
      {parsedPanel.type === 'site-theme' && (
        <SitePanel subSection="theme" />
      )}

      {/* Fallback for unknown panel */}
      {parsedPanel.type === 'unknown' && (
        <DataPanel />
      )}
    </div>
  )
}

// Parse panel string to type and optional name
function parsePanel(panel: string | null): {
  type: 'data' | 'dataset' | 'reference-view' | 'group' | 'site-structure' | 'site-pages' | 'site-theme' | 'unknown'
  name?: string
} {
  if (!panel) {
    return { type: 'data' }
  }

  // Direct types
  if (panel === 'data') return { type: 'data' }
  if (panel === 'site-structure') return { type: 'site-structure' }
  if (panel === 'site-pages') return { type: 'site-pages' }
  if (panel === 'site-theme') return { type: 'site-theme' }

  // Prefixed types: group-{name}, dataset-{name}, reference-view-{name}
  if (panel.startsWith('group-')) {
    return { type: 'group', name: panel.substring(6) }
  }
  if (panel.startsWith('dataset-')) {
    return { type: 'dataset', name: panel.substring(8) }
  }
  if (panel.startsWith('reference-view-')) {
    return { type: 'reference-view', name: panel.substring(15) }
  }

  return { type: 'unknown' }
}
