/**
 * PublishModule - Orchestrator for the Publish section
 *
 * The publish experience is now a single workflow-oriented page.
 * Legacy sub-routes are normalized to the main route with optional panels.
 */

import { useEffect } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { usePublishBootstrap } from '@/features/publish/hooks/usePublishBootstrap'
import PublishOverviewContent from '@/features/publish/views'

export function PublishModule() {
  const location = useLocation()
  const navigate = useNavigate()
  usePublishBootstrap()

  useEffect(() => {
    const normalizedPath = location.pathname.replace(/\/+$/, '')

    if (normalizedPath === '/publish') {
      return
    }

    if (normalizedPath === '/publish/build') {
      navigate('/publish', { replace: true })
      return
    }

    if (normalizedPath === '/publish/deploy') {
      navigate('/publish?panel=destinations', { replace: true })
      return
    }

    if (normalizedPath === '/publish/history') {
      navigate('/publish?panel=history', { replace: true })
      return
    }

    if (normalizedPath.startsWith('/publish/')) {
      navigate('/publish', { replace: true })
    }
  }, [location.pathname, navigate])

  return <PublishOverviewContent />
}
