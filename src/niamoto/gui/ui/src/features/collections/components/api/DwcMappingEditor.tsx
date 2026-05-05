import { useEffect, useMemo, useRef, useState } from 'react'
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
import {
  FieldSelector,
  type FieldSelectorOption,
} from '@/features/collections/components/data/FieldSelector'

type DwcMappingMode = 'static' | 'source' | 'generator'

interface DwcMappingEditorProps {
  value?: Record<string, unknown>
  onChange: (value: Record<string, unknown>) => void
  title?: string
  description?: string
  referenceHelp?: string
  sourceFields?: string[]
  generatorOptions?: string[]
}

interface DwcMappingRow {
  id: string
  term: string
  mode: DwcMappingMode
  staticValue: string
  reference: string
  generator: string
  paramsText: string
}

const LEGACY_DWC_GENERATORS = [
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

const MEASUREMENT_FIELD_HINTS = new Set([
  'dbh',
  'diameter',
  'diameter_at_breast_height',
  'height',
  'tree_height',
  'strata',
  'flower',
  'fruit',
  'bark_thickness',
  'leaf_area',
  'leaf_ldmc',
  'leaf_sla',
  'leaf_thickness',
  'wood_density',
  'rainfall',
  'holdridge',
  'in_forest',
  'in_um',
])

let nextRowId = 0

function createRowId() {
  nextRowId += 1
  return `dwc-mapping-${nextRowId}`
}

function createEmptyRow(): DwcMappingRow {
  return {
    id: createRowId(),
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
  return Object.entries(value).map(([term, rawConfig]) => {
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
        id: createRowId(),
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
        id: createRowId(),
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
        id: createRowId(),
        term,
        mode: 'source',
        staticValue: '',
        reference: rawConfig,
        generator: '',
        paramsText: '',
      }
    }

    return {
      id: createRowId(),
      term,
      mode: 'static',
      staticValue: stringifyStaticValue(rawConfig),
      reference: '',
      generator: '',
      paramsText: '',
    }
  })
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

      serialized[term] = { source: toSourceReference(reference) }
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

function uniqueSourceFields(sourceFields: string[] = []) {
  const fields = sourceFields
    .map((field) => field.trim())
    .filter((field) => field.length > 0)
  return Array.from(new Set(fields))
}

function normalizeFieldName(value: string) {
  return value
    .toLowerCase()
    .trim()
    .replace(/[\s.:-]+/g, '_')
    .replace(/[^a-z0-9_]/g, '')
}

function normalizeSourceReference(reference: string) {
  const trimmed = reference.trim()
  if (trimmed.startsWith('@source.')) {
    return trimmed.replace(/^@source\./, '')
  }
  if (trimmed.startsWith('@') && trimmed.includes('.')) {
    return trimmed.replace(/^@[^.]+\./, '')
  }
  if (trimmed.startsWith('@')) {
    return trimmed.replace(/^@/, '')
  }
  return trimmed
}

function toSourceReference(reference: string) {
  const trimmed = reference.trim()
  if (!trimmed || trimmed.startsWith('@')) {
    return trimmed
  }
  return `@source.${trimmed}`
}

function sourceFieldSelectValue(reference: string, sourceFields: string[]) {
  const normalizedReference = normalizeSourceReference(reference)
  return sourceFields.includes(normalizedReference) ? normalizedReference : undefined
}

function sourceFieldGroup(field: string) {
  const [root] = field.split('.').filter(Boolean)
  if (!root) {
    return { key: 'fields', label: 'Fields' }
  }
  return {
    key: root,
    label: root
      .replace(/[_-]+/g, ' ')
      .replace(/\b\w/g, (letter) => letter.toUpperCase()),
  }
}

function guessGeometryField(sourceFields: string[]) {
  const preferred = ['geo_pt', 'geometry', 'geom', 'point', 'coordinates', 'geo_pt_geom']
  for (const candidate of preferred) {
    const match = sourceFields.find(
      (field) => normalizeFieldName(field) === candidate,
    )
    if (match) {
      return match
    }
  }
  return sourceFields.find((field) => {
    const normalized = normalizeFieldName(field)
    return normalized.includes('geom') || normalized.startsWith('geo_')
  })
}

function guessMeasurementFields(sourceFields: string[]) {
  return sourceFields.filter((field) =>
    MEASUREMENT_FIELD_HINTS.has(normalizeFieldName(field)),
  )
}

function suggestedGeneratorParamsText(
  row: DwcMappingRow,
  sourceFields: string[],
): string | null {
  const generator = row.generator.trim()
  if (!generator) {
    return null
  }

  if (generator === 'constant') {
    return JSON.stringify({ value: '' }, null, 2)
  }

  if (generator === 'unique_occurrence_id') {
    return JSON.stringify({ prefix: 'occurrence_' }, null, 2)
  }

  if (generator === 'extract_geometry_coordinate') {
    const source = guessGeometryField(sourceFields)
    if (!source) {
      return null
    }
    const normalizedTerm = normalizeFieldName(row.term)
    return JSON.stringify(
      {
        source,
        coordinate: normalizedTerm.includes('longitude') ? 'longitude' : 'latitude',
      },
      null,
      2,
    )
  }

  if (generator === 'format_measurements' || generator === 'dynamic_properties') {
    const fields = guessMeasurementFields(sourceFields)
    if (fields.length === 0) {
      return null
    }
    return JSON.stringify({ fields }, null, 2)
  }

  return null
}

export function DwcMappingEditor({
  value = {},
  onChange,
  title,
  description,
  referenceHelp,
  sourceFields = [],
  generatorOptions,
}: DwcMappingEditorProps) {
  return (
    <DwcMappingEditorForm
      value={value}
      onChange={onChange}
      title={title}
      description={description}
      referenceHelp={referenceHelp}
      sourceFields={sourceFields}
      generatorOptions={generatorOptions}
    />
  )
}

function DwcMappingEditorForm({
  value = {},
  onChange,
  title,
  description,
  referenceHelp,
  sourceFields = [],
  generatorOptions = LEGACY_DWC_GENERATORS,
}: DwcMappingEditorProps) {
  const { t } = useTranslation(['sources', 'common'])
  const [rows, setRows] = useState<DwcMappingRow[]>(() => parseRows(value))
  const [error, setError] = useState<string | null>(null)
  const externalValueKey = useMemo(() => JSON.stringify(value), [value])
  const lastExternalValueKeyRef = useRef(externalValueKey)
  const sourceFieldOptions = useMemo(
    () => uniqueSourceFields(sourceFields),
    [sourceFields],
  )
  const fieldSelectorOptions = useMemo<FieldSelectorOption[]>(
    () =>
      sourceFieldOptions.map((field) => {
        const group = sourceFieldGroup(field)
        return {
          value: field,
          label: field,
          description: field,
          groupKey: group.key,
          groupLabel: group.label,
        }
      }),
    [sourceFieldOptions],
  )

  useEffect(() => {
    if (externalValueKey === lastExternalValueKeyRef.current) {
      return
    }

    // The editor keeps local draft rows so invalid intermediate input can stay editable.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setRows(parseRows(value))
    setError(null)
    lastExternalValueKeyRef.current = externalValueKey
  }, [externalValueKey, value])

  const availableGeneratorOptions = useMemo(() => {
    const extraGenerators = rows
      .map((row) => row.generator.trim())
      .filter((generator) => generator && !generatorOptions.includes(generator))

    return [...generatorOptions, ...extraGenerators]
  }, [generatorOptions, rows])

  const commit = (nextRows: DwcMappingRow[]) => {
    setRows(nextRows)
    const serialized = serializeRows(nextRows, t)
    setError(serialized.error)
    const serializedKey = JSON.stringify(serialized.value)
    if (!serialized.error && serializedKey !== externalValueKey) {
      lastExternalValueKeyRef.current = serializedKey
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

  const updateGenerator = (index: number, generator: string) => {
    const nextRows = [...rows]
    const nextRow = {
      ...nextRows[index],
      generator,
    }
    if (!nextRow.paramsText.trim()) {
      nextRow.paramsText =
        suggestedGeneratorParamsText(nextRow, sourceFieldOptions) ?? ''
    }
    nextRows[index] = nextRow
    commit(nextRows)
  }

  const addRow = () => {
    commit([...rows, createEmptyRow()])
  }

  const removeRow = (index: number) => {
    const nextRows = rows.filter((_, currentIndex) => currentIndex !== index)
    commit(nextRows)
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
          <h3 className="text-sm font-semibold">
            {title ?? t('collectionPanel.api.dwcMapping')}
          </h3>
          <p className="text-sm text-muted-foreground">
            {description ?? t('collectionPanel.api.dwcMappingHelp')}
          </p>
        </div>
        <Button type="button" variant="outline" size="sm" onClick={addRow}>
          <Plus className="mr-2 h-4 w-4" />
          {t('common:actions.add')}
        </Button>
      </div>

      <p className="text-xs text-muted-foreground">
        {referenceHelp ?? t('collectionPanel.api.dwcReferenceHelp')}
      </p>

      <div className="space-y-4">
        {rows.length === 0 && (
          <div className="rounded-md border border-dashed bg-muted/20 p-4 text-sm text-muted-foreground">
            {t('collectionPanel.api.dwcMappingEmpty')}
          </div>
        )}
        {rows.map((row, index) => {
          const suggestedParamsText = suggestedGeneratorParamsText(
            row,
            sourceFieldOptions,
          )

          return (
          <div key={row.id} className="rounded-md border p-3">
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
              <div className="mt-3 grid gap-3 md:grid-cols-[minmax(0,240px)_minmax(0,1fr)]">
                {sourceFieldOptions.length > 0 && (
                  <div className="space-y-2">
                    <Label>{t('collectionPanel.api.sourceField')}</Label>
                    <FieldSelector
                      value={sourceFieldSelectValue(row.reference, sourceFieldOptions)}
                      onChange={(field) => updateRow(index, 'reference', field)}
                      options={fieldSelectorOptions}
                      placeholder={t('collectionPanel.api.sourceFieldPlaceholder')}
                      searchPlaceholder={t('collectionPanel.api.fieldMappings.searchSourcePath')}
                      emptyLabel={t('collectionPanel.api.fieldMappings.noSourcePaths')}
                      ariaLabel={t('collectionPanel.api.sourceField')}
                    />
                  </div>
                )}
                <div className="space-y-2">
                  <Label>
                    {sourceFieldOptions.length > 0
                      ? t('collectionPanel.api.customSourceReference')
                      : t('collectionPanel.api.sourceReference')}
                  </Label>
                  <Input
                    value={row.reference}
                    onChange={(event) => updateRow(index, 'reference', event.target.value)}
                    placeholder={t('collectionPanel.api.sourceReferencePlaceholder')}
                  />
                </div>
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
                    onValueChange={(generator) => updateGenerator(index, generator)}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder={t('collectionPanel.api.generatorPlaceholder')} />
                    </SelectTrigger>
                    <SelectContent>
                      {availableGeneratorOptions.map((generator) => (
                        <SelectItem key={generator} value={generator}>
                          {generator}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-2">
                  <div className="flex items-center justify-between gap-2">
                    <Label>{t('collectionPanel.api.generatorParams')}</Label>
                    {suggestedParamsText && (
                      <Button
                        type="button"
                        variant="ghost"
                        size="sm"
                        className="h-7 px-2 text-xs"
                        onClick={() =>
                          updateRow(index, 'paramsText', suggestedParamsText)
                        }
                      >
                        {t('collectionPanel.api.useSuggestedGeneratorParams')}
                      </Button>
                    )}
                  </div>
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
          )
        })}
      </div>

      {error && (
        <Alert variant="destructive">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}
    </div>
  )
}
