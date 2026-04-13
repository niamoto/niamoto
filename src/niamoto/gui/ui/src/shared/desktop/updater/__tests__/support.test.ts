import { describe, expect, it } from 'vitest'
import { isInAppUpdateInstallSupported } from '../support'

describe('updater support', () => {
  it('disables in-app installation on windows', () => {
    expect(isInAppUpdateInstallSupported('windows')).toBe(false)
  })

  it('keeps in-app installation enabled on macos and linux', () => {
    expect(isInAppUpdateInstallSupported('macos')).toBe(true)
    expect(isInAppUpdateInstallSupported('linux')).toBe(true)
  })
})
