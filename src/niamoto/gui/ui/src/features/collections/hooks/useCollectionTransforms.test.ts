import { describe, expect, it } from 'vitest'

import {
  applyCompletedTransformGroups,
  getTransformActivityByGroup,
} from './useCollectionTransforms'

describe('getTransformActivityByGroup', () => {
  it('only marks the currently processed group as running during a multi-group transform', () => {
    const activity = getTransformActivityByGroup({
      runningJob: {
        group_bys: ['plots', 'shapes', 'taxons'],
        group_by: null,
        message: 'Processing taxons · elevation_binned_distribution_bar_plot',
        progress: 52,
      },
      trackedJobs: [],
    })

    expect(activity.get('taxons')).toEqual({
      state: 'running',
      progress: 52,
      message: 'Processing taxons · elevation_binned_distribution_bar_plot',
    })
    expect(activity.has('plots')).toBe(false)
    expect(activity.has('shapes')).toBe(false)
  })

  it('keeps completed groups green without overriding the current running group', () => {
    const activity = getTransformActivityByGroup({
      runningJob: {
        group_bys: ['plots', 'shapes', 'taxons'],
        group_by: null,
        message: 'Processing shapes · area_histogram',
        progress: 38,
      },
      trackedJobs: [],
    })

    const merged = applyCompletedTransformGroups(activity, ['taxons', 'shapes'])

    expect(merged.get('taxons')).toEqual({ state: 'completed', progress: 100 })
    expect(merged.get('shapes')).toEqual({
      state: 'running',
      progress: 38,
      message: 'Processing shapes · area_histogram',
    })
  })
})
