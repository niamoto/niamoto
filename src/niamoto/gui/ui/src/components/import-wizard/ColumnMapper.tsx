import { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { Check, AlertCircle, GripVertical, Loader2 } from 'lucide-react'
import { cn } from '@/lib/utils'
import type { ImportType } from './types'
import { useImportFields, type RequiredField } from '@/hooks/useImportFields'

interface ColumnMapperProps {
  importType: ImportType
  fileAnalysis: any
  onMappingComplete: (mappings: Record<string, string>) => void
}


export function ColumnMapper({ importType, fileAnalysis, onMappingComplete }: ColumnMapperProps) {
  const { t } = useTranslation(['import', 'common'])
  const [mappings, setMappings] = useState<Record<string, string>>({})
  const [draggedColumn, setDraggedColumn] = useState<string | null>(null)

  // Use the hook to get fields dynamically
  const { fields, loading: fieldsLoading, error: fieldsError } = useImportFields(importType)

  const sourceColumns = fileAnalysis?.columns || []
  const suggestions = fileAnalysis?.suggestions || {}

  // Check if there was an error in file analysis
  if (fileAnalysis?.error) {
    return (
      <div className="rounded-lg border border-destructive/50 bg-destructive/10 p-4">
        <p className="text-sm text-destructive">
          {t('fieldMapping.errorAnalyzing', { error: fileAnalysis.error })}
        </p>
      </div>
    )
  }

  useEffect(() => {
    // Auto-apply suggestions
    const autoMappings: Record<string, string> = {}
    for (const field of fields) {
      const suggested = suggestions[field.key]
      if (suggested && suggested.length > 0) {
        autoMappings[field.key] = suggested[0]
      }
    }
    setMappings(autoMappings)
  }, [suggestions, fields])

  const handleDrop = (fieldKey: string, column: string) => {
    setMappings({ ...mappings, [fieldKey]: column })
    setDraggedColumn(null)
  }

  const removeMapping = (fieldKey: string) => {
    const newMappings = { ...mappings }
    delete newMappings[fieldKey]
    setMappings(newMappings)
  }

  const isValid = () => {
    const requiredFieldKeys = fields.filter(f => f.required).map(f => f.key)
    return requiredFieldKeys.every(key => mappings[key])
  }

  useEffect(() => {
    if (isValid()) {
      onMappingComplete(mappings)
    }
  }, [mappings])

  const unmappedColumns = sourceColumns.filter(
    (col: string) => !Object.values(mappings).includes(col)
  )

  if (fieldsLoading) {
    return (
      <div className="flex items-center justify-center p-8">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        <span className="ml-2">{t('fieldMapping.loadingDefinitions')}</span>
      </div>
    )
  }

  if (fieldsError) {
    return (
      <div className="rounded-lg border border-destructive/50 bg-destructive/10 p-4">
        <p className="text-sm text-destructive">
          {fieldsError}
        </p>
      </div>
    )
  }

  return (
    <div>
      <h2 className="mb-4 text-xl font-semibold">{t('fieldMapping.title')}</h2>
      <p className="mb-6 text-sm text-muted-foreground">
        {t('fieldMapping.dragInstruction')}
      </p>

      <div className="grid gap-6 lg:grid-cols-2">
        {/* Source Columns */}
        <div>
          <h3 className="mb-3 font-medium">{t('fieldMapping.sourceColumns')}</h3>
          <div className="rounded-lg border bg-card p-4">
            <div className="space-y-2">
              {unmappedColumns.length === 0 ? (
                <p className="text-sm text-muted-foreground">{t('common:messages.allMapped')}</p>
              ) : (
                unmappedColumns.map((column: string) => (
                  <div
                    key={column}
                    draggable={true}
                    onDragStart={(e) => {
                      setDraggedColumn(column)
                      e.dataTransfer.setData('text/plain', column)
                      e.dataTransfer.effectAllowed = 'copy'
                    }}
                    onDragEnd={() => setDraggedColumn(null)}
                    className={cn(
                      "rounded-md border bg-background px-3 py-2 text-sm transition-all hover:bg-accent hover:border-primary/50 cursor-move select-none",
                      draggedColumn === column && "opacity-50 scale-95"
                    )}
                  >
                    <div className="flex items-center gap-2">
                      <GripVertical className="h-3 w-3 text-muted-foreground" />
                      <span>{column}</span>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>

        {/* Target Fields */}
        <div>
          <h3 className="mb-3 font-medium">{t('fieldMapping.targetFields')}</h3>
          <div className="space-y-3">
            {fields.map((field) => {
              // Special handling for occurrence_link_field
              if (field.key === 'occurrence_link_field' && importType === 'plots') {
                return (
                  <OccurrenceLinkField
                    key={field.key}
                    field={field}
                    value={mappings[field.key] || ''}
                    onChange={(value) => handleDrop(field.key, value)}
                    availableColumns={fileAnalysis?.occurrenceColumns || []}
                  />
                )
              }

              // Special handling for link_field - show standard plot_ref fields
              if (field.key === 'link_field' && importType === 'plots') {
                return (
                  <PlotLinkField
                    key={field.key}
                    field={field}
                    mappedColumn={mappings[field.key]}
                    availableColumns={['id', 'plot_id', 'locality']} // Standard plot_ref fields (plot_name is in extra_data, not a direct field)
                    onSelect={(column) => handleDrop(field.key, column)}
                    onRemove={() => removeMapping(field.key)}
                  />
                )
              }

              // Special handling for type field in shapes - free text input
              if (field.key === 'type' && importType === 'shapes') {
                return (
                  <ShapeTypeField
                    key={field.key}
                    field={field}
                    value={mappings[field.key] || ''}
                    onChange={(value) => handleDrop(field.key, value)}
                  />
                )
              }

              return (
                <FieldMapping
                  key={field.key}
                  field={field}
                  mappedColumn={mappings[field.key]}
                  suggestions={suggestions[field.key] || []}
                  availableColumns={unmappedColumns}
                  onDrop={(column) => handleDrop(field.key, column)}
                  onRemove={() => removeMapping(field.key)}
                  isDragActive={draggedColumn !== null}
                />
              )
            })}
          </div>
        </div>
      </div>

      {/* Validation Summary */}
      {!isValid() && (
        <div className="mt-6 rounded-lg border border-warning/50 bg-warning/10 p-4">
          <div className="flex items-start space-x-2">
            <AlertCircle className="mt-0.5 h-4 w-4 text-warning" />
            <div>
              <p className="text-sm font-medium">{t('common:validation.missingRequired')}</p>
              <p className="text-sm text-muted-foreground">
                {t('common:validation.mapAllRequired')}
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

interface FieldMappingProps {
  field: RequiredField
  mappedColumn?: string
  suggestions: string[]
  availableColumns: string[]
  onDrop: (column: string) => void
  onRemove: () => void
  isDragActive: boolean
}

function FieldMapping({
  field,
  mappedColumn,
  suggestions,
  availableColumns,
  onDrop,
  onRemove,
  isDragActive,
}: FieldMappingProps) {
  const { t } = useTranslation(['import', 'common'])
  const [showDropdown, setShowDropdown] = useState(false)
  const [isDragOver, setIsDragOver] = useState(false)

  return (
    <div
      className={cn(
        "rounded-lg border p-4 transition-all",
        isDragActive && !mappedColumn && "border-primary bg-primary/5 border-dashed cursor-copy",
        isDragOver && !mappedColumn && "border-primary bg-primary/10 scale-[1.02] shadow-lg cursor-copy",
        mappedColumn && "bg-accent/50"
      )}
      onDragOver={(e) => {
        e.preventDefault()
        e.stopPropagation()
        if (e.dataTransfer) {
          e.dataTransfer.dropEffect = 'copy'
        }
      }}
      onDragEnter={(e) => {
        e.preventDefault()
        e.stopPropagation()
        if (!mappedColumn) setIsDragOver(true)
      }}
      onDragLeave={(e) => {
        e.preventDefault()
        e.stopPropagation()
        // Only set to false if we're actually leaving the drop zone
        const rect = e.currentTarget.getBoundingClientRect()
        const x = e.clientX
        const y = e.clientY
        if (x < rect.left || x > rect.right || y < rect.top || y > rect.bottom) {
          setIsDragOver(false)
        }
      }}
      onDrop={(e) => {
        e.preventDefault()
        e.stopPropagation()
        setIsDragOver(false)
        const column = e.dataTransfer.getData('text/plain')
        if (column && !mappedColumn) {
          onDrop(column)
        }
      }}
    >
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <div className="flex items-center space-x-2">
            <h4 className="font-medium">
              {field.label}
              {field.required && <span className="text-destructive">*</span>}
            </h4>
            {suggestions.length > 0 && !mappedColumn && (
              <span className="text-xs text-primary">{t('common:messages.suggested')}</span>
            )}
          </div>
          <p className="mt-1 text-sm text-muted-foreground">{field.description}</p>

          {mappedColumn ? (
            <div className="mt-2 flex items-center space-x-2">
              <div className="flex items-center space-x-2 rounded-md bg-primary/10 px-3 py-1 text-sm">
                <Check className="h-3 w-3 text-primary" />
                <span>{mappedColumn}</span>
              </div>
              <button
                onClick={onRemove}
                className="text-xs text-muted-foreground hover:text-foreground"
              >
                {t('common:actions.remove')}
              </button>
            </div>
          ) : (
            <div className="relative mt-2">
              {isDragActive ? (
                <div className="rounded-md border-2 border-dashed border-primary/30 bg-primary/5 px-3 py-2 text-center text-sm text-muted-foreground">
                  {t('fieldMapping.dropHere')}
                </div>
              ) : (
                <button
                  onClick={() => setShowDropdown(!showDropdown)}
                  className="text-sm text-primary hover:underline"
                >
                  {t('fieldMapping.selectColumn')}
                </button>
              )}

              {showDropdown && (
                <div className="absolute left-0 z-10 mt-1 max-h-48 w-64 overflow-auto rounded-md border bg-popover p-1 shadow-md">
                  {availableColumns.map((col) => (
                    <button
                      key={col}
                      onClick={() => {
                        onDrop(col)
                        setShowDropdown(false)
                      }}
                      className={cn(
                        "w-full rounded px-2 py-1 text-left text-sm hover:bg-accent",
                        suggestions.includes(col) && "font-medium text-primary"
                      )}
                    >
                      {col}
                      {suggestions.includes(col) && (
                        <span className="ml-2 text-xs text-muted-foreground">{t('common:messages.suggested')}</span>
                      )}
                    </button>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

// Special component for Plot Link Field
interface PlotLinkFieldProps {
  field: RequiredField
  mappedColumn?: string
  availableColumns: string[]
  onSelect: (column: string) => void
  onRemove: () => void
}

function PlotLinkField({ field, mappedColumn, availableColumns, onSelect, onRemove }: PlotLinkFieldProps) {
  const { t } = useTranslation(['import', 'common'])
  return (
    <div className="rounded-lg border p-4 bg-accent/20">
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <div className="flex items-center space-x-2">
            <h4 className="font-medium">
              {field.label}
              {field.required && <span className="text-destructive">*</span>}
            </h4>
          </div>
          <p className="mt-1 text-sm text-muted-foreground">
            {field.description}
          </p>

          {mappedColumn ? (
            <div className="mt-2 flex items-center space-x-2">
              <div className="flex items-center space-x-2 rounded-md bg-primary/10 px-3 py-1 text-sm">
                <Check className="h-3 w-3 text-primary" />
                <span>{mappedColumn}</span>
              </div>
              <button
                onClick={onRemove}
                className="text-xs text-muted-foreground hover:text-foreground"
              >
                {t('common:actions.change')}
              </button>
            </div>
          ) : (
            <div className="relative mt-2">
              <select
                value={mappedColumn || ''}
                onChange={(e) => {
                  if (e.target.value) {
                    onSelect(e.target.value)
                  }
                }}
                className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
              >
                <option value="">{t('common:messages.selectField')}</option>
                {availableColumns.map((col) => (
                  <option key={col} value={col}>{col}</option>
                ))}
              </select>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

// Special component for Occurrence Link Field
interface OccurrenceLinkFieldProps {
  field: RequiredField
  value: string
  onChange: (value: string) => void
  availableColumns: string[]
}

function OccurrenceLinkField({ field, value, onChange, availableColumns }: OccurrenceLinkFieldProps) {
  const { t } = useTranslation(['import', 'common'])
  return (
    <div className="rounded-lg border p-4 bg-accent/20">
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <div className="flex items-center space-x-2">
            <h4 className="font-medium">
              {field.label}
              {field.required && <span className="text-destructive">*</span>}
            </h4>
          </div>
          <p className="mt-1 text-sm text-muted-foreground">
            {field.description}
          </p>

          <div className="mt-2">
            {availableColumns.length > 0 ? (
              <>
                <select
                  value={value}
                  onChange={(e) => onChange(e.target.value)}
                  className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                >
                  <option value="">{t('common:messages.selectField')}</option>
                  {availableColumns.map((col) => (
                    <option key={col} value={col}>{col}</option>
                  ))}
                </select>
                <p className="mt-1 text-xs text-muted-foreground">
                  {t('fieldMapping.fieldsFromOccurrences')}
                </p>
              </>
            ) : (
              <>
                <input
                  type="text"
                  value={value}
                  onChange={(e) => onChange(e.target.value)}
                  placeholder={t('common:messages.example', { example: 'plot_name' })}
                  className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                />
                <p className="mt-1 text-xs text-muted-foreground">
                  {t('fieldMapping.mustExistInOccurrences')}
                </p>
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

// Special component for Shape Type Field
interface ShapeTypeFieldProps {
  field: RequiredField
  value: string
  onChange: (value: string) => void
}

function ShapeTypeField({ field, value, onChange }: ShapeTypeFieldProps) {
  const { t } = useTranslation(['import', 'common'])
  return (
    <div className="rounded-lg border p-4 bg-accent/20">
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <div className="flex items-center space-x-2">
            <h4 className="font-medium">
              {field.label}
              {field.required && <span className="text-destructive">*</span>}
            </h4>
          </div>
          <p className="mt-1 text-sm text-muted-foreground">
            {field.description}
          </p>

          <div className="mt-2">
            <input
              type="text"
              value={value}
              onChange={(e) => onChange(e.target.value)}
              placeholder={t('common:messages.example', { example: 'commune, province, région' })}
              className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
            />
          </div>
        </div>
      </div>
    </div>
  )
}
