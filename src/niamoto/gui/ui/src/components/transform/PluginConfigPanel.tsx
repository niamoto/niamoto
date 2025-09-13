import { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { X, Plus, Trash2 } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Separator } from '@/components/ui/separator'
import type { Node } from 'reactflow'

interface FieldMapping {
  id: string
  source: string
  field: string
  target: string
  transformation?: string
  format?: string
}

interface PluginConfig {
  nodeId: string
  pluginId: string
  widgetName?: string
  params?: any
}

interface PluginConfigPanelProps {
  selectedNode: Node | null
  availableSources: string[]
  onConfigChange: (config: PluginConfig) => void
  onClose: () => void
}

export function PluginConfigPanel({
  selectedNode,
  availableSources,
  onConfigChange,
  onClose
}: PluginConfigPanelProps) {
  const { t } = useTranslation()
  const [widgetName, setWidgetName] = useState('')
  const [fieldMappings, setFieldMappings] = useState<FieldMapping[]>([])

  useEffect(() => {
    if (selectedNode?.data?.config) {
      setWidgetName(selectedNode.data.config.widgetName || '')
      setFieldMappings(selectedNode.data.config.fieldMappings || [])
    }
  }, [selectedNode])

  const pluginId = selectedNode?.data?.plugin?.id

  const addFieldMapping = () => {
    const newMapping: FieldMapping = {
      id: Date.now().toString(),
      source: availableSources[0] || '',
      field: '',
      target: '',
    }
    setFieldMappings([...fieldMappings, newMapping])
  }

  const updateFieldMapping = (id: string, updates: Partial<FieldMapping>) => {
    setFieldMappings(fieldMappings.map(mapping =>
      mapping.id === id ? { ...mapping, ...updates } : mapping
    ))
  }

  const removeFieldMapping = (id: string) => {
    setFieldMappings(fieldMappings.filter(mapping => mapping.id !== id))
  }

  const handleSave = () => {
    if (!selectedNode) return

    const config: PluginConfig = {
      nodeId: selectedNode.id,
      pluginId: pluginId || '',
      widgetName,
      params: {
        fields: fieldMappings.map(({ id, ...mapping }) => mapping)
      }
    }

    onConfigChange(config)
  }

  if (!selectedNode || selectedNode.type === 'source' || selectedNode.type === 'output') {
    return null
  }

  // Configuration UI for field_aggregator
  if (pluginId === 'field_aggregator') {
    return (
      <Card className="absolute right-4 top-20 w-[500px] z-50 shadow-xl">
        <CardHeader className="flex flex-row items-center justify-between pb-3">
          <CardTitle className="text-lg">
            {t('transform.config.title', 'Configure')} {selectedNode.data.label}
          </CardTitle>
          <Button
            variant="ghost"
            size="icon"
            className="h-8 w-8"
            onClick={onClose}
          >
            <X className="h-4 w-4" />
          </Button>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Widget Name */}
          <div className="space-y-2">
            <Label>{t('transform.config.widget_name', 'Widget Name')}</Label>
            <Input
              value={widgetName}
              onChange={(e) => setWidgetName(e.target.value)}
              placeholder="e.g., general_info"
            />
          </div>

          <Separator />

          {/* Field Mappings */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <Label>{t('transform.config.field_mappings', 'Field Mappings')}</Label>
              <Button
                size="sm"
                variant="outline"
                onClick={addFieldMapping}
              >
                <Plus className="mr-2 h-4 w-4" />
                {t('transform.config.add_field', 'Add Field')}
              </Button>
            </div>

            <ScrollArea className="h-[400px] pr-4">
              <div className="space-y-3">
                {fieldMappings.map((mapping, index) => (
                  <Card key={mapping.id} className="p-3">
                    <div className="space-y-3">
                      <div className="flex items-center justify-between">
                        <span className="text-sm font-medium">
                          {t('transform.config.field', 'Field')} {index + 1}
                        </span>
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-6 w-6"
                          onClick={() => removeFieldMapping(mapping.id)}
                        >
                          <Trash2 className="h-3 w-3" />
                        </Button>
                      </div>

                      <div className="grid grid-cols-2 gap-2">
                        {/* Source */}
                        <div className="space-y-1">
                          <Label className="text-xs">
                            {t('transform.config.source', 'Source')}
                          </Label>
                          <Select
                            value={mapping.source}
                            onValueChange={(value) => updateFieldMapping(mapping.id, { source: value })}
                          >
                            <SelectTrigger className="h-8 text-xs">
                              <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                              {availableSources.map(source => (
                                <SelectItem key={source} value={source}>
                                  {source}
                                </SelectItem>
                              ))}
                            </SelectContent>
                          </Select>
                        </div>

                        {/* Field */}
                        <div className="space-y-1">
                          <Label className="text-xs">
                            {t('transform.config.field_name', 'Field')}
                          </Label>
                          <Input
                            className="h-8 text-xs"
                            value={mapping.field}
                            onChange={(e) => updateFieldMapping(mapping.id, { field: e.target.value })}
                            placeholder="e.g., full_name"
                          />
                        </div>

                        {/* Target */}
                        <div className="space-y-1">
                          <Label className="text-xs">
                            {t('transform.config.target', 'Target')}
                          </Label>
                          <Input
                            className="h-8 text-xs"
                            value={mapping.target}
                            onChange={(e) => updateFieldMapping(mapping.id, { target: e.target.value })}
                            placeholder="e.g., name"
                          />
                        </div>

                        {/* Transformation (optional) */}
                        <div className="space-y-1">
                          <Label className="text-xs">
                            {t('transform.config.transformation', 'Transform')}
                          </Label>
                          <Select
                            value={mapping.transformation || 'none'}
                            onValueChange={(value) => updateFieldMapping(mapping.id, {
                              transformation: value === 'none' ? undefined : value
                            })}
                          >
                            <SelectTrigger className="h-8 text-xs">
                              <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                              <SelectItem value="none">None</SelectItem>
                              <SelectItem value="count">Count</SelectItem>
                              <SelectItem value="sum">Sum</SelectItem>
                              <SelectItem value="mean">Mean</SelectItem>
                              <SelectItem value="max">Max</SelectItem>
                              <SelectItem value="min">Min</SelectItem>
                            </SelectContent>
                          </Select>
                        </div>

                        {/* Format (optional) */}
                        <div className="space-y-1 col-span-2">
                          <Label className="text-xs">
                            {t('transform.config.format', 'Format')}
                          </Label>
                          <Select
                            value={mapping.format || 'none'}
                            onValueChange={(value) => updateFieldMapping(mapping.id, {
                              format: value === 'none' ? undefined : value
                            })}
                          >
                            <SelectTrigger className="h-8 text-xs">
                              <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                              <SelectItem value="none">None</SelectItem>
                              <SelectItem value="boolean">Boolean</SelectItem>
                              <SelectItem value="number">Number</SelectItem>
                              <SelectItem value="url">URL</SelectItem>
                              <SelectItem value="range">Range</SelectItem>
                            </SelectContent>
                          </Select>
                        </div>
                      </div>
                    </div>
                  </Card>
                ))}
              </div>
            </ScrollArea>
          </div>

          {/* Actions */}
          <div className="flex justify-end gap-2 pt-2">
            <Button variant="outline" onClick={onClose}>
              {t('common.cancel', 'Cancel')}
            </Button>
            <Button onClick={handleSave}>
              {t('common.save', 'Save')}
            </Button>
          </div>
        </CardContent>
      </Card>
    )
  }

  // Default configuration UI for other plugins
  return (
    <Card className="absolute right-4 top-20 w-[400px] z-50 shadow-xl">
      <CardHeader className="flex flex-row items-center justify-between pb-3">
        <CardTitle className="text-lg">
          {t('transform.config.title', 'Configure')} {selectedNode.data.label}
        </CardTitle>
        <Button
          variant="ghost"
          size="icon"
          className="h-8 w-8"
          onClick={onClose}
        >
          <X className="h-4 w-4" />
        </Button>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          <div className="space-y-2">
            <Label>{t('transform.config.widget_name', 'Widget Name')}</Label>
            <Input
              value={widgetName}
              onChange={(e) => setWidgetName(e.target.value)}
              placeholder="e.g., distribution_map"
            />
          </div>

          <div className="text-sm text-muted-foreground">
            {t('transform.config.plugin_specific', 'Plugin-specific configuration coming soon...')}
          </div>

          <div className="flex justify-end gap-2">
            <Button variant="outline" onClick={onClose}>
              {t('common.cancel', 'Cancel')}
            </Button>
            <Button onClick={handleSave}>
              {t('common.save', 'Save')}
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
