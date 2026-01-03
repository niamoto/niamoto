/**
 * BinaryMappingWizard - Configure binary class_object mappings
 *
 * Helps users configure binary_aggregator widgets by:
 * - Showing detected binary class_objects
 * - Auto-suggesting mappings (Forêt → forest)
 * - Allowing custom mapping overrides
 * - Grouping related class_objects together
 */
import { useState, useMemo } from 'react'
import {
  Binary,
  ArrowRight,
  Check,
  Edit2,
  Sparkles,
  Link2,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Card, CardContent } from '@/components/ui/card'
import { Checkbox } from '@/components/ui/checkbox'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog'
import type { ClassObjectSuggestion } from '@/lib/api/widget-suggestions'

interface BinaryMapping {
  field: string
  label: string
  classes: [string, string]
  class_mapping: Record<string, string>
}

interface BinaryMappingWizardProps {
  binaryClassObjects: ClassObjectSuggestion[]
  onGenerate: (config: { groups: BinaryMapping[] }) => void
  className?: string
}

export function BinaryMappingWizard({
  binaryClassObjects,
  onGenerate,
  className,
}: BinaryMappingWizardProps) {
  const [selectedFields, setSelectedFields] = useState<Set<string>>(new Set())
  const [mappings, setMappings] = useState<Record<string, BinaryMapping>>({})
  const [editingField, setEditingField] = useState<string | null>(null)

  // Detect related binary fields (same pattern group)
  const relatedGroups = useMemo(() => {
    const groups: Record<string, ClassObjectSuggestion[]> = {}
    binaryClassObjects.forEach((co) => {
      if (co.pattern_group) {
        if (!groups[co.pattern_group]) {
          groups[co.pattern_group] = []
        }
        groups[co.pattern_group].push(co)
      }
    })
    return groups
  }, [binaryClassObjects])

  // Initialize mapping from auto-config
  const initializeMapping = (co: ClassObjectSuggestion): BinaryMapping => {
    const autoConfig = co.auto_config as {
      groups?: Array<{
        field: string
        classes: string[]
        class_mapping: Record<string, string>
      }>
    }
    const group = autoConfig?.groups?.[0]

    if (group) {
      return {
        field: co.name,
        label: co.name.replace(/_/g, ' ').replace(/^cover /, ''),
        classes: group.classes as [string, string],
        class_mapping: group.class_mapping,
      }
    }

    // Fallback: use class_names directly
    const [first, second] = co.class_names
    return {
      field: co.name,
      label: co.name.replace(/_/g, ' '),
      classes: ['positive', 'negative'],
      class_mapping: {
        [first]: 'positive',
        [second]: 'negative',
      },
    }
  }

  const toggleField = (name: string) => {
    setSelectedFields((prev) => {
      const next = new Set(prev)
      if (next.has(name)) {
        next.delete(name)
        // Remove mapping
        setMappings((m) => {
          const { [name]: _, ...rest } = m
          return rest
        })
      } else {
        next.add(name)
        // Initialize mapping
        const co = binaryClassObjects.find((c) => c.name === name)
        if (co) {
          setMappings((m) => ({
            ...m,
            [name]: initializeMapping(co),
          }))
        }
      }
      return next
    })
  }

  const selectGroup = (groupName: string) => {
    const group = relatedGroups[groupName]
    if (!group) return

    group.forEach((co) => {
      if (!selectedFields.has(co.name)) {
        setSelectedFields((prev) => new Set([...prev, co.name]))
        setMappings((m) => ({
          ...m,
          [co.name]: initializeMapping(co),
        }))
      }
    })
  }

  const updateMapping = (field: string, updates: Partial<BinaryMapping>) => {
    setMappings((prev) => ({
      ...prev,
      [field]: { ...prev[field], ...updates },
    }))
  }

  const handleGenerate = () => {
    const groups = Array.from(selectedFields).map((field) => mappings[field])
    onGenerate({ groups })
  }

  return (
    <div className={cn('space-y-4', className)}>
      {/* Header */}
      <div className="flex items-center gap-2">
        <Binary className="h-4 w-4 text-emerald-600" />
        <h3 className="text-sm font-medium">Configuration binaire</h3>
        <Badge variant="secondary" className="ml-auto">
          {binaryClassObjects.length} disponibles
        </Badge>
      </div>

      <p className="text-xs text-muted-foreground">
        Selectionnez les class_objects binaires a inclure et configurez les mappings.
      </p>

      {/* Related groups shortcuts */}
      {Object.keys(relatedGroups).length > 0 && (
        <div className="flex flex-wrap gap-2">
          {Object.entries(relatedGroups).map(([groupName, items]) => (
            <Button
              key={groupName}
              variant="outline"
              size="sm"
              className="h-7 text-xs"
              onClick={() => selectGroup(groupName)}
            >
              <Link2 className="h-3 w-3 mr-1" />
              {groupName} ({items.length})
            </Button>
          ))}
        </div>
      )}

      {/* Class objects list */}
      <div className="space-y-2">
        {binaryClassObjects.map((co) => {
          const isSelected = selectedFields.has(co.name)
          const mapping = mappings[co.name]
          const hasAutoMapping = Object.keys(co.mapping_hints).length > 0

          return (
            <Card
              key={co.name}
              className={cn(
                'transition-colors',
                isSelected && 'border-primary/50 bg-primary/5'
              )}
            >
              <CardContent className="p-3">
                <div className="flex items-start gap-3">
                  <Checkbox
                    checked={isSelected}
                    onCheckedChange={() => toggleField(co.name)}
                    className="mt-0.5"
                  />

                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-medium">{co.name}</span>
                      {hasAutoMapping && (
                        <Badge
                          variant="secondary"
                          className="text-[10px] bg-amber-100 text-amber-700"
                        >
                          <Sparkles className="h-2.5 w-2.5 mr-0.5" />
                          Auto
                        </Badge>
                      )}
                    </div>

                    {/* Original values */}
                    <div className="flex items-center gap-2 mt-1">
                      <span className="text-xs text-muted-foreground">
                        {co.class_names.join(' / ')}
                      </span>
                    </div>

                    {/* Mapping preview */}
                    {isSelected && mapping && (
                      <div className="mt-2 flex items-center gap-2 flex-wrap">
                        {Object.entries(mapping.class_mapping).map(([from, to]) => (
                          <div
                            key={from}
                            className="flex items-center gap-1 text-xs bg-muted/50 px-2 py-0.5 rounded"
                          >
                            <span className="text-muted-foreground">{from}</span>
                            <ArrowRight className="h-3 w-3" />
                            <span className="font-medium">{to}</span>
                          </div>
                        ))}
                        <Button
                          variant="ghost"
                          size="sm"
                          className="h-6 w-6 p-0"
                          onClick={() => setEditingField(co.name)}
                        >
                          <Edit2 className="h-3 w-3" />
                        </Button>
                      </div>
                    )}
                  </div>

                  {isSelected && (
                    <Check className="h-4 w-4 text-primary flex-shrink-0" />
                  )}
                </div>
              </CardContent>
            </Card>
          )
        })}
      </div>

      {/* Generate button */}
      {selectedFields.size > 0 && (
        <Button onClick={handleGenerate} className="w-full">
          Generer la configuration ({selectedFields.size} champs)
        </Button>
      )}

      {/* Edit mapping dialog */}
      <EditMappingDialog
        open={editingField !== null}
        onOpenChange={(open) => !open && setEditingField(null)}
        mapping={editingField ? mappings[editingField] : null}
        classObject={binaryClassObjects.find((co) => co.name === editingField) || null}
        onSave={(updated) => {
          if (editingField) {
            updateMapping(editingField, updated)
          }
          setEditingField(null)
        }}
      />
    </div>
  )
}

