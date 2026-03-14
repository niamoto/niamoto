import { useState, useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import { Plus, Trash2, Settings2 } from 'lucide-react'
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
import {
  Collapsible,
  CollapsibleContent,
} from '@/components/ui/collapsible'
import { Card } from '@/components/ui/card'
import { FieldTreeSelector } from './FieldTreeSelector'
import { useSourceColumns, type SourceInfo } from '@/lib/api/recipes'

/**
 * Configuration for a single field in the aggregator
 */
export interface FieldConfig {
  source: string
  field: string
  target: string
  transformation?: 'direct' | 'count' | 'sum'
  format?: 'boolean' | 'url' | 'text' | 'number'
  units?: string
  labels?: Record<string, string>
}

interface FieldAggregatorBuilderProps {
  groupBy: string
  sources: SourceInfo[]
  value: FieldConfig[]
  onChange: (fields: FieldConfig[]) => void
}

interface FieldRowProps {
  groupBy: string
  sources: SourceInfo[]
  field: FieldConfig
  index: number
  onChange: (index: number, field: FieldConfig) => void
  onDelete: (index: number) => void
}

function FieldRow({
  groupBy,
  sources,
  field,
  index,
  onChange,
  onDelete,
}: FieldRowProps) {
  const { t } = useTranslation(['widgets', 'common'])
  const [showAdvanced, setShowAdvanced] = useState(false)

  // Get columns for the selected source
  const { columns, loading: columnsLoading } = useSourceColumns(
    groupBy,
    field.source || null
  )

  const handleFieldChange = useCallback(
    (updates: Partial<FieldConfig>) => {
      onChange(index, { ...field, ...updates })
    },
    [field, index, onChange]
  )

  // Auto-generate target from field name
  const handleFieldSelect = useCallback(
    (fieldPath: string) => {
      // Extract the last part of the path for target
      const parts = fieldPath.split('.')
      const suggestedTarget = parts[parts.length - 1]
      handleFieldChange({
        field: fieldPath,
        target: field.target || suggestedTarget,
      })
    },
    [field.target, handleFieldChange]
  )

  return (
    <Card className="p-3 space-y-3">
      {/* Main row: source, field, target, transformation, delete */}
      <div className="flex items-center gap-2">
        {/* Source selector */}
        <div className="w-32">
          <Select
            value={field.source}
            onValueChange={(v) => handleFieldChange({ source: v, field: '' })}
          >
            <SelectTrigger className="h-8">
              <SelectValue placeholder="Source" />
            </SelectTrigger>
            <SelectContent>
              {sources.map((src) => (
                <SelectItem key={src.name} value={src.name}>
                  <div className="flex items-center gap-1">
                    <span
                      className={`w-2 h-2 rounded-full ${
                        src.type === 'reference'
                          ? 'bg-blue-500'
                          : src.type === 'dataset'
                            ? 'bg-green-500'
                            : 'bg-orange-500'
                      }`}
                    />
                    {src.name}
                  </div>
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {/* Field selector (tree) */}
        <div className="flex-1 min-w-[150px]">
          <FieldTreeSelector
            columns={columns}
            value={field.field}
            onChange={handleFieldSelect}
            placeholder={t('recipe.field')}
            disabled={!field.source}
            loading={columnsLoading}
          />
        </div>

        {/* Arrow */}
        <span className="text-muted-foreground px-1">→</span>

        {/* Target input */}
        <div className="w-32">
          <Input
            className="h-8"
            placeholder="target"
            value={field.target}
            onChange={(e) => handleFieldChange({ target: e.target.value })}
          />
        </div>

        {/* Transformation */}
        <div className="w-24">
          <Select
            value={field.transformation || 'direct'}
            onValueChange={(v) =>
              handleFieldChange({
                transformation: v as FieldConfig['transformation'],
              })
            }
          >
            <SelectTrigger className="h-8">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="direct">direct</SelectItem>
              <SelectItem value="count">count</SelectItem>
              <SelectItem value="sum">sum</SelectItem>
            </SelectContent>
          </Select>
        </div>

        {/* Advanced toggle */}
        <Button
          variant="ghost"
          size="icon"
          className="h-8 w-8"
          onClick={() => setShowAdvanced(!showAdvanced)}
        >
          <Settings2 className="h-4 w-4" />
        </Button>

        {/* Delete button */}
        <Button
          variant="ghost"
          size="icon"
          className="h-8 w-8 text-destructive hover:text-destructive"
          onClick={() => onDelete(index)}
        >
          <Trash2 className="h-4 w-4" />
        </Button>
      </div>

      {/* Advanced options (collapsible) */}
      <Collapsible open={showAdvanced} onOpenChange={setShowAdvanced}>
        <CollapsibleContent className="pt-2 border-t space-y-3">
          <div className="grid grid-cols-3 gap-3">
            {/* Format */}
            <div className="space-y-1">
              <Label className="text-xs">Format</Label>
              <Select
                value={field.format || ''}
                onValueChange={(v) =>
                  handleFieldChange({
                    format: v ? (v as FieldConfig['format']) : undefined,
                  })
                }
              >
                <SelectTrigger className="h-8">
                  <SelectValue placeholder={t('recipe.none')} />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="">{t('recipe.none')}</SelectItem>
                  <SelectItem value="boolean">boolean</SelectItem>
                  <SelectItem value="url">url</SelectItem>
                  <SelectItem value="text">text</SelectItem>
                  <SelectItem value="number">number</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {/* Units */}
            <div className="space-y-1">
              <Label className="text-xs">{t('recipe.units')}</Label>
              <Input
                className="h-8"
                placeholder="ex: ha, m, km²"
                value={field.units || ''}
                onChange={(e) =>
                  handleFieldChange({
                    units: e.target.value || undefined,
                  })
                }
              />
            </div>
          </div>

          {/* Labels mapping (for boolean/categorical) */}
          {(field.format === 'boolean' || field.transformation === 'direct') && (
            <div className="space-y-1">
              <Label className="text-xs">{t('recipe.labelsJson')}</Label>
              <Input
                className="h-8 font-mono text-xs"
                placeholder='{"1": "Oui", "0": "Non"}'
                value={field.labels ? JSON.stringify(field.labels) : ''}
                onChange={(e) => {
                  try {
                    const parsed = e.target.value
                      ? JSON.parse(e.target.value)
                      : undefined
                    handleFieldChange({ labels: parsed })
                  } catch {
                    // Invalid JSON, keep the text but don't update
                  }
                }}
              />
            </div>
          )}
        </CollapsibleContent>
      </Collapsible>
    </Card>
  )
}

export function FieldAggregatorBuilder({
  groupBy,
  sources,
  value,
  onChange,
}: FieldAggregatorBuilderProps) {
  const { t } = useTranslation(['widgets', 'common'])

  const handleFieldChange = useCallback(
    (index: number, field: FieldConfig) => {
      const newFields = [...value]
      newFields[index] = field
      onChange(newFields)
    },
    [value, onChange]
  )

  const handleDelete = useCallback(
    (index: number) => {
      const newFields = value.filter((_, i) => i !== index)
      onChange(newFields)
    },
    [value, onChange]
  )

  const handleAdd = useCallback(() => {
    // Default to first source if available
    const defaultSource = sources.length > 0 ? sources[0].name : ''
    onChange([
      ...value,
      {
        source: defaultSource,
        field: '',
        target: '',
        transformation: 'direct',
      },
    ])
  }, [value, sources, onChange])

  return (
    <div className="space-y-3">
      {/* Field list */}
      {value.map((field, index) => (
        <FieldRow
          key={index}
          groupBy={groupBy}
          sources={sources}
          field={field}
          index={index}
          onChange={handleFieldChange}
          onDelete={handleDelete}
        />
      ))}

      {/* Add button */}
      <Button
        variant="outline"
        className="w-full h-8 text-xs"
        onClick={handleAdd}
      >
        <Plus className="h-3 w-3 mr-1" />
        {t('recipe.addField')}
      </Button>

      {/* Help text */}
      {value.length === 0 && (
        <p className="text-xs text-muted-foreground text-center py-2">
          {t('recipe.addFieldsHint')}
        </p>
      )}
    </div>
  )
}
