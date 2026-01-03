/**
 * WidgetWizard - Guided widget configuration wizard
 *
 * Provides a step-by-step interface to configure complex widgets
 * based on plugin schemas and available class_objects.
 */
import { useState, useMemo } from 'react'
import {
  Wand2,
  ChevronRight,
  ChevronLeft,
  Check,
  X,
  Plus,
  Trash2,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Label } from '@/components/ui/label'
import { Input } from '@/components/ui/input'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Checkbox } from '@/components/ui/checkbox'
import type {
  ClassObjectSuggestion,
  PluginSchema,
  PluginParameter,
  ClassObjectCategory,
} from '@/lib/api/widget-suggestions'
import { CATEGORY_INFO } from '@/lib/api/widget-suggestions'
import yaml from 'js-yaml'

const COMPLEXITY_COLORS = {
  simple: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-950/50 dark:text-emerald-400',
  medium: 'bg-amber-100 text-amber-700 dark:bg-amber-950/50 dark:text-amber-400',
  complex: 'bg-red-100 text-red-700 dark:bg-red-950/50 dark:text-red-400',
}

const COMPLEXITY_LABELS = {
  simple: 'Simple',
  medium: 'Moyen',
  complex: 'Avance',
}

interface WidgetWizardProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  classObjects: ClassObjectSuggestion[]
  pluginSchemas: Record<string, PluginSchema>
  sourceName: string
  onComplete: (config: Record<string, unknown>, widgetId: string, pluginName: string) => void
}

type WizardStep = 'select-plugin' | 'configure' | 'review'

