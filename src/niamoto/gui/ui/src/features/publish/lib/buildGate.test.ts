import { describe, expect, it } from 'vitest'
import { getBuildGate } from './buildGate'

describe('getBuildGate', () => {
  it('allows generation when the site is configured', () => {
    expect(getBuildGate('fresh')).toEqual({
      canGenerate: true,
      showConfigurationRequired: false,
      siteBuilderPath: null,
    })
  })

  it('blocks generation and exposes the site builder CTA when the site is unconfigured', () => {
    expect(getBuildGate('unconfigured')).toEqual({
      canGenerate: false,
      showConfigurationRequired: true,
      siteBuilderPath: '/site/pages',
    })
  })

  it('keeps never_run blocked until the site is configured', () => {
    expect(getBuildGate('never_run')).toEqual({
      canGenerate: false,
      showConfigurationRequired: true,
      siteBuilderPath: '/site/pages',
    })
  })

  it('keeps the view usable while the pipeline status is still loading', () => {
    expect(getBuildGate(undefined)).toEqual({
      canGenerate: false,
      showConfigurationRequired: false,
      siteBuilderPath: null,
    })
  })
})
