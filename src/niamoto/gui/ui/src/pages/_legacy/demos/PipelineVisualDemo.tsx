import { useState, useCallback, useMemo } from 'react'
import ReactFlow, {
  Controls,
  Background,
  MiniMap,
  useNodesState,
  useEdgesState,
  addEdge,
  MarkerType,
  Handle,
  Position,
  type Node,
  type Edge,
  type Connection,
  type NodeTypes,
  type BackgroundVariant,
} from 'reactflow'
import 'reactflow/dist/style.css'
import { DemoWrapper } from '@/components/demos/DemoWrapper'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import {
  Database,
  Settings2,
  Package,
  FileOutput,
  Save,
  Download,
  Upload,
  Code,
  Layers
} from 'lucide-react'
import * as yaml from 'js-yaml'

// Custom Node Components
function ImportNode({ data }: { data: any }) {
  return (
    <div className="bg-blue-50 border-2 border-blue-200 rounded-lg p-4 min-w-[200px]">
      <div className="flex items-center gap-2 mb-2">
        <Database className="h-4 w-4 text-blue-600" />
        <span className="font-medium text-sm">{data.label}</span>
      </div>
      <div className="text-xs text-gray-600">
        {data.type === 'csv' && <Badge variant="outline" className="text-xs">CSV</Badge>}
        {data.type === 'shapefile' && <Badge variant="outline" className="text-xs">Shapefile</Badge>}
        {data.type === 'raster' && <Badge variant="outline" className="text-xs">Raster</Badge>}
      </div>
      <div className="text-xs text-gray-500 mt-1">{data.path}</div>
      <Handle type="source" position={Position.Right} className="!bg-blue-600" />
    </div>
  )
}

function TransformNode({ data }: { data: any }) {
  return (
    <div className="bg-green-50 border-2 border-green-200 rounded-lg p-4 min-w-[220px]">
      <Handle type="target" position={Position.Left} className="!bg-green-600" />
      <div className="flex items-center gap-2 mb-2">
        <Settings2 className="h-4 w-4 text-green-600" />
        <span className="font-medium text-sm">{data.label}</span>
      </div>
      <div className="space-y-1">
        <Badge variant="secondary" className="text-xs">{data.plugin}</Badge>
        {data.widgets && (
          <div className="text-xs text-gray-600">
            {data.widgets.length} widget{data.widgets.length > 1 ? 's' : ''}
          </div>
        )}
      </div>
      <Handle type="source" position={Position.Right} className="!bg-green-600" />
    </div>
  )
}

function WidgetNode({ data }: { data: any }) {
  return (
    <div className="bg-purple-50 border-2 border-purple-200 rounded-lg p-4 min-w-[180px]">
      <Handle type="target" position={Position.Left} className="!bg-purple-600" />
      <div className="flex items-center gap-2 mb-2">
        <Package className="h-4 w-4 text-purple-600" />
        <span className="font-medium text-sm">{data.label}</span>
      </div>
      <Badge variant="outline" className="text-xs">{data.plugin}</Badge>
      <div className="text-xs text-gray-500 mt-1">{data.title}</div>
    </div>
  )
}

function ExportNode({ data }: { data: any }) {
  return (
    <div className="bg-orange-50 border-2 border-orange-200 rounded-lg p-4 min-w-[200px]">
      <Handle type="target" position={Position.Left} className="!bg-orange-600" />
      <div className="flex items-center gap-2 mb-2">
        <FileOutput className="h-4 w-4 text-orange-600" />
        <span className="font-medium text-sm">{data.label}</span>
      </div>
      <div className="text-xs text-gray-600">
        {data.type === 'html' && <Badge variant="outline" className="text-xs">HTML</Badge>}
        {data.type === 'api' && <Badge variant="outline" className="text-xs">API</Badge>}
      </div>
      <div className="text-xs text-gray-500 mt-1">{data.output}</div>
    </div>
  )
}

const nodeTypes: NodeTypes = {
  import: ImportNode,
  transform: TransformNode,
  widget: WidgetNode,
  export: ExportNode,
}

