import type { Platform } from '@/shared/hooks/usePlatform'

export const WINDOWS_MANUAL_UPDATE_URL = 'https://github.com/niamoto/niamoto/releases/latest'

export function isInAppUpdateInstallSupported(platform: Platform): boolean {
  return platform !== 'windows'
}
