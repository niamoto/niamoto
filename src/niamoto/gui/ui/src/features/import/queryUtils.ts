import { isAxiosError } from 'axios'
import type { QueryClient } from '@tanstack/react-query'
import { apiClient } from '@/shared/lib/api/client'
import type {
  DatasetInfo,
  DatasetsResponse,
  ReferenceInfo,
  ReferencesResponse,
} from '@/features/import/api/entities'
import { listTables, queryTable } from '@/features/import/api/data-explorer'
import type { ImportSummaryDetailed } from '@/features/import/api/summary'
import { importQueryKeys } from '@/features/import/queryKeys'

export interface EntityConfigResponse<TConfig = unknown> {
  name: string
  config: TConfig
}

export const IMPORT_DETAIL_PAGE_SIZE = 20

export function fetchDatasetConfig(name: string): Promise<EntityConfigResponse> {
  return apiClient
    .get<EntityConfigResponse>(`/config/datasets/${encodeURIComponent(name)}/config`)
    .then((response) => response.data)
}

export function fetchReferenceConfig(name: string): Promise<EntityConfigResponse> {
  return apiClient
    .get<EntityConfigResponse>(`/config/references/${encodeURIComponent(name)}/config`)
    .then((response) => response.data)
}

export function datasetConfigQueryOptions(name: string) {
  return {
    queryKey: importQueryKeys.config.dataset(name),
    queryFn: () => fetchDatasetConfig(name),
    staleTime: 30_000,
  }
}

export function referenceConfigQueryOptions(name: string) {
  return {
    queryKey: importQueryKeys.config.reference(name),
    queryFn: () => fetchReferenceConfig(name),
    staleTime: 30_000,
  }
}

export function tablesQueryOptions() {
  return {
    queryKey: importQueryKeys.dataPreview.tables(),
    queryFn: listTables,
    staleTime: 60_000,
  }
}

export function tablePreviewQueryOptions(
  tableName: string,
  page: number = 0,
  pageSize: number = IMPORT_DETAIL_PAGE_SIZE
) {
  return {
    queryKey: importQueryKeys.dataPreview.tablePage(tableName, page, pageSize),
    queryFn: () =>
      queryTable({
        table: tableName,
        limit: pageSize,
        offset: page * pageSize,
      }),
    staleTime: 30_000,
    retry: (failureCount: number, error: unknown) => {
      if (isAxiosError(error) && error.response?.status === 404) return false
      return failureCount < 2
    },
  }
}

export async function prefetchImportEntityDetail(
  queryClient: QueryClient,
  entity: DatasetInfo | ReferenceInfo
) {
  const configPrefetch =
    'kind' in entity
      ? queryClient.prefetchQuery(referenceConfigQueryOptions(entity.name))
      : queryClient.prefetchQuery(datasetConfigQueryOptions(entity.name))

  await Promise.all([
    configPrefetch,
    queryClient.prefetchQuery(tablesQueryOptions()),
    queryClient.prefetchQuery(tablePreviewQueryOptions(entity.table_name)),
  ])
}

interface RemoveImportEntityFromCacheParams {
  entityType: 'dataset' | 'reference'
  entityName: string
  tableName: string
}

export function removeImportEntityFromCache(
  queryClient: QueryClient,
  { entityType, entityName, tableName }: RemoveImportEntityFromCacheParams
) {
  const entityAliases = new Set([entityName, tableName])

  if (entityType === 'dataset') {
    queryClient.setQueryData<DatasetsResponse>(
      importQueryKeys.entities.datasets(),
      (current) => {
        if (!current) return current

        const datasets = current.datasets.filter((dataset) => dataset.name !== entityName)
        if (datasets.length === current.datasets.length) return current

        return {
          ...current,
          datasets,
          total: datasets.length,
        }
      }
    )
  } else {
    queryClient.setQueryData<ReferencesResponse>(
      importQueryKeys.entities.references(),
      (current) => {
        if (!current) return current

        const references = current.references.filter((reference) => reference.name !== entityName)
        if (references.length === current.references.length) return current

        return {
          ...current,
          references,
          total: references.length,
        }
      }
    )
  }

  queryClient.setQueryData<ImportSummaryDetailed>(importQueryKeys.summary(), (current) => {
    if (!current) return current

    const removedEntities = current.entities.filter((entity) => entityAliases.has(entity.name))
    const removedAlerts = current.alerts.filter((alert) => entityAliases.has(alert.entity))

    if (removedEntities.length === 0 && removedAlerts.length === 0) return current

    const removedRows = removedEntities.reduce((sum, entity) => sum + entity.row_count, 0)

    return {
      ...current,
      total_entities: Math.max(0, current.total_entities - removedEntities.length),
      total_rows: Math.max(0, current.total_rows - removedRows),
      entities: current.entities.filter((entity) => !entityAliases.has(entity.name)),
      alerts: current.alerts.filter((alert) => !entityAliases.has(alert.entity)),
    }
  })
}
