/**
 * Theme Provider - Initializes theme on app load
 *
 * This component ensures the theme is applied when the app starts.
 * It also handles system theme change events.
 */

import { useEffect, useLayoutEffect, type ReactNode } from 'react'
import { getTheme, getSystemMode } from '@/themes'
import { DEFAULT_THEME_ID, useThemeStore } from '@/stores/themeStore'

interface ThemeProviderProps {
  children: ReactNode
}

export function ThemeProvider({ children }: ThemeProviderProps) {
  const themeId = useThemeStore((s) => s.themeId)
  const mode = useThemeStore((s) => s.mode)
  const systemMode = useThemeStore((s) => s.systemMode)
  const fontOverride = useThemeStore((s) => s.fontOverride)
  const applyCurrentTheme = useThemeStore((s) => s.applyCurrentTheme)
  const setTheme = useThemeStore((s) => s.setTheme)
  const setSystemMode = useThemeStore((s) => s.setSystemMode)

  // Validate persisted theme ids and apply the active theme before paint.
  useLayoutEffect(() => {
    if (!getTheme(themeId)) {
      setTheme(DEFAULT_THEME_ID)
      return
    }

    applyCurrentTheme()
  }, [applyCurrentTheme, fontOverride, mode, setTheme, systemMode, themeId])

  // Listen for system preference changes in a single place.
  useEffect(() => {
    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)')
    setSystemMode(getSystemMode())

    const handleChange = (event: MediaQueryListEvent) => {
      setSystemMode(event.matches ? 'dark' : 'light')
    }

    mediaQuery.addEventListener('change', handleChange)
    return () => mediaQuery.removeEventListener('change', handleChange)
  }, [setSystemMode])

  return <>{children}</>
}
