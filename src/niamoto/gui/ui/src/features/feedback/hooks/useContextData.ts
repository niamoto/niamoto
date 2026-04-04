import { useCallback } from 'react'
import { useLocation } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useRuntimeMode } from '@/shared/hooks/useRuntimeMode'
import { useThemeStore } from '@/stores/themeStore'
import { redactObject } from '../lib/redact'
import { getRecentErrors } from '../lib/error-buffer'
import { getNavigationHistory } from '../lib/navigation-tracker'
import { getFailedRequests } from '../lib/api-tracker'
import { getRecentCrashes } from '../lib/crash-tracker'
import { getStateSnapshot } from '../lib/state-snapshot'
import type { FeedbackContext } from '../types'

declare const __APP_VERSION__: string

export function useContextData() {
  const { pathname } = useLocation()
  const { mode: runtimeMode } = useRuntimeMode()
  const themeId = useThemeStore((s) => s.themeId)
  const themeMode = useThemeStore((s) => s.mode)
  const { i18n } = useTranslation()

  const collect = useCallback(async (): Promise<FeedbackContext> => {
    const context: FeedbackContext = {
      app_version: typeof __APP_VERSION__ !== 'undefined' ? __APP_VERSION__ : 'unknown',
      os: navigator.userAgent,
      current_page: pathname,
      runtime_mode: runtimeMode,
      theme: `${themeId} (${themeMode})`,
      language: i18n.language,
      window_size: `${window.innerWidth}×${window.innerHeight}`,
      screen_size: `${screen.width}×${screen.height} @${devicePixelRatio}x`,
      timestamp: new Date().toISOString(),
      uptime: Math.round(performance.now() / 1000) + 's',
    }

    // Collect recent console errors
    const errors = getRecentErrors()
    if (errors.length > 0) {
      context.recent_errors = errors
    }

    // Navigation history (last 10 pages visited)
    const navHistory = getNavigationHistory()
    if (navHistory.length > 0) {
      context.navigation_history = navHistory
    }

    // Failed/slow API requests
    const failedReqs = getFailedRequests()
    if (failedReqs.length > 0) {
      context.failed_requests = failedReqs
    }

    // React component crashes
    const crashes = getRecentCrashes()
    if (crashes.length > 0) {
      context.crashes = crashes
    }

    // Zustand stores state snapshot
    context.state_snapshot = getStateSnapshot()

    // Performance memory info (Chromium/WebKit)
    const perfMemory = (performance as unknown as { memory?: { usedJSHeapSize: number; jsHeapSizeLimit: number } }).memory
    if (perfMemory) {
      context.memory = `${Math.round(perfMemory.usedJSHeapSize / 1024 / 1024)}MB / ${Math.round(perfMemory.jsHeapSizeLimit / 1024 / 1024)}MB`
    }

    // Optional diagnostic from local backend (non-blocking)
    try {
      const response = await fetch('/api/health/diagnostic', {
        signal: AbortSignal.timeout(1500),
      })
      if (response.ok) {
        const diagnostic = await response.json()
        context.diagnostic = {
          database: diagnostic.database,
          config_files: diagnostic.config_files,
        }
      }
    } catch {
      context.backend_status = 'unreachable'
    }

    // Single redaction pass on the entire context
    return redactObject(context)
  }, [pathname, runtimeMode, themeId, themeMode, i18n.language])

  return { collect }
}
