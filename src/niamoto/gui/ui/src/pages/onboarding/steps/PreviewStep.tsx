import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { CheckCircle2, FileCode, Download, Copy, Check, AlertCircle } from 'lucide-react'
import type { WizardState } from '../QuickSetupWizard'
import yaml from 'js-yaml'

interface PreviewStepProps {
  wizardState: WizardState
  updateState: (_updates: Partial<WizardState>) => void
  onNext: () => void
  onBack: () => void
}

export default function PreviewStep({ wizardState, onNext, onBack }: PreviewStepProps) {
  const [copied, setCopied] = useState(false)

  if (!wizardState.autoConfigResult) {
    return (
      <Alert variant="destructive">
        <AlertCircle className="w-4 h-4" />
        <AlertDescription>No configuration found. Please go back and run auto-configure.</AlertDescription>
      </Alert>
    )
  }

  const result = wizardState.autoConfigResult

  // Generate YAML
  const yamlConfig: any = {
    version: '1.0',
    entities: {
      datasets: result.entities.datasets || {},
      references: result.entities.references || {}
    }
  }

  // Add metadata if present
  if (result.entities.metadata) {
    yamlConfig.metadata = result.entities.metadata
  }

  const yamlString = yaml.dump(yamlConfig, {
    indent: 2,
    lineWidth: -1,
    noRefs: true
  })

  const handleCopy = () => {
    navigator.clipboard.writeText(yamlString)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const handleDownload = () => {
    const blob = new Blob([yamlString], { type: 'text/yaml' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'import.yml'
    a.click()
    URL.revokeObjectURL(url)
  }

  const datasetCount = Object.keys(result.entities.datasets || {}).length
  const referenceCount = Object.keys(result.entities.references || {}).length
  const layerCount = result.entities.metadata?.layers?.length || 0

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="text-center pb-4 border-b">
        <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-blue-500/10 mb-4">
          <FileCode className="w-8 h-8 text-blue-500" />
        </div>
        <h2 className="text-2xl font-bold mb-2">Review Configuration</h2>
        <p className="text-muted-foreground">
          Check the generated import.yml before proceeding
        </p>
      </div>

      {/* Tabs */}
      <Tabs defaultValue="visual" className="w-full">
        <TabsList className="grid w-full grid-cols-2">
          <TabsTrigger value="visual">Visual Preview</TabsTrigger>
          <TabsTrigger value="yaml">YAML Source</TabsTrigger>
        </TabsList>

        <TabsContent value="visual" className="space-y-4">
          <div className="grid md:grid-cols-2 gap-4">
            {/* Datasets */}
            <div className="space-y-2">
              <h3 className="font-semibold">Datasets ({datasetCount})</h3>
              {Object.entries(result.entities.datasets || {}).map(([name, config]: [string, any]) => (
                <div key={name} className="border rounded-lg p-4 space-y-2">
                  <div className="font-medium text-lg">{name}</div>

                  <div className="space-y-1 text-sm">
                    <div className="flex items-center gap-2">
                      <Badge variant="outline">
                        {config.connector?.format || config.connector?.type || 'file'}
                      </Badge>
                      <span className="text-muted-foreground text-xs">
                        {config.connector?.path}
                      </span>
                    </div>

                    <div>
                      <strong>ID Field:</strong> {config.schema?.id_field || 'id'}
                    </div>

                    {config.schema?.fields && config.schema.fields.length > 0 && (
                      <div>
                        <strong>Fields:</strong>
                        <ul className="list-disc list-inside pl-2">
                          {config.schema.fields.map((field: any, i: number) => (
                            <li key={i}>
                              {field.name} <Badge variant="secondary" className="text-xs">{field.type}</Badge>
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}

                    {config.links && config.links.length > 0 && (
                      <div>
                        <strong>Links:</strong>
                        <ul className="list-disc list-inside pl-2">
                          {config.links.map((link: any, i: number) => (
                            <li key={i} className="text-green-600">
                              {link.field} → {link.entity}.{link.target_field}
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>

            {/* References */}
            <div className="space-y-2">
              <h3 className="font-semibold">References ({referenceCount})</h3>
              {Object.entries(result.entities.references || {}).map(([name, config]: [string, any]) => (
                <div key={name} className="border rounded-lg p-4 space-y-2">
                  <div className="font-medium text-lg flex items-center gap-2">
                    {name}
                    {config.kind && <Badge>{config.kind}</Badge>}
                  </div>

                  <div className="space-y-1 text-sm">
                    {config.connector?.type === 'derived' && (
                      <div className="bg-blue-50 dark:bg-blue-950 p-2 rounded">
                        <strong>Derived from:</strong> {config.connector.source}
                        {config.connector.extraction?.levels && (
                          <div className="mt-1 text-xs">
                            Levels: {config.connector.extraction.levels.map((l: any) => l.name).join(' → ')}
                          </div>
                        )}
                      </div>
                    )}

                    {config.connector?.type === 'file_multi_feature' && (
                      <div className="bg-purple-50 dark:bg-purple-950 p-2 rounded">
                        <strong>Multi-source shapes:</strong>
                        <ul className="list-disc list-inside pl-2 mt-1 text-xs">
                          {config.connector.sources?.map((source: any, idx: number) => (
                            <li key={idx}>
                              {source.name} ({source.name_field})
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}

                    {config.connector?.type === 'file' && (
                      <div className="flex items-center gap-2">
                        <Badge variant="outline">File</Badge>
                        <span className="text-muted-foreground text-xs">{config.connector.path}</span>
                      </div>
                    )}

                    {config.hierarchy && config.hierarchy.levels && (
                      <div>
                        <strong>Hierarchy:</strong> {config.hierarchy.levels.join(' → ')}
                        {config.hierarchy.hierarchy_type && (
                          <Badge variant="outline" className="ml-2 text-xs">
                            {config.hierarchy.hierarchy_type}
                          </Badge>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Detected Links Details */}
          {result.entities.detected_links && Object.keys(result.entities.detected_links).length > 0 && (
            <div className="border rounded-lg p-4 bg-blue-50 dark:bg-blue-950/20">
              <h3 className="font-semibold mb-3 flex items-center gap-2">
                <CheckCircle2 className="w-5 h-5 text-blue-600" />
                Detected Relationships
              </h3>
              <div className="space-y-3">
                {Object.entries(result.entities.detected_links).map(([dataset, links]) => (
                  <div key={dataset} className="bg-white dark:bg-gray-900 rounded-lg p-3">
                    <div className="font-medium mb-2">{dataset}</div>
                    <div className="space-y-2">
                      {(Array.isArray(links) ? links : []).map((link: any, idx: number) => (
                        <div key={idx} className="flex items-center gap-2 text-sm bg-accent/50 rounded p-2">
                          <div className="flex-1">
                            <span className="font-mono text-xs bg-blue-100 dark:bg-blue-900 px-2 py-1 rounded">
                              {link.field}
                            </span>
                            <span className="mx-2">→</span>
                            <span className="font-mono text-xs bg-green-100 dark:bg-green-900 px-2 py-1 rounded">
                              {link.entity}.{link.target_field}
                            </span>
                          </div>
                          {link.match_type && (
                            <Badge variant="outline" className="text-xs">
                              {link.match_type.replace(/_/g, ' ')}
                            </Badge>
                          )}
                          {link.confidence && (
                            <Badge
                              variant={link.confidence > 0.8 ? "default" : "secondary"}
                              className="text-xs"
                            >
                              {Math.round(link.confidence * 100)}%
                            </Badge>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Referenced By Summary */}
          {result.entities.referenced_by && Object.keys(result.entities.referenced_by).length > 0 && (
            <div className="border rounded-lg p-4 bg-green-50 dark:bg-green-950/20">
              <h3 className="font-semibold mb-3 flex items-center gap-2">
                <CheckCircle2 className="w-5 h-5 text-green-600" />
                References Detected
              </h3>
              <div className="text-sm space-y-2">
                {Object.entries(result.entities.referenced_by).map(([entity, refs]) => (
                  <div key={entity} className="bg-white dark:bg-gray-900 rounded p-2">
                    <span className="font-medium">{entity}</span> is referenced by:
                    <ul className="list-disc list-inside ml-4 mt-1">
                      {(Array.isArray(refs) ? refs : []).map((ref: any, idx: number) => (
                        <li key={idx}>
                          <span className="font-mono text-xs">{ref.from}</span> via{' '}
                          <span className="font-mono text-xs bg-blue-100 dark:bg-blue-900 px-1 rounded">
                            {ref.field}
                          </span>
                          {' '}
                          <Badge variant="secondary" className="text-xs ml-1">
                            {Math.round(ref.confidence * 100)}%
                          </Badge>
                        </li>
                      ))}
                    </ul>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Metadata Layers */}
          {layerCount > 0 && (
            <div className="border rounded-lg p-4">
              <h3 className="font-semibold mb-3">Metadata Layers ({layerCount})</h3>
              <div className="grid grid-cols-2 gap-2">
                {result.entities.metadata?.layers?.map((layer: any, idx: number) => (
                  <div key={idx} className="bg-accent rounded p-3">
                    <div className="font-medium">{layer.name}</div>
                    <div className="text-xs text-muted-foreground">
                      {layer.type} {layer.format && `(${layer.format})`}
                    </div>
                    <div className="text-xs text-muted-foreground truncate">
                      {layer.path}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </TabsContent>

        <TabsContent value="yaml" className="space-y-4">
          <div className="relative">
            <pre className="bg-muted p-4 rounded-lg overflow-x-auto text-sm font-mono max-h-[500px] overflow-y-auto">
              {yamlString}
            </pre>

            <div className="absolute top-2 right-2 flex gap-2">
              <Button
                variant="secondary"
                size="sm"
                onClick={handleCopy}
              >
                {copied ? (
                  <>
                    <Check className="w-4 h-4 mr-1" />
                    Copied!
                  </>
                ) : (
                  <>
                    <Copy className="w-4 h-4 mr-1" />
                    Copy
                  </>
                )}
              </Button>

              <Button
                variant="secondary"
                size="sm"
                onClick={handleDownload}
              >
                <Download className="w-4 h-4 mr-1" />
                Download
              </Button>
            </div>
          </div>

          <Alert>
            <FileCode className="w-4 h-4" />
            <AlertDescription>
              This YAML file is ready to use as <code className="bg-muted px-1 py-0.5 rounded">config/import.yml</code>
            </AlertDescription>
          </Alert>
        </TabsContent>
      </Tabs>

      {/* Validation Summary */}
      <div className="border rounded-lg p-4 bg-green-50 dark:bg-green-950/20">
        <div className="flex items-center gap-2 mb-2">
          <CheckCircle2 className="w-5 h-5 text-green-600" />
          <h3 className="font-semibold">Configuration Valid</h3>
        </div>
        <div className="grid grid-cols-3 gap-4 text-center text-sm">
          <div>
            <div className="font-bold text-blue-600">{datasetCount}</div>
            <div className="text-muted-foreground">Datasets</div>
          </div>
          <div>
            <div className="font-bold text-green-600">{referenceCount}</div>
            <div className="text-muted-foreground">References</div>
          </div>
          <div>
            <div className="font-bold text-purple-600">{layerCount}</div>
            <div className="text-muted-foreground">Layers</div>
          </div>
        </div>
      </div>

      {/* Actions */}
      <div className="flex justify-between pt-4 border-t">
        <Button variant="outline" onClick={onBack}>
          Back
        </Button>

        <Button onClick={onNext} size="lg">
          Start Import
          <CheckCircle2 className="w-4 h-4 ml-2" />
        </Button>
      </div>
    </div>
  )
}
