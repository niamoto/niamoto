import type { GroupInfo } from '@/shared/hooks/useSiteConfig'

export function hasEnabledGroupIndex(group: GroupInfo): boolean {
  return group.index_generator?.enabled === true
}

export function getGroupIndexOutputPattern(group: GroupInfo): string | null {
  if (!hasEnabledGroupIndex(group)) {
    return null
  }
  return group.index_output_pattern ?? `${group.name}/index.html`
}

export function getGroupIndexUrl(group: GroupInfo): string | undefined {
  const outputPattern = getGroupIndexOutputPattern(group)
  return outputPattern ? `/${outputPattern}` : undefined
}
