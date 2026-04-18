import { useQuery } from '@tanstack/react-query'
import {
  fetchHelpManifest,
  fetchHelpPage,
  fetchHelpSearchIndex,
} from '../api'

export function useHelpManifest() {
  return useQuery({
    queryKey: ['help', 'manifest'],
    queryFn: fetchHelpManifest,
    staleTime: 5 * 60 * 1000,
  })
}

export function useHelpSearchIndex(enabled = true) {
  return useQuery({
    queryKey: ['help', 'search-index'],
    queryFn: fetchHelpSearchIndex,
    staleTime: 5 * 60 * 1000,
    enabled,
  })
}

export function useHelpPage(slug: string | null | undefined) {
  return useQuery({
    queryKey: ['help', 'page', slug],
    queryFn: () => fetchHelpPage(slug as string),
    staleTime: 5 * 60 * 1000,
    enabled: Boolean(slug),
  })
}
