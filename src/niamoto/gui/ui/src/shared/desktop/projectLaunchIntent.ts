const MANUAL_PROJECT_OPEN_KEY = 'niamoto.manualProjectOpen'
const MANUAL_PROJECT_OPEN_TTL_MS = 30_000

interface ManualProjectOpenIntent {
  path: string
  timestamp: number
}

function readManualProjectOpenIntent(): ManualProjectOpenIntent | null {
  if (typeof window === 'undefined') {
    return null
  }

  try {
    const raw = window.localStorage.getItem(MANUAL_PROJECT_OPEN_KEY)
    if (!raw) {
      return null
    }

    const parsed = JSON.parse(raw) as Partial<ManualProjectOpenIntent>
    if (
      typeof parsed.path !== 'string' ||
      typeof parsed.timestamp !== 'number' ||
      Date.now() - parsed.timestamp > MANUAL_PROJECT_OPEN_TTL_MS
    ) {
      window.localStorage.removeItem(MANUAL_PROJECT_OPEN_KEY)
      return null
    }

    return {
      path: parsed.path,
      timestamp: parsed.timestamp,
    }
  } catch {
    window.localStorage.removeItem(MANUAL_PROJECT_OPEN_KEY)
    return null
  }
}

export function markManualProjectOpen(path: string): void {
  if (typeof window === 'undefined') {
    return
  }

  const payload: ManualProjectOpenIntent = {
    path,
    timestamp: Date.now(),
  }

  window.localStorage.setItem(MANUAL_PROJECT_OPEN_KEY, JSON.stringify(payload))
}

export function getManualProjectOpenTarget(): string | null {
  return readManualProjectOpenIntent()?.path ?? null
}

export function clearManualProjectOpenTarget(): void {
  if (typeof window === 'undefined') {
    return
  }

  window.localStorage.removeItem(MANUAL_PROJECT_OPEN_KEY)
}
