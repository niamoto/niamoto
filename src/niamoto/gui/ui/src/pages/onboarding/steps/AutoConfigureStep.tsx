import { useEffect, useState } from 'react'
import { Button } from '@/components/ui/button'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import {
  Loader2,
  Sparkles,
  CheckCircle2,
  AlertCircle,
  Database,
  Network,
  ChevronRight,
  Map,
  TrendingUp
} from 'lucide-react'
import { autoConfigureEntities, type AutoConfigureResponse } from '@/lib/api/smart-config'
import type { WizardState } from '../QuickSetupWizard'

interface AutoConfigureStepProps {
  wizardState: WizardState
  updateState: (updates: Partial<WizardState>) => void
  onNext: () => void
  onBack: () => void
}

export default function AutoConfigureStep({
  wizardState,
  updateState,
  onNext,
  onBack
}: AutoConfigureStepProps) {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<AutoConfigureResponse | null>(null)

  useEffect(() => {
    // Auto-run detection when entering this step
    if (!result && wizardState.selectedFiles.length > 0) {
      runAutoConfig()
    }
  }, [])

  const runAutoConfig = async () => {
    try {
      setLoading(true)
      setError(null)

      const configResult = await autoConfigureEntities({
        files: wizardState.selectedFiles
      })

      setResult(configResult)
      updateState({ autoConfigResult: configResult })

    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'Failed to auto-configure entities')
    } finally {
      setLoading(false)
    }
  }

  const getConfidenceBadge = (confidence: number) => {
    if (confidence >= 0.8) {
      return <Badge className="bg-green-500">High confidence: {Math.round(confidence * 100)}%</Badge>
    } else if (confidence >= 0.6) {
      return <Badge className="bg-yellow-500">Medium confidence: {Math.round(confidence * 100)}%</Badge>
    } else {
      return <Badge variant="destructive">Low confidence: {Math.round(confidence * 100)}%</Badge>
    }
  }

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center py-16">
        <div className="relative mb-8">
          <Sparkles className="w-16 h-16 text-primary animate-pulse" />
        </div>
        <h3 className="text-xl font-semibold mb-2">Analyzing your files...</h3>
        <p className="text-muted-foreground text-center max-w-md">
          Our smart detection engine is analyzing {wizardState.selectedFiles.length} file(s),
          detecting hierarchies, relationships, and spatial correspondences.
        </p>
        <div className="mt-6 space-y-2 text-sm text-muted-foreground">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-green-500" />
            Detecting columns and types
          </div>
          <div className="flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-green-500" />
            Finding hierarchical structures
          </div>
          <div className="flex items-center gap-2">
            <Loader2 className="w-4 h-4 animate-spin" />
            Analyzing spatial relationships...
          </div>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="py-8 space-y-4">
        <Alert variant="destructive">
          <AlertCircle className="w-4 h-4" />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
        <div className="flex gap-2">
          <Button variant="outline" onClick={onBack}>Go Back</Button>
          <Button onClick={runAutoConfig}>Retry</Button>
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
  const totalEntities = datasetCount + referenceCount

  return (
    <div className="space-y-6">
      {/* Success header */}
      <div className="text-center pb-4 border-b">
        <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-green-500/10 mb-4">
          <CheckCircle2 className="w-8 h-8 text-green-500" />
        </div>
        <h2 className="text-2xl font-bold mb-2">Configuration Generated!</h2>
        <p className="text-muted-foreground">
          We detected <strong>{totalEntities} entities</strong> and <strong>{layerCount} metadata layers</strong>
        </p>
        <div className="mt-2">
          {getConfidenceBadge(result.confidence)}
        </div>
      </div>

      {/* Warnings */}
      {result.warnings && result.warnings.length > 0 && (
        <Alert>
          <AlertCircle className="w-4 h-4" />
          <AlertDescription>
            <ul className="list-disc list-inside space-y-1">
              {result.warnings.map((warning, i) => (
                <li key={i}>{warning}</li>
              ))}
            </ul>
          </AlertDescription>
        </Alert>
      )}

      {/* Detected entities */}
      <div className="grid md:grid-cols-2 gap-4">
        {/* Datasets */}
        <div className="border rounded-lg p-4">
          <h3 className="font-semibold flex items-center gap-2 mb-3">
            <Database className="w-5 h-5 text-blue-500" />
            Datasets ({datasetCount})
          </h3>
          <div className="space-y-2">
            {Object.entries(result.entities.datasets || {}).map(([name, config]: [string, any]) => (
              <div key={name} className="bg-accent rounded p-3">
                <div className="font-medium">{name}</div>
                <div className="text-xs text-muted-foreground mt-1 space-y-1">
                  <div>Connector: {config.connector?.type || 'file'}</div>
                  <div>ID: {config.schema?.id_field || 'id'}</div>
                  {config.schema?.fields && config.schema.fields.length > 0 && (
                    <div>
                      Fields: {config.schema.fields.map((f: any) => f.name).join(', ')}
                    </div>
                  )}
                  {config.links && config.links.length > 0 && (
                    <div className="mt-2 space-y-1">
                      <div className="flex items-center gap-1 text-green-600 font-medium">
                        <Network className="w-3 h-3" />
                        {config.links.length} link(s) detected:
                      </div>
                      {config.links.map((link: any, idx: number) => (
                        <div key={idx} className="pl-4 text-xs bg-green-50 dark:bg-green-950/20 rounded p-1.5">
                          <div className="flex items-center gap-1 flex-wrap">
                            <span className="font-mono bg-blue-100 dark:bg-blue-900 px-1 rounded">{link.field}</span>
                            <ChevronRight className="w-3 h-3" />
                            <span className="font-mono bg-green-100 dark:bg-green-900 px-1 rounded">
                              {link.entity}.{link.target_field}
                            </span>
                            {link.confidence && (
                              <Badge variant="secondary" className="text-[10px] px-1 py-0 h-4">
                                {Math.round(link.confidence * 100)}%
                              </Badge>
                            )}
                            {link.match_type && (
                              <span className="text-[10px] text-muted-foreground">
                                ({link.match_type.replace(/_/g, ' ')})
                              </span>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* References */}
        <div className="border rounded-lg p-4">
          <h3 className="font-semibold flex items-center gap-2 mb-3">
            <Network className="w-5 h-5 text-green-500" />
            References ({referenceCount})
          </h3>
          <div className="space-y-2">
            {Object.entries(result.entities.references || {}).map(([name, config]: [string, any]) => (
              <div key={name} className="bg-accent rounded p-3">
                <div className="font-medium">{name}</div>
                <div className="text-xs text-muted-foreground mt-1 space-y-1">
                  {config.kind && <Badge variant="outline">{config.kind}</Badge>}

                  {config.connector?.type === 'derived' && (
                    <div className="text-blue-600">
                      Derived from: {config.connector.source}
                    </div>
                  )}

                  {config.connector?.type === 'file_multi_feature' && (
                    <div className="space-y-1">
                      <div className="text-purple-600">Multi-source shapes:</div>
                      {config.connector.sources?.map((source: any, idx: number) => (
                        <div key={idx} className="pl-2 text-xs">
                          • {source.name} ({source.name_field})
                        </div>
                      ))}
                    </div>
                  )}

                  {config.hierarchy && config.hierarchy.levels && (
                    <div>
                      <div className="flex items-center gap-2">
                        <span>Levels: {config.hierarchy.levels.join(' → ')}</span>
                        {config.hierarchy.hierarchy_type && (
                          <Badge variant="outline" className="text-[10px] px-1 py-0 h-4">
                            {config.hierarchy.hierarchy_type}
                          </Badge>
                        )}
                      </div>
                    </div>
                  )}

                  {/* Show which datasets reference this */}
                  {result.entities.referenced_by && result.entities.referenced_by[name] && (
                    <div className="mt-2 pt-2 border-t">
                      <div className="flex items-center gap-1 text-blue-600 font-medium mb-1">
                        <TrendingUp className="w-3 h-3" />
                        Referenced by:
                      </div>
                      {result.entities.referenced_by[name].map((ref: any, idx: number) => (
                        <div key={idx} className="pl-4 text-xs bg-blue-50 dark:bg-blue-950/20 rounded p-1.5 mt-1">
                          <div className="flex items-center gap-1 flex-wrap">
                            <span className="font-medium">{ref.from}</span>
                            <span className="text-muted-foreground">via</span>
                            <span className="font-mono bg-blue-100 dark:bg-blue-900 px-1 rounded">{ref.field}</span>
                            <Badge variant="secondary" className="text-[10px] px-1 py-0 h-4">
                              {Math.round(ref.confidence * 100)}%
                            </Badge>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Metadata Layers */}
      {layerCount > 0 && (
        <div className="border rounded-lg p-4">
          <h3 className="font-semibold flex items-center gap-2 mb-3">
            <Map className="w-5 h-5 text-purple-500" />
            Metadata Layers ({layerCount})
          </h3>
          <div className="grid grid-cols-2 gap-2">
            {result.entities.metadata?.layers?.map((layer: any, idx: number) => (
              <div key={idx} className="bg-accent rounded p-3">
                <div className="font-medium flex items-center gap-2">
                  {layer.type === 'raster' ? '🌍' : '🗺️'}
                  <span>{layer.name}</span>
                </div>
                <div className="text-xs text-muted-foreground mt-1">
                  Type: {layer.type}
                  {layer.format && ` (${layer.format})`}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Configuration Summary */}
      <div className="border rounded-lg p-4 bg-muted/20">
        <h3 className="font-semibold flex items-center gap-2 mb-3">
          <TrendingUp className="w-5 h-5" />
          Configuration Summary
        </h3>
        <div className="grid grid-cols-3 gap-4 text-center">
          <div>
            <div className="text-2xl font-bold text-blue-500">{datasetCount}</div>
            <div className="text-sm text-muted-foreground">Datasets</div>
          </div>
          <div>
            <div className="text-2xl font-bold text-green-500">{referenceCount}</div>
            <div className="text-sm text-muted-foreground">References</div>
          </div>
          <div>
            <div className="text-2xl font-bold text-purple-500">{layerCount}</div>
            <div className="text-sm text-muted-foreground">Layers</div>
          </div>
        </div>
      </div>

      {/* Actions */}
      <div className="flex justify-between pt-4 border-t">
        <Button variant="outline" onClick={onBack}>
          Back
        </Button>

        <div className="flex gap-2">
          <Button variant="outline" onClick={runAutoConfig}>
            <Sparkles className="w-4 h-4 mr-2" />
            Re-analyze
          </Button>
          <Button onClick={onNext} size="lg">
            Review Configuration
            <ChevronRight className="w-4 h-4 ml-2" />
          </Button>
        </div>
      </div>
    </div>
  )
}
