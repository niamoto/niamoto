import { describe, expect, it, vi } from 'vitest'

import {
  normalizeCollectionsPreviewPreference,
  readStoredCollectionsPreviewPreference,
  resolveCollectionsPreviewMode,
  shouldAutoRefreshCollectionsDetailPreview,
  writeStoredCollectionsPreviewPreference,
} from './previewPolicy'

describe('previewPolicy', () => {
  it('normalizes stored preview preferences', () => {
    expect(normalizeCollectionsPreviewPreference('off')).toBe('off')
    expect(normalizeCollectionsPreviewPreference('focused')).toBe('focused')
    expect(normalizeCollectionsPreviewPreference('thumbnail')).toBe('thumbnail')
    expect(normalizeCollectionsPreviewPreference('auto')).toBe('focused')
    expect(normalizeCollectionsPreviewPreference('weird')).toBe('focused')
    expect(normalizeCollectionsPreviewPreference(null)).toBe('focused')
  })

  it('forces previews off during drag operations', () => {
    expect(
      resolveCollectionsPreviewMode({
        preference: 'thumbnail',
        isDragging: true,
      }),
    ).toBe('off')
  })

  it('uses the explicit preference when not dragging', () => {
    expect(
      resolveCollectionsPreviewMode({
        preference: 'focused',
        isDragging: false,
      }),
    ).toBe('focused')
    expect(
      resolveCollectionsPreviewMode({
        preference: 'thumbnail',
        isDragging: false,
      }),
    ).toBe('thumbnail')
  })

  it('auto-refreshes detail previews only when thumbnails are enabled', () => {
    expect(shouldAutoRefreshCollectionsDetailPreview('off')).toBe(false)
    expect(shouldAutoRefreshCollectionsDetailPreview('focused')).toBe(false)
    expect(shouldAutoRefreshCollectionsDetailPreview('thumbnail')).toBe(true)
  })

  it('reads and writes the stored preference', () => {
    const storage = {
      getItem: vi.fn().mockReturnValue('focused'),
      setItem: vi.fn(),
    }

    expect(readStoredCollectionsPreviewPreference(storage)).toBe('focused')

    writeStoredCollectionsPreviewPreference('thumbnail', storage)
    expect(storage.setItem).toHaveBeenCalledWith(
      'niamoto.collectionsPreviewPreference',
      'thumbnail',
    )
  })
})
