import { useCallback } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { usePipelineStatus, type EntityStatus, type RunningJob } from '@/hooks/usePipelineStatus'
import { executeTransform } from '@/lib/api/transform'
import { useNotificationStore, type TrackedJob } from '@/stores/notificationStore'

type PipelineTransformJobLike = Pick<RunningJob, 'group_by' | 'group_bys'>
type TrackedTransformJobLike = Pick<TrackedJob, 'meta'>
type TransformJobLike = PipelineTransformJobLike | TrackedTransformJobLike
type RunningTransformJobLike = Pick<RunningJob, 'message' | 'group_by' | 'group_bys' | 'progress'>

export interface TransformGroupActivity {
  state: 'running' | 'completed'
  progress: number
  message?: string | null
}

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

export function getCurrentTransformBatchGroup(message?: string | null): string | null {
  if (!message) return null
  const match = message.match(/^Processing\s+(.+?)\s+·/)
  return match?.[1]?.trim() || null
}

export function getTransformActivityByGroup({
  runningJob,
  trackedJobs,
  pendingGroups = [],
}: {
  runningJob: RunningTransformJobLike | null
  trackedJobs: TrackedJob[]
  pendingGroups?: string[]
}): Map<string, TransformGroupActivity> {
  const states = new Map<string, TransformGroupActivity>()

  if (runningJob) {
    const jobGroups = getTransformJobGroups(runningJob)
    if (jobGroups.length > 0) {
      const currentGroup = getCurrentTransformBatchGroup(runningJob.message)
      const progress = runningJob.progress ?? 0

      if (jobGroups.length > 1 && currentGroup && jobGroups.includes(currentGroup)) {
        states.set(currentGroup, {
          state: 'running',
          progress,
          message: runningJob.message,
        })
        return states
      }

      for (const groupName of jobGroups) {
        states.set(groupName, {
          state: 'running',
          progress,
          message: runningJob.message,
        })
      }
      return states
    }
  }

  if (pendingGroups.length > 0) {
    for (const groupName of pendingGroups) {
      states.set(groupName, { state: 'running', progress: 0 })
    }
    return states
  }

  for (const job of trackedJobs) {
    if (job.jobType !== 'transform') continue
    for (const groupName of getTransformJobGroups(job)) {
      states.set(groupName, {
        state: 'running',
        progress: job.progress,
        message: job.message,
      })
    }
  }

  return states
}

export function applyCompletedTransformGroups(
  activityByGroup: Map<string, TransformGroupActivity>,
  completedGroups: string[]
): Map<string, TransformGroupActivity> {
  if (completedGroups.length === 0) return activityByGroup

  const states = new Map(activityByGroup)
  for (const groupName of completedGroups) {
    if (states.get(groupName)?.state === 'running') continue
    states.set(groupName, { state: 'completed', progress: 100 })
  }
  return states
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
