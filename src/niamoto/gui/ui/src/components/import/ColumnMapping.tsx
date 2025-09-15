import { useTranslation } from 'react-i18next'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Label } from '@/components/ui/label'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { AlertCircle, CheckCircle2 } from 'lucide-react'

interface FieldDefinition {
  key: string
  label: string
  required: boolean
  description?: string
}

interface ColumnMappingProps {
  sourceColumns: string[]
  targetFields: FieldDefinition[]
  mapping: Record<string, string>
  onMappingChange: (mapping: Record<string, string>) => void
  className?: string
}

export function ColumnMapping({
  sourceColumns,
  targetFields,
  mapping,
  onMappingChange,
  className
}: ColumnMappingProps) {
  const { t } = useTranslation()

  const handleFieldMapping = (targetField: string, sourceColumn: string) => {
    const newMapping = { ...mapping }

    if (sourceColumn === '') {
      delete newMapping[targetField]
    } else {
      newMapping[targetField] = sourceColumn
    }

    onMappingChange(newMapping)
  }

  const getMappedSourceColumns = () => {
    return new Set(Object.values(mapping))
  }

  const getValidationStatus = (field: FieldDefinition) => {
    const isMapped = mapping[field.key]
    if (field.required && !isMapped) return 'error'
    if (isMapped) return 'success'
    return 'optional'
  }

  const mappedSourceColumns = getMappedSourceColumns()

  return (
    <Card className={className}>
      <CardHeader>
        <CardTitle className="text-base">
          {t('import.columnMapping.title', 'Column Mapping')}
        </CardTitle>
        <p className="text-sm text-muted-foreground">
          {t('import.columnMapping.description', 'Map your file columns to the required fields')}
        </p>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          {targetFields.map((field) => {
            const validationStatus = getValidationStatus(field)
            const selectedValue = mapping[field.key] || ''

            return (
              <div key={field.key} className="space-y-2">
                <div className="flex items-center gap-2">
                  <Label htmlFor={`field-${field.key}`} className="text-sm font-medium">
                    {field.label}
                  </Label>
                  {field.required ? (
                    <Badge variant={validationStatus === 'error' ? 'destructive' : 'default'} className="text-xs">
                      {t('common.required', 'Required')}
                    </Badge>
                  ) : (
                    <Badge variant="secondary" className="text-xs">
                      {t('common.optional', 'Optional')}
                    </Badge>
                  )}
                  {validationStatus === 'error' && (
                    <AlertCircle className="h-4 w-4 text-destructive" />
                  )}
                  {validationStatus === 'success' && (
                    <CheckCircle2 className="h-4 w-4 text-green-600" />
                  )}
                </div>

                {field.description && (
                  <p className="text-xs text-muted-foreground">{field.description}</p>
                )}

                <Select
                  value={selectedValue}
                  onValueChange={(value) => handleFieldMapping(field.key, value)}
                >
                  <SelectTrigger id={`field-${field.key}`} className="w-full">
                    <SelectValue
                      placeholder={t('import.columnMapping.selectColumn', 'Select column...')}
                    />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="">
                      {t('import.columnMapping.noMapping', 'No mapping')}
                    </SelectItem>
                    {sourceColumns.map((column) => (
                      <SelectItem
                        key={column}
                        value={column}
                        disabled={mappedSourceColumns.has(column) && mapping[field.key] !== column}
                      >
                        <div className="flex items-center gap-2">
                          <span>{column}</span>
                          {mappedSourceColumns.has(column) && mapping[field.key] !== column && (
                            <Badge variant="secondary" className="text-xs">
                              {t('import.columnMapping.mapped', 'Mapped')}
                            </Badge>
                          )}
                        </div>
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            )
          })}
        </div>

        {/* Mapping Summary */}
        <div className="mt-6 pt-4 border-t">
          <div className="flex items-center justify-between text-sm">
            <span className="text-muted-foreground">
              {t('import.columnMapping.mappingSummary', 'Mapping Summary')}
            </span>
            <div className="flex gap-4">
              <span className="flex items-center gap-1">
                <CheckCircle2 className="h-3 w-3 text-green-600" />
                {Object.keys(mapping).length} {t('import.columnMapping.mapped', 'mapped')}
              </span>
              <span className="flex items-center gap-1">
                <AlertCircle className="h-3 w-3 text-destructive" />
                {targetFields.filter(f => f.required && !mapping[f.key]).length} {t('import.columnMapping.missing', 'missing')}
              </span>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
