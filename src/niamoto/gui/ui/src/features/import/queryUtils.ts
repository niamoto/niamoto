import { isAxiosError } from 'axios'
import type { QueryClient } from '@tanstack/react-query'
import { apiClient } from '@/shared/lib/api/client'
import type {
  DatasetInfo,
  DatasetsResponse,
  ReferenceInfo,
  ReferencesResponse,
} from '@/features/import/api/entities'
import {
  getTableColumns,
  listTables,
  queryTable,
} from '@/features/import/api/data-explorer'
import {
  getHierarchyInspection,
  type HierarchyInspectionParams,
} from '@/features/import/api/hierarchy'
import type { ImportSummaryDetailed } from '@/features/import/api/summary'
import { importQueryKeys } from '@/features/import/queryKeys'

export interface EntityConfigResponse<TConfig = unknown> {
  name: string
  config: TConfig
}

export const IMPORT_DETAIL_PAGE_SIZE = 20
export const IMPORT_DETAIL_PREVIEW_MAX_COLUMNS = 6
export const HIERARCHY_INSPECTION_PAGE_SIZE = 100

export function getPreviewColumnNames(columnNames: string[], maxColumns: number): string[] {
  return columnNames.slice(0, Math.max(1, maxColumns))
}

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

export function tableColumnsQueryOptions(tableName: string) {
  return {
    queryKey: importQueryKeys.dataPreview.tableColumns(tableName),
    queryFn: () => getTableColumns(tableName),
    staleTime: 60_000,
  }
}

export function tablePreviewQueryOptions(
  tableName: string,
  page: number = 0,
  pageSize: number = IMPORT_DETAIL_PAGE_SIZE,
  columns?: string[]
) {
  const selectedColumns = columns?.length ? columns : undefined

  return {
    queryKey: importQueryKeys.dataPreview.tablePage(
      tableName,
      page,
      pageSize,
      selectedColumns
    ),
    queryFn: () =>
      queryTable({
        table: tableName,
        columns: selectedColumns,
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

export function hierarchyInspectionQueryOptions(
  referenceName: string,
  params: HierarchyInspectionParams = {}
) {
  const mode = params.mode ?? 'roots'
  const search = params.search?.trim() ?? ''
  const parentId = params.parentId
  const limit = params.limit ?? HIERARCHY_INSPECTION_PAGE_SIZE
  const offset = params.offset ?? 0

  const queryKey =
    mode === 'children' && parentId != null
      ? importQueryKeys.hierarchy.children(referenceName, parentId, limit, offset)
      : mode === 'search'
        ? importQueryKeys.hierarchy.search(referenceName, search, limit, offset)
        : importQueryKeys.hierarchy.roots(referenceName, limit, offset)

  return {
    queryKey,
    queryFn: () => getHierarchyInspection(referenceName, params),
    staleTime: 60_000,
  }
}

export function hierarchyInspectionInfiniteQueryOptions(
  referenceName: string,
  params: HierarchyInspectionParams = {}
) {
  const mode = params.mode ?? 'roots'
  const search = params.search?.trim() ?? ''
  const parentId = params.parentId
  const limit = params.limit ?? HIERARCHY_INSPECTION_PAGE_SIZE
  const initialOffset = params.offset ?? 0

  const queryKey =
    mode === 'children' && parentId != null
      ? importQueryKeys.hierarchy.children(referenceName, parentId, limit, initialOffset)
      : mode === 'search'
        ? importQueryKeys.hierarchy.search(referenceName, search, limit, initialOffset)
        : importQueryKeys.hierarchy.roots(referenceName, limit, initialOffset)

  return {
    queryKey,
    queryFn: ({ pageParam = initialOffset }: { pageParam?: number }) =>
      getHierarchyInspection(referenceName, {
        ...params,
        limit,
        offset: pageParam,
        search: mode === 'search' ? search : params.search,
      }),
    initialPageParam: initialOffset,
    getNextPageParam: (lastPage: Awaited<ReturnType<typeof getHierarchyInspection>>) =>
      lastPage.next_offset ?? undefined,
    staleTime: 60_000,
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
    queryClient.prefetchQuery(tableColumnsQueryOptions(entity.table_name)),
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
