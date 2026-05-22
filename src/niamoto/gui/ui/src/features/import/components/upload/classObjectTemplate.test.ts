// @vitest-environment jsdom

import { afterEach, describe, expect, it, vi } from 'vitest'

const invokeMock = vi.hoisted(() => vi.fn())
const isTauriMock = vi.hoisted(() => vi.fn())

vi.mock('@tauri-apps/api/core', () => ({
  invoke: invokeMock,
  isTauri: isTauriMock,
}))

describe('CSV template downloads', () => {
  afterEach(() => {
    vi.clearAllMocks()
    vi.restoreAllMocks()
    document.body.innerHTML = ''
  })

  it('uses the native save dialog in Tauri desktop mode', async () => {
    isTauriMock.mockReturnValue(true)
    invokeMock.mockResolvedValue(true)

    const { downloadCsvTemplate } = await import('./classObjectTemplate')
    await downloadCsvTemplate('reference')

    expect(invokeMock).toHaveBeenCalledWith('save_text_file', {
      filename: 'reference-table-template.csv',
      contents: expect.stringContaining('id,name,description\n'),
    })
  })

  it('falls back to browser download outside Tauri', async () => {
    isTauriMock.mockReturnValue(false)
    const objectUrl = 'blob:template'
    const createObjectURL = vi.spyOn(URL, 'createObjectURL').mockReturnValue(objectUrl)
    const revokeObjectURL = vi.spyOn(URL, 'revokeObjectURL').mockImplementation(() => {})
    const clickMock = vi.fn()
    const originalCreateElement = document.createElement.bind(document)

    vi.spyOn(document, 'createElement').mockImplementation((tagName) => {
      const element = originalCreateElement(tagName)
      if (tagName === 'a') {
        element.click = clickMock
      }
      return element
    })
    vi.useFakeTimers()

    const { downloadCsvTemplate } = await import('./classObjectTemplate')
    await downloadCsvTemplate('occurrences')

    expect(createObjectURL).toHaveBeenCalledTimes(1)
    expect(clickMock).toHaveBeenCalledTimes(1)

    vi.runAllTimers()
    expect(revokeObjectURL).toHaveBeenCalledWith(objectUrl)
    vi.useRealTimers()
  })
})