export function WidgetWizard({
  open,
  onOpenChange,
  classObjects,
  pluginSchemas,
  sourceName,
  onComplete,
}: WidgetWizardProps) {
  const [step, setStep] = useState<WizardStep>('select-plugin')
  const [selectedPlugin, setSelectedPlugin] = useState<string | null>(null)
  const [widgetId, setWidgetId] = useState('')
  const [paramValues, setParamValues] = useState<Record<string, unknown>>({})

  // Get schema for selected plugin
  const schema = selectedPlugin ? pluginSchemas[selectedPlugin] : null

  // Filter class_objects by category for a parameter
  const getFilteredClassObjects = (param: PluginParameter) => {
    const categories = Array.isArray(param.filter_category)
      ? param.filter_category
      : [param.filter_category]
    return classObjects.filter((co) =>
      categories.includes(co.category as string)
    )
  }

  // Generate final config
  const generateConfig = (): Record<string, unknown> => {
    if (!schema || !selectedPlugin) return {}

    const config: Record<string, unknown> = {
      source: sourceName,
    }

    // Build config based on plugin type
    schema.parameters.forEach((param) => {
      const value = paramValues[param.name]
      if (value !== undefined) {
        if (param.type === 'class_object_select') {
          config[param.name] = value
        } else if (param.type === 'class_object_list') {
          config[param.name] = value
        } else if (param.type === 'binary_mapping_list') {
          config.groups = value
        } else {
          config[param.name] = value
        }
      }
    })

    return config
  }

  // Reset wizard
  const resetWizard = () => {
    setStep('select-plugin')
    setSelectedPlugin(null)
    setWidgetId('')
    setParamValues({})
  }

  // Handle close
  const handleClose = () => {
    resetWizard()
    onOpenChange(false)
  }

  // Handle plugin selection
  const handleSelectPlugin = (pluginName: string) => {
    setSelectedPlugin(pluginName)
    setParamValues({})
    // Generate default widget ID
    const schema = pluginSchemas[pluginName]
    const baseName = schema.name.toLowerCase().replace(/\s+/g, '_')
    setWidgetId(`${baseName}_1`)
    setStep('configure')
  }

  // Handle complete
  const handleComplete = () => {
    const config = generateConfig()
    onComplete(config, widgetId, selectedPlugin || '')
    handleClose()
  }

  // Check if current step is valid
  const isStepValid = (): boolean => {
    if (step === 'select-plugin') {
      return selectedPlugin !== null
    }
    if (step === 'configure') {
      if (!schema) return false
      // Check all required params have values
      return schema.parameters.every((param) => {
        if (!param.required) return true
        const value = paramValues[param.name]
        if (param.type === 'class_object_list') {
          return Array.isArray(value) && value.length >= (param.min_items || 1)
        }
        return value !== undefined && value !== ''
      })
    }
    if (step === 'review') {
      return widgetId.trim() !== ''
    }
    return false
  }

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="max-w-3xl">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Wand2 className="h-5 w-5 text-primary" />
            Assistant de configuration
          </DialogTitle>
          <DialogDescription>
            {step === 'select-plugin' && 'Choisissez le type de widget a creer'}
            {step === 'configure' && schema && `Configuration: ${schema.name}`}
            {step === 'review' && 'Verifiez et finalisez votre configuration'}
          </DialogDescription>
        </DialogHeader>

        {/* Progress indicator */}
        <div className="flex items-center justify-center gap-2 py-2">
          {(['select-plugin', 'configure', 'review'] as WizardStep[]).map(
            (s, i) => (
              <div key={s} className="flex items-center">
                <div
                  className={cn(
                    'w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium',
                    step === s
                      ? 'bg-primary text-primary-foreground'
                      : i <
                        ['select-plugin', 'configure', 'review'].indexOf(step)
                      ? 'bg-primary/20 text-primary'
                      : 'bg-muted text-muted-foreground'
                  )}
                >
                  {i + 1}
                </div>
                {i < 2 && (
                  <div
                    className={cn(
                      'w-12 h-0.5 mx-1',
                      i < ['select-plugin', 'configure', 'review'].indexOf(step)
                        ? 'bg-primary/50'
                        : 'bg-muted'
                    )}
                  />
                )}
              </div>
            )
          )}
        </div>

        {/* Step content - fixed height with scroll */}
        <div className="h-[400px] overflow-y-auto border rounded-md">
          <div className="p-4">
            {step === 'select-plugin' && (
              <PluginSelectionStep
                pluginSchemas={pluginSchemas}
                classObjects={classObjects}
                onSelect={handleSelectPlugin}
              />
            )}

            {step === 'configure' && schema && (
              <ConfigurationStep
                schema={schema}
                classObjects={classObjects}
                paramValues={paramValues}
                onParamChange={(name, value) =>
                  setParamValues((prev) => ({ ...prev, [name]: value }))
                }
                getFilteredClassObjects={getFilteredClassObjects}
              />
            )}

            {step === 'review' && schema && (
              <ReviewStep
                schema={schema}
                config={generateConfig()}
                widgetId={widgetId}
                onWidgetIdChange={setWidgetId}
              />
            )}
          </div>
        </div>

        {/* Footer with navigation */}
        <div className="flex justify-between pt-4 border-t">
          <Button
            variant="outline"
            onClick={() => {
              if (step === 'configure') setStep('select-plugin')
              else if (step === 'review') setStep('configure')
              else handleClose()
            }}
          >
            {step === 'select-plugin' ? (
              <>
                <X className="h-4 w-4 mr-2" />
                Annuler
              </>
            ) : (
              <>
                <ChevronLeft className="h-4 w-4 mr-2" />
                Precedent
              </>
            )}
          </Button>

          <Button
            onClick={() => {
              if (step === 'select-plugin') setStep('configure')
              else if (step === 'configure') setStep('review')
              else handleComplete()
            }}
            disabled={!isStepValid()}
          >
            {step === 'review' ? (
              <>
                <Check className="h-4 w-4 mr-2" />
                Creer le widget
              </>
            ) : (
              <>
                Suivant
                <ChevronRight className="h-4 w-4 ml-2" />
              </>
            )}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  )
}

// Step 1: Plugin selection
interface PluginSelectionStepProps {
  pluginSchemas: Record<string, PluginSchema>
  classObjects: ClassObjectSuggestion[]
  onSelect: (pluginName: string) => void
}

