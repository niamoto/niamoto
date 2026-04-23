import { describe, expect, it } from 'vitest'

import { getApiErrorMessage } from './errors'

describe('getApiErrorMessage', () => {
  it('prefers API detail from axios-style errors', () => {
    const error = {
      isAxiosError: true,
      response: { data: { detail: 'Detailed backend failure' } },
      message: 'Fallback axios message',
    }

    expect(getApiErrorMessage(error, 'Fallback')).toBe('Detailed backend failure')
  })

  it('falls back to the axios error message when detail is missing', () => {
    const error = {
      isAxiosError: true,
      response: { data: {} },
      message: 'Network timeout',
    }

    expect(getApiErrorMessage(error, 'Fallback')).toBe('Network timeout')
  })

  it('uses generic Error messages before the provided fallback', () => {
    expect(getApiErrorMessage(new Error('Boom'), 'Fallback')).toBe('Boom')
  })

  it('returns the provided fallback for unknown payloads', () => {
    expect(getApiErrorMessage({ reason: 'opaque' }, 'Fallback')).toBe('Fallback')
  })
})
