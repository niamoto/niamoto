import { describe, expect, it } from 'vitest'

import {
  deriveSourceProgress,
  type EnrichmentJob,
  type EnrichmentSourceStats,
} from './useEnrichmentState'

describe('deriveSourceProgress', () => {
  const sourceStats: EnrichmentSourceStats = {
    source_id: 'endemia',
    label: 'Endemia NC',
    enabled: true,
    total: 1667,
    enriched: 1608,
    pending: 59,
    status: 'running',
  }

  it('uses runtime progress for the active source during a reset run', () => {
    const job: EnrichmentJob = {
      id: 'job-1',
      reference_name: 'taxons',
      mode: 'single',
      strategy: 'reset',
      status: 'running',
      total: 1667,
      processed: 4,
      successful: 4,
      failed: 0,
      already_completed: 0,
      pending_total: 1667,
      pending_processed: 4,
      started_at: '2026-04-22T16:20:00',
      updated_at: '2026-04-22T16:21:00',
      source_ids: ['endemia'],
      source_id: 'endemia',
      source_label: 'Endemia NC',
      current_source_id: 'endemia',
      current_source_label: 'Endemia NC',
      current_source_processed: 4,
      current_source_total: 1667,
      current_source_already_completed: 0,
      current_source_pending_total: 1667,
      current_source_pending_processed: 4,
      error: null,
      current_entity: 'Abebaia',
    }

    expect(deriveSourceProgress('endemia', sourceStats, job)).toEqual({
      total: 1667,
      processed: 4,
      percentage: (4 / 1667) * 100,
    })
  })

  it('falls back to persisted stats once the job is terminal', () => {
    const job: EnrichmentJob = {
      id: 'job-1',
      reference_name: 'taxons',
      mode: 'single',
      strategy: 'reset',
      status: 'completed',
      total: 1667,
      processed: 1667,
      successful: 1608,
      failed: 59,
      already_completed: 0,
      pending_total: 1667,
      pending_processed: 1667,
      started_at: '2026-04-22T16:20:00',
      updated_at: '2026-04-22T16:29:00',
      source_ids: ['endemia'],
      source_id: 'endemia',
      source_label: 'Endemia NC',
      current_source_id: 'endemia',
      current_source_label: 'Endemia NC',
      current_source_processed: 1667,
      current_source_total: 1667,
      current_source_already_completed: 0,
      current_source_pending_total: 1667,
      current_source_pending_processed: 1667,
      error: null,
      current_entity: null,
    }

    expect(deriveSourceProgress('endemia', sourceStats, job)).toEqual({
      total: 1667,
      processed: 1608,
      percentage: (1608 / 1667) * 100,
    })
  })
})
