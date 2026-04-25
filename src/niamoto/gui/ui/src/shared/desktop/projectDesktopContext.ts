const PROJECT_DESKTOP_CONTEXT_STORAGE_KEY_PREFIX = 'niamoto.projectDesktopContext'

const RESTORABLE_EXACT_ROUTES = [
  '/',
  '/site/pages',
  '/site/general',
  '/site/appearance',
  '/publish',
  '/tools/explorer',
  '/tools/preview',
  '/tools/settings',
  '/tools/plugins',
  '/tools/docs',
  '/tools/config-editor',
]

const RESTORABLE_ROUTE_PREFIXES = ['/sources', '/groups', '/help']

const MAX_ROUTE_SEGMENT_LENGTH = 512

export interface ProjectDesktopRoute {
  pathname: string
  search: string
  hash: string
}

export interface ProjectDesktopContext {
  lastRoute: ProjectDesktopRoute | null
  updatedAt: number | null
}

interface StoredProjectDesktopContext {
  lastRoute?: unknown
  updatedAt?: unknown
}

export const DEFAULT_PROJECT_DESKTOP_CONTEXT: ProjectDesktopContext = {
  lastRoute: null,
  updatedAt: null,
}

export function buildProjectDesktopContextStorageKey(
  projectScope: string,
): string {
  return `${PROJECT_DESKTOP_CONTEXT_STORAGE_KEY_PREFIX}:${encodeURIComponent(projectScope)}`
}

function isSafeRouteSegment(value: unknown, prefix: '?' | '#'): value is string {
  if (typeof value !== 'string') {
    return false
  }

  if (value.length === 0) {
    return true
  }

  return (
    value.startsWith(prefix)
    && value.length <= MAX_ROUTE_SEGMENT_LENGTH
    && !/[\r\n]/.test(value)
  )
}

export function isRestorableProjectRoute(pathname: string): boolean {
  if (RESTORABLE_EXACT_ROUTES.includes(pathname)) {
    return true
  }

  if (
    !pathname.startsWith('/')
    || pathname.startsWith('//')
    || pathname.length > MAX_ROUTE_SEGMENT_LENGTH
    || /[\r\n?#]/.test(pathname)
  ) {
    return false
  }

  return RESTORABLE_ROUTE_PREFIXES.some(
    (prefix) => pathname === prefix || pathname.startsWith(`${prefix}/`),
  )
}

export function normalizeProjectDesktopRoute(
  value: unknown,
): ProjectDesktopRoute | null {
  if (typeof value !== 'object' || value === null || Array.isArray(value)) {
    return null
  }

  const candidate = value as Record<string, unknown>
  const pathname = candidate.pathname

  if (typeof pathname !== 'string' || !isRestorableProjectRoute(pathname)) {
    return null
  }

  const search = candidate.search ?? ''
  const hash = candidate.hash ?? ''

  if (!isSafeRouteSegment(search, '?') || !isSafeRouteSegment(hash, '#')) {
    return null
  }

  return {
    pathname,
    search,
    hash,
  }
}

export function serializeProjectDesktopRoute(
  route: ProjectDesktopRoute,
): string {
  return `${route.pathname}${route.search}${route.hash}`
}

function normalizeUpdatedAt(value: unknown): number | null {
  return typeof value === 'number' && Number.isFinite(value) && value > 0
    ? value
    : null
}

function sanitizeProjectDesktopContext(
  context: ProjectDesktopContext,
): StoredProjectDesktopContext {
  const stored: StoredProjectDesktopContext = {}
  const normalizedRoute = context.lastRoute
    ? normalizeProjectDesktopRoute(context.lastRoute)
    : null

  if (normalizedRoute) {
    stored.lastRoute = normalizedRoute
  }

  if (
    normalizedRoute
    && typeof context.updatedAt === 'number'
    && Number.isFinite(context.updatedAt)
  ) {
    stored.updatedAt = context.updatedAt
  }

  return stored
}

export function readStoredProjectDesktopContext(
  projectScope: string | null,
  storage:
    | Pick<Storage, 'getItem' | 'removeItem'>
    | undefined = typeof window !== 'undefined'
    ? window.localStorage
    : undefined,
): ProjectDesktopContext {
  if (!projectScope || !storage) {
    return DEFAULT_PROJECT_DESKTOP_CONTEXT
  }

  const storageKey = buildProjectDesktopContextStorageKey(projectScope)

  try {
    const raw = storage.getItem(storageKey)
    if (!raw) {
      return DEFAULT_PROJECT_DESKTOP_CONTEXT
    }

    const parsed = JSON.parse(raw) as StoredProjectDesktopContext
    return {
      lastRoute: normalizeProjectDesktopRoute(parsed.lastRoute),
      updatedAt: normalizeUpdatedAt(parsed.updatedAt),
    }
  } catch {
    storage.removeItem(storageKey)
    return DEFAULT_PROJECT_DESKTOP_CONTEXT
  }
}

export function writeStoredProjectDesktopContext(
  projectScope: string | null,
  context: ProjectDesktopContext,
  storage:
    | Pick<Storage, 'setItem' | 'removeItem'>
    | undefined = typeof window !== 'undefined'
    ? window.localStorage
    : undefined,
): void {
  if (!projectScope || !storage) {
    return
  }

  const storageKey = buildProjectDesktopContextStorageKey(projectScope)
  const stored = sanitizeProjectDesktopContext(context)

  if (Object.keys(stored).length === 0) {
    storage.removeItem(storageKey)
    return
  }

  storage.setItem(storageKey, JSON.stringify(stored))
}

export function writeStoredProjectDesktopRoute(
  projectScope: string | null,
  route: ProjectDesktopRoute,
  storage:
    | Pick<Storage, 'setItem' | 'removeItem'>
    | undefined = typeof window !== 'undefined'
    ? window.localStorage
    : undefined,
  now = Date.now(),
): void {
  const normalizedRoute = normalizeProjectDesktopRoute(route)
  if (!normalizedRoute) {
    return
  }

  writeStoredProjectDesktopContext(
    projectScope,
    {
      lastRoute: normalizedRoute,
      updatedAt: now,
    },
    storage,
  )
}
