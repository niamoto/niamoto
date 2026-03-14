/**
 * EntityConfigEditor - Routes to the appropriate form based on entity type
 *
 * Handles editing of auto-detected entity configurations:
 * - Datasets: connector, schema, links
 * - References: derived (hierarchy), file, spatial (multi-source)
 * - Layers: metadata layers (raster/vector)
 */

import { DatasetConfigForm } from './DatasetConfigForm'
import { ReferenceConfigForm } from './ReferenceConfigForm'
import { LayerConfigForm } from './LayerConfigForm'

export type EntityType = 'dataset' | 'reference' | 'layer'

export interface DatasetConfig {
  connector: {
    type: string
    format?: string
    path: string
  }
  // Note: schema and links are NOT part of datasets in Niamoto
  // They belong to references only
}

export interface ReferenceConfig {
  kind?: 'hierarchical' | 'generic' | 'spatial'
  description?: string
  connector: {
    type: string // 'derived' | 'file' | 'file_multi_feature'
    format?: string
    path?: string
    source?: string // For derived references
    extraction?: {
      levels: Array<{ name: string; column: string }>
      id_column?: string
      name_column?: string
      id_strategy?: string
      incomplete_rows?: string
    }
    sources?: Array<{
      name: string
      path: string
      name_field?: string
      layer?: string
    }>
  }
  hierarchy?: {
    strategy: string
    levels: string[]
  }
  schema?: {
    id_field?: string
    fields?: Array<{ name: string; type: string; description?: string }>
  }
  links?: Array<{
    entity: string
    field: string
    target_field: string
  }>
  enrichment?: Array<{
    plugin: string
    enabled: boolean
    config: Record<string, any>
  }>
}

export interface LayerConfig {
  name: string
  type: 'raster' | 'vector'
  format?: string
  path: string
  description?: string
}

interface EntityConfigEditorProps {
  entityName: string
  entityType: EntityType
  config: DatasetConfig | ReferenceConfig | LayerConfig
  /** Available columns from auto-detection (for dropdowns) */
  detectedColumns?: string[]
  /** Available references (for FK links in datasets) */
  availableReferences?: Array<{
    name: string
    columns: string[]
  }>
  /** Available datasets (for derived reference source) */
  availableDatasets?: string[]
  /** Callback when config is updated */
  onSave: (updated: DatasetConfig | ReferenceConfig | LayerConfig) => void
  /** Optional callback for cancel */
  onCancel?: () => void
}

export function EntityConfigEditor({
  entityName,
  entityType,
  config,
  detectedColumns = [],
  availableReferences = [],
  availableDatasets = [],
  onSave,
  onCancel,
}: EntityConfigEditorProps) {
  switch (entityType) {
    case 'dataset':
      return (
        <DatasetConfigForm
          name={entityName}
          config={config as DatasetConfig}
          detectedColumns={detectedColumns}
          availableReferences={availableReferences}
          onSave={onSave}
          onCancel={onCancel}
        />
      )

    case 'reference':
      return (
        <ReferenceConfigForm
          name={entityName}
          config={config as ReferenceConfig}
          detectedColumns={detectedColumns}
          availableDatasets={availableDatasets}
          onSave={onSave}
          onCancel={onCancel}
        />
      )

    case 'layer':
      return (
        <LayerConfigForm
          config={config as LayerConfig}
          onSave={onSave}
          onCancel={onCancel}
        />
      )

    default:
      return (
        <div className="p-4 text-sm text-muted-foreground">
          Type d'entite non supporte: {entityType}
        </div>
      )
  }
}
