import { describe, expect, it } from 'vitest'
import {
  BACKGROUND_JOB_RECHECK_MS,
  shouldPollEnrichmentJob,
} from './enrichmentPolling'

describe('shouldPollEnrichmentJob', () => {
  it('polls immediately when no job has been seen yet', () => {
    expect(
      shouldPollEnrichmentJob({
        hasTrackedJob: false,
        knownJob: undefined,
      })
    ).toBe(true)
  })

  it('keeps polling known running jobs', () => {
    expect(
      shouldPollEnrichmentJob({
        hasTrackedJob: false,
        knownJob: { status: 'running' },
        lastBackgroundProbeAt: Date.now(),
      })
    ).toBe(true)
  })

  it('does not re-poll absent jobs before the background cooldown elapses', () => {
    expect(
      shouldPollEnrichmentJob({
        hasTrackedJob: false,
        knownJob: null,
        lastBackgroundProbeAt: 10_000,
        now: 10_000 + BACKGROUND_JOB_RECHECK_MS - 1,
      })
    ).toBe(false)
  })

  it('re-polls absent jobs after the background cooldown elapses', () => {
    expect(
      shouldPollEnrichmentJob({
        hasTrackedJob: false,
        knownJob: null,
        lastBackgroundProbeAt: 10_000,
        now: 10_000 + BACKGROUND_JOB_RECHECK_MS,
      })
    ).toBe(true)
  })

  it('always polls when a tracked enrichment job exists', () => {
    expect(
      shouldPollEnrichmentJob({
        hasTrackedJob: true,
        knownJob: null,
        lastBackgroundProbeAt: Date.now(),
      })
    ).toBe(true)
  })
})
