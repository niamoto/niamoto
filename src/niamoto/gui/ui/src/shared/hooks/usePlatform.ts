import { useLayoutEffect } from 'react'

export type Platform = 'macos' | 'windows' | 'linux' | 'web'

interface PlatformInfo {
  platform: Platform
  isMac: boolean
  isWindows: boolean
  isLinux: boolean
  isWeb: boolean
  isDesktop: boolean
}

const KNOWN_PLATFORMS: Platform[] = ['macos', 'windows', 'linux', 'web']

function isPlatform(value: string | null): value is Platform {
  return value !== null && KNOWN_PLATFORMS.includes(value as Platform)
}

function getBootstrappedPlatform(): Platform | null {
  if (typeof document === 'undefined') return null

  const platform = document.documentElement.getAttribute('data-platform')
  return isPlatform(platform) ? platform : null
}

/**
 * Detect platform synchronously to avoid flash of wrong UI
 */
function detectPlatformSync(): Platform {
  if (typeof navigator === 'undefined') return 'web'

  // Use userAgentData if available (modern browsers)
  const userAgentData = (navigator as Navigator & { userAgentData?: { platform: string } }).userAgentData
  if (userAgentData?.platform) {
    const plat = userAgentData.platform.toLowerCase()
    if (plat.includes('mac')) return 'macos'
    if (plat.includes('win')) return 'windows'
    if (plat.includes('linux')) return 'linux'
  }

  // Fallback to navigator.platform
  const nav = navigator.platform.toLowerCase()
  if (nav.includes('mac')) return 'macos'
  if (nav.includes('win')) return 'windows'
  if (nav.includes('linux')) return 'linux'

  return 'web'
}

// Cache the platform detection result
const detectedPlatform = getBootstrappedPlatform() ?? detectPlatformSync()

/**
 * Detect the current platform (macOS, Windows, Linux, or Web)
 * Uses synchronous detection to avoid UI flash
 */
export function usePlatform(): PlatformInfo {
  const platform = detectedPlatform

  // Also set data-platform attribute on html element
  useLayoutEffect(() => {
    if (document.documentElement.getAttribute('data-platform') === platform) {
      return
    }

    document.documentElement.setAttribute('data-platform', platform)
  }, [platform])

  return {
    platform,
    isMac: platform === 'macos',
    isWindows: platform === 'windows',
    isLinux: platform === 'linux',
    isWeb: platform === 'web',
    isDesktop: platform !== 'web',
  }
}
