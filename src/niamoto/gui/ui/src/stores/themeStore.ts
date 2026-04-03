/**
 * Theme Store - Zustand store for theme management
 *
 * Manages the active theme and mode (light/dark/system)
 * with localStorage persistence.
 */

import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import {
  type Theme,
  type ThemeMode,
  registerTheme,
  getTheme,
  getAllThemes,
  applyTheme,
  getSystemMode,
  laboratoryTheme,
  forestTheme,
  frondTheme,
  slateTheme,
  frostTheme,
  mistTheme,
  lapisTheme,
  tidalTheme,
  basaltTheme,
  inkTheme,
} from '@/themes'

// Register all built-in themes
registerTheme(frondTheme)     // Brand default
registerTheme(slateTheme)
registerTheme(frostTheme)
registerTheme(mistTheme)
registerTheme(lapisTheme)
registerTheme(tidalTheme)
registerTheme(basaltTheme)
registerTheme(inkTheme)
registerTheme(laboratoryTheme)
registerTheme(forestTheme)

interface ThemeStore {
  // State
  themeId: string
  mode: ThemeMode

  // Computed-like getters (call as functions)
  getResolvedMode: () => 'light' | 'dark'
  getCurrentTheme: () => Theme | undefined
  getAvailableThemes: () => Theme[]

  // Actions
  setTheme: (themeId: string) => void
  setMode: (mode: ThemeMode) => void
  cycleMode: () => void
  applyCurrentTheme: () => void
}

export const useThemeStore = create<ThemeStore>()(
  persist(
    (set, get) => ({
      // Initial state — frond is the default for fresh installs
      themeId: 'frond',
      mode: 'system',

      // Getters
      getResolvedMode: () => {
        const { mode } = get()
        if (mode === 'system') {
          return getSystemMode()
        }
        return mode
      },

      getCurrentTheme: () => {
        return getTheme(get().themeId)
      },

      getAvailableThemes: () => {
        return getAllThemes()
      },

      // Actions
      setTheme: (themeId: string) => {
        const theme = getTheme(themeId)
        if (theme) {
          set({ themeId })
          // Apply immediately
          const resolvedMode = get().getResolvedMode()
          applyTheme(theme, resolvedMode)
        }
      },

      setMode: (mode: ThemeMode) => {
        set({ mode })
        // Apply immediately
        const theme = get().getCurrentTheme()
        if (theme) {
          const resolvedMode = mode === 'system' ? getSystemMode() : mode
          applyTheme(theme, resolvedMode)
        }
      },

      cycleMode: () => {
        const { mode } = get()
        const modes: ThemeMode[] = ['light', 'dark', 'system']
        const currentIndex = modes.indexOf(mode)
        const nextMode = modes[(currentIndex + 1) % modes.length]
        get().setMode(nextMode)
      },

      applyCurrentTheme: () => {
        const theme = get().getCurrentTheme()
        if (theme) {
          const resolvedMode = get().getResolvedMode()
          applyTheme(theme, resolvedMode)
        }
      },
    }),
    {
      name: 'niamoto-theme',
      partialize: (state) => ({
        themeId: state.themeId,
        mode: state.mode,
      }),
    }
  )
)

// Default theme id used for fresh installs and invalid persisted values
const DEFAULT_THEME_ID = 'frond'

// Initialize theme on module load
if (typeof window !== 'undefined') {
  const state = useThemeStore.getState()

  // Validate persisted theme — fall back to default if missing or removed
  if (!getTheme(state.themeId)) {
    state.setTheme(DEFAULT_THEME_ID)
  }

  // Apply theme immediately
  state.applyCurrentTheme()

  // Listen for system theme changes
  const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)')
  mediaQuery.addEventListener('change', () => {
    const { mode, applyCurrentTheme } = useThemeStore.getState()
    if (mode === 'system') {
      applyCurrentTheme()
    }
  })
}

// Helper hook for common operations
export function useTheme() {
  const store = useThemeStore()
  return {
    themeId: store.themeId,
    mode: store.mode,
    resolvedMode: store.getResolvedMode(),
    currentTheme: store.getCurrentTheme(),
    themes: store.getAvailableThemes(),
    setTheme: store.setTheme,
    setMode: store.setMode,
    cycleMode: store.cycleMode,
  }
}
