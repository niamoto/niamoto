import { describe, expect, it } from 'vitest'

import { extractPreviewRenderMs } from './collectionsPerf'

describe('collectionsPerf', () => {
  it('extracts render timing from the explicit preview header', () => {
    const headers = new Headers({
      'x-preview-render-ms': '18.4',
      'server-timing': 'preview;dur=17.2',
    })

    expect(extractPreviewRenderMs(headers)).toBe(18.4)
  })

  it('falls back to the Server-Timing header when needed', () => {
    const headers = new Headers({
      'server-timing': 'preview;dur=42.6, total;dur=55.0',
    })

    expect(extractPreviewRenderMs(headers)).toBe(42.6)
  })

  it('returns null when no preview timing header is present', () => {
    expect(extractPreviewRenderMs(new Headers())).toBeNull()
    expect(extractPreviewRenderMs(undefined)).toBeNull()
  })
})
