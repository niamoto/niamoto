import { useQuery } from '@tanstack/react-query'

import type {
  CollectionReviewStatus,
  CollectionRole,
} from './useCollectionsCatalog'
import type { StandardProfileType } from './useStandardProfiles'

const API_BASE = '/api/collections'
export const collectionDataOptionsQueryKey = ['collection-data-options'] as const

export type DataOutputFamily = 'simple_json' | 'standard'
export type DataConfiguredOutputKind =
  | 'api_json'
  | 'standard_profile'
  | 'legacy_standard_hint'
export type DataOptionSuitability =
  | 'recommended'
  | 'possible'
  | 'not_recommended'
export type DataOptionsState = 'configured' | 'recommended' | 'needs_intent'

export interface CollectionDataSourceSummary {
  type: string
  name: string
}

export interface CollectionDataSummary {
  name: string
  label: string
  grain: string
  roles: CollectionRole[]
  source: CollectionDataSourceSummary
  review_status: CollectionReviewStatus
}

export interface CollectionDataEvidence {
  kind: string
  message: string
  confidence: number
  details: Record<string, unknown>
}

export interface CollectionDataAction {
  type: string
  label: string
  target: Record<string, unknown>
}

export interface CollectionDataConfiguredOutput {
  id: string
  kind: DataConfiguredOutputKind
  name: string
  label: string
  enabled: boolean
  status: string
  family: DataOutputFamily
  source?: CollectionDataSourceSummary | null
  standard?: StandardProfileType | null
  target_grain?: string | null
  validation_status?: string | null
  actions: CollectionDataAction[]
  evidence: CollectionDataEvidence[]
  summary: Record<string, unknown>
}

export interface CollectionDataOption {
  id: string
  family: DataOutputFamily
  label: string
  suitability: DataOptionSuitability
  confidence: number
  standard?: StandardProfileType | null
  target_grain?: string | null
  reasons: string[]
  missing_evidence: string[]
  evidence: CollectionDataEvidence[]
  action?: CollectionDataAction | null
}

export interface CollectionDataOptionsResponse {
  collection: CollectionDataSummary
  state: DataOptionsState
  configured_outputs: CollectionDataConfiguredOutput[]
  available_options: CollectionDataOption[]
  primary_action?: CollectionDataAction | null
  missing_evidence: string[]
  sensitivity: Record<string, unknown>
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

async function fetchCollectionDataOptions(
  collectionName: string,
): Promise<CollectionDataOptionsResponse> {
  const response = await fetch(
    `${API_BASE}/${encodeURIComponent(collectionName)}/data-options`,
  )
  return readJson<CollectionDataOptionsResponse>(response)
}

export function useCollectionDataOptions(
  collectionName?: string | null,
  options: { enabled?: boolean } = {},
) {
  return useQuery({
    queryKey: [...collectionDataOptionsQueryKey, collectionName],
    queryFn: () => fetchCollectionDataOptions(collectionName || ''),
    enabled: Boolean(collectionName) && (options.enabled ?? true),
    staleTime: 30000,
  })
}
