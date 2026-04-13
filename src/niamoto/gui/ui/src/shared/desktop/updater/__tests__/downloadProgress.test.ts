import { describe, expect, it } from 'vitest'
import {
  createInitialDownloadProgressState,
  reduceDownloadProgressEvent,
} from '../downloadProgress'

describe('downloadProgress', () => {
  it('keeps an indeterminate label when content length is unknown', () => {
    let state = createInitialDownloadProgressState()

    state = reduceDownloadProgressEvent(state, { event: 'Started', data: {} }, { isLinux: false, isWindows: false })
    expect(state.progress).toBeUndefined()
    expect(state.label).not.toContain('0%')

    state = reduceDownloadProgressEvent(
      state,
      { event: 'Progress', data: { chunkLength: 1536 } },
      { isLinux: false, isWindows: false }
    )

    expect(state.progress).toBeUndefined()
    expect(state.label).toContain('1.5 KB')
  })

  it('computes percentage progress when total size is known', () => {
    let state = createInitialDownloadProgressState()

    state = reduceDownloadProgressEvent(
      state,
      { event: 'Started', data: { contentLength: 400 } },
      { isLinux: false, isWindows: false }
    )
    state = reduceDownloadProgressEvent(
      state,
      { event: 'Progress', data: { chunkLength: 100 } },
      { isLinux: false, isWindows: false }
    )

    expect(state.progress).toBe(25)
    expect(state.label).toContain('25%')
  })

  it('avoids a misleading 0% label when linux may be waiting on system auth', () => {
    const state = reduceDownloadProgressEvent(
      createInitialDownloadProgressState(),
      { event: 'Started', data: { contentLength: 400 } },
      { isLinux: true, isWindows: false }
    )

    expect(state.progress).toBeUndefined()
    expect(state.label).toContain('authentification système')
    expect(state.label).not.toContain('0%')
  })

  it('avoids percentage progress on windows because the native installer takes over', () => {
    let state = createInitialDownloadProgressState()

    state = reduceDownloadProgressEvent(
      state,
      { event: 'Started', data: { contentLength: 400 } },
      { isLinux: false, isWindows: true }
    )
    expect(state.progress).toBeUndefined()
    expect(state.label).toContain('programme d’installation Windows')
    expect(state.label).not.toContain('0%')

    state = reduceDownloadProgressEvent(
      state,
      { event: 'Progress', data: { chunkLength: 100 } },
      { isLinux: false, isWindows: true }
    )
    expect(state.progress).toBeUndefined()
    expect(state.label).toBe('Téléchargement de la mise à jour...')
  })

  it('switches to an installation label after download completion on linux', () => {
    let state = createInitialDownloadProgressState()

    state = reduceDownloadProgressEvent(
      state,
      { event: 'Finished' },
      { isLinux: true, isWindows: false }
    )

    expect(state.status).toBe('installing')
    expect(state.label).toContain('Validation système')
  })

  it('switches to a native installer label after download completion on windows', () => {
    const state = reduceDownloadProgressEvent(
      createInitialDownloadProgressState(),
      { event: 'Finished' },
      { isLinux: false, isWindows: true }
    )

    expect(state.status).toBe('installing')
    expect(state.progress).toBeUndefined()
    expect(state.label).toContain('programme d’installation Windows')
  })
})
