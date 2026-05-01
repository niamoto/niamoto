import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

const API_BASE = '/api/standard-profiles'
export const standardProfilesQueryKey = ['standard-profiles'] as const

export type StandardProfileType = 'darwin_core_occurrence' | 'humboldt_event'
export type StandardProfileSourceType =
  | 'collection'
  | 'reference'
  | 'dataset'
  | 'transform_group'
export type StandardProfileOutputType =
  | 'api_json'
  | 'dwc_archive'
  | 'standard_files'
export type StandardProfileValidationStatus =
  | 'draft'
  | 'partial'
  | 'invalid'
  | 'conformant'
export type StandardCompatibilityStatus = 'compatible' | 'plausible' | 'blocked'
export type StandardValidationSeverity =
  | 'critical'
  | 'warning'
  | 'recommended'
  | 'info'
export type StandardChecklistStatus = 'pass' | 'warn' | 'fail'

export interface StandardProfileSource {
  type: StandardProfileSourceType
  name: string
}

export interface StandardProfileOutput {
  type: StandardProfileOutputType
  enabled: boolean
  params: Record<string, unknown>
}

export interface StandardProfileConfig {
  name: string
  enabled: boolean
  standard: StandardProfileType
  target_grain: string
  source: StandardProfileSource
  context?: StandardProfileSource | null
  mappings: Record<string, unknown>
  outputs: StandardProfileOutput[]
  validation_status: StandardProfileValidationStatus
  metadata: Record<string, unknown>
}

export interface LegacyStandardProfileHint {
  export_name: string
  standard: StandardProfileType
  message: string
}

export interface StandardProfileListResponse {
  profiles: StandardProfileConfig[]
  legacy_hints: LegacyStandardProfileHint[]
  total: number
}

export interface StandardProfileMutationResponse {
  profile: StandardProfileConfig
}

export interface StandardProfileEvidence {
  kind: string
  message: string
  confidence: number
  details: Record<string, unknown>
}

export interface StandardCompatibilityReport {
  standard: StandardProfileType
  target_grain: string
  source: StandardProfileSource
  source_grain: string
  context?: StandardProfileSource | null
  status: StandardCompatibilityStatus
  confidence: number
  evidence: StandardProfileEvidence[]
  warnings: string[]
  blockers: string[]
}

export interface StandardValidationIssue {
  code: string
  severity: StandardValidationSeverity
  message: string
  path?: string | null
}

export interface StandardValidationChecklistItem {
  code: string
  label: string
  status: StandardChecklistStatus
  severity: StandardValidationSeverity
  message?: string | null
}

export interface StandardValidationReport {
  profile_name: string
  standard: StandardProfileType
  status: StandardProfileValidationStatus
  summary: Record<StandardValidationSeverity, number>
  compatibility: StandardCompatibilityReport
  checklist: StandardValidationChecklistItem[]
  issues: StandardValidationIssue[]
}

export interface StandardProfileOutputResult {
  profile_name: string
  standard: StandardProfileType
  output_type: StandardProfileOutputType
  status: 'success' | 'skipped' | 'error'
  validation_status: StandardProfileValidationStatus
  source_grain: string
  output_path?: string | null
  files_generated: number
  files: string[]
  errors: string[]
  warnings: string[]
  metadata: Record<string, unknown>
}

export interface StandardProfileOutputPreviewResult {
  profile_name: string
  standard: StandardProfileType
  output_type: StandardProfileOutputType
  validation_status: StandardProfileValidationStatus
  source_grain: string
  item_id?: string | number | null
  preview: unknown
  source: Record<string, unknown>
  warnings: string[]
  errors: string[]
  metadata: Record<string, unknown>
}

export interface StandardProfileAutoConfigTerm {
  term: string
  status: 'mapped' | 'unresolved'
  mapping?: Record<string, unknown> | null
  confidence: number
  source_column?: string | null
  evidence: string[]
}

export interface StandardProfileAutoConfigResponse {
  profile: StandardProfileConfig
  terms: StandardProfileAutoConfigTerm[]
  unresolved: string[]
  notes: string[]
  record_source?: StandardProfileSource | null
  rows_sampled: number
  columns_inspected: number
}

export interface StandardProfileAutoConfigRequest {
  name?: string
  standard: StandardProfileType
  target_grain?: string
  source: StandardProfileSource
}

export interface StandardProfileSourceField {
  name: string
  type?: string | null
}

export interface StandardProfileSourceFieldsResponse {
  source: StandardProfileSource
  record_source: StandardProfileSource
  fields: StandardProfileSourceField[]
  total: number
}

export interface StandardProfileSourceFieldsRequest {
  standard: StandardProfileType
  target_grain?: string
  source: StandardProfileSource
}

export type StandardProfileCreate = Omit<
  StandardProfileConfig,
  'validation_status' | 'metadata'
> & {
  validation_status?: StandardProfileValidationStatus
  metadata?: Record<string, unknown>
}

export type StandardProfileUpdate = Partial<
  Omit<StandardProfileConfig, 'name'>
>

