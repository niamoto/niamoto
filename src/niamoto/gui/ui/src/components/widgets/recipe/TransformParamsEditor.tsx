import { useCallback, useEffect, useState } from 'react'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Switch } from '@/components/ui/switch'
import type { TransformParamDef } from '@/lib/api/recipes'

interface TransformParamsEditorProps {
  /** The currently selected transform type */
  selectedTransform: string | undefined
  /** Schema definitions for each transform type */
  transformSchemas: Record<string, Record<string, TransformParamDef>>
  /** Current transform_params value */
  value: Record<string, unknown> | undefined
  /** Callback when params change */
  onChange: (value: Record<string, unknown> | undefined) => void
}

/**
 * Dynamic editor for transform_params based on selected transform type.
 * Renders a form with appropriate inputs for each parameter defined in the schema.
 */
export function TransformParamsEditor({
  selectedTransform,
  transformSchemas,
  value,
  onChange,
}: TransformParamsEditorProps) {
  // Local state for editing
  const [localParams, setLocalParams] = useState<Record<string, unknown>>(value || {})

  // Get the schema for the selected transform
  const currentSchema = selectedTransform ? transformSchemas[selectedTransform] : null

  // Initialize params with defaults when transform changes
  useEffect(() => {
    if (currentSchema) {
      const newParams: Record<string, unknown> = {}
      for (const [key, def] of Object.entries(currentSchema)) {
        if (def.default !== undefined) {
          newParams[key] = value?.[key] ?? def.default
        } else if (value?.[key] !== undefined) {
          newParams[key] = value[key]
        }
      }
      setLocalParams(newParams)
    } else {
      setLocalParams({})
    }
  }, [selectedTransform, currentSchema])

  // Sync local params to parent
  useEffect(() => {
    const hasValues = Object.keys(localParams).length > 0 &&
                      Object.values(localParams).some(v => v !== undefined && v !== '')
    onChange(hasValues ? localParams : undefined)
  }, [localParams])

  const updateParam = useCallback((key: string, val: unknown) => {
    setLocalParams(prev => ({
      ...prev,
      [key]: val,
    }))
  }, [])

  // No transform selected or no schema
  if (!selectedTransform || !currentSchema) {
    return null
  }

  const paramEntries = Object.entries(currentSchema)

  if (paramEntries.length === 0) {
    return null
  }

  return (
    <div className="space-y-3 p-3 bg-muted/30 rounded border">
      <Label className="text-xs font-medium text-muted-foreground">
        Parametres de transformation ({selectedTransform})
      </Label>

      <div className="grid gap-3">
        {paramEntries.map(([key, def]) => (
          <div key={key} className="space-y-1">
            <Label className="text-xs">
              {key.replace(/_/g, ' ')}
              {def.description && (
                <span className="ml-1 text-muted-foreground font-normal">
                  - {def.description}
                </span>
              )}
            </Label>

            {def.type === 'boolean' ? (
              <div className="flex items-center gap-2">
                <Switch
                  checked={Boolean(localParams[key] ?? def.default)}
                  onCheckedChange={(checked) => updateParam(key, checked)}
                />
                <span className="text-xs text-muted-foreground">
                  {localParams[key] ? 'Oui' : 'Non'}
                </span>
              </div>
            ) : def.type === 'array' ? (
              <Input
                className="h-8"
                value={Array.isArray(localParams[key])
                  ? (localParams[key] as string[]).join(', ')
                  : String(localParams[key] ?? '')}
                onChange={(e) => {
                  const vals = e.target.value.split(',').map(s => s.trim()).filter(Boolean)
                  updateParam(key, vals.length > 0 ? vals : undefined)
                }}
                placeholder={`ex: valeur1, valeur2`}
              />
            ) : def.type === 'number' || def.type === 'integer' ? (
              <Input
                type="number"
                className="h-8"
                value={String(localParams[key] ?? def.default ?? '')}
                onChange={(e) => updateParam(key, e.target.value ? Number(e.target.value) : undefined)}
              />
            ) : (
              <Input
                className="h-8"
                value={String(localParams[key] ?? def.default ?? '')}
                onChange={(e) => updateParam(key, e.target.value || undefined)}
                placeholder={def.default ? String(def.default) : undefined}
              />
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
