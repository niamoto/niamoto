import { useMemo } from 'react'

import { useProjectInfo } from '@/hooks/useProjectInfo'
import { useRuntimeMode } from './useRuntimeMode'

function normalizeProjectToken(value?: string | null): string | null {
  if (typeof value !== 'string') {
    return null
  }

  const normalized = value.trim()
  return normalized.length > 0 ? normalized : null
}

export function buildDesktopProjectScope(
  projectPath?: string | null,
): string | null {
  const normalizedProjectPath = normalizeProjectToken(projectPath)
  return normalizedProjectPath ? `desktop:${normalizedProjectPath}` : null
}

export function buildFallbackProjectScope(
  projectInfo?: { name?: string; created_at?: string } | null,
): string | null {
  const name = normalizeProjectToken(projectInfo?.name)
  if (!name) {
    return null
  }

  const createdAt = normalizeProjectToken(projectInfo?.created_at) ?? 'unknown'
  return `project:${name}:${createdAt}`
}

export function useCurrentProjectScope() {
  const runtimeMode = useRuntimeMode()
  const { data: projectInfo } = useProjectInfo()

  const desktopProjectScope = useMemo(
    () => buildDesktopProjectScope(runtimeMode.project),
    [runtimeMode.project],
  )
  const fallbackProjectScope = useMemo(
    () => buildFallbackProjectScope(projectInfo ?? null),
    [projectInfo],
  )
  const projectScope = useMemo(
    () => desktopProjectScope ?? fallbackProjectScope,
    [desktopProjectScope, fallbackProjectScope],
  )

  return {
    projectScope,
    desktopProjectScope,
    fallbackProjectScope,
  }
}
