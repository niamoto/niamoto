const WINDOWS_RESERVED_PROJECT_NAMES = new Set([
  'CON',
  'PRN',
  'AUX',
  'NUL',
  'COM1',
  'COM2',
  'COM3',
  'COM4',
  'COM5',
  'COM6',
  'COM7',
  'COM8',
  'COM9',
  'LPT1',
  'LPT2',
  'LPT3',
  'LPT4',
  'LPT5',
  'LPT6',
  'LPT7',
  'LPT8',
  'LPT9',
])

export function getProjectNameValidationError(name: string): string | null {
  const trimmed = name.trim()

  if (!trimmed) {
    return 'name_required'
  }

  if (trimmed !== name) {
    return 'whitespace_edge'
  }

  if (trimmed === '.' || trimmed === '..') {
    return 'invalid_name'
  }

  if (trimmed.endsWith('.') || trimmed.endsWith(' ')) {
    return 'trailing_dot_or_space'
  }

  if ([...trimmed].some((char) => {
    const codePoint = char.codePointAt(0)
    return codePoint !== undefined && (codePoint <= 0x1f || codePoint === 0x7f)
  })) {
    return 'unsupported_characters'
  }

  if (/[<>:"/\\|?*]/.test(trimmed)) {
    return 'unsupported_characters'
  }

  const windowsStem = trimmed.split('.')[0]?.toUpperCase() ?? trimmed.toUpperCase()
  if (WINDOWS_RESERVED_PROJECT_NAMES.has(windowsStem)) {
    return 'reserved_name'
  }

  return null
}
