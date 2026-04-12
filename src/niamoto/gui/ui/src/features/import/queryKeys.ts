export const importQueryKeys = {
  all: () => ['import'] as const,
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
