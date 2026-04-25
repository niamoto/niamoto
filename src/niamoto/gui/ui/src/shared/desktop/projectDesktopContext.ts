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
  '/tools/history',
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
  viewPreferences: Record<string, string>
  updatedAt: number | null
}

interface StoredProjectDesktopContext {
  lastRoute?: unknown
  viewPreferences?: unknown
  updatedAt?: unknown
}

export const DEFAULT_PROJECT_DESKTOP_CONTEXT: ProjectDesktopContext = {
  lastRoute: null,
  viewPreferences: {},
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

function isSafePreferenceKey(value: string): boolean {
  return /^[a-z][a-z0-9._:-]{0,79}$/i.test(value)
}

function isSafePreferenceValue(value: string): boolean {
  return value.length > 0 && value.length <= 80 && !/[\r\n]/.test(value)
}

export function normalizeProjectDesktopViewPreferences(
  value: unknown,
): Record<string, string> {
  if (typeof value !== 'object' || value === null || Array.isArray(value)) {
    return {}
  }

  return Object.fromEntries(
    Object.entries(value).filter(
      ([key, preference]) =>
        isSafePreferenceKey(key)
        && typeof preference === 'string'
        && isSafePreferenceValue(preference),
    ),
  )
}

function sanitizeProjectDesktopContext(
  context: ProjectDesktopContext,
): StoredProjectDesktopContext {
  const stored: StoredProjectDesktopContext = {}
  const normalizedRoute = context.lastRoute
    ? normalizeProjectDesktopRoute(context.lastRoute)
    : null
  const viewPreferences = normalizeProjectDesktopViewPreferences(
    context.viewPreferences,
  )

  if (normalizedRoute) {
    stored.lastRoute = normalizedRoute
  }

  if (Object.keys(viewPreferences).length > 0) {
    stored.viewPreferences = viewPreferences
  }

  if (
    (normalizedRoute || Object.keys(viewPreferences).length > 0)
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
      viewPreferences: normalizeProjectDesktopViewPreferences(
        parsed.viewPreferences,
      ),
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

export function readStoredProjectDesktopViewPreference<TValue extends string>(
  projectScope: string | null,
  key: string,
  allowedValues: readonly TValue[],
  storage:
    | Pick<Storage, 'getItem' | 'removeItem'>
    | undefined = typeof window !== 'undefined'
    ? window.localStorage
    : undefined,
): TValue | null {
  if (!isSafePreferenceKey(key)) {
    return null
  }

  const context = readStoredProjectDesktopContext(projectScope, storage)
  const storedValue = context.viewPreferences[key]

  return allowedValues.includes(storedValue as TValue)
    ? (storedValue as TValue)
    : null
}

export function writeStoredProjectDesktopViewPreference<TValue extends string>(
  projectScope: string | null,
  key: string,
  value: TValue,
  allowedValues: readonly TValue[],
  storage:
    | Pick<Storage, 'getItem' | 'setItem' | 'removeItem'>
    | undefined = typeof window !== 'undefined'
    ? window.localStorage
    : undefined,
  now = Date.now(),
): void {
  if (
    !isSafePreferenceKey(key)
    || !isSafePreferenceValue(value)
    || !allowedValues.includes(value)
  ) {
    return
  }

  const context = readStoredProjectDesktopContext(projectScope, storage)
  writeStoredProjectDesktopContext(
    projectScope,
    {
      ...context,
      viewPreferences: {
        ...context.viewPreferences,
        [key]: value,
      },
      updatedAt: now,
    },
    storage,
  )
}

export function writeStoredProjectDesktopRoute(
  projectScope: string | null,
  route: ProjectDesktopRoute,
  storage:
    | Pick<Storage, 'getItem' | 'setItem' | 'removeItem'>
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
      viewPreferences: readStoredProjectDesktopContext(
        projectScope,
        storage,
      ).viewPreferences,
      updatedAt: now,
    },
    storage,
  )
}
