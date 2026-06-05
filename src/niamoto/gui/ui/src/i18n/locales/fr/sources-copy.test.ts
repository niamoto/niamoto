import { describe, expect, it } from 'vitest'

import sources from './sources.json'

describe('French source copy', () => {
  it('names occurrence data explicitly in the pre-import overview', () => {
    const description = sources.preImport.assistant.overview.description

    expect(description).toContain("données d'occurrences")
    expect(description).not.toContain('relevés')
  })

  it('uses plain French labels for auto-configuration sections', () => {
    expect(sources.autoConfig.sections.aggregationCandidates).toBe(
      'Collections proposées ({{count}})'
    )
    expect(sources.autoConfig.sections.supportingSources).toBe(
      'Fichiers importés ({{count}})'
    )
    expect(sources.autoConfig.sections.aggregationCandidates).not.toContain('candidates')
    expect(sources.autoConfig.sections.supportingSources).not.toContain('support')
  })
})
