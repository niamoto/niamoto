import { describe, expect, it } from 'vitest'
import { isInAppUpdateSupported } from '../support'

describe('updater support', () => {
  it('disables in-app updates on windows', () => {
    expect(isInAppUpdateSupported('windows')).toBe(false)
  })

  it('keeps in-app updates enabled on macos and linux', () => {
    expect(isInAppUpdateSupported('macos')).toBe(true)
    expect(isInAppUpdateSupported('linux')).toBe(true)
  })
})
