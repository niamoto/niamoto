/**
 * WidgetConfigForm - Combined form for transformer and widget parameters
 *
 * Displays two JsonSchemaForm sections:
 * 1. Transformer params (from transform.yml)
 * 2. Widget params (from export.yml)
 *
 * Supports:
 * - Live preview updates via onChange callback (debounced)
 * - Validation before save
 * - Loading states for both schemas
 */
import { useState, useEffect, useCallback, useRef, useMemo } from 'react'
import { useTranslation } from 'react-i18next'
import { Loader2, Settings2, Palette, Save, X } from 'lucide-react'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { LocalizedInput, type LocalizedString } from '@/components/ui/localized-input'
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from '@/components/ui/accordion'
import JsonSchemaForm from '@/components/forms/JsonSchemaForm'
import type { ConfiguredWidget } from './useWidgetConfig'

interface WidgetConfigFormProps {
  widget: ConfiguredWidget
  groupBy: string
  availableFields?: string[]
  onSave: (config: Partial<ConfiguredWidget>) => Promise<boolean>
  onCancel: () => void
  onChange?: (config: Partial<ConfiguredWidget>) => void
  className?: string
  // i18n
  languages?: string[]
  defaultLang?: string
}

export function WidgetConfigForm({
  widget,
  groupBy,
  availableFields = [],
  onSave,
  onCancel,
  onChange,
  className,
  languages = ['fr', 'en'],
  defaultLang = 'fr',
}: WidgetConfigFormProps) {
  const { t } = useTranslation('widgets')

  // Local state for form values (title and description support LocalizedString)
  const [title, setTitle] = useState<LocalizedString | undefined>(widget.title as LocalizedString | undefined)
  const [description, setDescription] = useState<LocalizedString | undefined>(
    (widget.description as LocalizedString | undefined) || undefined
  )
  const [transformerParams, setTransformerParams] = useState<Record<string, unknown>>(
    widget.transformerParams
  )
  const [widgetParams, setWidgetParams] = useState<Record<string, unknown>>(
    widget.widgetParams
  )

  // Loading/saving states
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Reset state when widget changes
  useEffect(() => {
    setTitle(widget.title as LocalizedString | undefined)
    setDescription((widget.description as LocalizedString | undefined) || undefined)
    setTransformerParams(widget.transformerParams)
    setWidgetParams(widget.widgetParams)
    setError(null)
  }, [widget.id])

  // Debounce ref for onChange
  const debounceRef = useRef<NodeJS.Timeout | null>(null)

  // Build current config from state
  const currentConfig = useMemo(() => ({
    title: title as string | Record<string, string> | undefined,
    description: description as string | Record<string, string> | undefined,
    transformerParams,
    widgetParams,
  }), [title, description, transformerParams, widgetParams])

  // Debounced onChange handler
  useEffect(() => {
    if (!onChange) return

    if (debounceRef.current) {
      clearTimeout(debounceRef.current)
    }

    debounceRef.current = setTimeout(() => {
      onChange(currentConfig)
    }, 300)

    return () => {
      if (debounceRef.current) {
        clearTimeout(debounceRef.current)
      }
    }
  }, [currentConfig, onChange])

  // Handle transformer params change
  const handleTransformerChange = useCallback((data: Record<string, unknown>) => {
    setTransformerParams(prev => ({ ...prev, ...data }))
  }, [])

  // Handle widget params change
  const handleWidgetChange = useCallback((data: Record<string, unknown>) => {
    setWidgetParams(prev => ({ ...prev, ...data }))
  }, [])

  // Handle save
  const handleSave = async () => {
    setSaving(true)
    setError(null)

    try {
      const success = await onSave(currentConfig)
      if (!success) {
        setError(t('form.saveError'))
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : t('form.unknownError'))
    } finally {
      setSaving(false)
    }
  }

  // Check if form has changes
  const hasChanges = useMemo(() => {
    return (
      JSON.stringify(title) !== JSON.stringify(widget.title) ||
      JSON.stringify(description) !== JSON.stringify(widget.description || undefined) ||
      JSON.stringify(transformerParams) !== JSON.stringify(widget.transformerParams) ||
      JSON.stringify(widgetParams) !== JSON.stringify(widget.widgetParams)
    )
  }, [title, description, transformerParams, widgetParams, widget])

  return (
    <div className={cn('flex flex-col h-full', className)}>
      {/* Basic info */}
      <div className="space-y-4 p-4 border-b">
        <LocalizedInput
          value={title}
          onChange={setTitle}
          placeholder={t('form.titlePlaceholder')}
          languages={languages}
          defaultLang={defaultLang}
          label={t('form.title', 'Titre')}
        />

        <LocalizedInput
          value={description}
          onChange={setDescription}
          placeholder={t('form.descriptionPlaceholder')}
          languages={languages}
          defaultLang={defaultLang}
          label={t('form.descriptionOptional', 'Description (optionnel)')}
          multiline
          rows={2}
        />
      </div>

      {/* Accordion sections for transformer and widget params */}
      <div className="flex-1 overflow-auto p-4">
        <Accordion type="multiple" defaultValue={['transformer', 'widget']} className="space-y-2">
          {/* Transformer params */}
          <AccordionItem value="transformer" className="border rounded-lg">
            <AccordionTrigger className="px-4 py-3 hover:no-underline">
              <div className="flex items-center gap-2">
                <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-amber-50 border border-amber-200">
                  <Settings2 className="h-4 w-4 text-amber-600" />
                </div>
                <div className="text-left">
                  <span className="font-medium">Transformation des donnees</span>
                  <p className="text-xs text-muted-foreground font-normal">
                    Plugin: {widget.transformerPlugin}
                  </p>
                </div>
              </div>
            </AccordionTrigger>
            <AccordionContent className="px-4 pb-4">
              <JsonSchemaForm
                pluginId={widget.transformerPlugin}
                groupBy={groupBy}
                onChange={handleTransformerChange}
                availableFields={availableFields}
                showTitle={false}
                className="border-0 shadow-none p-0"
                initialValues={transformerParams}
              />
            </AccordionContent>
          </AccordionItem>

          {/* Widget params */}
          <AccordionItem value="widget" className="border rounded-lg">
            <AccordionTrigger className="px-4 py-3 hover:no-underline">
              <div className="flex items-center gap-2">
                <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-emerald-50 border border-emerald-200">
                  <Palette className="h-4 w-4 text-emerald-600" />
                </div>
                <div className="text-left">
                  <span className="font-medium">Visualisation</span>
                  <p className="text-xs text-muted-foreground font-normal">
                    Plugin: {widget.widgetPlugin}
                  </p>
                </div>
              </div>
            </AccordionTrigger>
            <AccordionContent className="px-4 pb-4">
              <JsonSchemaForm
                pluginId={widget.widgetPlugin}
                groupBy={groupBy}
                onChange={handleWidgetChange}
                availableFields={availableFields}
                showTitle={false}
                className="border-0 shadow-none p-0"
                initialValues={widgetParams}
              />
            </AccordionContent>
          </AccordionItem>
        </Accordion>
      </div>

      {/* Error display */}
      {error && (
        <div className="px-4 pb-2">
          <div className="p-3 rounded-lg bg-destructive/10 text-destructive text-sm">
            {error}
          </div>
        </div>
      )}

      {/* Action buttons */}
      <div className="shrink-0 flex items-center justify-end gap-2 p-4 border-t bg-muted/30">
        <Button
          variant="outline"
          onClick={onCancel}
          disabled={saving}
        >
          <X className="mr-2 h-4 w-4" />
          Annuler
        </Button>
        <Button
          onClick={handleSave}
          disabled={saving || !hasChanges}
        >
          {saving ? (
            <>
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              Sauvegarde...
            </>
          ) : (
            <>
              <Save className="mr-2 h-4 w-4" />
              Sauvegarder
            </>
          )}
        </Button>
      </div>
    </div>
  )
}
