export async function openExternalUrl(url: string): Promise<void> {
  const trimmedUrl = url.trim()
  if (!trimmedUrl) return

  try {
    if (window.__TAURI__?.core) {
      await window.__TAURI__.core.invoke('open_external_url', {
        url: trimmedUrl,
      })
      return
    }
  } catch {
    // Fall back to browser semantics below when the desktop bridge is unavailable.
  }

  window.open(trimmedUrl, '_blank', 'noopener,noreferrer')
}
