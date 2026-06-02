import { describe, expect, it } from 'vitest'

import { candidatePreviewFromApplyResponse } from './widgetCandidateApplyState'

describe('candidatePreviewFromApplyResponse', () => {
  it('uses the fresh preview token and changes returned by a failed apply response', () => {
    const preview = candidatePreviewFromApplyResponse(
      {
        collection: 'taxons',
        writes_files: false,
        preview_token: 'old-token',
        changes: [
          {
            candidate_id: 'stale-candidate',
            widget_id: 'stale-candidate',
            title: 'Old candidate',
            action: 'add',
          },
        ],
        conflicts: [],
        invalid: [],
      },
      {
        collection: 'taxons',
        success: false,
        applied: [],
        skipped: [
          {
            candidate_id: 'stale-candidate',
            widget_id: 'stale-candidate',
            title: 'Old candidate',
            action: 'invalid',
            reason: 'Preview is stale.',
          },
        ],
        message: 'Preview is stale; rebuild the preview before applying.',
        preview_token: 'fresh-token',
        written_files: [],
        backup_files: [],
      },
    )

    expect(preview.preview_token).toBe('fresh-token')
    expect(preview.changes).toHaveLength(1)
    expect(preview.invalid[0]?.reason).toBe('Preview is stale.')
  })
})
