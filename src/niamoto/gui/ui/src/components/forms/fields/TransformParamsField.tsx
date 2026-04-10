import { useEffect, useMemo, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Switch } from '@/components/ui/switch'
import { FormDescription, FormItem, FormMessage } from '@/components/ui/form'
import { humanizeFieldName } from '../formSchemaUtils'

interface TransformParamDef {
  type: string
  default?: unknown
  description?: string
}

interface TransformParamsFieldProps {
  name: string
  label?: string
  description?: string
  value?: Record<string, unknown>
  onChange?: (value: Record<string, unknown> | undefined) => void
  required?: boolean
  disabled?: boolean
  error?: string
  className?: string
  selectedTransform?: string
  transformSchemas?: Record<string, Record<string, TransformParamDef>>
}

export default function TransformParamsField({
  name: _name,
  label,
  description,
  value,
  onChange,
  required = false,
  disabled = false,
  error,
  className = '',
  selectedTransform,
  transformSchemas,
}: TransformParamsFieldProps) {
  const { t } = useTranslation(['widgets', 'common'])
  const currentSchema = selectedTransform && transformSchemas
    ? transformSchemas[selectedTransform]
    : null
  const resolvedParams = useMemo<Record<string, unknown>>(() => {
    if (!currentSchema) {
      return {}
    }

    const nextParams: Record<string, unknown> = {}
    Object.entries(currentSchema).forEach(([key, def]) => {
      if (value?.[key] !== undefined) {
        nextParams[key] = value[key]
      } else if (def.default !== undefined) {
        nextParams[key] = def.default
      }
    })

    return nextParams
  }, [currentSchema, value])
  const sourceKey = useMemo(
    () => JSON.stringify([selectedTransform ?? null, resolvedParams]),
    [resolvedParams, selectedTransform]
  )
  const [localState, setLocalState] = useState(() => ({
    sourceKey,
    params: resolvedParams,
  }))
  const lastEmittedValueRef = useRef('')
  const localParams = localState.sourceKey === sourceKey ? localState.params : resolvedParams

  useEffect(() => {
    const hasValues = Object.values(localParams).some(
      (paramValue) => paramValue !== undefined && paramValue !== ''
    )
    const nextValue = hasValues ? localParams : undefined
    const nextKey = JSON.stringify(nextValue ?? null)

    if (nextKey === lastEmittedValueRef.current) {
      return
    }

    lastEmittedValueRef.current = nextKey
    onChange?.(nextValue)
  }, [localParams, onChange])

  if (!selectedTransform || !currentSchema) {
    return null
  }

  return (
    <FormItem className={className}>
      {label && (
        <Label>
          {label}
          {required && <span className="text-red-500 ml-1">*</span>}
        </Label>
      )}

      <div className="space-y-3 rounded-md border bg-muted/30 p-3">
        <div className="text-xs font-medium text-muted-foreground">
          {t('widgets:form.transformParamsFor', { transform: selectedTransform })}
        </div>

        {Object.entries(currentSchema).map(([key, def]) => (
          <div key={key} className="space-y-1">
            <Label className="text-xs">
              {t(`widgets:form.fieldLabels.${key}`, { defaultValue: humanizeFieldName(key) })}
            </Label>

            {def.type === 'boolean' ? (
              <div className="flex items-center">
                <Switch
                  checked={Boolean(localParams[key] ?? def.default)}
                  onCheckedChange={(checked) =>
                    setLocalState({
                      sourceKey,
                      params: { ...localParams, [key]: checked },
                    })
                  }
                  disabled={disabled}
                />
              </div>
            ) : def.type === 'array' ? (
              <Input
                className="h-8"
                value={Array.isArray(localParams[key])
                  ? (localParams[key] as string[]).join(', ')
                  : String(localParams[key] ?? '')}
                onChange={(e) => {
                  const vals = e.target.value
                    .split(',')
                    .map((item) => item.trim())
                    .filter(Boolean)
                  setLocalState({
                    sourceKey,
                    params: {
                      ...localParams,
                      [key]: vals.length > 0 ? vals : undefined,
                    },
                  })
                }}
                placeholder={t('widgets:form.commaSeparatedValues')}
                disabled={disabled}
              />
            ) : def.type === 'number' || def.type === 'integer' ? (
              <Input
                type="number"
                className="h-8"
                value={String(localParams[key] ?? def.default ?? '')}
                onChange={(e) =>
                  setLocalState({
                    sourceKey,
                    params: {
                      ...localParams,
                      [key]: e.target.value ? Number(e.target.value) : undefined,
                    },
                  })
                }
                disabled={disabled}
              />
            ) : (
              <Input
                className="h-8"
                value={String(localParams[key] ?? def.default ?? '')}
                onChange={(e) =>
                  setLocalState({
                    sourceKey,
                    params: {
                      ...localParams,
                      [key]: e.target.value || undefined,
                    },
                  })
                }
                placeholder={def.default ? String(def.default) : undefined}
                disabled={disabled}
              />
            )}

            {def.description && (
              <p className="text-xs text-muted-foreground">{def.description}</p>
            )}
          </div>
        ))}
      </div>

      {description && !error && (
        <FormDescription>{description}</FormDescription>
      )}
      {error && (
        <FormMessage className="text-red-500">{error}</FormMessage>
      )}
    </FormItem>
  )
}
