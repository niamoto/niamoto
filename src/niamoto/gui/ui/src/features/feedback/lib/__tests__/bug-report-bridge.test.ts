import { beforeEach, describe, expect, it, vi } from 'vitest'

describe('bug-report-bridge', () => {
  beforeEach(() => {
    vi.resetModules()
  })

  it('notifies subscribed listeners with the provided draft', async () => {
    const mod = await import('../bug-report-bridge')
    const listener = vi.fn()

    const unsubscribe = mod.subscribeToBugReportRequests(listener)
    mod.requestBugReport({
      title: 'Server error on /api/stats/summary',
      description: 'Catalog error',
    })

    expect(listener).toHaveBeenCalledWith({
      title: 'Server error on /api/stats/summary',
      description: 'Catalog error',
    })

    unsubscribe()
  })

  it('stops notifying a listener after unsubscribe', async () => {
    const mod = await import('../bug-report-bridge')
    const listener = vi.fn()

    const unsubscribe = mod.subscribeToBugReportRequests(listener)
    unsubscribe()
    mod.requestBugReport({ title: 'Crash in WidgetPanel' })

    expect(listener).not.toHaveBeenCalled()
  })
})
