import { invokeDesktop, isDesktopTauri } from './tauri'

function isAllowedExternalUrl(url: string): boolean {
  try {
    const parsed = new URL(url)
    return parsed.protocol === 'http:' || parsed.protocol === 'https:' || parsed.protocol === 'mailto:'
  } catch {
    return false
  }
}

export async function openExternalUrl(url: string): Promise<void> {
  const trimmedUrl = url.trim()
  if (!trimmedUrl) return
  if (!isAllowedExternalUrl(trimmedUrl)) {
    throw new Error('Unsupported external URL')
  }

  try {
    if (isDesktopTauri()) {
      await invokeDesktop('open_external_url', {
        url: trimmedUrl,
      })
      return
    }
  } catch {
    // Fall back to browser semantics below when the desktop bridge is unavailable.
  }

  window.open(trimmedUrl, '_blank', 'noopener,noreferrer')
}