function PluginSelectionStep({
  pluginSchemas,
  classObjects,
  onSelect,
}: PluginSelectionStepProps) {
  // Count class_objects by category
  const categoryCounts = useMemo(() => {
    const counts: Record<string, number> = {}
    classObjects.forEach((co) => {
      counts[co.category] = (counts[co.category] || 0) + 1
    })
    return counts
  }, [classObjects])

  // Filter plugins that have applicable class_objects
  const applicablePlugins = useMemo(() => {
    return Object.entries(pluginSchemas).filter(([, schema]) =>
      schema.applicable_categories.some((cat) => (categoryCounts[cat] || 0) > 0)
    )
  }, [pluginSchemas, categoryCounts])

  return (
    <div className="space-y-4">
      <p className="text-sm text-muted-foreground">
        Selectionnez le type de widget que vous souhaitez creer. Seuls les
        plugins compatibles avec vos donnees sont affiches.
      </p>

      <div className="grid gap-3">
        {applicablePlugins.map(([pluginName, schema]) => (
          <Card
            key={pluginName}
            className="cursor-pointer hover:border-primary/50 hover:shadow-md transition-all"
            onClick={() => onSelect(pluginName)}
          >
            <CardHeader className="p-4 pb-2">
              <div className="flex items-start justify-between">
                <div>
                  <CardTitle className="text-base">{schema.name}</CardTitle>
                  <CardDescription className="text-sm mt-1">
                    {schema.description}
                  </CardDescription>
                </div>
                <Badge
                  className={cn(
                    'text-xs',
                    COMPLEXITY_COLORS[schema.complexity as keyof typeof COMPLEXITY_COLORS]
                  )}
                >
                  {COMPLEXITY_LABELS[schema.complexity as keyof typeof COMPLEXITY_LABELS]}
                </Badge>
              </div>
            </CardHeader>
            <CardContent className="p-4 pt-2">
              <div className="flex flex-wrap gap-1">
                {schema.applicable_categories.map((cat) => {
                  const info = CATEGORY_INFO[cat as ClassObjectCategory]
                  const count = categoryCounts[cat] || 0
                  return (
                    <Badge
                      key={cat}
                      variant="outline"
                      className={cn('text-xs', count > 0 && info?.bgColor)}
                    >
                      {info?.label || cat} ({count})
                    </Badge>
                  )
                })}
              </div>
            </CardContent>
          </Card>
        ))}

        {applicablePlugins.length === 0 && (
          <div className="text-center py-8 text-muted-foreground">
            Aucun plugin disponible pour les donnees actuelles.
          </div>
        )}
      </div>
    </div>
  )
}

// Step 2: Configuration
interface ConfigurationStepProps {
  schema: PluginSchema
  classObjects: ClassObjectSuggestion[]
  paramValues: Record<string, unknown>
  onParamChange: (name: string, value: unknown) => void
  getFilteredClassObjects: (param: PluginParameter) => ClassObjectSuggestion[]
}

function ConfigurationStep({
  schema,
  paramValues,
  onParamChange,
  getFilteredClassObjects,
}: ConfigurationStepProps) {
  return (
    <div className="space-y-6">
      {schema.parameters.map((param) => (
        <div key={param.name} className="space-y-2">
          <Label className="text-sm font-medium">
            {param.label}
            {param.required && <span className="text-destructive ml-1">*</span>}
          </Label>

          {param.type === 'class_object_select' && (
            <ClassObjectSelect
              classObjects={getFilteredClassObjects(param)}
              value={paramValues[param.name] as string | undefined}
              onChange={(value) => onParamChange(param.name, value)}
            />
          )}

          {param.type === 'class_object_list' && (
            <ClassObjectMultiSelect
              classObjects={getFilteredClassObjects(param)}
              value={(paramValues[param.name] as string[]) || []}
              onChange={(value) => onParamChange(param.name, value)}
              minItems={param.min_items}
            />
          )}

          {param.type === 'binary_mapping_list' && (
            <BinaryMappingEditor
              classObjects={getFilteredClassObjects(param)}
              value={
                (paramValues[param.name] as Array<{
                  field: string
                  label: string
                  classes: string[]
                  class_mapping: Record<string, string>
                }>) || []
              }
              onChange={(value) => onParamChange(param.name, value)}
            />
          )}
        </div>
      ))}
    </div>
  )
}

// Class object single select
interface ClassObjectSelectProps {
  classObjects: ClassObjectSuggestion[]
  value: string | undefined
  onChange: (value: string) => void
}

