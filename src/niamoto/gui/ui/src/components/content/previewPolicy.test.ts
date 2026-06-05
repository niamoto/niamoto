import { describe, expect, it } from 'vitest'

import {
  resolveCollectionsPreviewMode,
  shouldAutoRefreshCollectionsDetailPreview,
} from './previewPolicy'

describe('previewPolicy', () => {
  it('uses thumbnails by default', () => {
    expect(resolveCollectionsPreviewMode()).toBe('thumbnail')
  })

  it('forces previews off during drag operations', () => {
    expect(
      resolveCollectionsPreviewMode({
        isDragging: true,
      }),
    ).toBe('off')
  })

  it('keeps thumbnails enabled when not dragging', () => {
    expect(
      resolveCollectionsPreviewMode({
        isDragging: false,
      }),
    ).toBe('thumbnail')
  })

  it('always auto-refreshes detail previews', () => {
    expect(shouldAutoRefreshCollectionsDetailPreview()).toBe(true)
  })
})
