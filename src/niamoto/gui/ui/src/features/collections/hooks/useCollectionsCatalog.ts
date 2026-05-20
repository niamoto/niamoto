import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { apiFetch } from '@/shared/lib/api/fetch'

const API_BASE = '/api/collections'
export const collectionsCatalogQueryKey = ['collections-catalog'] as const

export type CollectionSourceType = 'reference' | 'dataset' | 'transform_group'
export type CollectionRole = 'site' | 'api' | 'standard' | 'technical'
export type CollectionReviewStatus =
  | 'pending'
  | 'accepted'
  | 'deferred'
  | 'rejected'

export interface CollectionEvidence {
  kind: string
  message: string
  confidence: number
  details: Record<string, unknown>
}

export interface CollectionCatalogEntry {
  name: string
  label: string
  source_type: CollectionSourceType
  source_name: string
  grain: string
  roles: CollectionRole[]
  visible: boolean
  review_status: CollectionReviewStatus
  confidence: number
  description?: string | null
  evidence: CollectionEvidence[]
}

export interface CollectionSourceOption {
  type: CollectionSourceType
  name: string
  label: string
}

export interface CollectionCatalog {
  collections: CollectionCatalogEntry[]
  sources: CollectionSourceOption[]
  total: number
}

export interface CollectionUpdate {
  label?: string
  roles?: CollectionRole[]
  visible?: boolean
  review_status?: CollectionReviewStatus
  grain?: string
  description?: string
}

export interface CollectionCreate {
  name: string
  source_type: CollectionSourceType
  source_name: string
  grain: string
  roles: CollectionRole[]
  visible: boolean
  label?: string
}

export interface CollectionMutationResponse {
  collection: CollectionCatalogEntry
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

async function fetchCollectionsCatalog(): Promise<CollectionCatalog> {
  const response = await fetch(API_BASE)
  return readJson<CollectionCatalog>(response)
}

async function updateCollection(
  collectionName: string,
  update: CollectionUpdate,
): Promise<CollectionMutationResponse> {
  const response = await apiFetch(`${API_BASE}/${encodeURIComponent(collectionName)}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(update),
  })
  return readJson<CollectionMutationResponse>(response)
}

async function createCollection(
  payload: CollectionCreate,
): Promise<CollectionMutationResponse> {
  const response = await apiFetch(API_BASE, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  return readJson<CollectionMutationResponse>(response)
}

export function useCollectionsCatalog(options: { enabled?: boolean } = {}) {
  return useQuery({
    queryKey: collectionsCatalogQueryKey,
    queryFn: fetchCollectionsCatalog,
    staleTime: 30000,
    enabled: options.enabled ?? true,
  })
}

export function useUpdateCollection() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({
      collectionName,
      update,
    }: {
      collectionName: string
      update: CollectionUpdate
    }) => updateCollection(collectionName, update),
    onSuccess: (result) => {
      queryClient.setQueryData<CollectionCatalog>(
        collectionsCatalogQueryKey,
        (current) => {
          if (!current) {
            return current
          }

          return {
            ...current,
            collections: current.collections.map((collection) =>
              collection.name === result.collection.name
                ? result.collection
                : collection,
            ),
          }
        },
      )
      queryClient.invalidateQueries({ queryKey: collectionsCatalogQueryKey })
      queryClient.invalidateQueries({ queryKey: ['collection-data-options'] })
    },
  })
}

export function useCreateCollection() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: createCollection,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: collectionsCatalogQueryKey })
      queryClient.invalidateQueries({ queryKey: ['collection-data-options'] })
    },
  })
}
