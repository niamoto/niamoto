import { describe, expect, it } from 'vitest'

import { getProjectNameValidationError } from './projectNameValidation'

describe('getProjectNameValidationError', () => {
  it('accepts Unicode project names that the desktop backend allows', () => {
    expect(getProjectNameValidationError('Nouvelle-calédonie')).toBeNull()
    expect(getProjectNameValidationError('Forêt_sèche')).toBeNull()
  })

  it('rejects forbidden filesystem characters', () => {
    expect(getProjectNameValidationError('demo/project')).toBe('unsupported_characters')
    expect(getProjectNameValidationError('demo*project')).toBe('unsupported_characters')
  })

  it('rejects Windows reserved device names', () => {
    expect(getProjectNameValidationError('CON')).toBe('reserved_name')
    expect(getProjectNameValidationError('Lpt1')).toBe('reserved_name')
  })

  it('rejects leading or trailing whitespace', () => {
    expect(getProjectNameValidationError(' demo')).toBe('whitespace_edge')
    expect(getProjectNameValidationError('demo ')).toBe('whitespace_edge')
  })
})
