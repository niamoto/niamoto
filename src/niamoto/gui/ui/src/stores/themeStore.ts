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
  forestTheme,
  frondTheme,
  lapisTheme,
  tidalTheme,
  inkTheme,
  herbierTheme,
} from '@/themes'

export const DEFAULT_THEME_ID = 'frond'

/** All locally bundled fonts available for override */
export const AVAILABLE_FONTS = [
  { id: 'plus-jakarta-sans', name: 'Plus Jakarta Sans', family: '"Plus Jakarta Sans", system-ui, sans-serif', category: 'sans' },
  { id: 'instrument-sans', name: 'Instrument Sans', family: '"Instrument Sans", system-ui, sans-serif', category: 'sans' },
  { id: 'barlow', name: 'Barlow', family: 'Barlow, system-ui, sans-serif', category: 'sans' },
  { id: 'archivo', name: 'Archivo', family: 'Archivo, system-ui, sans-serif', category: 'sans' },
  { id: 'nunito', name: 'Nunito', family: 'Nunito, system-ui, sans-serif', category: 'sans' },
  { id: 'dm-sans', name: 'DM Sans', family: '"DM Sans", system-ui, sans-serif', category: 'sans' },
  { id: 'inter', name: 'Inter', family: 'Inter, system-ui, sans-serif', category: 'sans' },
  { id: 'crimson-pro', name: 'Crimson Pro', family: '"Crimson Pro", Georgia, serif', category: 'serif' },
  { id: 'source-serif-4', name: 'Source Serif 4', family: '"Source Serif 4", Georgia, serif', category: 'serif' },
  { id: 'jetbrains-mono', name: 'JetBrains Mono', family: '"JetBrains Mono", monospace', category: 'mono' },
  { id: 'ibm-plex-mono', name: 'IBM Plex Mono', family: '"IBM Plex Mono", monospace', category: 'mono' },
] as const

// Register all built-in themes
registerTheme(frondTheme)     // Brand default
registerTheme(lapisTheme)
registerTheme(tidalTheme)
registerTheme(inkTheme)
registerTheme(forestTheme)
registerTheme(herbierTheme)

interface ThemeStore {
  // State
  themeId: string
  mode: ThemeMode
  systemMode: 'light' | 'dark'
  fontOverride: string | null

  // Computed-like getters (call as functions)
  getResolvedMode: () => 'light' | 'dark'
  getCurrentTheme: () => Theme | undefined
  getAvailableThemes: () => Theme[]

  // Actions
  setTheme: (themeId: string) => void
  setMode: (mode: ThemeMode) => void
  setSystemMode: (systemMode: 'light' | 'dark') => void
  setFontOverride: (font: string | null) => void
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
      fontOverride: null,

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
          set({ themeId, fontOverride: null })
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

      setFontOverride: (font: string | null) => {
        set({ fontOverride: font })
      },

      applyCurrentTheme: () => {
        const theme = get().getCurrentTheme()
        if (theme) {
          const resolvedMode = get().getResolvedMode()
          applyTheme(theme, resolvedMode)

          // Apply font override if set
          const { fontOverride } = get()
          if (fontOverride) {
            const root = document.documentElement
            root.style.setProperty('--font-display', fontOverride)
            root.style.setProperty('--font-body', fontOverride)
            // Mono fonts also override code blocks
            if (fontOverride.toLowerCase().includes('mono')) {
              root.style.setProperty('--font-mono', fontOverride)
            }
          }
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
        fontOverride: state.fontOverride,
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
    fontOverride: store.fontOverride,
    resolvedMode: store.getResolvedMode(),
    currentTheme: store.getCurrentTheme(),
    themes: store.getAvailableThemes(),
    setTheme: store.setTheme,
    setMode: store.setMode,
    setFontOverride: store.setFontOverride,
    cycleMode: store.cycleMode,
  }
}
