/**
 * Tracks React component crashes caught by Error Boundaries.
 * Call `recordCrash()` from your ErrorBoundary's componentDidCatch.
 */

interface CrashEntry {
  component: string
  error: string
  timestamp: string
}

const MAX_ENTRIES = 5
const crashes: CrashEntry[] = []

export function recordCrash(componentName: string, error: Error): void {
  if (crashes.length >= MAX_ENTRIES) crashes.shift()
  crashes.push({
    component: componentName,
    error: `${error.name}: ${error.message}`,
    timestamp: new Date().toISOString(),
  })
}

export function getRecentCrashes(): CrashEntry[] {
  return [...crashes]
}
