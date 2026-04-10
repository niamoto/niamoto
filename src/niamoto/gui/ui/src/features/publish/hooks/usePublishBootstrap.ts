import { useEffect } from 'react'
import { listExportJobs, type ExportJobListItem } from '@/features/publish/api/export'
import { apiClient } from '@/shared/lib/api/client'
import { usePublishStore, type BuildJob } from '@/features/publish/store/publishStore'

function mapExportStatus(status: string): BuildJob['status'] {
  switch (status) {
    case 'running':
      return 'running'
    case 'completed':
      return 'completed'
    case 'cancelled':
      return 'cancelled'
    default:
      return 'failed'
  }
}

function mapBuildMetrics(result: ExportJobListItem['result']): BuildJob['metrics'] | undefined {
  if (!result) return undefined

  const targets: { name: string; files: number }[] = []
  let totalFiles = 0

  Object.entries(result.exports || {}).forEach(([name, exportData]) => {
    const filesGenerated = typeof exportData === 'object' && exportData
      ? ((exportData as { data?: { files_generated?: number } }).data?.files_generated || 0)
      : 0

    if (filesGenerated > 0) {
      targets.push({ name, files: filesGenerated })
      totalFiles += filesGenerated
    }
  })

  if (totalFiles === 0 && result.metrics?.generated_pages) {
    totalFiles = result.metrics.generated_pages
  }

  const duration = result.metrics?.execution_time
  if (totalFiles === 0 && !duration) return undefined

  return {
    totalFiles,
    duration: duration ? parseFloat(Number(duration).toFixed(1)) : 0,
    targets,
  }
}

function mapExportJob(item: ExportJobListItem): BuildJob {
  return {
    id: item.job_id,
    status: mapExportStatus(item.status),
    progress: item.progress,
    message: item.message,
    startedAt: item.started_at,
    completedAt: item.completed_at ?? undefined,
    metrics: mapBuildMetrics(item.result),
    error: item.error ?? undefined,
  }
}

export function usePublishBootstrap() {
  const { setProjectScope, hydrateBuildState } = usePublishStore()

  useEffect(() => {
    let cancelled = false

    const syncPublishState = async () => {
      try {
        const projectResponse = await apiClient.get('/config/project')
        const scope = projectResponse.data.working_directory || '.'

        if (cancelled) return
        setProjectScope(scope)

        const { jobs } = await listExportJobs()
        if (cancelled) return

        const mappedJobs = jobs.map(mapExportJob)
        const currentBuild = mappedJobs.find(job => job.status === 'running') ?? null
        const buildHistory = mappedJobs.filter(job => job.status !== 'running')

        hydrateBuildState({ currentBuild, buildHistory })
      } catch (error) {
        console.error('Failed to bootstrap publish state:', error)
        if (!cancelled) {
          hydrateBuildState({ currentBuild: null, buildHistory: [] })
        }
      }
    }

    void syncPublishState()

    return () => {
      cancelled = true
    }
  }, [hydrateBuildState, setProjectScope])
}
