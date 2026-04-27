import { beforeEach, describe, expect, it, vi } from 'vitest'

const apiGetSpy = vi.hoisted(() => vi.fn())
const getApiErrorMessageSpy = vi.hoisted(() => vi.fn())

vi.mock('@/shared/lib/api/client', () => ({
  apiClient: {
    get: apiGetSpy,
  },
}))

vi.mock('@/shared/lib/api/errors', () => ({
  getApiErrorMessage: getApiErrorMessageSpy,
}))

import { getSpatialMapInspection, getSpatialMapRenderUrl } from './spatial-map'

describe('spatial map API', () => {
  beforeEach(() => {
    apiGetSpy.mockReset()
    getApiErrorMessageSpy.mockReset()
  })

  it('loads spatial map inspection with encoded parameters', async () => {
    const payload = {
      reference_name: 'shape layers',
      table_name: 'entity_shapes',
      is_mappable: true,
    }
    apiGetSpy.mockResolvedValue({ data: payload })

    const result = await getSpatialMapInspection('shape layers', {
      limit: 0,
      offset: 250,
      layer: 'Protected Areas',
    })

    expect(result).toBe(payload)
    expect(apiGetSpy).toHaveBeenCalledWith(
      '/stats/spatial-map/shape%20layers?limit=0&offset=250&layer=Protected+Areas'
    )
  })

  it('wraps spatial map inspection errors with the shared API message', async () => {
    apiGetSpy.mockRejectedValue(new Error('boom'))
    getApiErrorMessageSpy.mockReturnValue('Spatial map failed')

    await expect(getSpatialMapInspection('shapes')).rejects.toThrow('Spatial map failed')
  })

  it('builds render URLs without fetching all layers implicitly', () => {
    expect(
      getSpatialMapRenderUrl('shape layers', {
        limit: 1000,
        layer: 'Protected Areas',
      })
    ).toBe('/api/stats/spatial-map/shape%20layers/render?limit=1000&layer=Protected+Areas')
  })
})
