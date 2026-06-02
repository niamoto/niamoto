const MANUAL_PROJECT_OPEN_KEY = 'niamoto.manualProjectOpen'
const CREATED_PROJECT_HOME_KEY = 'niamoto.createdProjectHome'
const MANUAL_PROJECT_OPEN_TTL_MS = 30_000

interface ManualProjectOpenIntent {
  path: string
  timestamp: number
}

function readProjectLaunchIntent(storageKey: string): ManualProjectOpenIntent | null {
  if (typeof window === 'undefined') {
    return null
  }

  try {
    const raw = window.localStorage.getItem(storageKey)
    if (!raw) {
      return null
    }

    const parsed = JSON.parse(raw) as Partial<ManualProjectOpenIntent>
    if (
      typeof parsed.path !== 'string' ||
      typeof parsed.timestamp !== 'number' ||
      Date.now() - parsed.timestamp > MANUAL_PROJECT_OPEN_TTL_MS
    ) {
      window.localStorage.removeItem(storageKey)
      return null
    }

    return {
      path: parsed.path,
      timestamp: parsed.timestamp,
    }
  } catch {
    window.localStorage.removeItem(storageKey)
    return null
  }
}

function writeProjectLaunchIntent(storageKey: string, path: string): void {
  if (typeof window === 'undefined') {
    return
  }

  const payload: ManualProjectOpenIntent = {
    path,
    timestamp: Date.now(),
  }

  window.localStorage.setItem(storageKey, JSON.stringify(payload))
}

export function markManualProjectOpen(path: string): void {
  writeProjectLaunchIntent(MANUAL_PROJECT_OPEN_KEY, path)
}

export function markCreatedProjectHomeTarget(path: string): void {
  writeProjectLaunchIntent(CREATED_PROJECT_HOME_KEY, path)
}

export function getManualProjectOpenTarget(): string | null {
  return readProjectLaunchIntent(MANUAL_PROJECT_OPEN_KEY)?.path ?? null
}

export function clearManualProjectOpenTarget(): void {
  if (typeof window === 'undefined') {
    return
  }

  window.localStorage.removeItem(MANUAL_PROJECT_OPEN_KEY)
}

export function consumeCreatedProjectHomeTarget(projectScope: string | null): boolean {
  const intent = readProjectLaunchIntent(CREATED_PROJECT_HOME_KEY)
  if (!projectScope || !intent) {
    return false
  }

  if (projectScope !== `desktop:${intent.path}`) {
    return false
  }

  window.localStorage.removeItem(CREATED_PROJECT_HOME_KEY)
  return true
}
