import { useCallback } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { usePipelineStatus, type EntityStatus, type RunningJob } from '@/hooks/usePipelineStatus'
import { executeTransform } from '@/lib/api/transform'
import { useNotificationStore, type TrackedJob } from '@/stores/notificationStore'

type PipelineTransformJobLike = Pick<RunningJob, 'group_by' | 'group_bys'>
type TrackedTransformJobLike = Pick<TrackedJob, 'meta'>
type TransformJobLike = PipelineTransformJobLike | TrackedTransformJobLike

function getTrackedJobGroups(job: TrackedTransformJobLike): string[] {
  return job.meta?.referenceNames ?? []
}

function isTrackedTransformJob(job: TransformJobLike): job is TrackedTransformJobLike {
  return 'meta' in job
}

export function getTransformJobGroups(job: TransformJobLike | null | undefined): string[] {
  if (!job) return []
  if (isTrackedTransformJob(job)) {
    return getTrackedJobGroups(job)
  }
  if (job.group_bys?.length) return job.group_bys
  if (job.group_by) return [job.group_by]
  return []
}

export function transformJobTargetsGroup(
  job: TransformJobLike | null | undefined,
  groupName: string
): boolean {
  return getTransformJobGroups(job).includes(groupName)
}

interface StartTransformJobOptions {
  groups: string[]
  trackingMessage: string
}

export function useStartTransformJob() {
  const queryClient = useQueryClient()
  const trackJob = useNotificationStore((state) => state.trackJob)

  return useCallback(async ({ groups, trackingMessage }: StartTransformJobOptions) => {
    const request = groups.length === 1
      ? { group_by: groups[0] }
      : { group_bys: groups }

    const response = await executeTransform(request)
    trackJob({
      jobId: response.job_id,
      jobType: 'transform',
      status: 'running',
      progress: 0,
      message: trackingMessage,
      startedAt: response.started_at,
      meta: { referenceNames: groups },
    })
    void queryClient.invalidateQueries({ queryKey: ['pipeline-status'] })
    return response
  }, [queryClient, trackJob])
}

export function useCollectionTransformState(referenceName: string) {
  const { data: pipelineStatus } = usePipelineStatus()
  const trackedJobs = useNotificationStore((state) => state.trackedJobs)

  const groupStatus = pipelineStatus?.groups.items.find((item) => item.name === referenceName) ?? null
  const runningJob = pipelineStatus?.running_job?.type === 'transform'
    ? pipelineStatus.running_job
    : null
  const trackedTransformJob = trackedJobs.find(
    (job) => job.jobType === 'transform' && transformJobTargetsGroup(job, referenceName)
  ) ?? null
  const activeTransformJob = transformJobTargetsGroup(runningJob, referenceName)
    ? runningJob
    : trackedTransformJob

  const otherTransformRunning = trackedJobs.some(
    (job) => job.jobType === 'transform' && !transformJobTargetsGroup(job, referenceName)
  ) || (runningJob != null && !transformJobTargetsGroup(runningJob, referenceName))
  const exportRunning = trackedJobs.some((job) => job.jobType === 'export')
    || pipelineStatus?.running_job?.type === 'export'

  return {
    groupStatus: groupStatus as EntityStatus | null,
    isTransforming: activeTransformJob != null,
    transformProgress: runningJob?.progress ?? trackedTransformJob?.progress ?? 0,
    transformMessage: runningJob?.message ?? trackedTransformJob?.message ?? '',
    isBlockedByOtherPipelineJob: otherTransformRunning || exportRunning,
  }
}