// Sample initial nodes and edges based on the config files
const initialNodes: Node[] = [
  // Import nodes
  {
    id: 'import-taxonomy',
    type: 'import',
    position: { x: 50, y: 100 },
    data: { label: 'Taxonomy', type: 'csv', path: 'imports/occurrences.csv' },
  },
  {
    id: 'import-occurrences',
    type: 'import',
    position: { x: 50, y: 200 },
    data: { label: 'Occurrences', type: 'csv', path: 'imports/occurrences.csv' },
  },
  {
    id: 'import-plots',
    type: 'import',
    position: { x: 50, y: 300 },
    data: { label: 'Plots', type: 'csv', path: 'imports/plots.csv' },
  },
  {
    id: 'import-shapes',
    type: 'import',
    position: { x: 50, y: 400 },
    data: { label: 'Shapes', type: 'shapefile', path: 'imports/shapes/*.gpkg' },
  },

  // Transform nodes
  {
    id: 'transform-taxon',
    type: 'transform',
    position: { x: 350, y: 150 },
    data: {
      label: 'Taxon Transform',
      plugin: 'nested_set',
      widgets: ['general_info', 'distribution_map', 'top_species']
    },
  },
  {
    id: 'transform-plot',
    type: 'transform',
    position: { x: 350, y: 350 },
    data: {
      label: 'Plot Transform',
      plugin: 'stats_loader',
      widgets: ['general_info', 'map_panel']
    },
  },

  // Widget nodes
  {
    id: 'widget-map',
    type: 'widget',
    position: { x: 650, y: 100 },
    data: {
      label: 'Map Widget',
      plugin: 'interactive_map',
      title: 'Distribution géographique'
    },
  },
  {
    id: 'widget-info',
    type: 'widget',
    position: { x: 650, y: 200 },
    data: {
      label: 'Info Grid',
      plugin: 'info_grid',
      title: 'Informations générales'
    },
  },
  {
    id: 'widget-chart',
    type: 'widget',
    position: { x: 650, y: 300 },
    data: {
      label: 'Bar Chart',
      plugin: 'bar_plot',
      title: 'Distribution DBH'
    },
  },

  // Export nodes
  {
    id: 'export-web',
    type: 'export',
    position: { x: 900, y: 150 },
    data: {
      label: 'Web Export',
      type: 'html',
      output: 'exports/web'
    },
  },
  {
    id: 'export-api',
    type: 'export',
    position: { x: 900, y: 250 },
    data: {
      label: 'API Export',
      type: 'api',
      output: 'exports/api'
    },
  },
]

const initialEdges: Edge[] = [
  {
    id: 'e1',
    source: 'import-taxonomy',
    target: 'transform-taxon',
    animated: true,
    style: { stroke: '#3b82f6' },
    markerEnd: { type: MarkerType.ArrowClosed, color: '#3b82f6' },
  },
  {
    id: 'e2',
    source: 'import-occurrences',
    target: 'transform-taxon',
    animated: true,
    style: { stroke: '#3b82f6' },
    markerEnd: { type: MarkerType.ArrowClosed, color: '#3b82f6' },
  },
  {
    id: 'e3',
    source: 'import-plots',
    target: 'transform-plot',
    animated: true,
    style: { stroke: '#3b82f6' },
    markerEnd: { type: MarkerType.ArrowClosed, color: '#3b82f6' },
  },
  {
    id: 'e4',
    source: 'transform-taxon',
    target: 'widget-map',
    style: { stroke: '#10b981' },
    markerEnd: { type: MarkerType.ArrowClosed, color: '#10b981' },
  },
  {
    id: 'e5',
    source: 'transform-taxon',
    target: 'widget-info',
    style: { stroke: '#10b981' },
    markerEnd: { type: MarkerType.ArrowClosed, color: '#10b981' },
  },
  {
    id: 'e6',
    source: 'transform-plot',
    target: 'widget-chart',
    style: { stroke: '#10b981' },
    markerEnd: { type: MarkerType.ArrowClosed, color: '#10b981' },
  },
  {
    id: 'e7',
    source: 'widget-map',
    target: 'export-web',
    style: { stroke: '#8b5cf6' },
    markerEnd: { type: MarkerType.ArrowClosed, color: '#8b5cf6' },
  },
  {
    id: 'e8',
    source: 'widget-info',
    target: 'export-web',
    style: { stroke: '#8b5cf6' },
    markerEnd: { type: MarkerType.ArrowClosed, color: '#8b5cf6' },
  },
  {
    id: 'e9',
    source: 'widget-chart',
    target: 'export-api',
    style: { stroke: '#8b5cf6' },
    markerEnd: { type: MarkerType.ArrowClosed, color: '#8b5cf6' },
  },
]

