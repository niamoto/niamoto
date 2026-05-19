import { hasDesktopBridge, invokeDesktop } from './bridge'

export const DESKTOP_API_AUTH_HEADER = 'x-niamoto-desktop-token'

let cachedDesktopApiAuthToken: string | null = null
let pendingDesktopApiAuthToken: Promise<string | null> | null = null

export async function getDesktopApiAuthToken(): Promise<string | null> {
  if (!hasDesktopBridge()) {
    return null
  }

  if (cachedDesktopApiAuthToken) {
    return cachedDesktopApiAuthToken
  }

  pendingDesktopApiAuthToken ??=
    invokeDesktop<string | null>('get_desktop_api_auth_token')
      .then(token => {
        if (token) {
          cachedDesktopApiAuthToken = token
        }
        return token
      })
      .catch(error => {
        console.warn('Failed to read desktop API auth token:', error)
        return null
      })
      .finally(() => {
        pendingDesktopApiAuthToken = null
      })

  return pendingDesktopApiAuthToken
}
