import { describe, expect, it } from 'vitest'
import {
  createInitialDownloadProgressState,
  reduceDownloadProgressEvent,
} from '../downloadProgress'

describe('downloadProgress', () => {
  it('keeps an indeterminate label when content length is unknown', () => {
    let state = createInitialDownloadProgressState()

    state = reduceDownloadProgressEvent(state, { event: 'Started', data: {} }, { isLinux: false })
    expect(state.progress).toBeUndefined()
    expect(state.label).not.toContain('0%')

    state = reduceDownloadProgressEvent(
      state,
      { event: 'Progress', data: { chunkLength: 1536 } },
      { isLinux: false }
    )

    expect(state.progress).toBeUndefined()
    expect(state.label).toContain('1.5 KB')
  })

  it('computes percentage progress when total size is known', () => {
    let state = createInitialDownloadProgressState()

    state = reduceDownloadProgressEvent(
      state,
      { event: 'Started', data: { contentLength: 400 } },
      { isLinux: false }
    )
    state = reduceDownloadProgressEvent(
      state,
      { event: 'Progress', data: { chunkLength: 100 } },
      { isLinux: false }
    )

    expect(state.progress).toBe(25)
    expect(state.label).toContain('25%')
  })

  it('avoids a misleading 0% label when linux may be waiting on system auth', () => {
    const state = reduceDownloadProgressEvent(
      createInitialDownloadProgressState(),
      { event: 'Started', data: { contentLength: 400 } },
      { isLinux: true }
    )

    expect(state.progress).toBeUndefined()
    expect(state.label).toContain('authentification système')
    expect(state.label).not.toContain('0%')
  })

  it('switches to an installation label after download completion on linux', () => {
    let state = createInitialDownloadProgressState()

    state = reduceDownloadProgressEvent(
      state,
      { event: 'Finished' },
      { isLinux: true }
    )

    expect(state.status).toBe('installing')
    expect(state.label).toContain('Validation système')
  })
})
