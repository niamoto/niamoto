import React, { useCallback, useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import ReactFlow, {
  type Node,
  type Edge,
  addEdge,
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  type Connection,
  Handle,
  Position,
  type NodeProps,
  ReactFlowProvider,
  type ReactFlowInstance,
} from 'reactflow'
import 'reactflow/dist/style.css'
import { Card } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Play, Save, RotateCcw, Settings } from 'lucide-react'
import { cn } from '@/lib/utils'
import type { Plugin } from './PluginCatalog'
import type { Source } from './GroupManager'
import { Database, BarChart, Map, Table as TableIcon, Calculator, TreePine, Layers, Filter } from 'lucide-react'
import { PluginConfigPanel } from './PluginConfigPanel'

type PipelineNodeData = {
  plugin?: Plugin
  source?: Source
  label: string
  type: 'source' | 'plugin' | 'output'
  inputs?: string[]
  outputs?: string[]
  config?: any
}

type PipelineNode = Node<PipelineNodeData>

// Map plugin IDs to their icons
const pluginIcons: Record<string, React.ComponentType<{ className?: string }>> = {
  nested_set: TreePine,
  stats_loader: BarChart,
  direct_attribute: Database,
  field_aggregator: Layers,
  sum_aggregator: Calculator,
  count_aggregator: TableIcon,
  top_ranking: BarChart,
  geo_extractor: Map,
  filter_plugin: Filter,
}

