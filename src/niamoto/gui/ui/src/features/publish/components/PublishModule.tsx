/**
 * PublishModule - Orchestrator for the Publish section
 *
 * The publish experience is a single workflow-oriented page.
 * Legacy aliases are normalized at the router level.
 */

import { usePublishBootstrap } from '@/features/publish/hooks/usePublishBootstrap'
import PublishOverviewContent from '@/features/publish/views'

export function PublishModule() {
  usePublishBootstrap()

  return <PublishOverviewContent />
}
