import { describe, expect, it } from 'vitest'

import type { GroupInfo } from '@/shared/hooks/useSiteConfig'
import {
  getGroupIndexOutputPattern,
  getGroupIndexUrl,
  hasEnabledGroupIndex,
} from './groupIndex'

function group(overrides: Partial<GroupInfo>): GroupInfo {
  return {
    name: 'plots',
    output_pattern: 'plots/{id}.html',
    index_output_pattern: null,
    index_generator: null,
    widgets_count: 0,
    ...overrides,
  }
}

describe('group index helpers', () => {
  it('treats a disabled index generator as no index page even with an output pattern', () => {
    const plots = group({
      index_output_pattern: 'plots/index.html',
      index_generator: {
        enabled: false,
        template: '_group_index.html',
        page_config: {},
        filters: [],
        display_fields: [],
        views: [],
      },
    })

    expect(hasEnabledGroupIndex(plots)).toBe(false)
    expect(getGroupIndexOutputPattern(plots)).toBeNull()
    expect(getGroupIndexUrl(plots)).toBeUndefined()
  })

  it('falls back to the default index path for enabled generators', () => {
    const plots = group({
      index_generator: {
        enabled: true,
        template: '_group_index.html',
        page_config: {},
        filters: [],
        display_fields: [],
        views: [],
      },
    })

    expect(hasEnabledGroupIndex(plots)).toBe(true)
    expect(getGroupIndexOutputPattern(plots)).toBe('plots/index.html')
    expect(getGroupIndexUrl(plots)).toBe('/plots/index.html')
  })
})