export function PipelineVisualDemo() {
  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes)
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges)
  const [viewMode, setViewMode] = useState<'visual' | 'yaml'>('visual')

  const onConnect = useCallback(
    (params: Connection) => {
      const newEdge = {
        ...params,
        animated: true,
        style: { stroke: '#64748b' },
        markerEnd: { type: MarkerType.ArrowClosed, color: '#64748b' },
      }
      setEdges((eds) => addEdge(newEdge, eds))
    },
    [setEdges]
  )

  const addNode = (type: 'import' | 'transform' | 'widget' | 'export') => {
    const newNode: Node = {
      id: `${type}-${Date.now()}`,
      type,
      position: { x: Math.random() * 400 + 200, y: Math.random() * 400 + 100 },
      data: {
        label: `New ${type}`,
        ...(type === 'import' && { type: 'csv', path: 'path/to/file' }),
        ...(type === 'transform' && { plugin: 'field_aggregator', widgets: [] }),
        ...(type === 'widget' && { plugin: 'info_grid', title: 'New Widget' }),
        ...(type === 'export' && { type: 'html', output: 'exports/output' }),
      },
    }
    setNodes((nds) => [...nds, newNode])
  }

  const yamlConfig = useMemo(() => {
    try {
      // Generate YAML from nodes and edges
      const imports: any = {}
      const transforms: any[] = []
      const exports: any[] = []

      nodes.forEach((node) => {
        if (node.type === 'import') {
          imports[node.data.label.toLowerCase()] = {
            type: node.data.type,
            path: node.data.path,
          }
        } else if (node.type === 'transform') {
          transforms.push({
            group_by: node.data.label.toLowerCase().replace(' transform', ''),
            plugin: node.data.plugin,
            widgets_data: node.data.widgets,
          })
        } else if (node.type === 'export') {
          exports.push({
            name: node.data.label.toLowerCase().replace(' export', ''),
            type: node.data.type,
            output: node.data.output,
          })
        }
      })

      return {
        import: yaml.dump(imports, { indent: 2 }),
        transform: yaml.dump(transforms, { indent: 2 }),
        export: yaml.dump({ exports }, { indent: 2 }),
      }
    } catch (e) {
      return {
        import: '# Error generating YAML',
        transform: '# Error generating YAML',
        export: '# Error generating YAML',
      }
    }
  }, [nodes])

  return (
    <DemoWrapper currentDemo="pipeline-visual">
      <div className="h-[calc(100vh-250px)]">
        <Card className="h-full">
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle>Pipeline Visual Editor</CardTitle>
                <CardDescription>
                  Glissez-déposez pour créer des connexions entre les nœuds du pipeline
                </CardDescription>
              </div>
              <div className="flex gap-2">
                <Button
                  variant={viewMode === 'visual' ? 'default' : 'outline'}
                  size="sm"
                  onClick={() => setViewMode('visual')}
                >
                  <Layers className="h-4 w-4 mr-1" />
                  Visuel
                </Button>
                <Button
                  variant={viewMode === 'yaml' ? 'default' : 'outline'}
                  size="sm"
                  onClick={() => setViewMode('yaml')}
                >
                  <Code className="h-4 w-4 mr-1" />
                  YAML
                </Button>
              </div>
            </div>
          </CardHeader>
          <CardContent className="p-0 h-[calc(100%-80px)]">
            {viewMode === 'visual' ? (
              <div className="relative h-full">
                <div className="absolute top-4 left-4 z-10 flex gap-2">
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => addNode('import')}
                  >
                    <Database className="h-4 w-4 mr-1" />
                    Import
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => addNode('transform')}
                  >
                    <Settings2 className="h-4 w-4 mr-1" />
                    Transform
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => addNode('widget')}
                  >
                    <Package className="h-4 w-4 mr-1" />
                    Widget
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => addNode('export')}
                  >
                    <FileOutput className="h-4 w-4 mr-1" />
                    Export
                  </Button>
                </div>

                <div className="absolute top-4 right-4 z-10 flex gap-2">
                  <Button size="sm" variant="outline">
                    <Save className="h-4 w-4 mr-1" />
                    Sauvegarder
                  </Button>
                  <Button size="sm" variant="outline">
                    <Download className="h-4 w-4 mr-1" />
                    Exporter
                  </Button>
                  <Button size="sm" variant="outline">
                    <Upload className="h-4 w-4 mr-1" />
                    Importer
                  </Button>
                </div>

                <ReactFlow
                  nodes={nodes}
                  edges={edges}
                  onNodesChange={onNodesChange}
                  onEdgesChange={onEdgesChange}
                  onConnect={onConnect}
                  nodeTypes={nodeTypes}
                  fitView
                >
                  <Controls />
                  <MiniMap
                    nodeColor={(node) => {
                      switch (node.type) {
                        case 'import': return '#3b82f6'
                        case 'transform': return '#10b981'
                        case 'widget': return '#8b5cf6'
                        case 'export': return '#f97316'
                        default: return '#64748b'
                      }
                    }}
                  />
                  <Background variant={"dots" as BackgroundVariant} gap={12} size={1} />
                </ReactFlow>
              </div>
            ) : (
              <div className="h-full p-4">
                <Tabs defaultValue="import" className="h-full">
                  <TabsList>
                    <TabsTrigger value="import">import.yml</TabsTrigger>
                    <TabsTrigger value="transform">transform.yml</TabsTrigger>
                    <TabsTrigger value="export">export.yml</TabsTrigger>
                  </TabsList>
                  <TabsContent value="import" className="h-[calc(100%-50px)]">
                    <ScrollArea className="h-full rounded-md border p-4">
                      <pre className="text-sm font-mono">
                        <code>{yamlConfig.import}</code>
                      </pre>
                    </ScrollArea>
                  </TabsContent>
                  <TabsContent value="transform" className="h-[calc(100%-50px)]">
                    <ScrollArea className="h-full rounded-md border p-4">
                      <pre className="text-sm font-mono">
                        <code>{yamlConfig.transform}</code>
                      </pre>
                    </ScrollArea>
                  </TabsContent>
                  <TabsContent value="export" className="h-[calc(100%-50px)]">
                    <ScrollArea className="h-full rounded-md border p-4">
                      <pre className="text-sm font-mono">
                        <code>{yamlConfig.export}</code>
                      </pre>
                    </ScrollArea>
                  </TabsContent>
                </Tabs>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </DemoWrapper>
  )
}
