import { useEffect, useMemo, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
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

import type { ApiExportFieldSuggestion } from '@/features/collections/hooks/useApiExportConfigs'
import {
  FieldSelector,
  type FieldSelectorOption,
} from '@/features/collections/components/data/FieldSelector'

export type ApiFieldMappingValue = string | Record<string, unknown>

export interface ApiFieldMappingsEditorProps {
  value?: ApiFieldMappingValue[]
  onChange: (value: ApiFieldMappingValue[]) => void
  suggestions?: ApiExportFieldSuggestion[]
  sourceFields?: ApiExportFieldSuggestion[]
  title?: string
  description?: string
}

interface ApiFieldMappingRow {
  id: string
  outputName: string
  mode: 'source' | 'generator'
  source: string
  generator: string
  paramsText: string
  valueKind: 'simple' | 'mapping'
}

interface SourceFieldOption {
  source: string
  name: string
  label: string
  quickLabel: string
  quickSuggestion: boolean
}

interface SourceFieldGroup {
  key: string
  label: string
  order: number
  options: SourceFieldOption[]
}

const VALUE_LEAVES = new Set(['value'])
const UNIT_LEAVES = new Set(['unit', 'units'])
const TECHNICAL_LEAVES = new Set([
  'id',
  'uuid',
  'created_at',
  'updated_at',
  'source',
  'source_id',
])

let nextRowId = 0

function createRowId() {
  nextRowId += 1
  return `api-field-mapping-${nextRowId}`
}

function parseStringField(entry: string): ApiFieldMappingRow {
  if (entry.includes(':')) {
    const separatorIndex = entry.indexOf(':')
    const outputName = entry.slice(0, separatorIndex)
    const source = entry.slice(separatorIndex + 1)
    return {
      id: createRowId(),
      outputName: outputName.trim(),
      mode: 'source',
      source: source.trim(),
      generator: '',
      paramsText: '',
      valueKind: 'mapping',
    }
  }

  return {
    id: createRowId(),
    outputName: entry,
    mode: 'source',
    source: entry,
    generator: '',
    paramsText: '',
    valueKind: 'simple',
  }
}

function parseRows(value: ApiFieldMappingValue[] = []): ApiFieldMappingRow[] {
  return value.map((entry) => {
    if (typeof entry === 'string') {
      return parseStringField(entry)
    }

    const [outputName, rawConfig] = Object.entries(entry)[0] ?? ['', '']

    if (rawConfig && typeof rawConfig === 'object' && 'generator' in rawConfig) {
      const generatorConfig = rawConfig as {
        generator?: string
        params?: Record<string, unknown>
      }
      return {
        id: createRowId(),
        outputName,
        mode: 'generator',
        source: '',
        generator: generatorConfig.generator || '',
        paramsText: generatorConfig.params
          ? JSON.stringify(generatorConfig.params, null, 2)
          : '',
        valueKind: 'mapping',
      } satisfies ApiFieldMappingRow
    }

    return {
      id: createRowId(),
      outputName,
      mode: 'source',
      source: typeof rawConfig === 'string' ? rawConfig : '',
      generator: '',
      paramsText: '',
      valueKind: 'mapping',
    } satisfies ApiFieldMappingRow
  })
}

function serializeRows(rows: ApiFieldMappingRow[]): {
  value: ApiFieldMappingValue[]
  error: string | null
} {
  const serialized: ApiFieldMappingValue[] = []

  for (const row of rows) {
    if (!row.outputName.trim()) continue

    if (row.mode === 'generator') {
      const entry: Record<string, unknown> = { generator: row.generator.trim() }
      if (row.paramsText.trim()) {
        try {
          entry.params = JSON.parse(row.paramsText)
        } catch {
          return {
            value: [],
            error: `Invalid JSON in params for "${row.outputName}"`,
          }
        }
      }
      serialized.push({ [row.outputName]: entry })
      continue
    }

    if (
      row.valueKind === 'simple' &&
      row.outputName.trim() === row.source.trim()
    ) {
      serialized.push(row.outputName.trim())
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
    id: createRowId(),
    outputName: '',
    mode: 'source',
    source: '',
    generator: '',
    paramsText: '',
    valueKind: 'mapping',
  }
}

function inferFieldName(source: string) {
  const parts = source.split('.').filter(Boolean)
  if (parts.length >= 2 && parts[parts.length - 1] === 'value') {
    return parts[parts.length - 2]
  }
  return parts[parts.length - 1] || source
}

function toOutputName(value: string) {
  return value
    .trim()
    .replace(/[^a-zA-Z0-9]+/g, '_')
    .replace(/^_+|_+$/g, '')
    .toLowerCase()
}

function toDisplayLabel(value: string) {
  return value
    .split(/[_\-\s]+/)
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ')
}

function getSourceGroup(source: string) {
  const parts = source.split('.').filter(Boolean)
  const root = parts[0] ?? source
  const leaf = parts[parts.length - 1] ?? source
  const lowerRoot = root.toLowerCase()
  const lowerLeaf = leaf.toLowerCase()

  if (lowerRoot === 'general_info') {
    return { key: 'generalInfo', order: 10, fallbackLabel: 'General information' }
  }

  if (
    ['stats', 'statistics', 'metrics', 'summary_stats', 'indicators'].includes(
      lowerRoot
    )
  ) {
    return { key: 'statistics', order: 20, fallbackLabel: 'Statistics' }
  }

  if (
    ['ecology', 'habitat', 'distribution', 'range', 'environment'].includes(
      lowerRoot
    )
  ) {
    return { key: 'ecology', order: 30, fallbackLabel: 'Ecology and habitat' }
  }

  if (['hierarchy_context', 'hierarchy', 'taxonomy'].includes(lowerRoot)) {
    return { key: 'hierarchy', order: 40, fallbackLabel: 'Hierarchy' }
  }

  if (['extra_data', 'external_data'].includes(lowerRoot)) {
    return { key: 'externalData', order: 50, fallbackLabel: 'External data' }
  }

  if (['metadata', 'provenance'].includes(lowerRoot)) {
    return { key: 'metadata', order: 80, fallbackLabel: 'Metadata' }
  }

  if (lowerRoot.startsWith('_') || TECHNICAL_LEAVES.has(lowerLeaf)) {
    return { key: 'technical', order: 90, fallbackLabel: 'Technical fields' }
  }

  return {
    key: `section:${lowerRoot}`,
    order: 60,
    fallbackLabel: toDisplayLabel(root),
  }
}

function buildSourceFieldOption(field: ApiExportFieldSuggestion): SourceFieldOption {
  const parts = field.source.split('.').filter(Boolean)
  const leaf = parts[parts.length - 1] ?? field.source
  const parent = parts[parts.length - 2]
  const lowerLeaf = leaf.toLowerCase()

  if (parent && VALUE_LEAVES.has(lowerLeaf)) {
    const parentLabel = toDisplayLabel(parent)
    return {
      source: field.source,
      name: toOutputName(parent),
      label: `${parentLabel} value`,
      quickLabel: parentLabel,
      quickSuggestion: true,
    }
  }

  if (parent && UNIT_LEAVES.has(lowerLeaf)) {
    const parentLabel = toDisplayLabel(parent)
    return {
      source: field.source,
      name: `${toOutputName(parent)}_unit`,
      label: `${parentLabel} unit`,
      quickLabel: `${parentLabel} unit`,
      quickSuggestion: false,
    }
  }

  const label = field.label || field.name || field.source

  return {
    source: field.source,
    name: field.name || toOutputName(inferFieldName(field.source)),
    label,
    quickLabel: label,
    quickSuggestion: true,
  }
}

export function ApiFieldMappingsEditor({
  value = [],
  onChange,
  suggestions = [],
  sourceFields,
  title,
  description,
}: ApiFieldMappingsEditorProps) {
  const { t } = useTranslation('sources')
  const serializedValue = useMemo(() => JSON.stringify(value), [value])
  const lastCommittedValueRef = useRef(serializedValue)
  const [rows, setRows] = useState<ApiFieldMappingRow[]>(() =>
    value.length > 0 ? parseRows(value) : [createEmptyRow()]
  )
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (serializedValue === lastCommittedValueRef.current) {
      return
    }

    lastCommittedValueRef.current = serializedValue
    // The editor keeps local draft rows so invalid intermediate input can stay editable.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setRows(value.length > 0 ? parseRows(value) : [createEmptyRow()])
    setError(null)
  }, [serializedValue, value])

  const sourceOptions = useMemo<SourceFieldOption[]>(() => {
    const bySource = new Map<string, SourceFieldOption>()

    const fields = sourceFields ?? suggestions

    fields.forEach((suggestion) => {
      if (!suggestion.source || bySource.has(suggestion.source)) return
      bySource.set(suggestion.source, buildSourceFieldOption(suggestion))
    })

    bySource.forEach((option, source) => {
      if (source.includes('.')) return
      if (!bySource.has(`${source}.value`)) return

      bySource.set(source, {
        ...option,
        label: `${option.label} (${t('collectionPanel.api.fieldMappings.allFields')})`,
        quickSuggestion: false,
      })
    })

    rows.forEach((row) => {
      if (!row.source || bySource.has(row.source)) return
      bySource.set(row.source, {
        source: row.source,
        name: toOutputName(inferFieldName(row.source)),
        label: row.source,
        quickLabel: row.source,
        quickSuggestion: false,
      })
    })

    return Array.from(bySource.values())
  }, [rows, sourceFields, suggestions, t])

  const sourceGroups = useMemo<SourceFieldGroup[]>(() => {
    const byGroup = new Map<string, SourceFieldGroup>()

    sourceOptions.forEach((option) => {
      const group = getSourceGroup(option.source)
      const label = group.key.startsWith('section:')
        ? group.fallbackLabel
        : t(`collectionPanel.api.fieldMappings.sourceGroups.${group.key}`, {
            defaultValue: group.fallbackLabel,
          })

      if (!byGroup.has(group.key)) {
        byGroup.set(group.key, {
          key: group.key,
          label,
          order: group.order,
          options: [],
        })
      }

      byGroup.get(group.key)?.options.push(option)
    })

    return Array.from(byGroup.values())
      .map((group) => ({
        ...group,
        options: [...group.options].sort(
          (left, right) =>
            left.label.localeCompare(right.label) ||
            left.source.localeCompare(right.source)
        ),
      }))
      .sort(
        (left, right) =>
          left.order - right.order || left.label.localeCompare(right.label)
      )
  }, [sourceOptions, t])

  const fieldSelectorOptions = useMemo<FieldSelectorOption[]>(
    () =>
      sourceGroups.flatMap((group) =>
        group.options.map((option) => ({
          value: option.source,
          label: option.label,
          description: option.source,
          groupKey: group.key,
          groupLabel: group.label,
        })),
      ),
    [sourceGroups],
  )

  const availableSuggestions = useMemo(
    () => {
      const byOutputName = new Map<string, SourceFieldOption>()
      const fields = sourceFields ?? suggestions

      fields.forEach((field) => {
        const suggestion = buildSourceFieldOption(field)
        if (!suggestion.quickSuggestion) return
        if (byOutputName.has(suggestion.name)) return
        if (
          rows.some(
            (row) =>
              row.outputName === suggestion.name && row.source === suggestion.source
          )
        ) {
          return
        }

        byOutputName.set(suggestion.name, suggestion)
      })

      return Array.from(byOutputName.values())
    },
    [rows, sourceFields, suggestions]
  )

  const commit = (nextRows: ApiFieldMappingRow[]) => {
    setRows(nextRows)
    const serialized = serializeRows(nextRows)
    setError(serialized.error)
    if (
      !serialized.error &&
      JSON.stringify(serialized.value) !== JSON.stringify(value)
    ) {
      lastCommittedValueRef.current = JSON.stringify(serialized.value)
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

  const updateSourcePath = (index: number, source: string) => {
    const selectedField = sourceOptions.find((option) => option.source === source)
    const nextRows = rows.map((row, currentIndex) => {
      if (currentIndex !== index) return row

      const shouldFillOutputName =
        !row.outputName.trim() || row.outputName.trim() === row.source.trim()

      return {
        ...row,
        source,
        outputName: shouldFillOutputName
          ? selectedField?.name || inferFieldName(source)
          : row.outputName,
      }
    })

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

  const addFieldButton = (
    <Button type="button" variant="outline" size="sm" onClick={() => addRow()}>
      <Plus className="mr-2 h-4 w-4" />
      {t('collectionPanel.api.fieldMappings.addField')}
    </Button>
  )

  return (
    <div className="space-y-4 rounded-lg border p-4">
      {(title || description) && (
        <div className="space-y-1">
          {title && <h3 className="text-sm font-semibold">{title}</h3>}
          {description && (
            <p className="text-sm text-muted-foreground">{description}</p>
          )}
        </div>
      )}

      {availableSuggestions.length > 0 && (
        <div className="space-y-2">
          <div className="flex items-center gap-2 text-xs font-medium text-muted-foreground">
            <Sparkles className="h-3.5 w-3.5" />
            {t('collectionPanel.api.fieldMappings.suggestions')}
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
                    id: createRowId(),
                    outputName: suggestion.name,
                    mode: 'source',
                    source: suggestion.source,
                    generator: '',
                    paramsText: '',
                    valueKind: 'mapping',
                  })
                }
              >
                {suggestion.quickLabel || suggestion.label || suggestion.name}
              </Button>
            ))}
          </div>
        </div>
      )}

      <div className="space-y-4">
        {rows.map((row, index) => (
          <div key={row.id} className="rounded-md border p-3">
            <div className="mb-3 flex items-center justify-between gap-2">
              <Badge variant="outline">
                {row.outputName || `${t('collectionPanel.api.fieldMappings.field')} ${index + 1}`}
              </Badge>
              <div className="flex items-center gap-1">
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  className="h-8 w-8"
                  onClick={() => moveRow(index, -1)}
                  disabled={index === 0}
                  aria-label={t('collectionPanel.api.fieldMappings.moveUp')}
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
                  aria-label={t('collectionPanel.api.fieldMappings.moveDown')}
                >
                  <ChevronDown className="h-4 w-4" />
                </Button>
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  className="h-8 w-8 text-muted-foreground hover:text-destructive"
                  onClick={() => removeRow(index)}
                  aria-label={t('collectionPanel.api.fieldMappings.remove')}
                >
                  <Trash2 className="h-4 w-4" />
                </Button>
              </div>
            </div>

            <div className="grid gap-3 md:grid-cols-3">
              <div className="space-y-1">
                <Label>{t('collectionPanel.api.fieldMappings.outputField')}</Label>
                <Input
                  value={row.outputName}
                  onChange={(event) =>
                    updateRow(index, 'outputName', event.target.value)
                  }
                  placeholder="scientificName"
                />
              </div>

              <div className="space-y-1">
                <Label>{t('collectionPanel.api.fieldMappings.mode')}</Label>
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
                    <SelectItem value="source">
                      {t('collectionPanel.api.fieldMappings.sourceField')}
                    </SelectItem>
                    <SelectItem value="generator">
                      {t('collectionPanel.api.fieldMappings.generatorMode')}
                    </SelectItem>
                  </SelectContent>
                </Select>
              </div>

              {row.mode === 'source' ? (
                <div className="space-y-1">
                  <Label>{t('collectionPanel.api.fieldMappings.sourcePath')}</Label>
                  <FieldSelector
                    value={row.source}
                    onChange={(source) => updateSourcePath(index, source)}
                    options={fieldSelectorOptions}
                    placeholder={t(
                      sourceOptions.length > 0
                        ? 'collectionPanel.api.fieldMappings.selectSourcePath'
                        : 'collectionPanel.api.fieldMappings.noSourcePaths'
                    )}
                    emptyLabel={t('collectionPanel.api.fieldMappings.noSourcePaths')}
                    searchPlaceholder={t('collectionPanel.api.fieldMappings.searchSourcePath')}
                    disabled={sourceOptions.length === 0}
                    ariaLabel={t('collectionPanel.api.fieldMappings.sourcePath')}
                  />
                </div>
              ) : (
                <div className="space-y-1">
                  <Label>{t('collectionPanel.api.fieldMappings.generatorName')}</Label>
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
                <Label>{t('collectionPanel.api.fieldMappings.generatorParams')}</Label>
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

      <div className="flex justify-end">{addFieldButton}</div>

      {error && <p className="text-sm text-destructive">{error}</p>}
    </div>
  )
}
