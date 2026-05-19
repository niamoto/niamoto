import {
  DESKTOP_API_AUTH_HEADER,
  getDesktopApiAuthToken,
} from '@/shared/desktop/apiAuth'

export async function apiFetch(
  input: RequestInfo | URL,
  init: RequestInit = {}
): Promise<Response> {
  const desktopApiAuthToken = await getDesktopApiAuthToken()
  if (!desktopApiAuthToken) {
    return fetch(input, init)
  }

  const headers = new Headers(init.headers)
  headers.set(DESKTOP_API_AUTH_HEADER, desktopApiAuthToken)

  return fetch(input, {
    ...init,
    headers,
  })
}
