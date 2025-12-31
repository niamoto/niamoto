/**
 * DisplayFieldEditor - Modal for editing a display field configuration
 *
 * Provides detailed editing for all display field properties:
 * - Basic: name, source, type, label
 * - Search: searchable flag
 * - Display: format, badge options
 * - Advanced: link settings, mapping
 */
import { useState, useEffect } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Switch } from '@/components/ui/switch'
import { Textarea } from '@/components/ui/textarea'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
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
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from '@/components/ui/accordion'
import { Settings2, Search, Palette, Link2, Braces, Plus, X } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import type { IndexDisplayField } from './useIndexConfig'

interface DisplayFieldEditorProps {
  field: IndexDisplayField
  open: boolean
  onOpenChange: (open: boolean) => void
  onSave: (field: Partial<IndexDisplayField>) => void
}

// Helper to parse JSON safely
function parseJsonObject(value: string): Record<string, string> | null {
  if (!value.trim()) return {}
  try {
    const parsed = JSON.parse(value)
    if (typeof parsed === 'object' && parsed !== null && !Array.isArray(parsed)) {
      return parsed
    }
    return null
  } catch {
    return null
  }
}

// Helper to stringify JSON for display
function stringifyJsonObject(obj: Record<string, string> | undefined): string {
  if (!obj || Object.keys(obj).length === 0) return ''
  return JSON.stringify(obj, null, 2)
}