interface EditMappingDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  mapping: BinaryMapping | null
  classObject: ClassObjectSuggestion | null
  onSave: (mapping: Partial<BinaryMapping>) => void
}

function EditMappingDialog({
  open,
  onOpenChange,
  mapping,
  classObject,
  onSave,
}: EditMappingDialogProps) {
  const [label, setLabel] = useState(mapping?.label || '')
  const [class1, setClass1] = useState(mapping?.classes[0] || '')
  const [class2, setClass2] = useState(mapping?.classes[1] || '')
  const [mapping1, setMapping1] = useState('')
  const [mapping2, setMapping2] = useState('')

  // Reset when dialog opens
  useState(() => {
    if (mapping && classObject) {
      setLabel(mapping.label)
      setClass1(mapping.classes[0])
      setClass2(mapping.classes[1])
      const entries = Object.entries(mapping.class_mapping)
      if (entries[0]) setMapping1(entries[0][0])
      if (entries[1]) setMapping2(entries[1][0])
    }
  })

  if (!mapping || !classObject) return null

  const handleSave = () => {
    onSave({
      label,
      classes: [class1, class2],
      class_mapping: {
        [mapping1 || classObject.class_names[0]]: class1,
        [mapping2 || classObject.class_names[1]]: class2,
      },
    })
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Modifier le mapping: {mapping.field}</DialogTitle>
        </DialogHeader>

        <div className="space-y-4">
          <div>
            <Label>Label d'affichage</Label>
            <Input
              value={label}
              onChange={(e) => setLabel(e.target.value)}
              placeholder="ex: emprise"
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <Label>Classe 1 (cle)</Label>
              <Input
                value={class1}
                onChange={(e) => setClass1(e.target.value)}
                placeholder="forest"
              />
            </div>
            <div>
              <Label>Classe 2 (cle)</Label>
              <Input
                value={class2}
                onChange={(e) => setClass2(e.target.value)}
                placeholder="non_forest"
              />
            </div>
          </div>

          <div className="p-3 bg-muted/50 rounded-md">
            <p className="text-xs text-muted-foreground mb-2">
              Valeurs originales dans le CSV:
            </p>
            <div className="flex gap-4">
              {classObject.class_names.map((name, i) => (
                <div key={name} className="flex items-center gap-1">
                  <span className="text-sm">{name}</span>
                  <ArrowRight className="h-3 w-3 text-muted-foreground" />
                  <Badge variant="outline" className="text-xs">
                    {i === 0 ? class1 : class2}
                  </Badge>
                </div>
              ))}
            </div>
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Annuler
          </Button>
          <Button onClick={handleSave}>Sauvegarder</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

export default BinaryMappingWizard