// Custom Node Component
function PluginNode({ data, selected }: NodeProps) {
  const plugin = data.plugin as Plugin | undefined
  const Icon = plugin ? pluginIcons[plugin.id] : undefined
  const isConfigured = !!data.config?.widgetName

  return (
    <Card className={cn(
      'min-w-[200px] transition-all',
      selected && 'ring-2 ring-primary shadow-lg',
      isConfigured && 'border-green-500 bg-green-50/50 dark:bg-green-950/20'
    )}>
      <div className="p-3">
        <div className="flex items-center gap-2 mb-2">
          {Icon && (
            <div className="rounded bg-primary/10 p-1">
              <Icon className="h-4 w-4 text-primary" />
            </div>
          )}
          <div className="flex-1">
            <div className="flex items-center gap-2">
              <div className="font-medium text-sm">{data.label}</div>
              {isConfigured && (
                <Settings className="h-3 w-3 text-green-500" />
              )}
            </div>
            {plugin && (
              <Badge variant="outline" className="text-xs mt-0.5">
                {plugin.type}
              </Badge>
            )}
            {isConfigured && data.config.widgetName ? (
              <div className="mt-2 rounded bg-green-100 dark:bg-green-900/30 px-2 py-1">
                <div className="text-xs font-medium text-green-700 dark:text-green-300">
                  📊 Widget Output
                </div>
                <div className="text-sm font-semibold text-green-800 dark:text-green-200">
                  {data.config.widgetName}
                </div>
              </div>
            ) : (
              <div className="mt-2 rounded bg-muted px-2 py-1">
                <div className="text-xs text-muted-foreground">
                  ⚙️ Configure to create widget
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Input handles */}
        {data.inputs && data.inputs.length > 0 && (
          <div className="absolute -left-2 top-1/2 -translate-y-1/2">
            {data.inputs.map((_input: string, index: number) => (
              <Handle
                key={`input-${index}`}
                type="target"
                position={Position.Left}
                id={`input-${index}`}
                style={{
                  top: `${(index + 1) * (100 / (data.inputs!.length + 1))}%`,
                  transform: 'translateY(-50%)',
                }}
                className="!w-3 !h-3 !bg-primary !border-2 !border-background"
              />
            ))}
          </div>
        )}

        {/* Output handles */}
        {data.outputs && data.outputs.length > 0 && (
          <div className="absolute -right-2 top-1/2 -translate-y-1/2">
            {data.outputs.map((_output: string, index: number) => (
              <Handle
                key={`output-${index}`}
                type="source"
                position={Position.Right}
                id={`output-${index}`}
                style={{
                  top: `${(index + 1) * (100 / (data.outputs!.length + 1))}%`,
                  transform: 'translateY(-50%)',
                }}
                className="!w-3 !h-3 !bg-primary !border-2 !border-background"
              />
            ))}
          </div>
        )}
      </div>
    </Card>
  )
}

// Source Node Component
function SourceNode({ data, selected }: NodeProps) {
  return (
    <Card className={cn(
      'min-w-[150px] bg-blue-50 dark:bg-blue-950/20 border-blue-200',
      selected && 'ring-2 ring-blue-500 shadow-lg'
    )}>
      <div className="p-3">
        <div className="font-medium text-sm text-blue-700 dark:text-blue-300">
          {data.label}
        </div>
        <Badge variant="secondary" className="text-xs mt-1">
          Source
        </Badge>

        {/* Output handle */}
        <Handle
          type="source"
          position={Position.Right}
          className="!w-3 !h-3 !bg-blue-500 !border-2 !border-background"
        />
      </div>
    </Card>
  )
}


const nodeTypes = {
  plugin: PluginNode,
  source: SourceNode,
}

interface PipelineCanvasProps {
  sources: Source[]
  groupBy: string
  onPipelineChange?: (nodes: Node[], edges: Edge[]) => void
}

function PipelineCanvasContent({ sources, groupBy, onPipelineChange }: PipelineCanvasProps) {
  const { t } = useTranslation()
  const [reactFlowInstance, setReactFlowInstance] = useState<ReactFlowInstance | null>(null)
  const [nodes, setNodes, onNodesChange] = useNodesState<PipelineNodeData>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const [selectedNode, setSelectedNode] = useState<Node | null>(null)
  const [showConfigPanel, setShowConfigPanel] = useState(false)

  // Initialize source nodes only (no default output node)
  useEffect(() => {
    const sourceNodes: PipelineNode[] = sources.map((source, index) => ({
      id: `source-${source.id}`,
      type: 'source',
      position: { x: 50, y: 100 + index * 120 },
      data: {
        source,
        label: source.name,
        type: 'source' as const,
        outputs: ['data'],
      },
    }))

    setNodes(sourceNodes)
  }, [sources, setNodes])

  const onConnect = useCallback(
    (params: Edge | Connection) => {
      setEdges((eds) => addEdge({ ...params, animated: true }, eds))
    },
    [setEdges]
  )

  const onDragOver = useCallback((event: React.DragEvent) => {
    event.preventDefault()
    event.dataTransfer.dropEffect = 'copy'
  }, [])

  const onDrop = useCallback(
    (event: React.DragEvent) => {
      event.preventDefault()

      if (!reactFlowInstance) {
        return
      }

      // Try both formats
      let pluginData = event.dataTransfer.getData('application/json')
      if (!pluginData) {
        pluginData = event.dataTransfer.getData('text/plain')
      }

      if (!pluginData) {
        return
      }

      const pluginBase = JSON.parse(pluginData)
      // Re-add the icon based on category
      const categoryIcons: Record<string, any> = {
        file: Filter,
        geo: Map,
        aggregation: Layers,
        statistics: Calculator,
        hierarchy: TreePine,
        data: Database,
        visualization: BarChart,
      }

      const plugin: Plugin = {
        ...pluginBase,
        icon: categoryIcons[pluginBase.category] || Database
      }

      // Use screenToFlowPosition instead of deprecated project
      const position = reactFlowInstance.screenToFlowPosition({
        x: event.clientX,
        y: event.clientY,
      })

      const newNode: PipelineNode = {
        id: `${plugin.id}-${Date.now()}`,
        type: 'plugin',
        position,
        data: {
          plugin,
          label: plugin.name,
          type: 'plugin' as const,
          inputs: plugin.inputs || [],
          outputs: plugin.outputs || [],
        },
      }

      setNodes((nds) => nds.concat(newNode))
    },
    [reactFlowInstance, setNodes]
  )

  const onNodesDelete = useCallback(
    (deleted: Node[]) => {
      // Don't allow deletion of source nodes
      const filteredDeleted = deleted.filter(
        (node) => node.type === 'plugin'
      )
      if (filteredDeleted.length > 0) {
        setNodes((nds) =>
          nds.filter((node) => !filteredDeleted.find((d) => d.id === node.id))
        )
      }
    },
    [setNodes]
  )

  const clearPipeline = () => {
    setNodes((nds) => nds.filter((node) => node.type !== 'plugin'))
    setEdges([])
  }

  const runPipeline = () => {
    // Collect all configured plugins as widgets
    const widgets = nodes
      .filter(node => node.type === 'plugin' && node.data.config?.widgetName)
      .map(node => ({
        name: node.data.config.widgetName,
        plugin: node.data.plugin?.id,
        params: node.data.config || {}
      }))

    console.log('Running pipeline with widgets:', widgets)
    // TODO: Implement pipeline execution with widgets
  }

  const savePipeline = () => {
    // Collect all configured plugins as widgets for saving
    const widgets = nodes
      .filter(node => node.type === 'plugin' && node.data.config?.widgetName)
      .map(node => ({
        name: node.data.config.widgetName,
        plugin: node.data.plugin?.id,
        params: node.data.config || {}
      }))

    onPipelineChange?.(nodes, edges)
    console.log('Saving pipeline with widgets:', widgets)
  }

  const onNodeDoubleClick = useCallback((_event: React.MouseEvent, node: Node) => {
    if (node.type === 'plugin') {
      setSelectedNode(node)
      setShowConfigPanel(true)
    }
  }, [])

  const handleConfigChange = useCallback((config: any) => {
    setNodes((nds) =>
      nds.map((node) => {
        if (node.id === config.nodeId) {
          return {
            ...node,
            data: {
              ...node.data,
              config: {
                widgetName: config.widgetName,
                ...config.params
              }
            }
          }
        }
        return node
      })
    )
    setShowConfigPanel(false)
  }, [setNodes])

  const getAvailableSources = useCallback(() => {
    // Get all source nodes
    const sourceNodes = nodes.filter(n => n.type === 'source')
    // Get connected sources for the selected node
    const connectedSources: string[] = []

    if (selectedNode) {
      // Find edges that connect to the selected node
      edges.forEach(edge => {
        if (edge.target === selectedNode.id) {
          const sourceNode = nodes.find(n => n.id === edge.source)
          if (sourceNode?.type === 'source') {
            connectedSources.push(sourceNode.data.source?.name || sourceNode.data.label)
          }
        }
      })
    }

    return connectedSources.length > 0 ? connectedSources : sourceNodes.map(n => n.data.source?.name || n.data.label)
  }, [nodes, edges, selectedNode])


  return (
    <div className="h-[600px] relative">
      {/* Toolbar */}
      <div className="absolute top-4 right-4 z-10 flex gap-2">
        <Button
          size="sm"
          variant="outline"
          onClick={clearPipeline}
        >
          <RotateCcw className="mr-2 h-4 w-4" />
          {t('transform.pipeline.clear', 'Clear')}
        </Button>
        <Button
          size="sm"
          variant="outline"
          onClick={savePipeline}
        >
          <Save className="mr-2 h-4 w-4" />
          {t('transform.pipeline.save', 'Save')}
        </Button>
        <Button
          size="sm"
          onClick={runPipeline}
        >
          <Play className="mr-2 h-4 w-4" />
          {t('transform.pipeline.run', 'Run')}
        </Button>
      </div>

      {/* Configuration Panel */}
      {showConfigPanel && (
        <PluginConfigPanel
          selectedNode={selectedNode}
          availableSources={getAvailableSources()}
          groupBy={groupBy}
          onConfigChange={handleConfigChange}
          onClose={() => setShowConfigPanel(false)}
        />
      )}

      <div
        className="h-full"
        onDrop={onDrop}
        onDragOver={onDragOver}
      >
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onConnect={onConnect}
          onInit={setReactFlowInstance}
          onNodesDelete={onNodesDelete}
          onNodeDoubleClick={onNodeDoubleClick}
          nodeTypes={nodeTypes}
          fitView
          deleteKeyCode="Delete"
        >
          <Background color="#aaa" gap={16} />
          <Controls />
          <MiniMap
            nodeStrokeColor={(node) => {
              if (node.type === 'source') return '#3b82f6'
              if (node.type === 'plugin' && node.data.config?.widgetName) return '#10b981'
              return '#6b7280'
            }}
            nodeColor={(node) => {
              if (node.type === 'source') return '#dbeafe'
              if (node.type === 'plugin' && node.data.config?.widgetName) return '#d1fae5'
              return '#f3f4f6'
            }}
          />
        </ReactFlow>
      </div>
    </div>
  )
}

// Export wrapper component with provider
export function PipelineCanvas(props: PipelineCanvasProps) {
  return (
    <ReactFlowProvider>
      <PipelineCanvasContent {...props} />
    </ReactFlowProvider>
  )
}
