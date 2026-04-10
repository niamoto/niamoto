export const siteConfigQueryKeys = {
  config: () => ['site', 'config'] as const,
  groups: () => ['site', 'groups'] as const,
  templates: () => ['site', 'templates'] as const,
  projectFiles: (folder: string) => ['site', 'project-files', folder] as const,
  fileContent: (path: string | null | undefined) =>
    ['site', 'file-content', path ?? null] as const,
  dataContent: (path: string | null | undefined) =>
    ['site', 'data-content', path ?? null] as const,
}
