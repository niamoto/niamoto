/**
 * @vitest-environment jsdom
 */
import { beforeEach, describe, expect, it, vi } from 'vitest'

const fetchMock = vi.fn()

const payload = {
  type: 'bug' as const,
  title: 'Broken feedback',
  description: 'The report button should stay local.',
  context: {
    app_version: '0.0.0',
    os: 'linux',
    current_page: '/settings',
    runtime_mode: 'desktop',
    theme: 'forest (light)',
    language: 'fr',
    window_size: '1280x900',
    timestamp: '2026-06-06T10:00:00.000Z',
  },
}

describe('feedback-api', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
    vi.resetModules()
    vi.unstubAllEnvs()
    fetchMock.mockReset()
    vi.stubGlobal('fetch', fetchMock)
  })

  it('downloads a GitHub-ready Markdown report without calling a remote feedback proxy', async () => {
    const { getDownloadedBlob, createObjectURL } = mockDownload()

    const mod = await import('../feedback-api')

    const result = await mod.sendFeedback({ payload })

    expect(fetchMock).not.toHaveBeenCalled()
    expect(result).toMatchObject({
      success: true,
      report_downloaded: true,
      report_format: 'markdown',
      screenshot_included: false,
    })
    expect(result.report_filename).toMatch(/^niamoto-feedback-.*broken-feedback\.md$/)
    expect(result.github_issue_url).toMatch(/^https:\/\/github\.com\/niamoto\/niamoto\/issues\/new\?/)
    expect(createObjectURL).toHaveBeenCalledWith(expect.any(Blob))

    const markdown = await getDownloadedBlob().text()
    expect(markdown).toContain('# Broken feedback')
    expect(markdown).toContain('## Description')
    expect(markdown).toContain('The report button should stay local.')
    expect(markdown).toContain('| Page | `/settings` |')
    expect(markdown).toContain('## Technical details')
    expect(markdown).toContain('```json')

    const issueUrl = new URL(result.github_issue_url!)
    expect(issueUrl.searchParams.get('title')).toBe('[Bug] Broken feedback')
    expect(issueUrl.searchParams.get('labels')).toBe('feedback,feedback:bug')
    expect(issueUrl.searchParams.get('body')).toContain('The report button should stay local.')
    expect(issueUrl.searchParams.get('body')).toContain('| Page | `/settings` |')
  })

  it('keeps screenshots in the downloaded Markdown but out of the GitHub issue URL', async () => {
    const screenshot = new Blob(['image-bytes'], { type: 'image/jpeg' })
    const { getDownloadedBlob } = mockDownload()

    const mod = await import('../feedback-api')

    const result = await mod.sendFeedback({ payload, screenshot })

    expect(result.screenshot_included).toBe(true)
    const markdown = await getDownloadedBlob().text()
    expect(markdown).toContain('## Screenshot')
    expect(markdown).toContain('data:image/jpeg;base64,')
    expect(markdown).toContain('Attach the screenshot manually when creating a GitHub issue.')

    const issueUrl = new URL(result.github_issue_url!)
    const issueBody = issueUrl.searchParams.get('body') ?? ''
    expect(issueBody).toContain('A screenshot was included in the downloaded report.')
    expect(issueBody).not.toContain('data:image/jpeg;base64,')
  })
})

function mockDownload(): {
  getDownloadedBlob: () => Blob
  createObjectURL: ReturnType<typeof vi.fn>
} {
  const anchor = document.createElement('a')
  vi.spyOn(anchor, 'click').mockImplementation(() => undefined)
  vi.spyOn(document, 'createElement').mockReturnValue(anchor)

  let downloadedBlob: Blob | null = null
  const createObjectURL = vi.fn((blob: Blob) => {
    downloadedBlob = blob
    return 'blob:feedback-report'
  })

  Object.defineProperty(URL, 'createObjectURL', {
    configurable: true,
    value: createObjectURL,
  })
  Object.defineProperty(URL, 'revokeObjectURL', {
    configurable: true,
    value: vi.fn(),
  })

  return {
    getDownloadedBlob: () => {
      if (!downloadedBlob) {
        throw new Error('No report was downloaded')
      }
      return downloadedBlob
    },
    createObjectURL,
  }
}