function ClassObjectSelect({
  classObjects,
  value,
  onChange,
}: ClassObjectSelectProps) {
  return (
    <Select value={value} onValueChange={onChange}>
      <SelectTrigger>
        <SelectValue placeholder="Selectionnez un class_object" />
      </SelectTrigger>
      <SelectContent>
        {classObjects.map((co) => (
          <SelectItem key={co.name} value={co.name}>
            <div className="flex items-center gap-2">
              <span>{co.name}</span>
              <span className="text-xs text-muted-foreground">
                ({co.cardinality} valeurs)
              </span>
            </div>
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  )
}

// Class object multi select
interface ClassObjectMultiSelectProps {
  classObjects: ClassObjectSuggestion[]
  value: string[]
  onChange: (value: string[]) => void
  minItems?: number
}

function ClassObjectMultiSelect({
  classObjects,
  value,
  onChange,
  minItems,
}: ClassObjectMultiSelectProps) {
  const toggleItem = (name: string) => {
    if (value.includes(name)) {
      onChange(value.filter((v) => v !== name))
    } else {
      onChange([...value, name])
    }
  }

  return (
    <div className="space-y-2">
      {minItems && (
        <p className="text-xs text-muted-foreground">
          Selectionnez au moins {minItems} elements
        </p>
      )}
      <div className="border rounded-md p-3 space-y-2 max-h-48 overflow-auto">
        {classObjects.map((co) => (
          <div key={co.name} className="flex items-center gap-2">
            <Checkbox
              checked={value.includes(co.name)}
              onCheckedChange={() => toggleItem(co.name)}
            />
            <span className="text-sm">{co.name}</span>
            <span className="text-xs text-muted-foreground ml-auto">
              {co.cardinality} valeurs
            </span>
          </div>
        ))}
      </div>
    </div>
  )
}

// Binary mapping editor
interface BinaryMappingEditorProps {
  classObjects: ClassObjectSuggestion[]
  value: Array<{
    field: string
    label: string
    classes: string[]
    class_mapping: Record<string, string>
  }>
  onChange: (
    value: Array<{
      field: string
      label: string
      classes: string[]
      class_mapping: Record<string, string>
    }>
  ) => void
}

function BinaryMappingEditor({
  classObjects,
  value,
  onChange,
}: BinaryMappingEditorProps) {
  const addMapping = (coName: string) => {
    const co = classObjects.find((c) => c.name === coName)
    if (!co) return

    const newMapping = {
      field: co.name,
      label: co.name.replace(/_/g, ' '),
      classes: Object.values(co.mapping_hints),
      class_mapping: co.mapping_hints,
    }

    onChange([...value, newMapping])
  }

  const removeMapping = (index: number) => {
    onChange(value.filter((_, i) => i !== index))
  }

  const usedFields = value.map((v) => v.field)
  const availableClassObjects = classObjects.filter(
    (co) => !usedFields.includes(co.name)
  )

  return (
    <div className="space-y-3">
      {value.map((mapping, index) => (
        <Card key={index} className="p-3">
          <div className="flex items-start justify-between">
            <div>
              <p className="font-medium text-sm">{mapping.field}</p>
              <div className="flex gap-2 mt-1">
                {Object.entries(mapping.class_mapping).map(([from, to]) => (
                  <Badge key={from} variant="outline" className="text-xs">
                    {from} → {to}
                  </Badge>
                ))}
              </div>
            </div>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => removeMapping(index)}
            >
              <Trash2 className="h-4 w-4" />
            </Button>
          </div>
        </Card>
      ))}

      {availableClassObjects.length > 0 && (
        <Select onValueChange={addMapping}>
          <SelectTrigger>
            <div className="flex items-center gap-2">
              <Plus className="h-4 w-4" />
              <span>Ajouter un champ binaire</span>
            </div>
          </SelectTrigger>
          <SelectContent>
            {availableClassObjects.map((co) => (
              <SelectItem key={co.name} value={co.name}>
                <div className="flex items-center gap-2">
                  <span>{co.name}</span>
                  <span className="text-xs text-muted-foreground">
                    ({co.class_names.join(' / ')})
                  </span>
                </div>
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      )}
    </div>
  )
}

// Step 3: Review
interface ReviewStepProps {
  schema: PluginSchema
  config: Record<string, unknown>
  widgetId: string
  onWidgetIdChange: (id: string) => void
}

function ReviewStep({
  schema,
  config,
  widgetId,
  onWidgetIdChange,
}: ReviewStepProps) {
  const yamlPreview = yaml.dump(config, { indent: 2 })

  return (
    <div className="space-y-4">
      <div>
        <Label>Identifiant du widget</Label>
        <Input
          value={widgetId}
          onChange={(e) => onWidgetIdChange(e.target.value)}
          placeholder="mon_widget"
          className="mt-1"
        />
        <p className="text-xs text-muted-foreground mt-1">
          Cet identifiant sera utilise dans la configuration YAML
        </p>
      </div>

      <div>
        <Label>Type de widget</Label>
        <p className="text-sm mt-1">{schema.name}</p>
      </div>

      <div>
        <Label>Apercu de la configuration</Label>
        <pre className="mt-2 p-3 rounded-md bg-muted text-xs overflow-auto max-h-64 font-mono">
          {yamlPreview}
        </pre>
      </div>
    </div>
  )
}

export default WidgetWizard
