const TERMINAL_JOB_STATUSES = ['completed', 'failed', 'cancelled'] as const

export const BACKGROUND_JOB_RECHECK_MS = 30_000

export interface EnrichmentJobPollingState {
  status: string
}

interface ShouldPollEnrichmentJobOptions {
  hasTrackedJob: boolean
  knownJob: EnrichmentJobPollingState | null | undefined
  lastBackgroundProbeAt?: number
  now?: number
}

export function shouldPollEnrichmentJob({
  hasTrackedJob,
  knownJob,
  lastBackgroundProbeAt,
  now = Date.now(),
}: ShouldPollEnrichmentJobOptions): boolean {
  if (hasTrackedJob) {
    return true
  }

  if (
    knownJob !== null &&
    knownJob !== undefined &&
    !TERMINAL_JOB_STATUSES.includes(
      knownJob.status as (typeof TERMINAL_JOB_STATUSES)[number]
    )
  ) {
    return true
  }

  if (knownJob === undefined) {
    return true
  }

  if (lastBackgroundProbeAt === undefined) {
    return true
  }

  return now - lastBackgroundProbeAt >= BACKGROUND_JOB_RECHECK_MS
}
