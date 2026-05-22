// @vitest-environment jsdom

import { beforeEach, describe, expect, it } from 'vitest'

import {
  resetNavigationStoreForTests,
  useNavigationStore,
} from './navigationStore'

describe('navigationStore', () => {
  beforeEach(() => {
    localStorage.clear()
    resetNavigationStoreForTests()
  })

  it('opens the sidebar on the first toggle from a stale compact state', () => {
    useNavigationStore.setState({
      sidebarMode: 'compact',
      sidebarExpanded: true,
    })

    useNavigationStore.getState().toggleSidebar()

    expect(useNavigationStore.getState().sidebarMode).toBe('full')
    expect(useNavigationStore.getState().sidebarExpanded).toBe(true)
  })

  it('rehydrates persisted compact mode with a consistent expanded flag', async () => {
    localStorage.setItem(
      'navigation-storage',
      JSON.stringify({
        state: { sidebarMode: 'compact' },
        version: 2,
      }),
    )

    await useNavigationStore.persist.rehydrate()

    expect(useNavigationStore.getState().sidebarMode).toBe('compact')
    expect(useNavigationStore.getState().sidebarExpanded).toBe(false)
  })
})
