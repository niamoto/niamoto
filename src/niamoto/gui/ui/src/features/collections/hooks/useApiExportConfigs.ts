import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { apiFetch } from '@/shared/lib/api/fetch'

const API_BASE = '/api/config/export/api-targets'

export interface ApiExportGroupEntry {
  group_by: string
  enabled: boolean
}

export interface ApiExportTargetSummary {
  name: string
  enabled: boolean
  exporter: string
  group_names: string[]
  groups: ApiExportGroupEntry[]
  params: Record<string, unknown>
}

export interface ApiExportTargetSettings {
  name: string
  enabled: boolean
  params: Record<string, unknown>
}

export interface ApiExportFieldSuggestion {
  name: string
  source: string
  label: string
}

export interface ApiExportSuggestions {
  display_fields: ApiExportFieldSuggestion[]
  available_fields?: ApiExportFieldSuggestion[]
  total_entities: number
}

export interface ApiExportGroupConfig {
  enabled: boolean
  group_by: string
  data_source?: string
  detail?: {
    pass_through?: boolean
    fields?: Array<string | Record<string, unknown>>
  }
  index?: {
    fields: Array<string | Record<string, unknown>>
  }
  json_options?: Record<string, unknown>
  transformer_plugin?: string
  transformer_params?: Record<string, unknown>
}

export type ApiExportAutoConfigConfidence = 'high' | 'medium' | 'low'

export interface ApiExportAutoConfigSection {
  confidence: ApiExportAutoConfigConfidence
  config?: Record<string, unknown>
  notes: string[]
  unresolved: string[]
}

export interface ApiExportAutoConfigProposal {
  export_name: string
  group_by: string
  total_entities: number
  proposal: ApiExportGroupConfig
  sections: Record<string, ApiExportAutoConfigSection>
}

export type ApiExportPreviewSection = 'index' | 'detail'

export interface ApiExportPreviewResponse {
  export_name: string
  group_by: string
  section: ApiExportPreviewSection
  item_id?: string | number | null
  preview: unknown
  source: Record<string, unknown>
  warnings: string[]
  errors: string[]
  metadata: Record<string, unknown>
}

async function readJson<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const error = await response
      .json()
      .catch(() => ({ detail: response.statusText }))
    throw new Error(error.detail || response.statusText)
  }
  return response.json()
}

async function fetchApiExportTargets(): Promise<ApiExportTargetSummary[]> {
  const response = await fetch(API_BASE)
  return readJson<ApiExportTargetSummary[]>(response)
}

async function fetchApiExportTargetSettings(
  exportName: string
): Promise<ApiExportTargetSettings> {
  const response = await fetch(`${API_BASE}/${encodeURIComponent(exportName)}/settings`)
  return readJson<ApiExportTargetSettings>(response)
}

async function updateApiExportTargetSettings(
  exportName: string,
  config: ApiExportTargetSettings
): Promise<ApiExportTargetSettings> {
  const response = await apiFetch(`${API_BASE}/${encodeURIComponent(exportName)}/settings`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(config),
  })
  return readJson<ApiExportTargetSettings>(response)
}

async function fetchApiExportGroupConfig(
  exportName: string,
  groupBy: string
): Promise<ApiExportGroupConfig> {
  const response = await apiFetch(
    `${API_BASE}/${encodeURIComponent(exportName)}/groups/${encodeURIComponent(groupBy)}`
  )
  return readJson<ApiExportGroupConfig>(response)
}

export async function updateApiExportGroupConfig(
  exportName: string,
  groupBy: string,
  config: ApiExportGroupConfig
): Promise<ApiExportGroupConfig> {
  const response = await apiFetch(
    `${API_BASE}/${encodeURIComponent(exportName)}/groups/${encodeURIComponent(groupBy)}`,
    {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(config),
    }
  )
  return readJson<ApiExportGroupConfig>(response)
}

async function fetchApiExportSuggestions(
  exportName: string,
  groupBy: string
): Promise<ApiExportSuggestions> {
  const response = await fetch(
    `${API_BASE}/${encodeURIComponent(exportName)}/groups/${encodeURIComponent(groupBy)}/suggestions`
  )
  return readJson<ApiExportSuggestions>(response)
}

