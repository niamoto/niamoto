/**
 * YamlPreview - Shows generated YAML configuration
 *
 * With copy and download functionality
 */

import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Download, Copy, Check, FileCode } from 'lucide-react'
import yaml from 'js-yaml'
import type { AutoConfigureResponse } from '@/features/import/api/smart-config'

interface YamlPreviewProps {
  result: AutoConfigureResponse | null
  maxHeight?: string
}

export function YamlPreview({ result, maxHeight = '400px' }: YamlPreviewProps) {
  const [copied, setCopied] = useState(false)

  if (!result) {
    return (
      <div className="py-4 text-center text-sm text-muted-foreground">
        Aucune configuration à afficher
      </div>
    )
  }

  // Generate YAML
  const yamlConfig: Record<string, unknown> = {
    version: '1.0',
    entities: {
      datasets: result.entities.datasets || {},
      references: result.entities.references || {},
    },
  }

  // Add metadata if present
  if (result.entities.metadata) {
    yamlConfig.metadata = result.entities.metadata
  }
  if (result.auxiliary_sources?.length) {
    yamlConfig.auxiliary_sources = result.auxiliary_sources
  }

  const yamlString = yaml.dump(yamlConfig, {
    indent: 2,
    lineWidth: -1,
    noRefs: true,
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

  return (
    <div className="space-y-3">
      <div className="relative">
        <pre
          className="overflow-x-auto overflow-y-auto rounded-lg bg-muted p-4 font-mono text-sm"
          style={{ maxHeight }}
        >
          {yamlString}
        </pre>

        <div className="absolute right-2 top-2 flex gap-2">
          <Button variant="secondary" size="sm" onClick={handleCopy}>
            {copied ? (
              <>
                <Check className="mr-1 h-4 w-4" />
                Copié !
              </>
            ) : (
              <>
                <Copy className="mr-1 h-4 w-4" />
                Copier
              </>
            )}
          </Button>

          <Button variant="secondary" size="sm" onClick={handleDownload}>
            <Download className="mr-1 h-4 w-4" />
            Télécharger
          </Button>
        </div>
      </div>

      <Alert>
        <FileCode className="h-4 w-4" />
        <AlertDescription>
          Ce fichier YAML sera enregistré dans{' '}
          <code className="rounded bg-muted px-1 py-0.5">config/import.yml</code>
        </AlertDescription>
      </Alert>
    </div>
  )
}
