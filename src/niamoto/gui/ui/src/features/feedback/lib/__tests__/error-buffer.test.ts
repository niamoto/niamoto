import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

// We need to test the module's side effects, so we use dynamic import
// and reset the module between tests.

describe('error-buffer', () => {
  let initErrorBuffer: () => void
  let getRecentErrors: () => Array<{ message: string; stack?: string; timestamp: string }>
  let originalConsoleError: typeof console.error

  beforeEach(async () => {
    originalConsoleError = console.error
    // Clear module cache for fresh buffer each test
    vi.resetModules()
    const mod = await import('../error-buffer')
    initErrorBuffer = mod.initErrorBuffer
    getRecentErrors = mod.getRecentErrors
  })

  afterEach(() => {
    console.error = originalConsoleError
    vi.restoreAllMocks()
  })

  it('captures console.error calls after init', () => {
    initErrorBuffer()
    console.error('test error message')
    const errors = getRecentErrors()
    expect(errors).toHaveLength(1)
    expect(errors[0].message).toBe('test error message')
    expect(errors[0].timestamp).toBeTruthy()
  })

  it('captures multiple arguments', () => {
    initErrorBuffer()
    console.error('error:', 42, 'details')
    const errors = getRecentErrors()
    expect(errors[0].message).toBe('error: 42 details')
  })

  it('maintains circular buffer of max 10 entries', () => {
    initErrorBuffer()
    for (let i = 0; i < 15; i++) {
      console.error(`error-${i}`)
    }
    const errors = getRecentErrors()
    expect(errors).toHaveLength(10)
    expect(errors[0].message).toBe('error-5')
    expect(errors[9].message).toBe('error-14')
  })

  it('returns a copy of the buffer', () => {
    initErrorBuffer()
    console.error('test')
    const a = getRecentErrors()
    const b = getRecentErrors()
    expect(a).not.toBe(b)
    expect(a).toEqual(b)
  })

  it('returns empty array before any errors', () => {
    initErrorBuffer()
    expect(getRecentErrors()).toEqual([])
  })
})
