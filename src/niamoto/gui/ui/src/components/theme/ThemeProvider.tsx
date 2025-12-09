/**
 * Theme Provider - Initializes theme on app load
 *
 * This component ensures the theme is applied when the app starts.
 * It also handles system theme change events.
 */

import { useEffect, type ReactNode } from 'react'
import { useThemeStore } from '@/stores/themeStore'

interface ThemeProviderProps {
  children: ReactNode
}

export function ThemeProvider({ children }: ThemeProviderProps) {
  const applyCurrentTheme = useThemeStore((s) => s.applyCurrentTheme)
  const mode = useThemeStore((s) => s.mode)

  // Apply theme on mount and when mode changes
  useEffect(() => {
    applyCurrentTheme()
  }, [applyCurrentTheme, mode])

  // Listen for system preference changes
  useEffect(() => {
    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)')

    const handleChange = () => {
      const currentMode = useThemeStore.getState().mode
      if (currentMode === 'system') {
        applyCurrentTheme()
      }
    }

    mediaQuery.addEventListener('change', handleChange)
    return () => mediaQuery.removeEventListener('change', handleChange)
  }, [applyCurrentTheme])

  return <>{children}</>
}
