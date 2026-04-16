import type { Platform } from '@/shared/hooks/usePlatform'

export const WINDOWS_MANUAL_UPDATE_URL = 'https://github.com/niamoto/niamoto/releases/latest'

export function isInAppUpdateInstallSupported(platform: Platform): boolean {
  return platform !== 'windows'
}

type UpdaterArchitecture = 'x86_64' | 'aarch64' | 'i686' | 'armv7'

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null
}

function detectUpdaterArchitecture(): UpdaterArchitecture | null {
  if (typeof navigator === 'undefined') return null

  const userAgentData = navigator as Navigator & {
    userAgentData?: {
      architecture?: string
      bitness?: string
    }
  }

  const architecture = userAgentData.userAgentData?.architecture?.toLowerCase()
  const bitness = userAgentData.userAgentData?.bitness

  if (architecture === 'arm' || architecture === 'arm64' || architecture === 'aarch64') {
    return 'aarch64'
  }

  if (architecture === 'x86') {
    return bitness === '32' ? 'i686' : 'x86_64'
  }

  const userAgent = navigator.userAgent.toLowerCase()

  if (/(arm64|aarch64|armv8)/.test(userAgent)) return 'aarch64'
  if (/(i[3-6]86|x86(?!_64))/i.test(userAgent)) return 'i686'
  if (/(x86_64|x64|win64|wow64|amd64)/.test(userAgent)) return 'x86_64'
  if (/armv7/.test(userAgent)) return 'armv7'

  return null
}

function getTauriPlatformPrefix(platform: Platform): string | null {
  if (platform === 'macos') return 'darwin'
  if (platform === 'windows' || platform === 'linux') return platform
  return null
}

function getPlatformArtifactUrl(
  rawJson: Record<string, unknown> | null | undefined,
  platform: Platform,
  architecture?: UpdaterArchitecture | null
): string | undefined {
  if (!isRecord(rawJson)) return undefined

  const prefix = getTauriPlatformPrefix(platform)
  if (!prefix) return undefined

  const platforms = rawJson.platforms
  if (!isRecord(platforms)) return undefined

  const resolvedArchitecture = architecture ?? detectUpdaterArchitecture()
  if (resolvedArchitecture) {
    const exactKey = `${prefix}-${resolvedArchitecture}`
    const exactEntry = platforms[exactKey]
    if (isRecord(exactEntry) && typeof exactEntry.url === 'string' && exactEntry.url.trim()) {
      return exactEntry.url
    }
  }

  const matchingEntries = Object.entries(platforms).filter(([key, value]) => {
    if (!key.startsWith(`${prefix}-`) || !isRecord(value)) {
      return false
    }

    return typeof value.url === 'string' && value.url.trim().length > 0
  })

  if (matchingEntries.length === 1) {
    const [, value] = matchingEntries[0]
    if (isRecord(value) && typeof value.url === 'string') {
      return value.url
    }
  }

  return undefined
}

export function getManualUpdateUrl(
  platform: Platform,
  rawJson?: Record<string, unknown> | null,
  architecture?: UpdaterArchitecture | null
): string | undefined {
  if (platform !== 'windows') return undefined

  return getPlatformArtifactUrl(rawJson, platform, architecture) ?? WINDOWS_MANUAL_UPDATE_URL
}
