import { describe, expect, it, vi } from 'vitest'

import type { PreviewDescriptor } from './types'
import { requestInlinePreview } from './usePreviewFrame'
import { apiFetch } from '@/shared/lib/api/fetch'

vi.mock('@/shared/lib/api/fetch', () => ({
  apiFetch: vi.fn().mockResolvedValue(new Response('<html></html>')),
}))

describe('requestInlinePreview', () => {
  it('uses apiFetch so desktop auth headers are applied by the shared wrapper', async () => {
    const descriptor: PreviewDescriptor = {
      templateId: 'bar_plot',
      groupBy: 'plots',
      source: 'plot_measurements',
      entityId: '42',
      mode: 'full',
      inline: {
        transformer_plugin: 'direct_attribute',
        transformer_params: { field: 'name' },
        widget_plugin: 'table_view',
        widget_params: { max_rows: 5 },
      },
    }
    const signal = new AbortController().signal

    await requestInlinePreview(descriptor, signal)

    expect(apiFetch).toHaveBeenCalledWith('/api/preview', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        template_id: 'bar_plot',
        group_by: 'plots',
        source: 'plot_measurements',
        entity_id: '42',
        mode: 'full',
        inline: descriptor.inline,
      }),
      signal,
    })
  })
})
