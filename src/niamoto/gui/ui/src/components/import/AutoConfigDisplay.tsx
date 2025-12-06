/**
 * AutoConfigDisplay - Shows auto-configuration results
 *
 * Displays detected datasets, references, links, and metadata layers
 * Supports reclassification via drag & drop or buttons
 */

import { Alert, AlertDescription } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  CheckCircle2,
  AlertCircle,
  AlertTriangle,
  Database,
  Network,
  ChevronRight,
  Map,
  TrendingUp,
  Loader2,
  Sparkles,
  Globe2,
  Layers,
  ArrowRightLeft,
  FileSpreadsheet,
  Key,
  GitBranch,
  Link2,
  HelpCircle,
} from 'lucide-react'
import type { AutoConfigureResponse } from '@/lib/api/smart-config'

interface AutoConfigDisplayProps {
  result: AutoConfigureResponse | null
  isLoading?: boolean
  /** Callback when entities are reclassified */
  onReclassify?: (updatedEntities: AutoConfigureResponse['entities']) => void
  /** Whether reclassification is enabled */
  editable?: boolean
}

export function AutoConfigDisplay({
  result,
  isLoading = false,
  onReclassify,
  editable = false,
}: AutoConfigDisplayProps) {
  // Handle moving entity from dataset to reference
  const moveToReference = (name: string) => {
    if (!result || !onReclassify) return

    const datasetConfig = result.entities.datasets?.[name]
    if (!datasetConfig) return

    // Create new entities object with entity moved
    const newDatasets = { ...result.entities.datasets }
    delete newDatasets[name]

    const newReferences = {
      ...result.entities.references,
      [name]: {
        kind: 'flat', // Default to flat reference
        connector: datasetConfig.connector,
        schema: datasetConfig.schema || {
          id_field: 'id',
          fields: [],
        },
      },
    }

    onReclassify({
      ...result.entities,
      datasets: newDatasets,
      references: newReferences,
    })
  }

  // Handle moving entity from reference to dataset
  const moveToDataset = (name: string) => {
    if (!result || !onReclassify) return

    const refConfig = result.entities.references?.[name]
    if (!refConfig) return

    // Create new entities object with entity moved
    const newReferences = { ...result.entities.references }
    delete newReferences[name]

    const newDatasets = {
      ...result.entities.datasets,
      [name]: {
        connector: refConfig.connector,
      },
    }

    onReclassify({
      ...result.entities,
      datasets: newDatasets,
      references: newReferences,
    })
  }

  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center py-8">
        <div className="relative mb-4">
          <Sparkles className="h-12 w-12 animate-pulse text-primary" />
        </div>
        <h3 className="mb-2 text-lg font-semibold">Analyse en cours...</h3>
        <p className="text-center text-sm text-muted-foreground">
          Detection des hierarchies, relations et correspondances spatiales
        </p>
        <div className="mt-4 space-y-2 text-sm text-muted-foreground">
          <div className="flex items-center gap-2">
            <Loader2 className="h-4 w-4 animate-spin" />
            Analyse des colonnes et types
          </div>
        </div>
      </div>
    )
  }

  if (!result) {
    return null
  }

  const datasetCount = Object.keys(result.entities.datasets || {}).length
  const referenceCount = Object.keys(result.entities.references || {}).length
  const layerCount = result.entities.metadata?.layers?.length || 0

  // Build detection details list
  const buildDetectionDetails = () => {
    const details: Array<{
      icon: React.ReactNode
      text: string
      status: 'success' | 'warning' | 'info'
    }> = []

    // Check datasets
    const datasets = result.entities.datasets || {}
    Object.entries(datasets).forEach(([name, config]: [string, any]) => {
      // Format detected
      const format = config.connector?.format || config.connector?.type || 'file'
      details.push({
        icon: <FileSpreadsheet className="h-4 w-4" />,
        text: `Format ${format.toUpperCase()} reconnu pour "${name}"`,
        status: 'success',
      })

      // ID field
      if (config.schema?.id_field) {
        details.push({
          icon: <Key className="h-4 w-4" />,
          text: `Colonne ID trouvee: ${config.schema.id_field}`,
          status: 'success',
        })
      }

      // Links/relations
      if (config.links && config.links.length > 0) {
        config.links.forEach((link: any) => {
          const confidence = link.confidence || 0
          details.push({
            icon: <Link2 className="h-4 w-4" />,
            text: `Relation ${name}.${link.field} → ${link.entity}`,
            status: confidence >= 0.7 ? 'success' : 'warning',
          })
        })
      }
    })

    // Check references
    const references = result.entities.references || {}
    Object.entries(references).forEach(([name, config]: [string, any]) => {
      // Kind detected
      if (config.kind) {
        details.push({
          icon: <Database className="h-4 w-4" />,
          text: `Reference "${name}" de type ${config.kind}`,
          status: 'success',
        })
      }

      // Hierarchy levels
      if (config.hierarchy?.levels && config.hierarchy.levels.length > 0) {
        details.push({
          icon: <GitBranch className="h-4 w-4" />,
          text: `Hierarchie detectee: ${config.hierarchy.levels.join(' → ')}`,
          status: 'success',
        })
      }

      // Derived reference
      if (config.connector?.type === 'derived') {
        details.push({
          icon: <Network className="h-4 w-4" />,
          text: `Reference derivee de "${config.connector.source}"`,
          status: 'info',
        })
      }

      // Spatial with multiple sources
      if (config.connector?.type === 'file_multi_feature') {
        const sourceCount = config.connector.sources?.length || 0
        details.push({
          icon: <Map className="h-4 w-4" />,
          text: `${sourceCount} couches spatiales detectees`,
          status: 'success',
        })
      }
    })

    // Metadata layers
    if (layerCount > 0) {
      details.push({
        icon: <Globe2 className="h-4 w-4" />,
        text: `${layerCount} couche(s) metadata (rasters/vecteurs)`,
        status: 'success',
      })
    }

    return details
  }

  const detectionDetails = buildDetectionDetails()
  const successCount = detectionDetails.filter((d) => d.status === 'success').length
  const warningCount = detectionDetails.filter((d) => d.status === 'warning').length

  return (
    <div className="space-y-4">
      {/* Detection details panel */}
      <div className="rounded-lg border bg-muted/30 p-3">
        <h4 className="mb-3 flex items-center gap-2 text-sm font-semibold">
          <Sparkles className="h-4 w-4 text-primary" />
          Detection automatique
          <span className="ml-auto text-xs font-normal text-muted-foreground">
            {successCount} element(s) detecte(s)
            {warningCount > 0 && `, ${warningCount} a verifier`}
          </span>
        </h4>
        <div className="space-y-1.5">
          {detectionDetails.map((detail, idx) => (
            <div
              key={idx}
              className="flex items-center gap-2 text-sm"
            >
              <span
                className={
                  detail.status === 'success'
                    ? 'text-green-600'
                    : detail.status === 'warning'
                      ? 'text-amber-600'
                      : 'text-blue-600'
                }
              >
                {detail.status === 'success' ? (
                  <CheckCircle2 className="h-4 w-4" />
                ) : detail.status === 'warning' ? (
                  <AlertTriangle className="h-4 w-4" />
                ) : (
                  <HelpCircle className="h-4 w-4" />
                )}
              </span>
              <span
                className={
                  detail.status === 'warning' ? 'text-amber-700 dark:text-amber-400' : ''
                }
              >
                {detail.text}
              </span>
            </div>
          ))}
          {detectionDetails.length === 0 && (
            <p className="text-sm text-muted-foreground">
              Aucune structure detectee automatiquement
            </p>
          )}
        </div>
      </div>

      {/* Warnings */}
      {result.warnings && result.warnings.length > 0 && (
        <Alert>
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>
            <ul className="list-inside list-disc space-y-1">
              {result.warnings.map((warning, i) => (
                <li key={i} className="text-sm">
                  {warning}
                </li>
              ))}
            </ul>
          </AlertDescription>
        </Alert>
      )}

      {/* Entities grid */}
      <div className="grid gap-4 md:grid-cols-2">
        {/* Datasets */}
        <div className="rounded-lg border p-3">
          <h4 className="mb-2 flex items-center gap-2 text-sm font-semibold">
            <Database className="h-4 w-4 text-blue-500" />
            Datasets ({datasetCount})
          </h4>
          <div className="space-y-2">
            {Object.entries(result.entities.datasets || {}).map(
              ([name, config]: [string, any]) => (
                <div key={name} className="group rounded bg-accent p-2">
                  <div className="flex items-center justify-between">
                    <span className="font-medium">{name}</span>
                    {editable && onReclassify && (
                      <Button
                        variant="ghost"
                        size="sm"
                        className="h-6 gap-1 px-2 text-xs opacity-0 transition-opacity group-hover:opacity-100"
                        onClick={() => moveToReference(name)}
                        title="Deplacer vers les references"
                      >
                        <ArrowRightLeft className="h-3 w-3" />
                        <span className="hidden sm:inline">→ Reference</span>
                      </Button>
                    )}
                  </div>
                  <div className="mt-1 space-y-1 text-xs text-muted-foreground">
                    <div>Connecteur: {config.connector?.type || 'file'}</div>
                    {config.schema?.id_field && <div>ID: {config.schema.id_field}</div>}
                    {config.links && config.links.length > 0 && (
                      <div className="mt-1 space-y-1">
                        <div className="flex items-center gap-1 font-medium text-green-600">
                          <Network className="h-3 w-3" />
                          {config.links.length} relation(s):
                        </div>
                        {config.links.map((link: any, idx: number) => (
                          <div
                            key={idx}
                            className="flex flex-wrap items-center gap-1 rounded bg-green-50 p-1 dark:bg-green-950/20"
                          >
                            <span className="rounded bg-blue-100 px-1 font-mono dark:bg-blue-900">
                              {link.field}
                            </span>
                            <ChevronRight className="h-3 w-3" />
                            <span className="rounded bg-green-100 px-1 font-mono dark:bg-green-900">
                              {link.entity}.{link.target_field}
                            </span>
                            {link.confidence && (
                              <Badge variant="secondary" className="h-4 px-1 py-0 text-[10px]">
                                {Math.round(link.confidence * 100)}%
                              </Badge>
                            )}
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              )
            )}
            {datasetCount === 0 && (
              <p className="py-2 text-center text-xs text-muted-foreground">
                Aucun dataset detecte
              </p>
            )}
          </div>
        </div>

        {/* References */}
        <div className="rounded-lg border p-3">
          <h4 className="mb-2 flex items-center gap-2 text-sm font-semibold">
            <Network className="h-4 w-4 text-green-500" />
            References ({referenceCount})
          </h4>
          <div className="space-y-2">
            {Object.entries(result.entities.references || {}).map(
              ([name, config]: [string, any]) => {
                // Check if this reference can be moved to dataset
                // Derived references (from occurrences) should not be movable
                const canMove =
                  editable &&
                  onReclassify &&
                  config.connector?.type !== 'derived' &&
                  config.kind !== 'hierarchical'

                return (
                  <div key={name} className="group rounded bg-accent p-2">
                    <div className="flex items-center justify-between gap-2">
                      <div className="flex items-center gap-2">
                        <span className="font-medium">{name}</span>
                        {config.kind && (
                          <Badge variant="outline" className="text-xs">
                            {config.kind}
                          </Badge>
                        )}
                      </div>
                      {canMove && (
                        <Button
                          variant="ghost"
                          size="sm"
                          className="h-6 gap-1 px-2 text-xs opacity-0 transition-opacity group-hover:opacity-100"
                          onClick={() => moveToDataset(name)}
                          title="Deplacer vers les datasets"
                        >
                          <ArrowRightLeft className="h-3 w-3" />
                          <span className="hidden sm:inline">→ Dataset</span>
                        </Button>
                      )}
                    </div>
                    <div className="mt-1 space-y-1 text-xs text-muted-foreground">
                      {config.connector?.type === 'derived' && (
                        <div className="text-blue-600">
                          Derive de: {config.connector.source}
                        </div>
                      )}
                      {config.connector?.type === 'file_multi_feature' && (
                        <div className="space-y-0.5">
                          <div className="text-purple-600">Multi-source:</div>
                          {config.connector.sources?.slice(0, 3).map((source: any, idx: number) => (
                            <div key={idx} className="pl-2">
                              {source.name}
                            </div>
                          ))}
                          {config.connector.sources?.length > 3 && (
                            <div className="pl-2 text-muted-foreground">
                              +{config.connector.sources.length - 3} autres
                            </div>
                          )}
                        </div>
                      )}
                      {config.hierarchy?.levels && (
                        <div>Niveaux: {config.hierarchy.levels.join(' → ')}</div>
                      )}
                      {/* Referenced by */}
                      {result.entities.referenced_by?.[name] && (
                        <div className="mt-1 border-t pt-1">
                          <span className="text-blue-600">
                            Reference par: {result.entities.referenced_by[name].length} dataset(s)
                          </span>
                        </div>
                      )}
                    </div>
                  </div>
                )
              }
            )}
            {referenceCount === 0 && (
              <p className="py-2 text-center text-xs text-muted-foreground">
                Aucune reference detectee
              </p>
            )}
          </div>
        </div>
      </div>

      {/* Metadata Layers */}
      {layerCount > 0 && (
        <div className="rounded-lg border p-3">
          <h4 className="mb-2 flex items-center gap-2 text-sm font-semibold">
            <Map className="h-4 w-4 text-purple-500" />
            Couches metadata ({layerCount})
          </h4>
          <div className="grid grid-cols-2 gap-2">
            {result.entities.metadata?.layers?.map((layer: any, idx: number) => (
              <div key={idx} className="rounded bg-accent p-2">
                <div className="flex items-center gap-2 font-medium">
                  {layer.type === 'raster' ? (
                    <Globe2 className="h-4 w-4 text-orange-500" />
                  ) : (
                    <Layers className="h-4 w-4 text-purple-500" />
                  )}
                  <span className="truncate">{layer.name}</span>
                </div>
                <div className="text-xs text-muted-foreground">
                  {layer.type}
                  {layer.format && ` (${layer.format})`}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Summary */}
      <div className="rounded-lg border bg-muted/20 p-3">
        <h4 className="mb-2 flex items-center gap-2 text-sm font-semibold">
          <TrendingUp className="h-4 w-4" />
          Resume
        </h4>
        <div className="grid grid-cols-3 gap-4 text-center">
          <div>
            <div className="text-xl font-bold text-blue-500">{datasetCount}</div>
            <div className="text-xs text-muted-foreground">Datasets</div>
          </div>
          <div>
            <div className="text-xl font-bold text-green-500">{referenceCount}</div>
            <div className="text-xs text-muted-foreground">References</div>
          </div>
          <div>
            <div className="text-xl font-bold text-purple-500">{layerCount}</div>
            <div className="text-xs text-muted-foreground">Layers</div>
          </div>
        </div>
      </div>
    </div>
  )
}
