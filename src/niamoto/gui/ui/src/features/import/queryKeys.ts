export const importQueryKeys = {
  entities: {
    datasets: () => ['import', 'entities', 'datasets'] as const,
    references: () => ['import', 'entities', 'references'] as const,
  },
  dashboard: {
    completeness: (entityName: string) =>
      ['import', 'dashboard', 'completeness', entityName] as const,
    geoCoverage: () => ['import', 'dashboard', 'geo-coverage'] as const,
  },
  summary: () => ['import', 'summary'] as const,
}
