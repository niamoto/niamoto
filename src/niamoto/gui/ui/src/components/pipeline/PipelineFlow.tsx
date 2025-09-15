import React, { useCallback } from 'react'
import ReactFlow, {
  Background,
  Controls,
  MiniMap,
  ReactFlowProvider,
  ConnectionMode,
  Panel,
} from 'reactflow'
import 'reactflow/dist/style.css'

import { usePipelineStore } from './store'
import { ImportNode } from './nodes/import/ImportNode'
import { TransformNode } from './nodes/transform/TransformNode'
import { ExportNode } from './nodes/export/ExportNode'
import { NodeCatalog } from './sidebar/NodeCatalog'
import { ConfigPanel } from './layouts/ConfigPanel'
import { PipelineToolbar } from './layouts/PipelineToolbar'

import type { PipelineNode } from './types'

// Define custom node types
const nodeTypes = {
  import: ImportNode,
  transform: TransformNode,
  export: ExportNode,
}

function PipelineFlowContent() {
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

      const catalogItem = JSON.parse(data)

      // Get the canvas position
      const target = event.target as HTMLElement
      const rect = target.getBoundingClientRect()
      const position = {
        x: event.clientX - rect.left,
        y: event.clientY - rect.top,
      }

      // Create new node based on catalog item
      const newNode: PipelineNode = {
        id: `${catalogItem.type}-${Date.now()}`,
        type: catalogItem.type,
        position,
        data: {
          nodeType: catalogItem.type,
          subType: catalogItem.subType,
          pluginId: catalogItem.pluginId,
          format: catalogItem.format,
          label: catalogItem.label,
          status: 'idle',
        } as any,
      }

      addNode(newNode)
    },
    [addNode]
  )

  // Validate pipeline whenever nodes or edges change
  React.useEffect(() => {
    validatePipeline()
  }, [nodes, edges, validatePipeline])

  const proOptions = { hideAttribution: true }

  return (
    <div className="h-full w-full flex">
      {/* Left Sidebar - Node Catalog */}
      <div className="w-64 border-r bg-background">
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
          nodeTypes={nodeTypes}
          connectionMode={ConnectionMode.Loose}
          fitView
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
