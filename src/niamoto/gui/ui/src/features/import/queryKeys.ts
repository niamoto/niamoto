export const importQueryKeys = {
  all: () => ['import'] as const,
  config: {
    dataset: (name: string) => ['import', 'config', 'dataset', name] as const,
    reference: (name: string) => ['import', 'config', 'reference', name] as const,
  },
  dataPreview: {
    tables: () => ['import', 'data-preview', 'tables'] as const,
    tableColumns: (tableName: string) =>
      ['import', 'data-preview', 'table-columns', tableName] as const,
    tablePage: (
      tableName: string,
      page: number,
      pageSize: number,
      columns?: readonly string[]
    ) =>
      [
        'import',
        'data-preview',
        'table',
        tableName,
        page,
        pageSize,
        columns ?? 'all',
      ] as const,
  },
  entities: {
    all: () => ['import', 'entities'] as const,
    datasets: () => ['import', 'entities', 'datasets'] as const,
    references: () => ['import', 'entities', 'references'] as const,
  },
  dashboard: {
    all: () => ['import', 'dashboard'] as const,
    completeness: (entityName: string) =>
      ['import', 'dashboard', 'completeness', entityName] as const,
    geoCoverage: () => ['import', 'dashboard', 'geo-coverage'] as const,
  },
  summary: () => ['import', 'summary'] as const,
}
