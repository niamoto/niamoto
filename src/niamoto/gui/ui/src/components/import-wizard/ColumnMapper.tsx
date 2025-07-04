import { useState, useEffect } from 'react'
import { Check, AlertCircle } from 'lucide-react'
import { cn } from '@/lib/utils'
import type { ImportType } from './ImportWizard'

interface ColumnMapperProps {
  importType: ImportType
  fileAnalysis: any
  onMappingComplete: (mappings: Record<string, string>) => void
}

interface RequiredField {
  key: string
  label: string
  description: string
  required: boolean
}

const requiredFields: Record<ImportType, RequiredField[]> = {
  taxonomy: [
    { key: 'taxon_id', label: 'Taxon ID', description: 'Unique identifier for each taxon', required: true },
    { key: 'full_name', label: 'Full Name', description: 'Complete scientific name', required: true },
    { key: 'authors', label: 'Authors', description: 'Taxonomic authority', required: true },
    { key: 'family', label: 'Family', description: 'Family rank', required: false },
    { key: 'genus', label: 'Genus', description: 'Genus rank', required: false },
    { key: 'species', label: 'Species', description: 'Species rank', required: false },
    { key: 'infra', label: 'Infra', description: 'Infraspecific rank', required: false },
  ],
  plots: [
    { key: 'identifier', label: 'Plot ID', description: 'Unique identifier for each plot', required: true },
    { key: 'locality', label: 'Locality', description: 'Plot name or locality', required: true },
    { key: 'location', label: 'Location', description: 'Geometry or coordinates', required: true },
    { key: 'link_field', label: 'Link Field', description: 'Field for linking with occurrences', required: false },
  ],
  occurrences: [
    { key: 'taxon_id', label: 'Taxon ID', description: 'Reference to taxonomy', required: true },
    { key: 'location', label: 'Location', description: 'Occurrence coordinates', required: true },
    { key: 'plot_name', label: 'Plot Name', description: 'Link to plot (optional)', required: false },
  ],
  shapes: [
    { key: 'name', label: 'Name', description: 'Shape name or label', required: true },
    { key: 'id', label: 'ID', description: 'Unique identifier', required: false },
  ],
}

export function ColumnMapper({ importType, fileAnalysis, onMappingComplete }: ColumnMapperProps) {
  const [mappings, setMappings] = useState<Record<string, string>>({})
  const [draggedColumn, setDraggedColumn] = useState<string | null>(null)

  const sourceColumns = fileAnalysis?.columns || []
  const suggestions = fileAnalysis?.suggestions || {}
  const fields = requiredFields[importType] || []

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
  }, [mappings, onMappingComplete])

  const unmappedColumns = sourceColumns.filter(
    (col: string) => !Object.values(mappings).includes(col)
  )

  return (
    <div>
      <h2 className="mb-4 text-xl font-semibold">Map Fields</h2>
      <p className="mb-6 text-sm text-muted-foreground">
        Drag columns from your file to the required fields, or click to select.
      </p>

      <div className="grid gap-6 lg:grid-cols-2">
        {/* Source Columns */}
        <div>
          <h3 className="mb-3 font-medium">Source Columns</h3>
          <div className="rounded-lg border bg-card p-4">
            <div className="space-y-2">
              {unmappedColumns.length === 0 ? (
                <p className="text-sm text-muted-foreground">All columns mapped</p>
              ) : (
                unmappedColumns.map((column: string) => (
                  <div
                    key={column}
                    draggable
                    onDragStart={() => setDraggedColumn(column)}
                    onDragEnd={() => setDraggedColumn(null)}
                    className={cn(
                      "cursor-move rounded-md border bg-background px-3 py-2 text-sm transition-colors hover:bg-accent",
                      draggedColumn === column && "opacity-50"
                    )}
                  >
                    {column}
                  </div>
                ))
              )}
            </div>
          </div>
        </div>

        {/* Target Fields */}
        <div>
          <h3 className="mb-3 font-medium">Target Fields</h3>
          <div className="space-y-3">
            {fields.map((field) => (
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
            ))}
          </div>
        </div>
      </div>

      {/* Validation Summary */}
      {!isValid() && (
        <div className="mt-6 rounded-lg border border-warning/50 bg-warning/10 p-4">
          <div className="flex items-start space-x-2">
            <AlertCircle className="mt-0.5 h-4 w-4 text-warning" />
            <div>
              <p className="text-sm font-medium">Missing Required Fields</p>
              <p className="text-sm text-muted-foreground">
                Please map all required fields before proceeding.
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
  const [showDropdown, setShowDropdown] = useState(false)

  return (
    <div
      className={cn(
        "rounded-lg border p-4 transition-colors",
        isDragActive && !mappedColumn && "border-primary bg-primary/5",
        mappedColumn && "bg-accent/50"
      )}
      onDragOver={(e) => e.preventDefault()}
      onDrop={(e) => {
        e.preventDefault()
        const column = e.dataTransfer.getData('text/plain')
        if (column) onDrop(column)
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
              <span className="text-xs text-primary">Auto-suggested</span>
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
                Remove
              </button>
            </div>
          ) : (
            <div className="relative mt-2">
              <button
                onClick={() => setShowDropdown(!showDropdown)}
                className="text-sm text-primary hover:underline"
              >
                Select column
              </button>

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
                        <span className="ml-2 text-xs text-muted-foreground">(suggested)</span>
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
