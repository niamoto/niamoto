// @vitest-environment jsdom

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { openDesktopProjectFromHome } from './projectNavigation'

const markManualProjectOpenSpy = vi.hoisted(() => vi.fn())

vi.mock('./projectLaunchIntent', () => ({
  markManualProjectOpen: markManualProjectOpenSpy,
}))

describe('projectNavigation', () => {
  let originalLocation: Location
  const replaceSpy = vi.fn()

  beforeEach(() => {
    originalLocation = window.location
    Object.defineProperty(window, 'location', {
      configurable: true,
      value: {
        ...originalLocation,
        replace: replaceSpy,
      },
    })
  })

  afterEach(() => {
    Object.defineProperty(window, 'location', {
      configurable: true,
      value: originalLocation,
    })
    vi.clearAllMocks()
  })

  it('opens a desktop project from the app home route', () => {
    openDesktopProjectFromHome('/tmp/project-b')

    expect(markManualProjectOpenSpy).toHaveBeenCalledWith('/tmp/project-b')
    expect(replaceSpy).toHaveBeenCalledWith('/')
  })
})
