// @vitest-environment jsdom

import { describe, expect, it } from 'vitest'

import { shouldUseCandidateApplyPath } from './addWidgetApplyMode'

describe('shouldUseCandidateApplyPath', () => {
  it('uses the candidate apply path only when every selected suggestion is candidate-backed', () => {
    const candidateSuggestionIds = new Set(['nav', 'info'])

    expect(shouldUseCandidateApplyPath([], candidateSuggestionIds)).toBe(false)
    expect(shouldUseCandidateApplyPath(['nav'], candidateSuggestionIds)).toBe(true)
    expect(shouldUseCandidateApplyPath(['nav', 'info'], candidateSuggestionIds)).toBe(
      true,
    )
    expect(shouldUseCandidateApplyPath(['nav', 'legacy'], candidateSuggestionIds)).toBe(
      false,
    )
  })

  it('falls back to the editable suggestion flow when a candidate-backed suggestion was customized', () => {
    const candidateSuggestionIds = new Set(['nav', 'info'])
    const customizedSuggestionIds = new Set(['nav'])

    expect(
      shouldUseCandidateApplyPath(
        ['nav'],
        candidateSuggestionIds,
        customizedSuggestionIds,
      ),
    ).toBe(false)
    expect(
      shouldUseCandidateApplyPath(
        ['info'],
        candidateSuggestionIds,
        customizedSuggestionIds,
      ),
    ).toBe(true)
  })
})
