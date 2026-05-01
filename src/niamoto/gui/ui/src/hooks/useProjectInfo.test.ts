import { describe, expect, it } from 'vitest'

import { getProjectDisplayName } from './useProjectInfo'

describe('getProjectDisplayName', () => {
  it('prefers the active instance name over the configured project name', () => {
    expect(
      getProjectDisplayName({
        name: 'niamoto-subset',
        working_directory: '/tmp/nouvelle-caledonie',
        instance_name: 'nouvelle-caledonie',
      })
    ).toBe('nouvelle-caledonie')
  })

  it('derives the instance name from the working directory when needed', () => {
    expect(
      getProjectDisplayName({
        name: 'niamoto-subset',
        working_directory: '/tmp/nouvelle-caledonie',
      })
    ).toBe('nouvelle-caledonie')
  })

  it('falls back to the configured project name without instance metadata', () => {
    expect(
      getProjectDisplayName({
        name: 'Biodiversity portal',
      })
    ).toBe('Biodiversity portal')
  })
})
