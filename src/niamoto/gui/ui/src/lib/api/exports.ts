import { apiClient } from './client'

export interface ExportFile {
  name: string
  path: string
  full_path: string
  size: number
  modified: number
}

export interface ExportsListResponse {
  exists: boolean
  path: string
  web: ExportFile[]
  api: ExportFile[]
  dwc: ExportFile[]
}

export interface ExportFileContent {
  path: string
  content: string
  parsed?: any
  size: number
  error?: string
}

/**
 * List all exported files
 */
export async function listExports(): Promise<ExportsListResponse> {
  const response = await apiClient.get<ExportsListResponse>('/files/exports/list')
  return response.data
}

/**
 * Read content of an exported file
 */
export async function readExportFile(filePath: string): Promise<ExportFileContent> {
  const response = await apiClient.get<ExportFileContent>('/files/exports/read', {
    params: { file_path: filePath }
  })
  return response.data
}

export interface ExportTreeItem {
  name: string
  type: 'directory' | 'file'
  path: string
  size?: number
  extension?: string
  count?: number
  children?: ExportTreeItem[]
}

export interface ExportsStructure {
  exists: boolean
  path: string
  tree: ExportTreeItem[]
}

/**
 * Get the directory structure of exports folder
 */
export async function getExportsStructure(): Promise<ExportsStructure> {
  const response = await apiClient.get<ExportsStructure>('/files/exports/structure')
  return response.data
}
