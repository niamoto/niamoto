import { describe, expect, it } from 'vitest'

import sources from './sources.json'

describe('French source copy', () => {
  it('names occurrence data explicitly in the pre-import overview', () => {
    const description = sources.preImport.assistant.overview.description

    expect(description).toContain("données d'occurrences")
    expect(description).not.toContain('relevés')
  })
})
