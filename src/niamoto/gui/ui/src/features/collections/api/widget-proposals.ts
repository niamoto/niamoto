import { apiFetch } from '@/shared/lib/api/fetch'

const API_BASE = '/api/collections'

export type ProposalStatus =
  | 'recommended'
  | 'warning'
  | 'missing_chart'
  | 'skipped'
  | 'already_configured'
  | 'review_only'

export type ApplyabilityStatus =
  | 'applicable'
  | 'review_only'
  | 'not_applicable'
  | 'stale'
  | 'conflict'

export interface ProposalWarning {
  code: string
  message: string
  severity: 'info' | 'warning' | 'error'
  details: Record<string, unknown>
}

export interface ProposalSkipReason {
  code: string
  message: string
  details: Record<string, unknown>
}

export interface TransformedShape {
  kind: string
  category_count?: number | null
  bin_count?: number | null
  point_count?: number | null
  series_count?: number | null
  metric_count?: number | null
  label_max_length?: number | null
  has_labels: boolean
  columns: string[]
  unsupported_reason?: string | null
  metadata: Record<string, unknown>
}

export interface ChartFitResult {
  widget: string
  status: 'primary' | 'secondary' | 'warning' | 'suppressed'
  score: number
  reason: string
  warnings: ProposalWarning[]
  params: Record<string, unknown>
  rank: number
}

export interface TransformationCandidate {
  id: string
  collection: string
  origin: string
  intent: string
  source_name?: string | null
  field_names: string[]
  transformer_plugin?: string | null
  reconstructability: string
  freshness: string
  warnings: ProposalWarning[]
  skip_reasons: ProposalSkipReason[]
}

export interface MissingChartOpportunity {
  reason: string
  suggested_family?: string | null
}

export interface WidgetProposal {
  id: string
  collection: string
  title: string
  status: ProposalStatus
  candidate: TransformationCandidate
  shape: TransformedShape
  primary_fit?: ChartFitResult | null
  alternatives: ChartFitResult[]
  suppressed_fits: ChartFitResult[]
  missing_chart?: MissingChartOpportunity | null
  score: { dimensions: Record<string, number>; weights: Record<string, number> }
  warnings: ProposalWarning[]
  skip_reasons: ProposalSkipReason[]
  applyability: ApplyabilityStatus
  fingerprint?: string | null
  recipe: Record<string, unknown>
}

export interface WidgetProposalGroups {
  collection: string
  recommended: WidgetProposal[]
  warnings: WidgetProposal[]
  missing_chart: WidgetProposal[]
  skipped: WidgetProposal[]
  already_configured: WidgetProposal[]
  review_only: WidgetProposal[]
  partial: boolean
  messages: string[]
}

export interface WidgetProposalSelection {
  proposal_id: string
  replacement?: 'add' | 'replace' | 'skip'
}

export interface WidgetProposalConfigChange {
  proposal_id: string
  widget_id: string
  title: string
  action: 'add' | 'replace' | 'conflict' | 'skip' | 'invalid'
  reason?: string | null
  transform_widget?: Record<string, unknown> | null
  export_widget?: Record<string, unknown> | null
}

export interface WidgetProposalPreviewResponse {
  collection: string
  writes_files: boolean
  preview_token: string
  changes: WidgetProposalConfigChange[]
  conflicts: WidgetProposalConfigChange[]
  invalid: WidgetProposalConfigChange[]
}

export interface WidgetProposalApplyResponse {
  collection: string
  success: boolean
  applied: WidgetProposalConfigChange[]
  skipped: WidgetProposalConfigChange[]
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

export async function fetchWidgetProposals(
  collectionName: string,
): Promise<WidgetProposalGroups> {
  const response = await apiFetch(
    `${API_BASE}/${encodeURIComponent(collectionName)}/widget-proposals`,
  )
  return readJson<WidgetProposalGroups>(response)
}

export async function previewWidgetProposals(
  collectionName: string,
  selections: WidgetProposalSelection[],
): Promise<WidgetProposalPreviewResponse> {
  const response = await apiFetch(
    `${API_BASE}/${encodeURIComponent(collectionName)}/widget-proposals/preview`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ selections }),
    },
  )
  return readJson<WidgetProposalPreviewResponse>(response)
}

export async function applyWidgetProposals(
  collectionName: string,
  selections: WidgetProposalSelection[],
  previewToken?: string | null,
): Promise<WidgetProposalApplyResponse> {
  const response = await apiFetch(
    `${API_BASE}/${encodeURIComponent(collectionName)}/widget-proposals/apply`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ selections, preview_token: previewToken ?? null }),
    },
  )
  return readJson<WidgetProposalApplyResponse>(response)
}