async function readJson<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const error = await response
      .json()
      .catch(() => ({ detail: response.statusText }))
    throw new Error(error.detail || response.statusText)
  }
  return response.json()
}

async function fetchStandardProfiles(): Promise<StandardProfileListResponse> {
  const response = await fetch(API_BASE)
  return readJson<StandardProfileListResponse>(response)
}

async function createStandardProfile(
  payload: StandardProfileCreate,
): Promise<StandardProfileMutationResponse> {
  const response = await fetch(API_BASE, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  return readJson<StandardProfileMutationResponse>(response)
}

async function autoConfigureStandardProfile(
  payload: StandardProfileAutoConfigRequest,
): Promise<StandardProfileAutoConfigResponse> {
  const response = await fetch(`${API_BASE}/auto-config`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  return readJson<StandardProfileAutoConfigResponse>(response)
}

async function fetchStandardProfileSourceFields(
  payload: StandardProfileSourceFieldsRequest,
): Promise<StandardProfileSourceFieldsResponse> {
  const response = await fetch(`${API_BASE}/source-fields`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  return readJson<StandardProfileSourceFieldsResponse>(response)
}

async function updateStandardProfile(
  profileName: string,
  payload: StandardProfileUpdate,
): Promise<StandardProfileMutationResponse> {
  const response = await fetch(`${API_BASE}/${encodeURIComponent(profileName)}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  return readJson<StandardProfileMutationResponse>(response)
}

async function fetchCompatibility(
  profileName: string,
): Promise<StandardCompatibilityReport> {
  const response = await fetch(
    `${API_BASE}/${encodeURIComponent(profileName)}/compatibility`,
  )
  return readJson<StandardCompatibilityReport>(response)
}

async function fetchValidation(
  profileName: string,
): Promise<StandardValidationReport> {
  const response = await fetch(
    `${API_BASE}/${encodeURIComponent(profileName)}/validation`,
  )
  return readJson<StandardValidationReport>(response)
}

async function executeStandardProfileOutput(
  profileName: string,
  outputType: StandardProfileOutputType,
): Promise<StandardProfileOutputResult> {
  const response = await fetch(
    `${API_BASE}/${encodeURIComponent(profileName)}/outputs/${outputType}`,
    { method: 'POST' },
  )
  return readJson<StandardProfileOutputResult>(response)
}

async function fetchStandardProfileOutputPreview(
  profileName: string,
  outputType: StandardProfileOutputType,
): Promise<StandardProfileOutputPreviewResult> {
  const response = await fetch(
    `${API_BASE}/${encodeURIComponent(profileName)}/outputs/${outputType}/preview`,
  )
  return readJson<StandardProfileOutputPreviewResult>(response)
}

export function useStandardProfiles() {
  return useQuery({
    queryKey: standardProfilesQueryKey,
    queryFn: fetchStandardProfiles,
    staleTime: 30000,
  })
}

export function useCreateStandardProfile() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: createStandardProfile,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: standardProfilesQueryKey })
    },
  })
}

export function useAutoConfigureStandardProfile() {
  return useMutation({
    mutationFn: autoConfigureStandardProfile,
  })
}

export function useStandardProfileSourceFields(
  payload?: StandardProfileSourceFieldsRequest | null,
  enabled = true,
) {
  return useQuery({
    queryKey: [...standardProfilesQueryKey, 'source-fields', payload],
    queryFn: () => fetchStandardProfileSourceFields(payload!),
    enabled: Boolean(payload) && enabled,
    staleTime: 30000,
  })
}

export function useUpdateStandardProfile(profileName: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (payload: StandardProfileUpdate) =>
      updateStandardProfile(profileName, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: standardProfilesQueryKey })
      queryClient.invalidateQueries({
        queryKey: [...standardProfilesQueryKey, profileName],
      })
    },
  })
}

export function useStandardProfileCompatibility(profileName?: string | null) {
  return useQuery({
    queryKey: [...standardProfilesQueryKey, profileName, 'compatibility'],
    queryFn: () => fetchCompatibility(profileName || ''),
    enabled: Boolean(profileName),
    staleTime: 30000,
  })
}

export function useStandardProfileValidation(profileName?: string | null) {
  return useQuery({
    queryKey: [...standardProfilesQueryKey, profileName, 'validation'],
    queryFn: () => fetchValidation(profileName || ''),
    enabled: Boolean(profileName),
    staleTime: 30000,
  })
}

export function useExecuteStandardProfileOutput(profileName: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (outputType: StandardProfileOutputType) =>
      executeStandardProfileOutput(profileName, outputType),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: [...standardProfilesQueryKey, profileName, 'validation'],
      })
    },
  })
}

export function useStandardProfileOutputPreview(
  profileName: string,
  outputType: StandardProfileOutputType,
  enabled = true,
) {
  return useQuery({
    queryKey: [
      ...standardProfilesQueryKey,
      profileName,
      'outputs',
      outputType,
      'preview',
    ],
    queryFn: () => fetchStandardProfileOutputPreview(profileName, outputType),
    enabled: enabled && Boolean(profileName) && Boolean(outputType),
    staleTime: 5000,
  })
}
