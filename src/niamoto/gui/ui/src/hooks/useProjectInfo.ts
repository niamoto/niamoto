import { useQuery } from '@tanstack/react-query'
import axios from 'axios'

export interface ProjectInfo {
  name: string
  version?: string
  niamoto_version?: string
  created_at?: string
  working_directory?: string
  instance_name?: string
}

function normalizeLabel(value?: string | null): string | null {
  if (typeof value !== 'string') {
    return null
  }

  const normalized = value.trim()
  return normalized.length > 0 ? normalized : null
}

function getPathBasename(path?: string | null): string | null {
  const normalized = normalizeLabel(path)
  if (!normalized) {
    return null
  }

  const parts = normalized.split(/[\\/]/).filter(Boolean)
  return parts[parts.length - 1] ?? normalized
}

export function getProjectDisplayName(
  projectInfo?: ProjectInfo | null
): string | null {
  return (
    normalizeLabel(projectInfo?.instance_name) ??
    getPathBasename(projectInfo?.working_directory) ??
    normalizeLabel(projectInfo?.name)
  )
}

export function useProjectInfo() {
  return useQuery<ProjectInfo>({
    queryKey: ['project-info'],
    queryFn: async () => {
      const response = await axios.get('/api/config/project')
      return response.data
    },
    staleTime: 5 * 60_000,
    retry: 1,
  })
}
