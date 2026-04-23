import { describe, expect, it, vi } from 'vitest'

import {
  classifyCollectionsPerformanceTier,
  getCollectionsHardwareConcurrency,
  normalizeCollectionsPreviewPreference,
  readStoredCollectionsPreviewPreference,
  resolveCollectionsPreviewMode,
  resolveDefaultCollectionsPreviewMode,
  shouldAutoRefreshCollectionsDetailPreview,
  writeStoredCollectionsPreviewPreference,
} from './previewPolicy'

describe('previewPolicy', () => {
  it('normalizes stored preview preferences', () => {
    expect(normalizeCollectionsPreviewPreference('off')).toBe('off')
    expect(normalizeCollectionsPreviewPreference('focused')).toBe('focused')
    expect(normalizeCollectionsPreviewPreference('thumbnail')).toBe('thumbnail')
    expect(normalizeCollectionsPreviewPreference('weird')).toBe('auto')
    expect(normalizeCollectionsPreviewPreference(null)).toBe('auto')
  })

  it('classifies low-power contexts conservatively', () => {
    expect(
      classifyCollectionsPerformanceTier({
        widgetCount: 6,
        hardwareConcurrency: 4,
      }),
    ).toBe('low')
    expect(
      classifyCollectionsPerformanceTier({
        widgetCount: 10,
        hardwareConcurrency: 6,
      }),
    ).toBe('low')
    expect(
      classifyCollectionsPerformanceTier({
        widgetCount: 18,
        hardwareConcurrency: 12,
      }),
    ).toBe('low')
  })

  it('defaults to thumbnail only when the context is light enough', () => {
    expect(
      resolveDefaultCollectionsPreviewMode({
        widgetCount: 4,
        hardwareConcurrency: 8,
      }),
    ).toBe('thumbnail')
    expect(
      resolveDefaultCollectionsPreviewMode({
        widgetCount: 12,
        hardwareConcurrency: 8,
      }),
    ).toBe('focused')
    expect(
      resolveDefaultCollectionsPreviewMode({
        widgetCount: 8,
        hardwareConcurrency: 4,
      }),
    ).toBe('focused')
  })

  it('forces previews off during drag operations', () => {
    expect(
      resolveCollectionsPreviewMode({
        preference: 'thumbnail',
        widgetCount: 5,
        hardwareConcurrency: 8,
        isDragging: true,
      }),
    ).toBe('off')
  })

  it('disables detail auto-refresh in conservative modes', () => {
    expect(
      shouldAutoRefreshCollectionsDetailPreview({
        preference: 'auto',
        widgetCount: 12,
        hardwareConcurrency: 4,
      }),
    ).toBe(false)
    expect(
      shouldAutoRefreshCollectionsDetailPreview({
        preference: 'thumbnail',
        widgetCount: 5,
        hardwareConcurrency: 8,
      }),
    ).toBe(true)
  })

  it('reads and writes the stored preference', () => {
    const storage = {
      getItem: vi.fn().mockReturnValue('focused'),
      setItem: vi.fn(),
      removeItem: vi.fn(),
    }

    expect(readStoredCollectionsPreviewPreference(storage)).toBe('focused')

    writeStoredCollectionsPreviewPreference('thumbnail', storage)
    expect(storage.setItem).toHaveBeenCalledWith(
      'niamoto.collectionsPreviewPreference',
      'thumbnail',
    )

    writeStoredCollectionsPreviewPreference('auto', storage)
    expect(storage.removeItem).toHaveBeenCalledWith(
      'niamoto.collectionsPreviewPreference',
    )
  })

  it('normalizes hardware concurrency safely', () => {
    expect(getCollectionsHardwareConcurrency({ hardwareConcurrency: 4 })).toBe(4)
    expect(getCollectionsHardwareConcurrency({ hardwareConcurrency: 0 })).toBeNull()
    expect(
      getCollectionsHardwareConcurrency({} as Pick<Navigator, 'hardwareConcurrency'>),
    ).toBeNull()
  })
})
