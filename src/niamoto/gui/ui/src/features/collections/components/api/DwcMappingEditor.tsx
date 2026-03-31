import { useEffect, useMemo, useState } from 'react'
import { ChevronDown, ChevronUp, Plus, Trash2 } from 'lucide-react'
import { useTranslation } from 'react-i18next'

import { Alert, AlertDescription } from '@/components/ui/alert'
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

type DwcMappingMode = 'static' | 'source' | 'generator'

interface DwcMappingEditorProps {
  value?: Record<string, unknown>
  onChange: (value: Record<string, unknown>) => void
}

interface DwcMappingRow {
  term: string
  mode: DwcMappingMode
  staticValue: string
  reference: string
  generator: string
  paramsText: string
}

const KNOWN_GENERATORS = [
  'unique_occurrence_id',
  'unique_event_id',
  'unique_identification_id',
  'extract_specific_epithet',
  'extract_infraspecific_epithet',
  'format_event_date',
  'extract_year',
  'extract_month',
  'extract_day',
  'format_media_urls',
  'format_coordinates',
  'map_establishment_means',
  'map_occurrence_status',
  'format_measurements',
  'format_phenology',
  'format_habitat',
  'count_occurrences',
  'current_date',
  'count_processed_taxa',
  'count_total_occurrences',
]

function createEmptyRow(): DwcMappingRow {
  return {
    term: '',
    mode: 'source',
    staticValue: '',
    reference: '',
    generator: '',
    paramsText: '',
  }
}

function stringifyStaticValue(value: unknown): string {
  if (typeof value === 'string') {
    return value
  }

  if (value === null || value === undefined) {
    return ''
  }

  return JSON.stringify(value)
}

function parseRows(value: Record<string, unknown> = {}): DwcMappingRow[] {
  const rows: DwcMappingRow[] = Object.entries(value).map(([term, rawConfig]) => {
    if (
      rawConfig &&
      typeof rawConfig === 'object' &&
      'generator' in rawConfig &&
      typeof rawConfig.generator === 'string'
    ) {
      const generatorConfig = rawConfig as {
        generator: string
        params?: Record<string, unknown>
      }

      return {
        term,
        mode: 'generator' as const,
        staticValue: '',
        reference: '',
        generator: generatorConfig.generator,
        paramsText: generatorConfig.params
          ? JSON.stringify(generatorConfig.params, null, 2)
          : '',
      }
    }

    if (
      rawConfig &&
      typeof rawConfig === 'object' &&
      'source' in rawConfig &&
      typeof rawConfig.source === 'string'
    ) {
      return {
        term,
        mode: 'source' as const,
        staticValue: '',
        reference: rawConfig.source,
        generator: '',
        paramsText: '',
      }
    }

    if (typeof rawConfig === 'string' && rawConfig.startsWith('@')) {
      return {
        term,
        mode: 'source',
        staticValue: '',
        reference: rawConfig,
        generator: '',
        paramsText: '',
      }
    }

    return {
      term,
      mode: 'static',
      staticValue: stringifyStaticValue(rawConfig),
      reference: '',
      generator: '',
      paramsText: '',
    }
  })

  return rows.length > 0 ? rows : [createEmptyRow()]
}

function serializeRows(
  rows: DwcMappingRow[],
  t: (key: string, options?: Record<string, unknown>) => string
): {
  value: Record<string, unknown>
  error: string | null
} {
  const serialized: Record<string, unknown> = {}

  for (const row of rows) {
    const term = row.term.trim()

    if (!term) {
      continue
    }

    if (row.mode === 'generator') {
      const generator = row.generator.trim()
      if (!generator) {
        return {
          value: serialized,
          error: t('collectionPanel.api.mappingErrors.generatorRequired', { term }),
        }
      }

      let params: Record<string, unknown> | undefined
      if (row.paramsText.trim()) {
        try {
          params = JSON.parse(row.paramsText) as Record<string, unknown>
        } catch (error) {
          return {
            value: serialized,
            error:
              error instanceof Error
                ? t('collectionPanel.api.mappingErrors.invalidGeneratorParams', {
                    term,
                    message: error.message,
                  })
                : t('collectionPanel.api.mappingErrors.invalidGeneratorParams', { term }),
          }
        }
      }

      serialized[term] = {
        generator,
        ...(params ? { params } : {}),
      }
      continue
    }

    if (row.mode === 'source') {
      const reference = row.reference.trim()
      if (!reference) {
        return {
          value: serialized,
          error: t('collectionPanel.api.mappingErrors.sourceRequired', { term }),
        }
      }

      serialized[term] = reference
      continue
    }

    if (!row.staticValue.trim()) {
      return {
        value: serialized,
        error: t('collectionPanel.api.mappingErrors.staticValueRequired', { term }),
      }
    }

    serialized[term] = row.staticValue
  }

  return { value: serialized, error: null }
}

