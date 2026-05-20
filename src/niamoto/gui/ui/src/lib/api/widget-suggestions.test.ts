import { beforeEach, describe, expect, it, vi } from 'vitest'

import { apiClient } from '@/shared/lib/api/client'
import { getCombinedWidgetSuggestions, getSemanticGroups } from './widget-suggestions'

vi.mock('@/shared/lib/api/client', () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
  },
}))

const getMock = vi.mocked(apiClient.get)
const postMock = vi.mocked(apiClient.post)

describe('getCombinedWidgetSuggestions', () => {
  beforeEach(() => {
    postMock.mockReset()
    postMock.mockResolvedValue({ data: { suggestions: [], semantic_groups: [] } })
  })

  it('omits source_name when no source is selected', async () => {
    await getCombinedWidgetSuggestions('plots', ['plot_id', 'plot_name'])

    expect(postMock).toHaveBeenCalledWith(
      '/templates/plots/combined-suggestions',
      {
        selected_fields: ['plot_id', 'plot_name'],
      }
    )
  })

  it('sends source_name when the caller selected a source', async () => {
    await getCombinedWidgetSuggestions('plots', ['plot_id', 'plot_name'], 'plot_measurements')

    expect(postMock).toHaveBeenCalledWith(
      '/templates/plots/combined-suggestions',
      {
        selected_fields: ['plot_id', 'plot_name'],
        source_name: 'plot_measurements',
      }
    )
  })
})

describe('getSemanticGroups', () => {
  beforeEach(() => {
    getMock.mockReset()
    getMock.mockResolvedValue({ data: { groups: [] } })
  })

  it('omits entity when no source is selected', async () => {
    await getSemanticGroups('plots')

    expect(apiClient.get).toHaveBeenCalledWith('/templates/plots/semantic-groups')
  })

  it('sends entity when the caller selected a source', async () => {
    await getSemanticGroups('plots', 'plot_measurements')

    expect(apiClient.get).toHaveBeenCalledWith(
      '/templates/plots/semantic-groups?entity=plot_measurements'
    )
  })
})
