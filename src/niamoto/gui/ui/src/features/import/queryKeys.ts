export const importQueryKeys = {
  dashboard: {
    completeness: (entityName: string) =>
      ['import', 'dashboard', 'completeness', entityName] as const,
    geoCoverage: () => ['import', 'dashboard', 'geo-coverage'] as const,
  },
}
