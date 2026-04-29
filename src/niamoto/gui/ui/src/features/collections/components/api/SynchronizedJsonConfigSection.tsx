import { useState, type ReactNode } from 'react'
import { useTranslation } from 'react-i18next'

import JsonField from '@/components/forms/fields/JsonField'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'

interface SynchronizedJsonConfigSectionProps<T> {
  name: string
  value: T
  onChange: (value: T) => void
  validate: (value: unknown) => value is T
  children: ReactNode
  jsonLabel?: string
  jsonDescription?: string
  showJsonPreview?: boolean
  jsonPreviewLabel?: string
  jsonPreviewValue?: unknown
  jsonPreviewLoading?: boolean
  jsonPreviewError?: string | null
}

export function SynchronizedJsonConfigSection<T>({
  name,
  value,
  onChange,
  validate,
  children,
  jsonLabel,
  jsonDescription,
  showJsonPreview = false,
  jsonPreviewLabel,
  jsonPreviewValue,
  jsonPreviewLoading = false,
  jsonPreviewError = null,
}: SynchronizedJsonConfigSectionProps<T>) {
  const { t } = useTranslation(['sources', 'common'])
  const [mode, setMode] = useState('visual')
  const [shapeError, setShapeError] = useState<string | null>(null)
  const previewLabel = jsonPreviewLabel ?? t('collectionPanel.api.jsonPreview')
  const previewValue = JSON.stringify(jsonPreviewValue ?? value, null, 2) ?? 'null'

  const handleJsonChange = (nextValue: unknown) => {
    if (validate(nextValue)) {
      setShapeError(null)
      onChange(nextValue)
      return
    }

    setShapeError(t('collectionPanel.api.jsonShapeError'))
  }

  return (
    <Tabs value={mode} onValueChange={setMode} className="space-y-3">
      <TabsList>
        <TabsTrigger value="visual">
          {t('collectionPanel.api.editorModes.visual')}
        </TabsTrigger>
        <TabsTrigger value="json">
          {t('collectionPanel.api.editorModes.json')}
        </TabsTrigger>
      </TabsList>
      <TabsContent value="visual">
        {showJsonPreview ? (
          <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_minmax(18rem,0.72fr)]">
            <div className="min-w-0">{children}</div>
            <aside className="min-w-0 rounded-md border bg-muted/30 p-3">
              <div className="mb-2 text-xs font-medium text-muted-foreground">
                {previewLabel}
              </div>
              {jsonPreviewLoading ? (
                <div className="rounded bg-background p-3 text-xs text-muted-foreground">
                  {t('collectionPanel.api.jsonPreviewLoading')}
                </div>
              ) : jsonPreviewError ? (
                <div className="rounded border border-destructive/30 bg-destructive/10 p-3 text-xs text-destructive">
                  {jsonPreviewError}
                </div>
              ) : (
                <pre
                  aria-label={previewLabel}
                  className="max-h-[28rem] overflow-auto whitespace-pre-wrap break-words rounded bg-background p-3 font-mono text-xs leading-relaxed text-foreground"
                >
                  {previewValue}
                </pre>
              )}
            </aside>
          </div>
        ) : (
          children
        )}
      </TabsContent>
      <TabsContent value="json" className="space-y-3">
        {shapeError && (
          <Alert variant="destructive">
            <AlertDescription>{shapeError}</AlertDescription>
          </Alert>
        )}
        <JsonField
          name={`${name}-json`}
          label={jsonLabel ?? t('collectionPanel.api.editorModes.json')}
          description={jsonDescription}
          value={value}
          onChange={handleJsonChange}
          error={shapeError ?? undefined}
        />
      </TabsContent>
    </Tabs>
  )
}
