import React, { useCallback, useState } from 'react'
import ReactFlow, {
  Background,
  Controls,
  MiniMap,
  ReactFlowProvider,
  ConnectionMode,
  Panel,
} from 'reactflow'
import type { ReactFlowInstance } from 'reactflow'
import 'reactflow/dist/style.css'

import { usePipelineStore } from './store'
import { ImportNode } from './nodes/import/ImportNode'
import { TransformNode } from './nodes/transform/TransformNode'
import { ExportNode } from './nodes/export/ExportNode'
import { NodeCatalog } from './sidebar/NodeCatalog'
import { ConfigPanel } from './layouts/ConfigPanel'
import { PipelineToolbar } from './layouts/PipelineToolbar'

import type { CatalogItem, PipelineNode, PipelineNodeData } from './types'

function buildNodeData(item: CatalogItem): PipelineNodeData {
  switch (item.type) {
    case 'import': {
      if (!item.subType) {
        throw new Error('Import catalog items must define a subType')
      }

      return {
        nodeType: 'import',
        subType: item.subType,
        status: 'idle',
        label: item.label,
        ...(item.defaultConfig ? { config: item.defaultConfig } : {}),
      }
    }
    case 'transform':
      return {
        nodeType: 'transform',
        pluginId: item.pluginId ?? 'unknown-plugin',
        pluginType: 'transformer',
        status: 'idle',
        label: item.label,
        ...(item.defaultConfig ? { config: item.defaultConfig } : {}),
      }
    case 'export': {
      const format = item.format ?? 'json'

      return {
        nodeType: 'export',
        format,
        status: 'idle',
        label: item.label,
        ...(item.defaultConfig ? { config: item.defaultConfig } : {}),
      }
    }
    default:
      throw new Error(`Unsupported catalog item type: ${item.type}`)
  }
}

// Define custom node types
const nodeTypes = {
  import: ImportNode,
  transform: TransformNode,
  export: ExportNode,
}

function PipelineFlowContent() {
  const [reactFlowInstance, setReactFlowInstance] = useState<ReactFlowInstance | null>(null)

  const {
    nodes,
    edges,
    onNodesChange,
    onEdgesChange,
    onConnect,
    addNode,
    setSelectedNode,
    validatePipeline,
  } = usePipelineStore()

  const onNodeClick = useCallback((_event: React.MouseEvent, node: PipelineNode) => {
    setSelectedNode(node)
  }, [setSelectedNode])

  const onDragOver = useCallback((event: React.DragEvent) => {
    event.preventDefault()
    event.dataTransfer.dropEffect = 'copy'
  }, [])

  const onDrop = useCallback(
    (event: React.DragEvent) => {
      event.preventDefault()

      const data = event.dataTransfer.getData('application/json')
      if (!data) return

      const catalogItem = JSON.parse(data) as CatalogItem

      // Check if reactFlowInstance is available
      if (!reactFlowInstance) {
        console.warn('ReactFlow instance not ready')
        return
      }

      // Use screenToFlowPosition to get the correct position
      const flowPosition = reactFlowInstance.screenToFlowPosition({
        x: event.clientX,
        y: event.clientY,
      })

      // Center the node on the cursor position
      // Typical node dimensions (adjust based on your actual node sizes)
      const nodeWidth = 210
      const nodeHeight = 77
      const position = {
        x: flowPosition.x - nodeWidth / 2,
        y: flowPosition.y - nodeHeight / 2,
      }

      // Create new node based on catalog item
      const newNode: PipelineNode = {
        id: `${catalogItem.type}-${Date.now()}`,
        type: catalogItem.type,
        position,
        data: buildNodeData(catalogItem),
      }

      addNode(newNode)
    },
    [addNode, reactFlowInstance]
  )

  // Validate pipeline whenever nodes or edges change
  React.useEffect(() => {
    validatePipeline()
  }, [nodes, edges, validatePipeline])

  const proOptions = { hideAttribution: true }

  return (
    <div className="h-full w-full flex">
      {/* Left Sidebar - Node Catalog */}
      <div className="w-64 h-full border-r bg-background overflow-hidden">
        <NodeCatalog />
      </div>

      {/* Main Canvas */}
      <div className="flex-1 relative">
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onConnect={onConnect}
          onNodeClick={onNodeClick}
          onDragOver={onDragOver}
          onDrop={onDrop}
          onInit={setReactFlowInstance}
          nodeTypes={nodeTypes}
          connectionMode={ConnectionMode.Loose}
          defaultViewport={{ x: 100, y: 100, zoom: 0.7 }}
          minZoom={0.1}
          maxZoom={2}
          proOptions={proOptions}
        >
          <Background color="#aaa" gap={16} />
          <Controls />
          <MiniMap
            nodeStrokeColor={(node) => {
              if (node.data?.nodeType === 'import') return '#3b82f6'
              if (node.data?.nodeType === 'export') return '#10b981'
              return '#6b7280'
            }}
            nodeColor={(node) => {
              if (node.data?.nodeType === 'import') return '#dbeafe'
              if (node.data?.nodeType === 'export') return '#d1fae5'
              return '#f3f4f6'
            }}
          />
          <Panel position="top-center">
            <PipelineToolbar />
          </Panel>
        </ReactFlow>
      </div>

      {/* Right Sidebar - Configuration Panel */}
      <ConfigPanel />
    </div>
  )
}

export function PipelineFlow() {
  return (
    <ReactFlowProvider>
      <PipelineFlowContent />
    </ReactFlowProvider>
  )
}
