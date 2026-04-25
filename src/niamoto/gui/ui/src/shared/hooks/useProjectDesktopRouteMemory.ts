import { useEffect } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'

import {
  normalizeProjectDesktopRoute,
  readStoredProjectDesktopContext,
  serializeProjectDesktopRoute,
  writeStoredProjectDesktopRoute,
} from '@/shared/desktop/projectDesktopContext'
import { useCurrentProjectScope } from './useCurrentProjectScope'

const restoredProjectScopes = new Set<string>()

interface UseProjectDesktopRouteMemoryOptions {
  enabled: boolean
  storage?: Pick<Storage, 'getItem' | 'setItem' | 'removeItem'>
}

function isStartupRoute(pathname: string, search: string, hash: string): boolean {
  return pathname === '/' && search.length === 0 && hash.length === 0
}

export function useProjectDesktopRouteMemory({
  enabled,
  storage,
}: UseProjectDesktopRouteMemoryOptions) {
  const location = useLocation()
  const navigate = useNavigate()
  const { projectScope } = useCurrentProjectScope()

  useEffect(() => {
    if (!enabled || !projectScope) {
      return
    }

    const currentRoute = normalizeProjectDesktopRoute({
      pathname: location.pathname,
      search: location.search,
      hash: location.hash,
    })

    if (!currentRoute) {
      return
    }

    if (!restoredProjectScopes.has(projectScope)) {
      restoredProjectScopes.add(projectScope)

      const storedContext = readStoredProjectDesktopContext(projectScope, storage)
      const storedRoute = storedContext.lastRoute

      if (
        storedRoute
        && isStartupRoute(
          currentRoute.pathname,
          currentRoute.search,
          currentRoute.hash,
        )
        && serializeProjectDesktopRoute(storedRoute)
          !== serializeProjectDesktopRoute(currentRoute)
      ) {
        navigate(serializeProjectDesktopRoute(storedRoute), { replace: true })
        return
      }
    }

    writeStoredProjectDesktopRoute(projectScope, currentRoute, storage)
  }, [
    enabled,
    location.hash,
    location.pathname,
    location.search,
    navigate,
    projectScope,
    storage,
  ])
}

export function resetProjectDesktopRouteMemoryForTests() {
  restoredProjectScopes.clear()
}
