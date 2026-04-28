// @vitest-environment jsdom

import { act, type ReactNode } from 'react'
import { createRoot } from 'react-dom/client'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { FileUploadZone } from './FileUploadZone'

globalThis.IS_REACT_ACT_ENVIRONMENT = true

const uploadFilesMock = vi.hoisted(() => vi.fn())

vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string, options?: { count?: number }) =>
      options?.count === undefined ? key : `${key}:${options.count}`,
  }),
}))

vi.mock('@/features/import/api/upload', () => ({
  uploadFiles: uploadFilesMock,
}))

function createHarness() {
  const container = document.createElement('div')
  document.body.appendChild(container)
  const root = createRoot(container)

  return {
    container,
    async render(element: ReactNode) {
      await act(async () => {
        root.render(element)
        await Promise.resolve()
      })
    },
    async unmount() {
      await act(async () => {
        root.unmount()
      })
      container.remove()
    },
  }
}

async function selectFiles(input: HTMLInputElement, files: File[]) {
  Object.defineProperty(input, 'files', {
    value: files,
    configurable: true,
  })

  await act(async () => {
    input.dispatchEvent(new Event('change', { bubbles: true }))
    await Promise.resolve()
  })
}

describe('FileUploadZone', () => {
  afterEach(() => {
    vi.clearAllMocks()
    document.body.innerHTML = ''
  })

  it('lets users add files in multiple selections before uploading', async () => {
    const harness = createHarness()
    const onFilesReady = vi.fn()
    const taxonsFile = new File(['taxons'], 'taxons.csv', { type: 'text/csv' })
    const plotsFile = new File(['plots'], 'plots.gpkg')

    uploadFilesMock.mockResolvedValue({
      success: true,
      uploaded_files: [
        {
          filename: 'taxons.csv',
          path: 'imports/taxons.csv',
          size: 6,
          size_mb: 0.01,
          type: 'csv',
          category: 'csv',
        },
        {
          filename: 'plots.gpkg',
          path: 'imports/plots.gpkg',
          size: 5,
          size_mb: 0.01,
          type: 'gpkg',
          category: 'gpkg',
        },
      ],
      uploaded_count: 2,
      existing_files: [],
      existing_count: 0,
      errors: [],
    })

    await harness.render(<FileUploadZone onFilesReady={onFilesReady} />)

    const firstInput = harness.container.querySelector<HTMLInputElement>('input[type="file"]')
    expect(firstInput).toBeTruthy()
    await selectFiles(firstInput!, [taxonsFile])

    expect(harness.container.textContent).toContain('taxons.csv')
    expect(harness.container.textContent).toContain('upload.addMore')

    const secondInput = harness.container.querySelector<HTMLInputElement>('input[type="file"]')
    expect(secondInput).toBeTruthy()
    await selectFiles(secondInput!, [plotsFile])

    expect(harness.container.textContent).toContain('plots.gpkg')

    const uploadButton = Array.from(harness.container.querySelectorAll('button')).find(
      (button) => button.textContent?.includes('upload.uploadSelected')
    )
    expect(uploadButton).toBeTruthy()

    await act(async () => {
      uploadButton?.click()
      await Promise.resolve()
    })

    expect(uploadFilesMock).toHaveBeenCalledWith([taxonsFile, plotsFile], false)
    expect(onFilesReady).toHaveBeenCalledWith(
      expect.any(Array),
      ['imports/taxons.csv', 'imports/plots.gpkg']
    )

    await harness.unmount()
  })
})
