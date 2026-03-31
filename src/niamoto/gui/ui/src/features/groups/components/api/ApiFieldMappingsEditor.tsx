import { useEffect, useMemo, useState } from 'react'
import { ChevronDown, ChevronUp, Plus, Sparkles, Trash2 } from 'lucide-react'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Textarea } from '@/components/ui/textarea'

import type { ApiExportFieldSuggestion } from '@/features/groups/hooks/useApiExportConfigs'

interface ApiFieldMappingsEditorProps {
  value?: Array<Record<string, unknown>>
  onChange: (value: Array<Record<string, unknown>>) => void
  suggestions?: ApiExportFieldSuggestion[]
  title: string
  description: string
}

interface ApiFieldMappingRow {
  outputName: string
  mode: 'source' | 'generator'
  source: string
  generator: string
  paramsText: string
}

function parseRows(value: Array<Record<string, unknown>> = []): ApiFieldMappingRow[] {
  return value.map((entry) => {
    const [outputName, rawConfig] = Object.entries(entry)[0] ?? ['', '']

    if (rawConfig && typeof rawConfig === 'object' && 'generator' in rawConfig) {
      const generatorConfig = rawConfig as {
        generator?: string
        params?: Record<string, unknown>
      }
      return {
        outputName,
        mode: 'generator',
        source: '',
        generator: generatorConfig.generator || '',
        paramsText: generatorConfig.params
          ? JSON.stringify(generatorConfig.params, null, 2)
          : '',
      }
    }

    return {
      outputName,
      mode: 'source',
      source: typeof rawConfig === 'string' ? rawConfig : '',
      generator: '',
      paramsText: '',
    }
  })
}

function serializeRows(rows: ApiFieldMappingRow[]): {
  value: Array<Record<string, unknown>>
  error: string | null
} {
  const serialized: Array<Record<string, unknown>> = []

  for (const row of rows) {
    if (!row.outputName.trim()) {
      continue
    }

    if (row.mode === 'generator') {
      let params: Record<string, unknown> | undefined
      if (row.paramsText.trim()) {
        try {
          params = JSON.parse(row.paramsText) as Record<string, unknown>
        } catch (error) {
          return {
            value: serialized,
            error:
              error instanceof Error
                ? error.message
                : 'Invalid JSON in generator params',
          }
        }
      }

      serialized.push({
        [row.outputName]: {
          generator: row.generator.trim(),
          ...(params ? { params } : {}),
        },
      })
      continue
    }

    serialized.push({
      [row.outputName]: row.source.trim(),
    })
  }

  return { value: serialized, error: null }
}

function createEmptyRow(): ApiFieldMappingRow {
  return {
    outputName: '',
    mode: 'source',
    source: '',
    generator: '',
    paramsText: '',
  }
}

