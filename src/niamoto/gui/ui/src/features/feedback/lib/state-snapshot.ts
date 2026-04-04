/**
 * Captures a lightweight snapshot of Zustand stores
 * for feedback debug context. Only includes non-sensitive, useful state.
 */
import { useNavigationStore } from '@/stores/navigationStore'
import { useThemeStore } from '@/stores/themeStore'

export function getStateSnapshot(): Record<string, unknown> {
  const nav = useNavigationStore.getState()
  const theme = useThemeStore.getState()

  return {
    sidebar_mode: nav.sidebarMode,
    theme_id: theme.themeId,
    theme_mode: theme.mode,
  }
}
