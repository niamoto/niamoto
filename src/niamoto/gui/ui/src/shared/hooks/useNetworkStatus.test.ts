import { describe, expect, it } from 'vitest'
import {
  applyConnectivityResult,
  getIsOffline,
  type NetworkStatus,
} from './useNetworkStatus'

function makeStatus(partial?: Partial<NetworkStatus>): NetworkStatus {
  return {
    isOnline: true,
    isInternetAvailable: null,
    isChecking: false,
    lastChecked: null,
    ...partial,
  }
}

describe('useNetworkStatus helpers', () => {
  it('does not report offline when backend connectivity is confirmed', () => {
    expect(
      getIsOffline(
        makeStatus({
          isOnline: false,
          isInternetAvailable: true,
        })
      )
    ).toBe(false)
  })

  it('reports offline when connectivity is explicitly unavailable', () => {
    expect(
      getIsOffline(
        makeStatus({
          isOnline: true,
          isInternetAvailable: false,
        })
      )
    ).toBe(true)
  })

  it('heals a stale browser offline flag after a successful backend probe', () => {
    const next = applyConnectivityResult(
      makeStatus({
        isOnline: false,
        isInternetAvailable: null,
        isChecking: true,
      }),
      true,
      new Date('2026-04-13T08:00:00.000Z')
    )

    expect(next.isOnline).toBe(true)
    expect(next.isInternetAvailable).toBe(true)
    expect(next.isChecking).toBe(false)
  })
})
