// @vitest-environment jsdom

import { act, useEffect } from 'react'
import { createRoot, type Root } from 'react-dom/client'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { useProjectSwitcher, type ProjectEntry } from './useProjectSwitcher'

globalThis.IS_REACT_ACT_ENVIRONMENT = true

const invokeDesktopSpy = vi.hoisted(() => vi.fn())
const reloadDesktopProjectSpy = vi.hoisted(() => vi.fn())
const openDesktopProjectFromHomeSpy = vi.hoisted(() => vi.fn())
const getDesktopShellSpy = vi.hoisted(() => vi.fn())

vi.mock('@/shared/desktop/bridge', () => ({
  invokeDesktop: invokeDesktopSpy,
}))

vi.mock('@/shared/desktop/projectNavigation', () => ({
  openDesktopProjectFromHome: openDesktopProjectFromHomeSpy,
}))

vi.mock('@/shared/desktop/projectReload', () => ({
  reloadDesktopProject: reloadDesktopProjectSpy,
}))

vi.mock('@/shared/desktop/runtime', () => ({
  getDesktopShell: getDesktopShellSpy,
}))

describe('useProjectSwitcher', () => {
  let container: HTMLDivElement
  let root: Root
  beforeEach(() => {
    getDesktopShellSpy.mockReturnValue({ kind: 'tauri' })
    reloadDesktopProjectSpy.mockResolvedValue({ state: 'loaded' })
    invokeDesktopSpy.mockImplementation(async (cmd: string) => {
      if (cmd === 'get_current_project') return '/tmp/project-a'
      if (cmd === 'get_recent_projects') {
        return [
          {
            path: '/tmp/project-a',
            name: 'project-a',
            last_accessed: '2026-06-02T12:00:00Z',
          },
        ] satisfies ProjectEntry[]
      }
      if (cmd === 'validate_recent_projects') return []
      if (cmd === 'validate_project') return true
      if (cmd === 'set_current_project') return null
      throw new Error(`Unexpected desktop command: ${cmd}`)
    })

    container = document.createElement('div')
    document.body.appendChild(container)
    root = createRoot(container)
  })

  afterEach(() => {
    root.unmount()
    container.remove()
    vi.clearAllMocks()
  })

  it('opens switched projects from the app home route before route memory restores them', async () => {
    let switchProject: ReturnType<typeof useProjectSwitcher>['switchProject'] | null = null

    function Probe() {
      const switcher = useProjectSwitcher()

      useEffect(() => {
        switchProject = switcher.switchProject
      }, [switcher.switchProject])

      return null
    }

    await act(async () => {
      root.render(<Probe />)
      await Promise.resolve()
      await Promise.resolve()
    })

    await act(async () => {
      await switchProject?.('/tmp/project-b')
    })

    expect(invokeDesktopSpy).toHaveBeenCalledWith('set_current_project', {
      path: '/tmp/project-b',
    })
    expect(openDesktopProjectFromHomeSpy).toHaveBeenCalledWith('/tmp/project-b')
  })
})
