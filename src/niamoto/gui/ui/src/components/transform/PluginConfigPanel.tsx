import { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { X } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Separator } from '@/components/ui/separator'
import JsonSchemaForm from '@/components/forms/JsonSchemaForm'
import type { Node } from 'reactflow'

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
  const [pluginParams, setPluginParams] = useState<any>({})
  const isFormValid = true; // Form validation handled by JsonSchemaForm

  useEffect(() => {
    if (selectedNode?.data?.config) {
      setWidgetName(selectedNode.data.config.widgetName || '')
      setPluginParams(selectedNode.data.config.params || {})
    }
  }, [selectedNode])

  const pluginId = selectedNode?.data?.plugin?.id

  const handleParamsChange = (params: any) => {
    setPluginParams(params)
  }

  const handleSave = () => {
    if (!selectedNode) return

    const config: PluginConfig = {
      nodeId: selectedNode.id,
      pluginId: pluginId || '',
      widgetName,
      params: pluginParams
    }

    onConfigChange(config)
  }

  if (!selectedNode || selectedNode.type === 'source' || selectedNode.type === 'output') {
    return null
  }

  // Unified configuration UI using JsonSchemaForm
  return (
    <Card className="absolute right-4 top-20 w-[600px] z-50 shadow-xl">
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
        <ScrollArea className="h-[500px] pr-4">
          <div className="space-y-4">
            {/* Widget Name */}
            <div className="space-y-2">
              <Label>{t('transform.config.widget_name', 'Widget Name')}</Label>
              <Input
                value={widgetName}
                onChange={(e) => setWidgetName(e.target.value)}
                placeholder={t('transform.config.widget_placeholder', 'Enter a unique widget identifier')}
              />
            </div>

            <Separator />

            {/* Plugin Configuration using JsonSchemaForm */}
            {pluginId && (
              <div className="space-y-2">
                <Label>{t('transform.config.parameters', 'Plugin Parameters')}</Label>
                <JsonSchemaForm
                  pluginId={pluginId}
                  pluginType="transformer"
                  onChange={handleParamsChange}
                  showTitle={false}
                  className="border-0 shadow-none p-0"
                  availableFields={availableSources}
                />
              </div>
            )}

            {/* Actions */}
            <div className="flex justify-end gap-2 pt-4 border-t">
              <Button variant="outline" onClick={onClose}>
                {t('common.cancel', 'Cancel')}
              </Button>
              <Button onClick={handleSave} disabled={!isFormValid || !widgetName}>
                {t('common.save', 'Save Configuration')}
              </Button>
            </div>
          </div>
        </ScrollArea>
      </CardContent>
    </Card>
  )
}
