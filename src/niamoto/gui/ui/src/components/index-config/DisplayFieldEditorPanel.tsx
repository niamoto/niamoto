/**
 * DisplayFieldEditorPanel - Panel for editing a display field configuration
 *
 * Provides detailed editing for all display field properties in a side panel:
 * - Basic: name, source, type, label
 * - Search: searchable flag
 * - Display: format, badge options
 * - Advanced: link settings, mapping
 */
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Switch } from '@/components/ui/switch'
import { Textarea } from '@/components/ui/textarea'
import { LocalizedInput } from '@/components/ui/localized-input'
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
import { Settings2, Search, Palette, Link2, Braces, Plus, X, PanelRightClose, Save } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { FieldSourcePicker } from './FieldSourcePicker'
import type { IndexDisplayField, SuggestedDisplayField } from './useIndexConfig'

interface DisplayFieldEditorPanelProps {
  field: IndexDisplayField
  fieldIndex: number
  availableFields?: SuggestedDisplayField[]
  loadingAvailableFields?: boolean
  onLoadAvailableFields?: () => void
  onSave: (field: Partial<IndexDisplayField>) => void
  onClose: () => void
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

function isPlaceholderFieldName(name: string): boolean {
  return !name.trim() || /^field_\d+$/i.test(name.trim())
}

export function DisplayFieldEditorPanel({
  field,
  fieldIndex,
  availableFields = [],
  loadingAvailableFields = false,
  onLoadAvailableFields,
  onSave,
  onClose,
}: DisplayFieldEditorPanelProps) {
  const { t } = useTranslation(['sources', 'common', 'indexConfig'])
  // Local state for editing
  const [localField, setLocalField] = useState<IndexDisplayField>(field)
  const [isDirty, setIsDirty] = useState(false)

  // State for JSON text editing
  const [mappingText, setMappingText] = useState(stringifyJsonObject(field.mapping))
  const [mappingError, setMappingError] = useState<string | null>(null)
  const [badgeColorsText, setBadgeColorsText] = useState(stringifyJsonObject(field.badge_colors))
  const [badgeColorsError, setBadgeColorsError] = useState<string | null>(null)

  // State for filter options
  const [newFilterValue, setNewFilterValue] = useState('')
  const [newFilterLabel, setNewFilterLabel] = useState('')

  // Update local field
  const updateField = (updates: Partial<IndexDisplayField>) => {
    setLocalField(prev => ({ ...prev, ...updates }))
    setIsDirty(true)
  }

  // Handle mapping text change
  const handleMappingChange = (text: string) => {
    setMappingText(text)
    const parsed = parseJsonObject(text)
    if (parsed === null) {
      setMappingError(t('indexConfig:fieldEditor.invalidJson'))
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
      setBadgeColorsError(t('indexConfig:fieldEditor.invalidJson'))
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
    setIsDirty(false)
  }

  const handleSelectSourceField = (suggestion: SuggestedDisplayField) => {
    const nextType =
      suggestion.type === 'number' ? 'text' : suggestion.type as IndexDisplayField['type']

    updateField({
      name: isPlaceholderFieldName(localField.name) ? suggestion.name : localField.name,
      source: suggestion.source,
      fallback: suggestion.fallback,
      type: nextType,
      label: localField.label || suggestion.label,
      searchable: suggestion.searchable,
      dynamic_options: suggestion.dynamic_options,
      display: suggestion.display ?? localField.display ?? 'normal',
      is_title: suggestion.is_title === true ? true : localField.is_title,
      inline_badge: suggestion.inline_badge ?? localField.inline_badge,
      format: suggestion.type === 'number'
        ? 'number'
        : suggestion.format as IndexDisplayField['format'],
      link_label: suggestion.link_label,
      link_title: suggestion.link_title,
      link_target: suggestion.link_target,
      image_fields: suggestion.image_fields,
    })
  }

  return (
    <div className="flex h-full flex-col bg-background">
      {/* Header */}
      <div className="flex items-center justify-between border-b px-4 py-3">
        <div>
          <h3 className="font-semibold">
            {localField.name || t('indexConfig:fieldEditor.newField')}
          </h3>
          <p className="text-xs text-muted-foreground">
            Champ #{fieldIndex + 1}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            size="sm"
            onClick={handleSave}
            disabled={!isDirty || !!mappingError || !!badgeColorsError}
          >
            <Save className="mr-2 h-4 w-4" />
            {t('common:actions.save')}
          </Button>
          <Button
            variant="ghost"
            size="icon"
            onClick={onClose}
            className="h-8 w-8"
          >
            <PanelRightClose className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-4">
        <Accordion type="multiple" defaultValue={['basic', 'display']} className="space-y-2">
          {/* Basic settings */}
          <AccordionItem value="basic" className="border rounded-lg">
            <AccordionTrigger className="px-4 py-3 hover:no-underline">
              <div className="flex items-center gap-2">
                <Settings2 className="h-4 w-4 text-muted-foreground" />
                <span className="font-medium">{t('indexConfig:fieldEditor.basicSettings')}</span>
              </div>
            </AccordionTrigger>
            <AccordionContent className="px-4 pb-4 space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="field-name">{t('indexConfig:fieldEditor.fieldName')}</Label>
                  <Input
                    id="field-name"
                    value={localField.name}
                    onChange={(e) => updateField({ name: e.target.value })}
                    placeholder="nom_du_champ"
                  />
                  <p className="text-xs text-muted-foreground">
                    {t('indexConfig:fieldEditor.fieldNameHint')}
                  </p>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="field-label">{t('indexConfig:fieldEditor.labelOptional')}</Label>
                  <LocalizedInput
                    value={localField.label || ''}
                    onChange={(value) => updateField({ label: value || undefined })}
                    placeholder={t('indexConfig:fieldEditor.displayedName')}
                  />
                  <p className="text-xs text-muted-foreground">
                    {t('indexConfig:fieldEditor.labelHint')}
                  </p>
                </div>
              </div>

              <div className="space-y-2">
                <Label>{t('indexConfig:fieldEditor.dataField')}</Label>
                <FieldSourcePicker
                  value={localField.source}
                  options={availableFields}
                  loading={loadingAvailableFields}
                  onLoad={onLoadAvailableFields}
                  onSelect={handleSelectSourceField}
                />
                <p className="text-xs text-muted-foreground">
                  {t('indexConfig:fieldEditor.dataFieldHint')}
                </p>
              </div>

              <div className="flex items-center justify-between rounded-lg border bg-muted/20 px-3 py-2">
                <div className="space-y-0.5">
                  <Label>{t('indexConfig:fieldEditor.useAsTitle')}</Label>
                  <p className="text-xs text-muted-foreground">
                    {t('indexConfig:fieldEditor.useAsTitleHint')}
                  </p>
                </div>
                <Switch
                  checked={localField.is_title ?? false}
                  onCheckedChange={(checked) => updateField({
                    is_title: checked,
                    searchable: checked ? true : localField.searchable,
                  })}
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>{t('indexConfig:fieldEditor.dataType')}</Label>
                  <Select
                    value={localField.type}
                    onValueChange={(value) => updateField({ type: value as IndexDisplayField['type'] })}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="text">{t('indexConfig:fieldEditor.typeText')}</SelectItem>
                      <SelectItem value="select">{t('indexConfig:fieldEditor.typeSelect')}</SelectItem>
                      <SelectItem value="boolean">{t('indexConfig:fieldEditor.typeBoolean')}</SelectItem>
                      <SelectItem value="json_array">{t('indexConfig:fieldEditor.typeJsonArray')}</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-2">
                  <Label>{t('indexConfig:fieldEditor.displayMode')}</Label>
                  <Select
                    value={localField.display}
                    onValueChange={(value) => updateField({ display: value as IndexDisplayField['display'] })}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="normal">{t('indexConfig:fieldEditor.displayNormal')}</SelectItem>
                      <SelectItem value="hidden">{t('indexConfig:fieldEditor.displayHidden')}</SelectItem>
                      <SelectItem value="image_preview">{t('indexConfig:fieldEditor.displayImagePreview')}</SelectItem>
                      <SelectItem value="link">{t('indexConfig:fieldEditor.displayLink')}</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>
            </AccordionContent>
          </AccordionItem>

          {/* Advanced source settings */}
          <AccordionItem value="source" className="border rounded-lg">
            <AccordionTrigger className="px-4 py-3 hover:no-underline">
              <div className="flex items-center gap-2">
                <Braces className="h-4 w-4 text-muted-foreground" />
                <span className="font-medium">{t('indexConfig:fieldEditor.advancedSource')}</span>
              </div>
            </AccordionTrigger>
            <AccordionContent className="px-4 pb-4 space-y-4">
              <div className="space-y-2">
                <Label htmlFor="field-source">{t('indexConfig:fieldEditor.sourceJsonPath')}</Label>
                <Input
                  id="field-source"
                  value={localField.source}
                  onChange={(e) => updateField({ source: e.target.value })}
                  placeholder="general_info.name.value"
                  className="font-mono"
                />
                <p className="text-xs text-muted-foreground">
                  {t('indexConfig:fieldEditor.sourceHint')}
                </p>
              </div>

              <div className="space-y-2">
                <Label htmlFor="field-fallback">{t('indexConfig:fieldEditor.fallbackOptional')}</Label>
                <Input
                  id="field-fallback"
                  value={localField.fallback || ''}
                  onChange={(e) => updateField({ fallback: e.target.value || undefined })}
                  placeholder="chemin.alternatif"
                  className="font-mono"
                />
                <p className="text-xs text-muted-foreground">
                  {t('indexConfig:fieldEditor.fallbackHint')}
                </p>
              </div>
            </AccordionContent>
          </AccordionItem>

          {/* Search settings */}
          <AccordionItem value="search" className="border rounded-lg">
            <AccordionTrigger className="px-4 py-3 hover:no-underline">
              <div className="flex items-center gap-2">
                <Search className="h-4 w-4 text-muted-foreground" />
                <span className="font-medium">{t('indexConfig:fieldEditor.search')}</span>
              </div>
            </AccordionTrigger>
            <AccordionContent className="px-4 pb-4 space-y-4">
              <div className="flex items-center justify-between">
                <div className="space-y-0.5">
                  <Label>{t('indexConfig:fieldEditor.searchable')}</Label>
                  <p className="text-xs text-muted-foreground">
                    {t('indexConfig:fieldEditor.searchableHint')}
                  </p>
                </div>
                <Switch
                  checked={localField.searchable}
                  onCheckedChange={(checked) => updateField({ searchable: checked })}
                />
              </div>

              <div className="flex items-center justify-between">
                <div className="space-y-0.5">
                  <Label>{t('indexConfig:fieldEditor.dynamicOptions')}</Label>
                  <p className="text-xs text-muted-foreground">
                    {t('indexConfig:fieldEditor.dynamicOptionsHint')}
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
                <span className="font-medium">{t('indexConfig:fieldEditor.appearance')}</span>
              </div>
            </AccordionTrigger>
            <AccordionContent className="px-4 pb-4 space-y-4">
              <div className="space-y-2">
                <Label>{t('indexConfig:fieldEditor.displayFormat')}</Label>
                <Select
                  value={localField.format || 'none'}
                  onValueChange={(value) => updateField({ format: value === 'none' ? undefined : value as IndexDisplayField['format'] })}
                >
                  <SelectTrigger>
                    <SelectValue placeholder={t('indexConfig:fieldEditor.formatNone')} />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="none">{t('indexConfig:fieldEditor.formatNone')}</SelectItem>
                    <SelectItem value="badge">{t('indexConfig:fieldEditor.formatBadge')}</SelectItem>
                    <SelectItem value="map">{t('indexConfig:fieldEditor.formatMapping')}</SelectItem>
                    <SelectItem value="number">{t('indexConfig:fieldEditor.formatNumber')}</SelectItem>
                    <SelectItem value="link">{t('indexConfig:fieldEditor.formatLink')}</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="flex items-center justify-between">
                <div className="space-y-0.5">
                  <Label>{t('indexConfig:fieldEditor.inlineBadge')}</Label>
                  <p className="text-xs text-muted-foreground">
                    {t('indexConfig:fieldEditor.inlineBadgeHint')}
                  </p>
                </div>
                <Switch
                  checked={localField.inline_badge}
                  onCheckedChange={(checked) => updateField({ inline_badge: checked })}
                />
              </div>

              {localField.inline_badge && (
                <div className="space-y-2">
                  <Label htmlFor="badge-color">{t('indexConfig:fieldEditor.badgeColorCss')}</Label>
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
                    <Label htmlFor="true-label">{t('indexConfig:fieldEditor.trueLabel')}</Label>
                    <LocalizedInput
                      value={localField.true_label || ''}
                      onChange={(value) => updateField({ true_label: value || undefined })}
                      placeholder="Oui"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="false-label">{t('indexConfig:fieldEditor.falseLabel')}</Label>
                    <LocalizedInput
                      value={localField.false_label || ''}
                      onChange={(value) => updateField({ false_label: value || undefined })}
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
                  <span className="font-medium">{t('indexConfig:fieldEditor.linkSettings')}</span>
                </div>
              </AccordionTrigger>
              <AccordionContent className="px-4 pb-4 space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="link-template">{t('indexConfig:fieldEditor.urlTemplate')}</Label>
                  <Input
                    id="link-template"
                    value={localField.link_template || ''}
                    onChange={(e) => updateField({ link_template: e.target.value || undefined })}
                    placeholder="https://example.com/{value}"
                    className="font-mono"
                  />
                  <p className="text-xs text-muted-foreground">
                    {t('indexConfig:fieldEditor.urlTemplateHint')}
                  </p>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="link-label">{t('indexConfig:fieldEditor.linkLabel')}</Label>
                    <LocalizedInput
                      value={localField.link_label || ''}
                      onChange={(value) => updateField({ link_label: value || undefined })}
                      placeholder={t('indexConfig:fields.linkLabelPlaceholder')}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="link-target">{t('indexConfig:fieldEditor.target')}</Label>
                    <Select
                      value={localField.link_target || '_self'}
                      onValueChange={(value) => updateField({ link_target: value })}
                    >
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="_self">{t('indexConfig:fieldEditor.sameWindow')}</SelectItem>
                        <SelectItem value="_blank">{t('indexConfig:fieldEditor.newWindow')}</SelectItem>
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
                <span className="font-medium">{t('indexConfig:fieldEditor.mappingFilters')}</span>
              </div>
            </AccordionTrigger>
            <AccordionContent className="px-4 pb-4 space-y-4">
              {/* Value Mapping */}
              <div className="space-y-2">
                <Label htmlFor="mapping">{t('indexConfig:fieldEditor.valueMapping')}</Label>
                <Textarea
                  id="mapping"
                  value={mappingText}
                  onChange={(e) => handleMappingChange(e.target.value)}
                  placeholder='{"species": "Species", "genus": "Genus"}'
                  className={`font-mono text-sm min-h-[80px] ${mappingError ? 'border-destructive' : ''}`}
                />
                {mappingError && (
                  <p className="text-xs text-destructive">{mappingError}</p>
                )}
                <p className="text-xs text-muted-foreground">
                  {t('indexConfig:fieldEditor.valueMappingHint')}
                </p>
              </div>

              {/* Filter Options (for select type) */}
              {localField.type === 'select' && !localField.dynamic_options && (
                <div className="space-y-2">
                  <Label>{t('indexConfig:fieldEditor.staticFilterOptions')}</Label>
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
                        <Label className="text-xs">{t('indexConfig:fieldEditor.value')}</Label>
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
                          placeholder="Species"
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
                    {t('indexConfig:fieldEditor.staticFilterHint')}
                  </p>
                </div>
              )}

              {/* Badge colors per value */}
              {(localField.inline_badge || localField.format === 'badge') && (
                <div className="space-y-2">
                  <Label htmlFor="badge-colors">{t('indexConfig:fieldEditor.badgeColorsJson')}</Label>
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
                    {t('indexConfig:fieldEditor.badgeColorsHint')}
                  </p>
                </div>
              )}
            </AccordionContent>
          </AccordionItem>
        </Accordion>
      </div>
    </div>
  )
}
