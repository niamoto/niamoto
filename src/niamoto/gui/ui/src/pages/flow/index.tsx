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
import { useDatasets } from '@/hooks/useDatasets'
import { getEntities } from '@/lib/api/import'
import { useNavigationStore } from '@/stores/navigationStore'
import { DataPanel } from './DataPanel'
import { ImportWizard } from './panels/ImportWizard'
import { DataDashboard } from './panels/DataDashboard'
import { DatasetDetailPanel } from './panels/DatasetDetailPanel'
import { ReferenceDetailPanel } from './panels/ReferenceDetailPanel'
import { ReferenceViewPanel } from './ReferenceViewPanel'
import { GroupPanel } from './GroupPanel'
import { SitePanel } from './SitePanel'

export default function FlowPage() {
  const { data: referencesData } = useReferences()
  const { data: datasetsData } = useDatasets()
  const references = referencesData?.references ?? []
  const datasets = datasetsData?.datasets ?? []

  // Fetch entities (legacy - for DatasetViewPanel compatibility)
  const { data: entities } = useQuery({
    queryKey: ['entities'],
    queryFn: getEntities,
    staleTime: 30000,
  })
  const legacyDatasets = entities?.datasets ?? []

  // Get active panel from navigation store
  const { activePanel, setActivePanel } = useNavigationStore()

  // Check if we have any data
  const hasData = datasets.length > 0 || references.length > 0

  // Set default panel based on data availability
  useEffect(() => {
    if (!activePanel) {
      // If no data, show import wizard; otherwise show dashboard
      setActivePanel(hasData ? 'dashboard' : 'import')
    }
  }, [activePanel, setActivePanel, hasData])

  // Parse panel type and name
  const parsedPanel = parsePanel(activePanel)

  // Get current entities based on panel type
  const currentReference =
    (parsedPanel.type === 'group' || parsedPanel.type === 'reference')
      ? references.find((r) => r.name === parsedPanel.name)
      : undefined

  const currentDataset =
    parsedPanel.type === 'dataset'
      ? datasets.find((d) => d.name === parsedPanel.name) ||
        legacyDatasets.find((d) => d.name === parsedPanel.name)
      : undefined

  // Legacy reference-view support
  const currentReferenceView =
    parsedPanel.type === 'reference-view'
      ? references.find((r) => r.name === parsedPanel.name)
      : undefined

  return (
    <div className="h-full overflow-auto">
      {/* Import wizard panel */}
      {parsedPanel.type === 'import' && <ImportWizard />}

      {/* Dashboard panel */}
      {parsedPanel.type === 'dashboard' && <DataDashboard />}

      {/* Legacy data overview panel */}
      {parsedPanel.type === 'data' && <DataPanel />}

      {/* Dataset detail panel (new) */}
      {parsedPanel.type === 'dataset' && currentDataset && (
        <DatasetDetailPanel
          datasetName={currentDataset.name}
          tableName={currentDataset.table_name}
          entityCount={'entity_count' in currentDataset ? currentDataset.entity_count : undefined}
          onBack={() => setActivePanel('dashboard')}
        />
      )}

      {/* Reference detail panel with enrichment (new) */}
      {parsedPanel.type === 'reference' && currentReference && (
        <ReferenceDetailPanel
          referenceName={currentReference.name}
          tableName={currentReference.table_name}
          kind={currentReference.kind}
          entityCount={currentReference.entity_count}
          onBack={() => setActivePanel('dashboard')}
        />
      )}

      {/* Legacy reference view panel */}
      {parsedPanel.type === 'reference-view' && currentReferenceView && (
        <ReferenceViewPanel
          referenceName={currentReferenceView.name}
          tableName={currentReferenceView.table_name}
          kind={currentReferenceView.kind}
          onBack={() => setActivePanel('dashboard')}
        />
      )}

      {/* Group configuration panel (widgets) */}
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
        <DataDashboard />
      )}
    </div>
  )
}

// Parse panel string to type and optional name
function parsePanel(panel: string | null): {
  type: 'import' | 'dashboard' | 'data' | 'dataset' | 'reference' | 'reference-view' | 'group' | 'site-structure' | 'site-pages' | 'site-theme' | 'unknown'
  name?: string
} {
  if (!panel) {
    return { type: 'dashboard' }
  }

  // Direct types
  if (panel === 'import') return { type: 'import' }
  if (panel === 'dashboard') return { type: 'dashboard' }
  if (panel === 'data') return { type: 'data' }
  if (panel === 'site-structure') return { type: 'site-structure' }
  if (panel === 'site-pages') return { type: 'site-pages' }
  if (panel === 'site-theme') return { type: 'site-theme' }

  // Prefixed types: group-{name}, dataset-{name}, reference-{name}, reference-view-{name}
  if (panel.startsWith('group-')) {
    return { type: 'group', name: panel.substring(6) }
  }
  if (panel.startsWith('dataset-')) {
    return { type: 'dataset', name: panel.substring(8) }
  }
  if (panel.startsWith('reference-view-')) {
    return { type: 'reference-view', name: panel.substring(15) }
  }
  if (panel.startsWith('reference-')) {
    return { type: 'reference', name: panel.substring(10) }
  }

  return { type: 'unknown' }
}
