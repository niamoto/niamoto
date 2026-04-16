import { describe, expect, it } from 'vitest'
import {
  getManualUpdateUrl,
  isInAppUpdateInstallSupported,
  WINDOWS_MANUAL_UPDATE_URL,
} from '../support'

describe('updater support', () => {
  it('disables in-app installation on windows', () => {
    expect(isInAppUpdateInstallSupported('windows')).toBe(false)
  })

  it('keeps in-app installation enabled on macos and linux', () => {
    expect(isInAppUpdateInstallSupported('macos')).toBe(true)
    expect(isInAppUpdateInstallSupported('linux')).toBe(true)
  })

  it('uses the direct windows updater artifact when it is available', () => {
    expect(
      getManualUpdateUrl(
        'windows',
        {
          platforms: {
            'windows-x86_64': {
              url: 'https://github.com/niamoto/niamoto/releases/download/v1.2.3/Niamoto_1.2.3_x64_en-US.msi.zip',
            },
          },
        },
        'x86_64'
      )
    ).toBe(
      'https://github.com/niamoto/niamoto/releases/download/v1.2.3/Niamoto_1.2.3_x64_en-US.msi.zip'
    )
  })

  it('falls back to the releases page when no matching windows artifact can be resolved', () => {
    expect(
      getManualUpdateUrl(
        'windows',
        {
          platforms: {
            'windows-x86_64': { url: 'https://example.com/x64.msi.zip' },
            'windows-aarch64': { url: 'https://example.com/arm64.msi.zip' },
          },
        },
        null
      )
    ).toBe(WINDOWS_MANUAL_UPDATE_URL)
  })
})