async function fetchApiExportAutoConfig(
  exportName: string,
  groupBy: string
): Promise<ApiExportAutoConfigProposal> {
  const response = await fetch(
    `${API_BASE}/${encodeURIComponent(exportName)}/groups/${encodeURIComponent(groupBy)}/auto-config`
  )
  return readJson<ApiExportAutoConfigProposal>(response)
}

async function fetchApiExportPreview(
  exportName: string,
  groupBy: string,
  section: ApiExportPreviewSection,
  config: ApiExportGroupConfig
): Promise<ApiExportPreviewResponse> {
  const response = await apiFetch(
    `${API_BASE}/${encodeURIComponent(exportName)}/groups/${encodeURIComponent(groupBy)}/preview`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ...config, section }),
    }
  )
  return readJson<ApiExportPreviewResponse>(response)
}

export interface ApiExportTargetCreate {
  name: string
  template: 'simple' | 'dwc'
  params?: Record<string, unknown>
}

async function createApiExportTarget(
  body: ApiExportTargetCreate
): Promise<ApiExportTargetSummary> {
  const response = await apiFetch(API_BASE, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  return readJson<ApiExportTargetSummary>(response)
}

export function useCreateApiExportTarget() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (body: ApiExportTargetCreate) => createApiExportTarget(body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['api-export-targets'] })
      queryClient.invalidateQueries({ queryKey: ['collection-data-options'] })
    },
  })
}

export function useApiExportTargets() {
  return useQuery({
    queryKey: ['api-export-targets'],
    queryFn: fetchApiExportTargets,
    staleTime: 30000,
  })
}

export function useApiExportTargetSettings(exportName: string) {
  return useQuery({
    queryKey: ['api-export-target', exportName],
    queryFn: () => fetchApiExportTargetSettings(exportName),
    enabled: !!exportName,
    staleTime: 30000,
  })
}

export function useUpdateApiExportTargetSettings(exportName: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (config: ApiExportTargetSettings) =>
      updateApiExportTargetSettings(exportName, config),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['api-export-targets'] })
      queryClient.invalidateQueries({ queryKey: ['api-export-target', exportName] })
      queryClient.invalidateQueries({ queryKey: ['collection-data-options'] })
    },
  })
}

export function useApiExportGroupConfig(exportName: string, groupBy: string) {
  return useQuery({
    queryKey: ['api-export-group', exportName, groupBy],
    queryFn: () => fetchApiExportGroupConfig(exportName, groupBy),
    enabled: !!exportName && !!groupBy,
    staleTime: 30000,
  })
}

export function useUpdateApiExportGroupConfig(exportName: string, groupBy: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (config: ApiExportGroupConfig) =>
      updateApiExportGroupConfig(exportName, groupBy, config),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['api-export-targets'] })
      queryClient.invalidateQueries({ queryKey: ['api-export-group', exportName, groupBy] })
      queryClient.invalidateQueries({ queryKey: ['collection-data-options'] })
    },
  })
}

export function useApiExportSuggestions(exportName: string, groupBy: string) {
  return useQuery({
    queryKey: ['api-export-suggestions', exportName, groupBy],
    queryFn: () => fetchApiExportSuggestions(exportName, groupBy),
    enabled: !!exportName && !!groupBy,
    staleTime: 30000,
  })
}

export function useApiExportAutoConfig(
  exportName: string,
  groupBy: string,
  enabled = false
) {
  return useQuery({
    queryKey: ['api-export-auto-config', exportName, groupBy],
    queryFn: () => fetchApiExportAutoConfig(exportName, groupBy),
    enabled: enabled && !!exportName && !!groupBy,
    staleTime: 0,
  })
}

export function useApiExportPreview(
  exportName: string,
  groupBy: string,
  section: ApiExportPreviewSection,
  config: ApiExportGroupConfig,
  enabled = false
) {
  return useQuery({
    queryKey: ['api-export-preview', exportName, groupBy, section, config],
    queryFn: () => fetchApiExportPreview(exportName, groupBy, section, config),
    enabled: enabled && !!exportName && !!groupBy,
    staleTime: 5000,
  })
}
