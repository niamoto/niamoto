import { useEffect } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'

import {
  normalizeProjectDesktopRoute,
  readNativeProjectDesktopContext,
  readStoredProjectDesktopContext,
  serializeProjectDesktopRoute,
  writeNativeProjectDesktopRoute,
  writeStoredProjectDesktopRoute,
  type ProjectDesktopContext,
  type ProjectDesktopRoute,
} from '@/shared/desktop/projectDesktopContext'
import { useCurrentProjectScope } from './useCurrentProjectScope'

const restoredProjectScopes = new Set<string>()
const lastWrittenRoutes = new Map<string, string>()

interface NativeProjectDesktopRouteStorage {
  read(projectScope: string): Promise<ProjectDesktopContext>
  writeRoute(projectScope: string, route: ProjectDesktopRoute): Promise<void>
}

const DEFAULT_NATIVE_ROUTE_STORAGE: NativeProjectDesktopRouteStorage = {
  read: readNativeProjectDesktopContext,
  writeRoute: writeNativeProjectDesktopRoute,
}

interface UseProjectDesktopRouteMemoryOptions {
  enabled: boolean
  projectScope?: string | null
  storage?: Pick<Storage, 'getItem' | 'setItem' | 'removeItem'>
  nativeStorage?: NativeProjectDesktopRouteStorage
}

function isStartupRoute(pathname: string, search: string, hash: string): boolean {
  return pathname === '/' && search.length === 0 && hash.length === 0
}

export function useProjectDesktopRouteMemory({
  enabled,
  projectScope: explicitProjectScope,
  storage,
  nativeStorage = DEFAULT_NATIVE_ROUTE_STORAGE,
}: UseProjectDesktopRouteMemoryOptions) {
  const location = useLocation()
  const navigate = useNavigate()
  const { desktopProjectScope } = useCurrentProjectScope()
  const projectScope = explicitProjectScope ?? desktopProjectScope

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

    const activeProjectScope = projectScope
    const activeRoute = currentRoute

    if (storage) {
      if (!restoredProjectScopes.has(activeProjectScope)) {
        restoredProjectScopes.add(activeProjectScope)

        const storedContext = readStoredProjectDesktopContext(
          activeProjectScope,
          storage,
        )
        const storedRoute = storedContext.lastRoute

        if (
          storedRoute
          && isStartupRoute(
            activeRoute.pathname,
            activeRoute.search,
            activeRoute.hash,
          )
          && serializeProjectDesktopRoute(storedRoute)
            !== serializeProjectDesktopRoute(activeRoute)
        ) {
          navigate(serializeProjectDesktopRoute(storedRoute), { replace: true })
          return
        }
      }

      writeStoredProjectDesktopRoute(activeProjectScope, activeRoute, storage)
      return
    }

    let cancelled = false

    async function restoreOrWriteNativeRoute() {
      if (!restoredProjectScopes.has(activeProjectScope)) {
        const storedContext = await nativeStorage.read(activeProjectScope)
        if (cancelled) {
          return
        }

        restoredProjectScopes.add(activeProjectScope)
        const storedRoute = storedContext.lastRoute

        if (
          storedRoute
          && isStartupRoute(
            activeRoute.pathname,
            activeRoute.search,
            activeRoute.hash,
          )
          && serializeProjectDesktopRoute(storedRoute)
            !== serializeProjectDesktopRoute(activeRoute)
        ) {
          navigate(serializeProjectDesktopRoute(storedRoute), { replace: true })
          return
        }
      }

      const serializedRoute = serializeProjectDesktopRoute(activeRoute)
      if (lastWrittenRoutes.get(activeProjectScope) === serializedRoute) {
        return
      }

      await nativeStorage.writeRoute(activeProjectScope, activeRoute)
      lastWrittenRoutes.set(activeProjectScope, serializedRoute)
    }

    void restoreOrWriteNativeRoute().catch((error: unknown) => {
      console.warn('Failed to sync project desktop route memory', error)
    })

    return () => {
      cancelled = true
    }
  }, [
    enabled,
    location.hash,
    location.pathname,
    location.search,
    nativeStorage,
    navigate,
    projectScope,
    storage,
  ])
}

export function resetProjectDesktopRouteMemoryForTests() {
  restoredProjectScopes.clear()
  lastWrittenRoutes.clear()
}
