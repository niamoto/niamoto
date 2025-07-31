import { useQuery } from '@tanstack/react-query'
import axios from 'axios'

interface ProjectInfo {
  name: string
  version?: string
  niamoto_version?: string
  created_at?: string
}

export function useProjectInfo() {
  return useQuery<ProjectInfo>({
    queryKey: ['project-info'],
    queryFn: async () => {
      const response = await axios.get('/api/config/project')
      return response.data
    },
    staleTime: Infinity, // Project info doesn't change during runtime
    retry: 1,
  })
}
