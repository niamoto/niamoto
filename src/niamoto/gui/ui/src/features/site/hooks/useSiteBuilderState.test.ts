import { describe, expect, it } from 'vitest'

import { createEnabledGroupIndexConfig } from './useSiteBuilderState'

describe('createEnabledGroupIndexConfig', () => {
  it('creates an enabled index config for Site Builder activation', () => {
    const config = createEnabledGroupIndexConfig('plots', 'List of plots')

    expect(config.enabled).toBe(true)
    expect(config.page_config.title).toBe('List of plots')
    expect(config.filters).toEqual([])
    expect(config.views).toEqual([
      { type: 'grid', default: true },
      { type: 'list', default: false },
    ])
  })
})
