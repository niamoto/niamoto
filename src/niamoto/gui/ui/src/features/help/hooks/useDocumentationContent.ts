import { keepPreviousData, useQuery } from '@tanstack/react-query'
import {
  fetchHelpManifest,
  fetchHelpPage,
  fetchHelpSearchIndex,
} from '../api'

export function useHelpManifest() {
  return useQuery({
    queryKey: ['help', 'manifest'],
    queryFn: fetchHelpManifest,
    staleTime: 0,
    refetchOnMount: 'always',
    refetchOnWindowFocus: true,
  })
}

export function useHelpSearchIndex(enabled = true) {
  return useQuery({
    queryKey: ['help', 'search-index'],
    queryFn: fetchHelpSearchIndex,
    staleTime: 0,
    refetchOnMount: 'always',
    refetchOnWindowFocus: true,
    enabled,
  })
}

export function useHelpPage(slug: string | null | undefined) {
  return useQuery({
    queryKey: ['help', 'page', slug],
    queryFn: () => fetchHelpPage(slug as string),
    placeholderData: keepPreviousData,
    staleTime: 0,
    refetchOnMount: 'always',
    refetchOnWindowFocus: true,
    enabled: Boolean(slug),
  })
}
