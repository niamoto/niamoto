import { useCallback } from 'react'
import { useLocation } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useRuntimeMode } from '@/shared/hooks/useRuntimeMode'
import { useThemeStore } from '@/stores/themeStore'
import { redactObject } from '../lib/redact'
import { getRecentErrors } from '../lib/error-buffer'
import type { FeedbackContext } from '../types'

declare const __APP_VERSION__: string

export function useContextData() {
  const { pathname } = useLocation()
  const { mode: runtimeMode } = useRuntimeMode()
  const themeId = useThemeStore((s) => s.themeId)
  const { i18n } = useTranslation()

  const collect = useCallback(async (): Promise<FeedbackContext> => {
    const context: FeedbackContext = {
      app_version: typeof __APP_VERSION__ !== 'undefined' ? __APP_VERSION__ : 'unknown',
      os: navigator.userAgent,
      current_page: pathname,
      runtime_mode: runtimeMode,
      theme: themeId,
      language: i18n.language,
      window_size: `${window.innerWidth}×${window.innerHeight}`,
      timestamp: new Date().toISOString(),
    }

    // Collect recent console errors
    const errors = getRecentErrors()
    if (errors.length > 0) {
      context.recent_errors = redactObject(errors)
    }

    // Optional diagnostic from local backend (non-blocking)
    try {
      const response = await fetch('/api/health/diagnostic', {
        signal: AbortSignal.timeout(1500),
      })
      if (response.ok) {
        const diagnostic = await response.json()
        context.diagnostic = redactObject({
          database: diagnostic.database,
          config_files: diagnostic.config_files,
        } as Record<string, unknown>)
      }
    } catch {
      // Backend unavailable — minimal context only
    }

    return context
  }, [pathname, runtimeMode, themeId, i18n.language])

  return { collect }
}