export function DisplayFieldEditor({
  field,
  open,
  onOpenChange,
  onSave,
}: DisplayFieldEditorProps) {
  // Local state for editing
  const [localField, setLocalField] = useState<IndexDisplayField>(field)

  // State for JSON text editing
  const [mappingText, setMappingText] = useState(stringifyJsonObject(field.mapping))
  const [mappingError, setMappingError] = useState<string | null>(null)
  const [badgeColorsText, setBadgeColorsText] = useState(stringifyJsonObject(field.badge_colors))
  const [badgeColorsError, setBadgeColorsError] = useState<string | null>(null)

  // State for filter options
  const [newFilterValue, setNewFilterValue] = useState('')
  const [newFilterLabel, setNewFilterLabel] = useState('')

  // Reset local state when field changes
  useEffect(() => {
    setLocalField(field)
    setMappingText(stringifyJsonObject(field.mapping))
    setMappingError(null)
    setBadgeColorsText(stringifyJsonObject(field.badge_colors))
    setBadgeColorsError(null)
    setNewFilterValue('')
    setNewFilterLabel('')
  }, [field])

  // Update local field
  const updateField = (updates: Partial<IndexDisplayField>) => {
    setLocalField(prev => ({ ...prev, ...updates }))
  }

  // Handle mapping text change
  const handleMappingChange = (text: string) => {
    setMappingText(text)
    const parsed = parseJsonObject(text)
    if (parsed === null) {
      setMappingError('JSON invalide')
    } else {
      setMappingError(null)
      updateField({ mapping: Object.keys(parsed).length > 0 ? parsed : undefined })
    }
  }

  // Handle badge colors text change
  const handleBadgeColorsChange = (text: string) => {
    setBadgeColorsText(text)
    const parsed = parseJsonObject(text)
    if (parsed === null) {
      setBadgeColorsError('JSON invalide')
    } else {
      setBadgeColorsError(null)
      updateField({ badge_colors: Object.keys(parsed).length > 0 ? parsed : undefined })
    }
  }

  // Handle adding filter option
  const handleAddFilterOption = () => {
    if (!newFilterValue.trim()) return
    const newOption = {
      value: newFilterValue.trim(),
      label: newFilterLabel.trim() || newFilterValue.trim()
    }
    const currentOptions = localField.filter_options || []
    updateField({ filter_options: [...currentOptions, newOption] })
    setNewFilterValue('')
    setNewFilterLabel('')
  }

  // Handle removing filter option
  const handleRemoveFilterOption = (index: number) => {
    const currentOptions = localField.filter_options || []
    updateField({
      filter_options: currentOptions.filter((_, i) => i !== index) || undefined
    })
  }

  // Handle save
  const handleSave = () => {
    // Don't save if there are JSON errors
    if (mappingError || badgeColorsError) return
    onSave(localField)
    onOpenChange(false)
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-hidden flex flex-col">
        <DialogHeader>
          <DialogTitle>Modifier le champ</DialogTitle>
          <DialogDescription>
            Configurez les proprietes du champ "{field.name || 'nouveau champ'}"
          </DialogDescription>
        </DialogHeader>

        <div className="flex-1 overflow-y-auto pr-2 -mr-2">
          <Accordion type="multiple" defaultValue={['basic', 'display']} className="space-y-2">
            {/* Basic settings */}
            <AccordionItem value="basic" className="border rounded-lg">
              <AccordionTrigger className="px-4 py-3 hover:no-underline">
                <div className="flex items-center gap-2">
                  <Settings2 className="h-4 w-4 text-muted-foreground" />
                  <span className="font-medium">Parametres de base</span>
                </div>
              </AccordionTrigger>
              <AccordionContent className="px-4 pb-4 space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="field-name">Nom du champ</Label>
                    <Input
                      id="field-name"
                      value={localField.name}
                      onChange={(e) => updateField({ name: e.target.value })}
                      placeholder="nom_du_champ"
                    />
                    <p className="text-xs text-muted-foreground">
                      Identifiant unique du champ
                    </p>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="field-label">Label (optionnel)</Label>
                    <Input
                      id="field-label"
                      value={localField.label || ''}
                      onChange={(e) => updateField({ label: e.target.value || undefined })}
                      placeholder="Nom affiche"
                    />
                    <p className="text-xs text-muted-foreground">
                      Label affiche dans l'interface
                    </p>
                  </div>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="field-source">Source (chemin JSON)</Label>
                  <Input
                    id="field-source"
                    value={localField.source}
                    onChange={(e) => updateField({ source: e.target.value })}
                    placeholder="general_info.name.value"
                    className="font-mono"
                  />
                  <p className="text-xs text-muted-foreground">
                    Chemin vers la valeur dans les donnees (ex: general_info.rank.value)
                  </p>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="field-fallback">Fallback (optionnel)</Label>
                  <Input
                    id="field-fallback"
                    value={localField.fallback || ''}
                    onChange={(e) => updateField({ fallback: e.target.value || undefined })}
                    placeholder="chemin.alternatif"
                    className="font-mono"
                  />
                  <p className="text-xs text-muted-foreground">
                    Chemin alternatif si la source est vide
                  </p>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label>Type de donnee</Label>
                    <Select
                      value={localField.type}
                      onValueChange={(value) => updateField({ type: value as IndexDisplayField['type'] })}
                    >
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="text">Texte</SelectItem>
                        <SelectItem value="select">Selection</SelectItem>
                        <SelectItem value="boolean">Booleen</SelectItem>
                        <SelectItem value="json_array">Tableau JSON</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="space-y-2">
                    <Label>Mode d'affichage</Label>
                    <Select
                      value={localField.display}
                      onValueChange={(value) => updateField({ display: value as IndexDisplayField['display'] })}
                    >
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="normal">Normal</SelectItem>
                        <SelectItem value="hidden">Cache</SelectItem>
                        <SelectItem value="image_preview">Apercu image</SelectItem>
                        <SelectItem value="link">Lien</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>
              </AccordionContent>
            </AccordionItem>

            {/* Search settings */}
            <AccordionItem value="search" className="border rounded-lg">
              <AccordionTrigger className="px-4 py-3 hover:no-underline">
                <div className="flex items-center gap-2">
                  <Search className="h-4 w-4 text-muted-foreground" />
                  <span className="font-medium">Recherche</span>
                </div>
              </AccordionTrigger>
              <AccordionContent className="px-4 pb-4 space-y-4">
                <div className="flex items-center justify-between">
                  <div className="space-y-0.5">
                    <Label>Champ recherchable</Label>
                    <p className="text-xs text-muted-foreground">
                      Inclure ce champ dans la recherche texte
                    </p>
                  </div>
                  <Switch
                    checked={localField.searchable}
                    onCheckedChange={(checked) => updateField({ searchable: checked })}
                  />
                </div>

                <div className="flex items-center justify-between">
                  <div className="space-y-0.5">
                    <Label>Options dynamiques</Label>
                    <p className="text-xs text-muted-foreground">
                      Generer les options de filtre depuis les donnees
                    </p>
                  </div>
                  <Switch
                    checked={localField.dynamic_options}
                    onCheckedChange={(checked) => updateField({ dynamic_options: checked })}
                  />
                </div>
              </AccordionContent>
            </AccordionItem>

            {/* Display/Badge settings */}
            <AccordionItem value="display" className="border rounded-lg">
              <AccordionTrigger className="px-4 py-3 hover:no-underline">
                <div className="flex items-center gap-2">
                  <Palette className="h-4 w-4 text-muted-foreground" />
                  <span className="font-medium">Apparence</span>
                </div>
              </AccordionTrigger>
              <AccordionContent className="px-4 pb-4 space-y-4">
                <div className="space-y-2">
                  <Label>Format d'affichage</Label>
                  <Select
                    value={localField.format || 'none'}
                    onValueChange={(value) => updateField({ format: value === 'none' ? undefined : value as IndexDisplayField['format'] })}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Aucun" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="none">Aucun</SelectItem>
                      <SelectItem value="badge">Badge</SelectItem>
                      <SelectItem value="map">Mapping</SelectItem>
                      <SelectItem value="number">Nombre</SelectItem>
                      <SelectItem value="link">Lien</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div className="flex items-center justify-between">
                  <div className="space-y-0.5">
                    <Label>Badge inline</Label>
                    <p className="text-xs text-muted-foreground">
                      Afficher comme badge dans le titre
                    </p>
                  </div>
                  <Switch
                    checked={localField.inline_badge}
                    onCheckedChange={(checked) => updateField({ inline_badge: checked })}
                  />
                </div>

                {localField.inline_badge && (
                  <div className="space-y-2">
                    <Label htmlFor="badge-color">Couleur du badge (classes CSS)</Label>
                    <Input
                      id="badge-color"
                      value={localField.badge_color || ''}
                      onChange={(e) => updateField({ badge_color: e.target.value || undefined })}
                      placeholder="bg-green-600 text-white"
                    />
                  </div>
                )}

                {localField.type === 'boolean' && (
                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label htmlFor="true-label">Label pour vrai</Label>
                      <Input
                        id="true-label"
                        value={localField.true_label || ''}
                        onChange={(e) => updateField({ true_label: e.target.value || undefined })}
                        placeholder="Oui"
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="false-label">Label pour faux</Label>
                      <Input
                        id="false-label"
                        value={localField.false_label || ''}
                        onChange={(e) => updateField({ false_label: e.target.value || undefined })}
                        placeholder="Non"
                      />
                    </div>
                  </div>
                )}
              </AccordionContent>
            </AccordionItem>

            {/* Link settings */}
            {localField.display === 'link' && (
              <AccordionItem value="link" className="border rounded-lg">
                <AccordionTrigger className="px-4 py-3 hover:no-underline">
                  <div className="flex items-center gap-2">
                    <Link2 className="h-4 w-4 text-muted-foreground" />
                    <span className="font-medium">Paramètres du lien</span>
                  </div>
                </AccordionTrigger>
                <AccordionContent className="px-4 pb-4 space-y-4">
                  <div className="space-y-2">
                    <Label htmlFor="link-template">Template URL</Label>
                    <Input
                      id="link-template"
                      value={localField.link_template || ''}
                      onChange={(e) => updateField({ link_template: e.target.value || undefined })}
                      placeholder="https://example.com/{value}"
                      className="font-mono"
                    />
                    <p className="text-xs text-muted-foreground">
                      Utilisez {'{value}'} pour inserer la valeur du champ
                    </p>
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label htmlFor="link-label">Label du lien</Label>
                      <Input
                        id="link-label"
                        value={localField.link_label || ''}
                        onChange={(e) => updateField({ link_label: e.target.value || undefined })}
                        placeholder="Voir plus"
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="link-target">Target</Label>
                      <Select
                        value={localField.link_target || '_self'}
                        onValueChange={(value) => updateField({ link_target: value })}
                      >
                        <SelectTrigger>
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="_self">Meme fenetre</SelectItem>
                          <SelectItem value="_blank">Nouvelle fenetre</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                  </div>
                </AccordionContent>
              </AccordionItem>
            )}

            {/* Advanced: Mapping & Filter Options */}
            <AccordionItem value="advanced" className="border rounded-lg">
              <AccordionTrigger className="px-4 py-3 hover:no-underline">
                <div className="flex items-center gap-2">
                  <Braces className="h-4 w-4 text-muted-foreground" />
                  <span className="font-medium">Mapping & Filtres</span>
                </div>
              </AccordionTrigger>
              <AccordionContent className="px-4 pb-4 space-y-4">
                {/* Value Mapping */}
                <div className="space-y-2">
                  <Label htmlFor="mapping">Mapping des valeurs (JSON)</Label>
                  <Textarea
                    id="mapping"
                    value={mappingText}
                    onChange={(e) => handleMappingChange(e.target.value)}
                    placeholder='{"species": "Espèce", "genus": "Genre"}'
                    className={`font-mono text-sm min-h-[80px] ${mappingError ? 'border-destructive' : ''}`}
                  />
                  {mappingError && (
                    <p className="text-xs text-destructive">{mappingError}</p>
                  )}
                  <p className="text-xs text-muted-foreground">
                    Transforme les valeurs pour l'affichage (ex: codes -&gt; labels)
                  </p>
                </div>

                {/* Filter Options (for select type) */}
                {localField.type === 'select' && !localField.dynamic_options && (
                  <div className="space-y-2">
                    <Label>Options de filtre statiques</Label>
                    <div className="space-y-2">
                      {(localField.filter_options || []).map((option, index) => (
                        <div key={index} className="flex items-center gap-2">
                          <Badge variant="secondary" className="flex-1 justify-between py-1.5">
                            <span className="font-mono text-xs">{option.value}</span>
                            <span className="text-muted-foreground mx-2">→</span>
                            <span className="text-xs">{option.label}</span>
                          </Badge>
                          <Button
                            variant="ghost"
                            size="icon"
                            className="h-7 w-7 shrink-0"
                            onClick={() => handleRemoveFilterOption(index)}
                          >
                            <X className="h-3 w-3" />
                          </Button>
                        </div>
                      ))}

                      {/* Add new filter option */}
                      <div className="flex items-end gap-2 mt-2">
                        <div className="flex-1 space-y-1">
                          <Label className="text-xs">Valeur</Label>
                          <Input
                            value={newFilterValue}
                            onChange={(e) => setNewFilterValue(e.target.value)}
                            placeholder="species"
                            className="h-8 text-sm"
                          />
                        </div>
                        <div className="flex-1 space-y-1">
                          <Label className="text-xs">Label</Label>
                          <Input
                            value={newFilterLabel}
                            onChange={(e) => setNewFilterLabel(e.target.value)}
                            placeholder="Espèce"
                            className="h-8 text-sm"
                          />
                        </div>
                        <Button
                          variant="outline"
                          size="sm"
                          className="h-8"
                          onClick={handleAddFilterOption}
                          disabled={!newFilterValue.trim()}
                        >
                          <Plus className="h-3 w-3" />
                        </Button>
                      </div>
                    </div>
                    <p className="text-xs text-muted-foreground">
                      Options fixes pour le filtre (desactiver "Options dynamiques" d'abord)
                    </p>
                  </div>
                )}

                {/* Badge colors per value */}
                {(localField.inline_badge || localField.format === 'badge') && (
                  <div className="space-y-2">
                    <Label htmlFor="badge-colors">Couleurs par valeur (JSON)</Label>
                    <Textarea
                      id="badge-colors"
                      value={badgeColorsText}
                      onChange={(e) => handleBadgeColorsChange(e.target.value)}
                      placeholder='{"endemic": "bg-green-600 text-white", "native": "bg-blue-600 text-white"}'
                      className={`font-mono text-sm min-h-[80px] ${badgeColorsError ? 'border-destructive' : ''}`}
                    />
                    {badgeColorsError && (
                      <p className="text-xs text-destructive">{badgeColorsError}</p>
                    )}
                    <p className="text-xs text-muted-foreground">
                      Classes CSS par valeur pour styliser les badges differemment
                    </p>
                  </div>
                )}
              </AccordionContent>
            </AccordionItem>
          </Accordion>
        </div>

        <DialogFooter className="mt-4">
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Annuler
          </Button>
          <Button
            onClick={handleSave}
            disabled={!!mappingError || !!badgeColorsError}
          >
            Enregistrer
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
