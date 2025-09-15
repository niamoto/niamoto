import React from 'react'
import { useTranslation } from 'react-i18next'
import { X, Settings, ChevronLeft, ChevronRight } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Separator } from '@/components/ui/separator'
import { cn } from '@/lib/utils'
import { usePipelineStore } from '../store'
import {
  TaxonomyForm,
  OccurrencesForm,
  PlotForm,
  ShapeForm,
  LayerForm
} from '../forms/import'

export function ConfigPanel() {
  const { t } = useTranslation()
  const { selectedNode, setSelectedNode, updateNode } = usePipelineStore()
  const [collapsed, setCollapsed] = React.useState(false)
  const [nodeConfig, setNodeConfig] = React.useState<any>({})

  React.useEffect(() => {
    if (selectedNode?.data.config) {
      setNodeConfig(selectedNode.data.config)
    } else {
      setNodeConfig({})
    }
  }, [selectedNode])

  const handleConfigChange = (config: any) => {
    setNodeConfig(config)
    if (selectedNode) {
      updateNode(selectedNode.id, {
        ...selectedNode.data,
        config,
        status: config && Object.keys(config).length > 0 ? 'configured' : 'idle'
      })
    }
  }

  if (!selectedNode && !collapsed) return null

  return (
    <div
      className={cn(
        'border-l bg-background transition-all duration-300',
        collapsed ? 'w-12' : 'w-96'
      )}
    >
      {collapsed ? (
        <Button
          variant="ghost"
          size="icon"
          className="h-12 w-12"
          onClick={() => setCollapsed(false)}
        >
          <ChevronLeft className="h-4 w-4" />
        </Button>
      ) : (
        <>
          <div className="flex items-center justify-between p-4 border-b">
            <div className="flex items-center gap-2">
              <Settings className="h-4 w-4" />
              <h3 className="font-semibold">
                {selectedNode
                  ? t('pipeline.config.title', 'Node Configuration')
                  : t('pipeline.config.empty', 'Select a node')}
              </h3>
            </div>
            <div className="flex items-center gap-1">
              {selectedNode && (
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() => setSelectedNode(null)}
                >
                  <X className="h-4 w-4" />
                </Button>
              )}
              <Button
                variant="ghost"
                size="icon"
                onClick={() => setCollapsed(true)}
              >
                <ChevronRight className="h-4 w-4" />
              </Button>
            </div>
          </div>

          {selectedNode && (
            <ScrollArea className="flex-1 p-4">
              <div className="space-y-4">
                {/* Node Info */}
                <div>
                  <h4 className="text-sm font-medium mb-2">
                    {t('pipeline.config.nodeInfo', 'Node Information')}
                  </h4>
                  <div className="space-y-2 text-sm">
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">ID:</span>
                      <span className="font-mono">{selectedNode.id}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Type:</span>
                      <span>{selectedNode.data.nodeType}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Label:</span>
                      <span>{selectedNode.data.label}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Status:</span>
                      <span>{selectedNode.data.status}</span>
                    </div>
                  </div>
                </div>

                <Separator />

                {/* Configuration Form */}
                <div>
                  <h4 className="text-sm font-medium mb-2">
                    {t('pipeline.config.configuration', 'Configuration')}
                  </h4>

                  {/* Render appropriate form based on node type */}
                  {selectedNode.data.nodeType === 'import' && (
                    <>
                      {(selectedNode.data as any).subType === 'taxonomy' && (
                        <TaxonomyForm
                          config={nodeConfig}
                          onConfigChange={handleConfigChange}
                        />
                      )}
                      {(selectedNode.data as any).subType === 'occurrences' && (
                        <OccurrencesForm
                          config={nodeConfig}
                          onConfigChange={handleConfigChange}
                        />
                      )}
                      {(selectedNode.data as any).subType === 'plots' && (
                        <PlotForm
                          config={nodeConfig}
                          onConfigChange={handleConfigChange}
                        />
                      )}
                      {(selectedNode.data as any).subType === 'shapes' && (
                        <ShapeForm
                          config={nodeConfig}
                          onConfigChange={handleConfigChange}
                        />
                      )}
                      {(selectedNode.data as any).subType === 'layers' && (
                        <LayerForm
                          config={nodeConfig}
                          onConfigChange={handleConfigChange}
                        />
                      )}
                    </>
                  )}

                  {selectedNode.data.nodeType === 'transform' && (
                    <div className="space-y-2">
                      <p className="text-sm text-muted-foreground">
                        Transform plugin: {(selectedNode.data as any).pluginId}
                      </p>
                      <p className="text-xs text-muted-foreground">
                        {t('pipeline.config.transformPlaceholder', 'Transform configuration forms will be implemented in Phase 3')}
                      </p>
                    </div>
                  )}

                  {selectedNode.data.nodeType === 'export' && (
                    <div className="space-y-2">
                      <p className="text-sm text-muted-foreground">
                        Export format: {(selectedNode.data as any).format}
                      </p>
                      <p className="text-xs text-muted-foreground">
                        {t('pipeline.config.exportPlaceholder', 'Export configuration forms will be implemented in Phase 4')}
                      </p>
                    </div>
                  )}
                </div>
              </div>
            </ScrollArea>
          )}

          {!selectedNode && (
            <div className="flex items-center justify-center h-full text-muted-foreground">
              <p className="text-sm">
                {t('pipeline.config.selectNode', 'Select a node to configure')}
              </p>
            </div>
          )}
        </>
      )}
    </div>
  )
}
