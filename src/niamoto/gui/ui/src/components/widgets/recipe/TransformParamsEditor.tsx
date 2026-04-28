import { useCallback, useMemo } from 'react'
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

function cleanParams(params: Record<string, unknown>): Record<string, unknown> | undefined {
  const entries = Object.entries(params).filter(
    ([, value]) => value !== undefined && value !== ''
  )

  if (entries.length === 0) {
    return undefined
  }

  return Object.fromEntries(entries)
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
  // Get the schema for the selected transform
  const currentSchema = selectedTransform ? transformSchemas[selectedTransform] : null

  const displayParams = useMemo(() => {
    const nextParams: Record<string, unknown> = {}
    if (currentSchema) {
      for (const [key, def] of Object.entries(currentSchema)) {
        if (def.default !== undefined) {
          nextParams[key] = value?.[key] ?? def.default
        } else if (value?.[key] !== undefined) {
          nextParams[key] = value[key]
        }
      }
    }

    return nextParams
  }, [currentSchema, value])

  const updateParam = useCallback((key: string, val: unknown) => {
    const nextParams = { ...displayParams }

    if (val === undefined || val === '') {
      delete nextParams[key]
    } else {
      nextParams[key] = val
    }

    onChange(cleanParams(nextParams))
  }, [displayParams, onChange])

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
        Paramètres de transformation ({selectedTransform})
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
                  checked={Boolean(displayParams[key] ?? def.default)}
                  onCheckedChange={(checked) => updateParam(key, checked)}
                />
                <span className="text-xs text-muted-foreground">
                  {displayParams[key] ? 'Oui' : 'Non'}
                </span>
              </div>
            ) : def.type === 'array' ? (
              <Input
                className="h-8"
                value={Array.isArray(displayParams[key])
                  ? (displayParams[key] as string[]).join(', ')
                  : String(displayParams[key] ?? '')}
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
                value={String(displayParams[key] ?? def.default ?? '')}
                onChange={(e) => updateParam(key, e.target.value ? Number(e.target.value) : undefined)}
              />
            ) : (
              <Input
                className="h-8"
                value={String(displayParams[key] ?? def.default ?? '')}
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
