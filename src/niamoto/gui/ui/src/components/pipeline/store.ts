import { create } from 'zustand'
import type { Edge, Connection, NodeChange, EdgeChange } from 'reactflow'
import { addEdge, applyNodeChanges, applyEdgeChanges } from 'reactflow'
import type { PipelineNode, PipelineNodeData, LayoutConfig } from './types'

interface PipelineStore {
  // Nodes and Edges
  nodes: PipelineNode[]
  edges: Edge[]
  setNodes: (nodes: PipelineNode[]) => void
  setEdges: (edges: Edge[]) => void
  onNodesChange: (changes: NodeChange[]) => void
  onEdgesChange: (changes: EdgeChange[]) => void
  onConnect: (connection: Connection) => void
  addNode: (node: PipelineNode) => void
  updateNode: (nodeId: string, data: Partial<PipelineNodeData>) => void
  deleteNode: (nodeId: string) => void

  // Selection
  selectedNode: PipelineNode | null
  setSelectedNode: (node: PipelineNode | null) => void

  // Layout
  layoutConfig: LayoutConfig
  setLayoutConfig: (config: LayoutConfig) => void

  // Pipeline State
  isValid: boolean
  errors: string[]
  validatePipeline: () => void

  // Execution
  isRunning: boolean
  setIsRunning: (running: boolean) => void
  executionProgress: Record<string, number>
  setNodeProgress: (nodeId: string, progress: number) => void

  // Catalog
  catalogFilter: 'all' | 'compatible'
  setCatalogFilter: (filter: 'all' | 'compatible') => void
  currentStep: 'import' | 'transform' | 'export' | null
  setCurrentStep: (step: 'import' | 'transform' | 'export' | null) => void
}

export const usePipelineStore = create<PipelineStore>((set, get) => ({
  // Nodes and Edges
  nodes: [],
  edges: [],

  setNodes: (nodes) => set({ nodes }),
  setEdges: (edges) => set({ edges }),

  onNodesChange: (changes) => {
    set({
      nodes: applyNodeChanges(changes, get().nodes) as PipelineNode[]
    })
  },

  onEdgesChange: (changes) => {
    set({
      edges: applyEdgeChanges(changes, get().edges)
    })
  },

  onConnect: (connection) => {
    set({
      edges: addEdge({ ...connection, animated: true }, get().edges)
    })
  },

  addNode: (node) => {
    set({ nodes: [...get().nodes, node] })
  },

  updateNode: (nodeId, data) => {
    set({
      nodes: get().nodes.map(node =>
        node.id === nodeId
          ? { ...node, data: { ...node.data, ...data } as PipelineNodeData }
          : node
      )
    })
  },

  deleteNode: (nodeId) => {
    set({
      nodes: get().nodes.filter(n => n.id !== nodeId),
      edges: get().edges.filter(e => e.source !== nodeId && e.target !== nodeId)
    })
  },

  // Selection
  selectedNode: null,
  setSelectedNode: (node) => set({ selectedNode: node }),

  // Layout
  layoutConfig: {
    type: 'side-panel',
    position: 'right',
    size: 'lg',
    collapsible: true,
    defaultCollapsed: false
  },

  setLayoutConfig: (config) => {
    set({ layoutConfig: config })
    // Save to localStorage
    localStorage.setItem('pipeline-layout', JSON.stringify(config))
  },

  // Pipeline State
  isValid: false,
  errors: [],

  validatePipeline: () => {
    const { nodes, edges } = get()
    const errors: string[] = []

    // Check for at least one import node
    const importNodes = nodes.filter(n => n.data.nodeType === 'import')
    if (importNodes.length === 0) {
      errors.push('Pipeline must have at least one import node')
    }

    // Check for proper connections
    const exportNodes = nodes.filter(n => n.data.nodeType === 'export')
    if (exportNodes.length === 0) {
      errors.push('Pipeline must have at least one export node')
    }

    // Check if all nodes are connected
    const connectedNodeIds = new Set<string>()
    edges.forEach(edge => {
      connectedNodeIds.add(edge.source)
      connectedNodeIds.add(edge.target)
    })

    const unconnectedNodes = nodes.filter(n => !connectedNodeIds.has(n.id))
    if (unconnectedNodes.length > 0 && nodes.length > 1) {
      errors.push(`${unconnectedNodes.length} node(s) are not connected`)
    }

    set({
      isValid: errors.length === 0,
      errors
    })
  },

  // Execution
  isRunning: false,
  setIsRunning: (running) => set({ isRunning: running }),
  executionProgress: {},
  setNodeProgress: (nodeId, progress) => {
    set({
      executionProgress: {
        ...get().executionProgress,
        [nodeId]: progress
      }
    })
  },

  // Catalog
  catalogFilter: 'compatible',
  setCatalogFilter: (filter) => set({ catalogFilter: filter }),
  currentStep: null,
  setCurrentStep: (step) => set({ currentStep: step })
}))

// Initialize layout from localStorage
if (typeof window !== 'undefined') {
  const savedLayout = localStorage.getItem('pipeline-layout')
  if (savedLayout) {
    try {
      const config = JSON.parse(savedLayout)
      usePipelineStore.setState({ layoutConfig: config })
    } catch (e) {
      console.error('Failed to load layout config:', e)
    }
  }
}
