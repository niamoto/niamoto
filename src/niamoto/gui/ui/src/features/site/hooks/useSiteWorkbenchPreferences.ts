import { useCallback, useEffect, useState } from 'react'

import { useCurrentProjectScope } from '@/shared/hooks/useCurrentProjectScope'
import {
  DEFAULT_SITE_WORKBENCH_PREFERENCES,
  readStoredSiteWorkbenchPreferences,
  type SiteWorkbenchLayout,
  type SiteWorkbenchPreferences,
  type SiteWorkbenchPreviewState,
  writeStoredSiteWorkbenchPreferences,
} from '../lib/siteWorkbenchPreferences'

export function useSiteWorkbenchPreferences() {
  const { projectScope } = useCurrentProjectScope()
  const [preferences, setPreferences] = useState<SiteWorkbenchPreferences>(() =>
    readStoredSiteWorkbenchPreferences(projectScope),
  )

  useEffect(() => {
    setPreferences(readStoredSiteWorkbenchPreferences(projectScope))
  }, [projectScope])

  const updatePreferences = useCallback(
    (
      updater:
        | SiteWorkbenchPreferences
        | ((current: SiteWorkbenchPreferences) => SiteWorkbenchPreferences),
    ) => {
      setPreferences((current) => {
        const next =
          typeof updater === 'function'
            ? updater(current)
            : updater

        writeStoredSiteWorkbenchPreferences(projectScope, next)
        return next
      })
    },
    [projectScope],
  )

  const setPreviewState = useCallback(
    (previewState: SiteWorkbenchPreviewState) => {
      updatePreferences((current) => ({
        ...current,
        previewState,
      }))
    },
    [updatePreferences],
  )

  const setPreviewDevice = useCallback(
    (previewDevice: SiteWorkbenchPreferences['previewDevice']) => {
      updatePreferences((current) => ({
        ...current,
        previewDevice,
      }))
    },
    [updatePreferences],
  )

  const setPreviewLayout = useCallback(
    (previewLayout: SiteWorkbenchLayout | null) => {
      updatePreferences((current) => ({
        ...current,
        previewLayout,
      }))
    },
    [updatePreferences],
  )

  return {
    projectScope,
    previewState: preferences.previewState,
    previewDevice: preferences.previewDevice,
    previewLayout: preferences.previewLayout,
    setPreviewState,
    setPreviewDevice,
    setPreviewLayout,
    resetPreferences: () =>
      updatePreferences(DEFAULT_SITE_WORKBENCH_PREFERENCES),
  }
}