export function DwcMappingEditor({
  value = {},
  onChange,
}: DwcMappingEditorProps) {
  const { t } = useTranslation(['sources', 'common'])
  const [rows, setRows] = useState<DwcMappingRow[]>(() => parseRows(value))
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    setRows(parseRows(value))
    setError(null)
  }, [value])

  const generatorOptions = useMemo(() => {
    const extraGenerators = rows
      .map((row) => row.generator.trim())
      .filter((generator) => generator && !KNOWN_GENERATORS.includes(generator))

    return [...KNOWN_GENERATORS, ...extraGenerators]
  }, [rows])

  const commit = (nextRows: DwcMappingRow[]) => {
    setRows(nextRows)
    const serialized = serializeRows(nextRows, t)
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
    key: keyof DwcMappingRow,
    nextValue: string
  ) => {
    const nextRows = [...rows]
    nextRows[index] = { ...nextRows[index], [key]: nextValue }
    commit(nextRows)
  }

  const addRow = () => {
    commit([...rows, createEmptyRow()])
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
      <div className="flex items-start justify-between gap-4">
        <div className="space-y-1">
          <h3 className="text-sm font-semibold">{t('collectionPanel.api.dwcMapping')}</h3>
          <p className="text-sm text-muted-foreground">
            {t('collectionPanel.api.dwcMappingHelp')}
          </p>
        </div>
        <Button type="button" variant="outline" size="sm" onClick={addRow}>
          <Plus className="mr-2 h-4 w-4" />
          {t('common:actions.add')}
        </Button>
      </div>

      <p className="text-xs text-muted-foreground">
        {t('collectionPanel.api.dwcReferenceHelp')}
      </p>

      <div className="space-y-4">
        {rows.map((row, index) => (
          <div key={`${index}-${row.term}-${row.generator}`} className="rounded-md border p-3">
            <div className="mb-3 flex items-center justify-between gap-2">
              <Badge variant="outline">
                {row.term || t('collectionPanel.api.mappingTermFallback', { index: index + 1 })}
              </Badge>
              <div className="flex items-center gap-1">
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  className="h-8 w-8"
                  onClick={() => moveRow(index, -1)}
                  disabled={index === 0}
                  aria-label={t('collectionPanel.api.moveMappingUp')}
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
                  aria-label={t('collectionPanel.api.moveMappingDown')}
                >
                  <ChevronDown className="h-4 w-4" />
                </Button>
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  className="h-8 w-8 text-muted-foreground hover:text-destructive"
                  onClick={() => removeRow(index)}
                  aria-label={t('collectionPanel.api.removeMapping')}
                >
                  <Trash2 className="h-4 w-4" />
                </Button>
              </div>
            </div>

            <div className="grid gap-3 md:grid-cols-2">
              <div className="space-y-2">
                <Label>{t('collectionPanel.api.dwcTerm')}</Label>
                <Input
                  value={row.term}
                  onChange={(event) => updateRow(index, 'term', event.target.value)}
                  placeholder={t('collectionPanel.api.dwcTermPlaceholder')}
                />
              </div>

              <div className="space-y-2">
                <Label>{t('collectionPanel.api.mappingMode')}</Label>
                <Select
                  value={row.mode}
                  onValueChange={(mode: DwcMappingMode) => updateRow(index, 'mode', mode)}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="source">
                      {t('collectionPanel.api.mappingModes.source')}
                    </SelectItem>
                    <SelectItem value="static">
                      {t('collectionPanel.api.mappingModes.static')}
                    </SelectItem>
                    <SelectItem value="generator">
                      {t('collectionPanel.api.mappingModes.generator')}
                    </SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>

            {row.mode === 'source' && (
              <div className="mt-3 space-y-2">
                <Label>{t('collectionPanel.api.sourceReference')}</Label>
                <Input
                  value={row.reference}
                  onChange={(event) => updateRow(index, 'reference', event.target.value)}
                  placeholder={t('collectionPanel.api.sourceReferencePlaceholder')}
                />
              </div>
            )}

            {row.mode === 'static' && (
              <div className="mt-3 space-y-2">
                <Label>{t('collectionPanel.api.staticValue')}</Label>
                <Input
                  value={row.staticValue}
                  onChange={(event) => updateRow(index, 'staticValue', event.target.value)}
                  placeholder={t('collectionPanel.api.staticValuePlaceholder')}
                />
              </div>
            )}

            {row.mode === 'generator' && (
              <div className="mt-3 grid gap-3 md:grid-cols-2">
                <div className="space-y-2">
                  <Label>{t('collectionPanel.api.generator')}</Label>
                  <Select
                    value={row.generator || undefined}
                    onValueChange={(generator) => updateRow(index, 'generator', generator)}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder={t('collectionPanel.api.generatorPlaceholder')} />
                    </SelectTrigger>
                    <SelectContent>
                      {generatorOptions.map((generator) => (
                        <SelectItem key={generator} value={generator}>
                          {generator}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-2">
                  <Label>{t('collectionPanel.api.generatorParams')}</Label>
                  <Textarea
                    value={row.paramsText}
                    onChange={(event) => updateRow(index, 'paramsText', event.target.value)}
                    rows={5}
                    placeholder={t('collectionPanel.api.generatorParamsPlaceholder')}
                  />
                </div>
              </div>
            )}
          </div>
        ))}
      </div>

      {error && (
        <Alert variant="destructive">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}
    </div>
  )
}
