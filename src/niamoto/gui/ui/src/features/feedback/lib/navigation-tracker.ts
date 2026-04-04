/**
 * Tracks the last N page navigations for debug context.
 * Initialized once, records are collected when feedback is sent.
 */

interface NavigationEntry {
  path: string
  timestamp: string
}

const MAX_ENTRIES = 10
const history: NavigationEntry[] = []

export function recordNavigation(path: string): void {
  // Avoid duplicate consecutive entries
  if (history.length > 0 && history[history.length - 1].path === path) return
  if (history.length >= MAX_ENTRIES) history.shift()
  history.push({ path, timestamp: new Date().toISOString() })
}

export function getNavigationHistory(): NavigationEntry[] {
  return [...history]
}
