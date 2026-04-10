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

export const DEFAULT_THEME_ID = 'frond'

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
  systemMode: 'light' | 'dark'

  // Computed-like getters (call as functions)
  getResolvedMode: () => 'light' | 'dark'
  getCurrentTheme: () => Theme | undefined
  getAvailableThemes: () => Theme[]

  // Actions
  setTheme: (themeId: string) => void
  setMode: (mode: ThemeMode) => void
  setSystemMode: (systemMode: 'light' | 'dark') => void
  cycleMode: () => void
  applyCurrentTheme: () => void
}

export const useThemeStore = create<ThemeStore>()(
  persist(
    (set, get) => ({
      // Initial state — frond is the default for fresh installs
      themeId: DEFAULT_THEME_ID,
      mode: 'system',
      systemMode:
        typeof window !== 'undefined' ? getSystemMode() : 'light',

      // Getters
      getResolvedMode: () => {
        const { mode, systemMode } = get()
        if (mode === 'system') {
          return systemMode
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
        if (getTheme(themeId)) {
          set({ themeId })
        }
      },

      setMode: (mode: ThemeMode) => {
        set({ mode })
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

      setSystemMode: (systemMode: 'light' | 'dark') => {
        set({ systemMode })
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
