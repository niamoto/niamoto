import { apiFetch } from '@/shared/lib/api/fetch'

const API_BASE = '/api/collections'

export type ApplyabilityStatus =
  | 'applicable'
  | 'review_only'
  | 'not_applicable'
  | 'stale'
  | 'conflict'

export type WidgetCandidateChangeAction =
  | 'add'
  | 'replace'
  | 'conflict'
  | 'skip'
  | 'invalid'

export type WidgetCandidateStatus =
  | 'recommended'
  | 'available'
  | 'needs_review'
  | 'missing_chart'
  | 'skipped'
  | 'configured'

export type WidgetCandidateCategory =
  | 'structure'
  | 'map'
  | 'metric'
  | 'chart'
  | 'table'
  | 'unsupported'

export interface WidgetCandidateRecommendation {
  reason: string
  score?: number | null
}

export interface WidgetCandidateDetail {
  shape: Record<string, unknown>
  warnings: Array<Record<string, unknown>>
  skip_reasons: Array<Record<string, unknown>>
  score: Record<string, unknown>
  provenance: Record<string, unknown>
  recipe_summary: Record<string, unknown>
}

export interface WidgetCandidate {
  id: string
  collection: string
  title: string
  subtitle?: string | null
  origin: string
  category: WidgetCandidateCategory
  status: WidgetCandidateStatus
  applyability: ApplyabilityStatus
  default_selected: boolean
  recommendation?: WidgetCandidateRecommendation | null
  source_fields: string[]
  source_name?: string | null
  transformer_plugin?: string | null
  widget_plugin?: string | null
  preview_descriptor?: Record<string, unknown> | null
  detail: WidgetCandidateDetail
  recipe_summary: Record<string, unknown>
  fingerprint?: string | null
}

export interface WidgetCandidateGroups {
  collection: string
  recommended: WidgetCandidate[]
  available: WidgetCandidate[]
  needs_review: WidgetCandidate[]
  missing_chart: WidgetCandidate[]
  skipped: WidgetCandidate[]
  configured: WidgetCandidate[]
  partial: boolean
  messages: string[]
}

export interface WidgetCandidateSelection {
  candidate_id: string
  replacement?: 'add' | 'replace' | 'skip'
}

export interface WidgetCandidateConfigChange {
  candidate_id: string
  widget_id: string
  title: string
  action: WidgetCandidateChangeAction
  reason?: string | null
  transform_widget?: Record<string, unknown> | null
  export_widget?: Record<string, unknown> | null
}

export interface WidgetCandidatePreviewResponse {
  collection: string
  writes_files: boolean
  preview_token: string
  changes: WidgetCandidateConfigChange[]
  conflicts: WidgetCandidateConfigChange[]
  invalid: WidgetCandidateConfigChange[]
}

export interface WidgetCandidateApplyResponse {
  collection: string
  success: boolean
  applied: WidgetCandidateConfigChange[]
  skipped: WidgetCandidateConfigChange[]
  message: string
  preview_token?: string | null
  written_files: string[]
  backup_files: string[]
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

export async function fetchWidgetCandidates(
  collectionName: string,
): Promise<WidgetCandidateGroups> {
  const response = await apiFetch(
    `${API_BASE}/${encodeURIComponent(collectionName)}/widget-candidates`,
  )
  return readJson<WidgetCandidateGroups>(response)
}

export async function previewWidgetCandidates(
  collectionName: string,
  selections: WidgetCandidateSelection[],
): Promise<WidgetCandidatePreviewResponse> {
  const response = await apiFetch(
    `${API_BASE}/${encodeURIComponent(collectionName)}/widget-candidates/preview`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ selections }),
    },
  )
  return readJson<WidgetCandidatePreviewResponse>(response)
}

export async function applyWidgetCandidates(
  collectionName: string,
  selections: WidgetCandidateSelection[],
  previewToken: string,
): Promise<WidgetCandidateApplyResponse> {
  const response = await apiFetch(
    `${API_BASE}/${encodeURIComponent(collectionName)}/widget-candidates/apply`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ selections, preview_token: previewToken }),
    },
  )
  return readJson<WidgetCandidateApplyResponse>(response)
}