export function ApiFieldMappingsEditor({
  value = [],
  onChange,
  suggestions = [],
  title,
  description,
}: ApiFieldMappingsEditorProps) {
  const [rows, setRows] = useState<ApiFieldMappingRow[]>(() =>
    value.length > 0 ? parseRows(value) : [createEmptyRow()]
  )
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    setRows(value.length > 0 ? parseRows(value) : [createEmptyRow()])
    setError(null)
  }, [value])

  const availableSuggestions = useMemo(
    () =>
      suggestions.filter(
        (suggestion) =>
          !rows.some((row) => row.outputName === suggestion.name && row.source === suggestion.source)
      ),
    [rows, suggestions]
  )

  const commit = (nextRows: ApiFieldMappingRow[]) => {
    setRows(nextRows)
    const serialized = serializeRows(nextRows)
    setError(serialized.error)
    if (
      !serialized.error &&
      JSON.stringify(serialized.value) !== JSON.stringify(value)
    ) {
      onChange(serialized.value)
    }
  }

  const updateRow = (
    index: number,
    key: keyof ApiFieldMappingRow,
    nextValue: string
  ) => {
    const nextRows = [...rows]
    nextRows[index] = { ...nextRows[index], [key]: nextValue }
    commit(nextRows)
  }

  const addRow = (row: ApiFieldMappingRow = createEmptyRow()) => {
    commit([...rows, row])
  }

  const removeRow = (index: number) => {
    const nextRows = rows.filter((_, currentIndex) => currentIndex !== index)
    commit(nextRows.length > 0 ? nextRows : [createEmptyRow()])
  }

  const moveRow = (index: number, direction: -1 | 1) => {
    const nextIndex = index + direction
    if (nextIndex < 0 || nextIndex >= rows.length) {
      return
    }
    const nextRows = [...rows]
    ;[nextRows[index], nextRows[nextIndex]] = [nextRows[nextIndex], nextRows[index]]
    commit(nextRows)
  }

  return (
    <div className="space-y-4 rounded-lg border p-4">
      <div className="space-y-1">
        <div className="flex items-center justify-between gap-2">
          <div>
            <h3 className="text-sm font-semibold">{title}</h3>
            <p className="text-sm text-muted-foreground">{description}</p>
          </div>
          <Button type="button" variant="outline" size="sm" onClick={() => addRow()}>
            <Plus className="mr-2 h-4 w-4" />
            Add field
          </Button>
        </div>
      </div>

      {availableSuggestions.length > 0 && (
        <div className="space-y-2">
          <div className="flex items-center gap-2 text-xs font-medium text-muted-foreground">
            <Sparkles className="h-3.5 w-3.5" />
            Suggestions
          </div>
          <div className="flex flex-wrap gap-2">
            {availableSuggestions.slice(0, 12).map((suggestion) => (
              <Button
                key={`${suggestion.name}-${suggestion.source}`}
                type="button"
                variant="secondary"
                size="sm"
                onClick={() =>
                  addRow({
                    outputName: suggestion.name,
                    mode: 'source',
                    source: suggestion.source,
                    generator: '',
                    paramsText: '',
                  })
                }
              >
                {suggestion.label || suggestion.name}
              </Button>
            ))}
          </div>
        </div>
      )}

      <div className="space-y-4">
        {rows.map((row, index) => (
          <div key={`${index}-${row.outputName}-${row.generator}`} className="rounded-md border p-3">
            <div className="mb-3 flex items-center justify-between gap-2">
              <Badge variant="outline">
                {row.outputName || `Field ${index + 1}`}
              </Badge>
              <div className="flex items-center gap-1">
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  className="h-8 w-8"
                  onClick={() => moveRow(index, -1)}
                  disabled={index === 0}
                >
                  <ChevronUp className="h-4 w-4" />
                </Button>
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  className="h-8 w-8"
                  onClick={() => moveRow(index, 1)}
                  disabled={index === rows.length - 1}
                >
                  <ChevronDown className="h-4 w-4" />
                </Button>
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  className="h-8 w-8 text-muted-foreground hover:text-destructive"
                  onClick={() => removeRow(index)}
                >
                  <Trash2 className="h-4 w-4" />
                </Button>
              </div>
            </div>

            <div className="grid gap-3 md:grid-cols-3">
              <div className="space-y-1">
                <Label>Output field</Label>
                <Input
                  value={row.outputName}
                  onChange={(event) =>
                    updateRow(index, 'outputName', event.target.value)
                  }
                  placeholder="scientificName"
                />
              </div>

              <div className="space-y-1">
                <Label>Mode</Label>
                <Select
                  value={row.mode}
                  onValueChange={(nextMode: 'source' | 'generator') =>
                    commit(
                      rows.map((currentRow, currentIndex) =>
                        currentIndex === index
                          ? {
                              ...currentRow,
                              mode: nextMode,
                              source:
                                nextMode === 'source' ? currentRow.source : '',
                              generator:
                                nextMode === 'generator' ? currentRow.generator : '',
                            }
                          : currentRow
                      )
                    )
                  }
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="source">Source field</SelectItem>
                    <SelectItem value="generator">Generator</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              {row.mode === 'source' ? (
                <div className="space-y-1">
                  <Label>Source path</Label>
                  <Input
                    value={row.source}
                    onChange={(event) => updateRow(index, 'source', event.target.value)}
                    placeholder="general_info.name.value"
                  />
                </div>
              ) : (
                <div className="space-y-1">
                  <Label>Generator</Label>
                  <Input
                    value={row.generator}
                    onChange={(event) =>
                      updateRow(index, 'generator', event.target.value)
                    }
                    placeholder="endpoint_url"
                  />
                </div>
              )}
            </div>

            {row.mode === 'generator' && (
              <div className="mt-3 space-y-1">
                <Label>Generator params (JSON)</Label>
                <Textarea
                  value={row.paramsText}
                  onChange={(event) =>
                    updateRow(index, 'paramsText', event.target.value)
                  }
                  rows={5}
                  placeholder='{"base_path":"/api"}'
                  className="font-mono text-sm"
                />
              </div>
            )}
          </div>
        ))}
      </div>

      {error && <p className="text-sm text-destructive">{error}</p>}
    </div>
  )
}
