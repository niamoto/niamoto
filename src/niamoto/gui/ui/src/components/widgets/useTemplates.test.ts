import { beforeEach, describe, expect, it, vi } from 'vitest'

import { fetchSuggestions } from './useTemplates'

describe('fetchSuggestions', () => {
  beforeEach(() => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        json: vi.fn().mockResolvedValue({ suggestions: [], columns_analyzed: 0 }),
      })
    )
  })

  it('omits entity when no source is selected', async () => {
    const signal = new AbortController().signal

    await fetchSuggestions('plots', undefined, signal)

    expect(fetch).toHaveBeenCalledWith('/api/templates/plots/suggestions', { signal })
  })

  it('sends entity when the caller selected a source', async () => {
    const signal = new AbortController().signal

    await fetchSuggestions('plots', 'plot_measurements', signal)

    expect(fetch).toHaveBeenCalledWith(
      '/api/templates/plots/suggestions?entity=plot_measurements',
      { signal }
    )
  })
})
