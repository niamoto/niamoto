// @vitest-environment jsdom

import { act, useState, type ReactElement } from 'react'
import { createRoot } from 'react-dom/client'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { MarkdownContentField } from './MarkdownContentField'

globalThis.IS_REACT_ACT_ENVIRONMENT = true

const useLanguages = vi.hoisted(() => vi.fn())
const useFileContent = vi.hoisted(() => vi.fn())
const useUpdateFileContent = vi.hoisted(() => vi.fn())
const useProjectFiles = vi.hoisted(() => vi.fn())
const useUploadFile = vi.hoisted(() => vi.fn())

const toastSuccess = vi.hoisted(() => vi.fn())
const toastError = vi.hoisted(() => vi.fn())

vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
    i18n: { language: 'fr', resolvedLanguage: 'fr' },
  }),
}))

vi.mock('sonner', () => ({
  toast: {
    success: toastSuccess,
    error: toastError,
  },
}))

vi.mock('@/shared/contexts/useLanguages', () => ({
  useLanguages,
}))

vi.mock('@/shared/hooks/useSiteConfig', () => ({
  useFileContent,
  useUpdateFileContent,
  useProjectFiles,
  useUploadFile,
}))

vi.mock('@/features/site/components/MarkdownEditor', () => ({
  MarkdownEditor: (props: {
    initialContent?: string
    onChange?: (value: string) => void
    readOnly?: boolean
  }) => {
    const [content, setContent] = useState(props.initialContent || '')

    return (
      <div
        data-testid={props.readOnly ? 'markdown-preview' : 'markdown-write'}
        data-content={content}
      >
        <span>{content}</span>
        {!props.readOnly ? (
          <button
            type="button"
            data-testid="markdown-change"
            onClick={() => {
              setContent('Changed draft markdown')
              props.onChange?.('Changed draft markdown')
            }}
          >
            change
          </button>
        ) : null}
      </div>
    )
  },
}))

vi.mock('@/features/site/components/MultilingualMarkdownEditor', () => ({
  MultilingualMarkdownEditor: () => (
    <div data-testid="multilingual-editor">Multilingual editor</div>
  ),
}))

function createHarness() {
  const container = document.createElement('div')
  document.body.appendChild(container)
  const root = createRoot(container)

  return {
    container,
    async render(element: ReactElement) {
      await act(async () => {
        root.render(element)
        await Promise.resolve()
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

describe('MarkdownContentField', () => {
  const mutateAsync = vi.fn()
  const refetchFiles = vi.fn()
  const uploadAsync = vi.fn()

  beforeEach(() => {
    mutateAsync.mockReset()
    refetchFiles.mockReset()
    uploadAsync.mockReset()
    toastSuccess.mockReset()
    toastError.mockReset()

    useLanguages.mockReturnValue({
      languages: ['fr'],
      defaultLang: 'fr',
    })
    useFileContent.mockReturnValue({
      data: { content: 'Initial markdown' },
      error: null,
      isLoading: false,
    })
    useUpdateFileContent.mockReturnValue({
      mutateAsync,
    })
    useProjectFiles.mockReturnValue({
      data: {
        files: [
          {
            path: 'templates/content/about.md',
            name: 'about.md',
            extension: '.md',
          },
        ],
      },
      isLoading: false,
      refetch: refetchFiles,
    })
    useUploadFile.mockReturnValue({
      isPending: false,
      mutateAsync: uploadAsync,
    })
  })

  afterEach(() => {
    vi.clearAllMocks()
    document.body.innerHTML = ''
  })

  it('opens directly in write mode when a single markdown file is selected', async () => {
    const harness = createHarness()

    await harness.render(
      <MarkdownContentField
        baseName="about"
        contentSource="templates/content/about.md"
        onContentSourceChange={vi.fn()}
        variant="authoring"
      />
    )

    const editor = harness.container.querySelector('[data-testid="markdown-write"]')
    expect(editor).not.toBeNull()
    expect(editor?.getAttribute('data-content')).toBe('Initial markdown')
    expect(
      harness.container.querySelector('[data-markdown-field-variant="authoring"]')
    ).not.toBeNull()
    expect(harness.container.textContent).toContain('about.md')

    await harness.unmount()
  })

  it('preserves the current draft when switching between write and source modes', async () => {
    const harness = createHarness()

    await harness.render(
      <MarkdownContentField
        baseName="about"
        contentSource="templates/content/about.md"
        onContentSourceChange={vi.fn()}
      />
    )

    const changeButton = harness.container.querySelector(
      '[data-testid="markdown-change"]'
    ) as HTMLButtonElement | null
    expect(changeButton).not.toBeNull()

    await act(async () => {
      changeButton?.click()
    })

    const sourceButton = harness.container.querySelector(
      'button[aria-label="site:pageEditor.sourceMode"]'
    ) as HTMLButtonElement | null
    expect(sourceButton).not.toBeNull()

    await act(async () => {
      sourceButton?.click()
    })

    expect(harness.container.textContent).toContain('Changed draft markdown')

    const writeButton = harness.container.querySelector(
      'button[aria-label="site:pageEditor.writeMode"]'
    ) as HTMLButtonElement | null
    expect(writeButton).not.toBeNull()

    await act(async () => {
      writeButton?.click()
    })

    expect(
      harness.container
        .querySelector('[data-testid="markdown-write"]')
        ?.getAttribute('data-content')
    ).toBe('Changed draft markdown')

    await harness.unmount()
  })

  it('clears the dirty draft when switching to another source file', async () => {
    const harness = createHarness()
    const onContentSourceChange = vi.fn()

    useFileContent.mockImplementation((path: string | null) => {
      if (path === 'templates/content/terms.md') {
        return {
          data: undefined,
          error: null,
          isLoading: true,
        }
      }

      return {
        data: { content: 'Initial markdown' },
        error: null,
        isLoading: false,
      }
    })

    await harness.render(
      <MarkdownContentField
        baseName="about"
        contentSource="templates/content/about.md"
        onContentSourceChange={onContentSourceChange}
      />
    )

    await act(async () => {
      ;(harness.container.querySelector('[data-testid="markdown-change"]') as HTMLButtonElement).click()
    })

    const dirtySaveButton = Array.from(harness.container.querySelectorAll('button')).find(
      (button) => button.textContent?.includes('site:pageEditor.save')
    ) as HTMLButtonElement | undefined
    expect(dirtySaveButton?.disabled).toBe(false)

    await harness.render(
      <MarkdownContentField
        baseName="about"
        contentSource="templates/content/terms.md"
        onContentSourceChange={onContentSourceChange}
      />
    )

    const saveButton = Array.from(harness.container.querySelectorAll('button')).find(
      (button) => button.textContent?.includes('site:pageEditor.save')
    ) as HTMLButtonElement | undefined

    expect(saveButton?.disabled).toBe(true)
    expect(harness.container.textContent).toContain('terms.md')
    expect(mutateAsync).not.toHaveBeenCalled()

    await harness.unmount()
  })

  it('mounts the write editor with the fetched content after switching to a loading page', async () => {
    const harness = createHarness()
    const onContentSourceChange = vi.fn()
    let termsLoaded = false

    useFileContent.mockImplementation((path: string | null) => {
      if (path === 'templates/content/terms.md') {
        return termsLoaded
          ? {
              data: { content: 'Terms markdown' },
              error: null,
              isLoading: false,
            }
          : {
              data: undefined,
              error: null,
              isLoading: true,
            }
      }

      return {
        data: { content: 'Initial markdown' },
        error: null,
        isLoading: false,
      }
    })

    await harness.render(
      <MarkdownContentField
        baseName="about"
        contentSource="templates/content/about.md"
        onContentSourceChange={onContentSourceChange}
      />
    )

    expect(
      harness.container
        .querySelector('[data-testid="markdown-write"]')
        ?.getAttribute('data-content')
    ).toBe('Initial markdown')

    await harness.render(
      <MarkdownContentField
        baseName="about"
        contentSource="templates/content/terms.md"
        onContentSourceChange={onContentSourceChange}
      />
    )

    expect(harness.container.querySelector('[data-testid="markdown-write"]')).toBeNull()

    termsLoaded = true
    await harness.render(
      <MarkdownContentField
        baseName="about"
        contentSource="templates/content/terms.md"
        onContentSourceChange={onContentSourceChange}
      />
    )

    expect(
      harness.container
        .querySelector('[data-testid="markdown-write"]')
        ?.getAttribute('data-content')
    ).toBe('Terms markdown')

    await harness.unmount()
  })

  it('only enables save once the current single-file draft is dirty', async () => {
    const harness = createHarness()

    await harness.render(
      <MarkdownContentField
        baseName="about"
        contentSource="templates/content/about.md"
        onContentSourceChange={vi.fn()}
      />
    )

    const saveButton = Array.from(harness.container.querySelectorAll('button')).find(
      (button) => button.textContent?.includes('site:pageEditor.save')
    ) as HTMLButtonElement | undefined

    expect(saveButton?.disabled).toBe(true)

    await act(async () => {
      ;(harness.container.querySelector('[data-testid="markdown-change"]') as HTMLButtonElement).click()
    })

    expect(saveButton?.disabled).toBe(false)

    await act(async () => {
      saveButton?.click()
      await Promise.resolve()
    })

    expect(mutateAsync).toHaveBeenCalledWith({
      path: 'templates/content/about.md',
      content: 'Changed draft markdown',
    })
    expect(
      harness.container
        .querySelector('[data-testid="markdown-write"]')
        ?.getAttribute('data-content')
    ).toBe('Changed draft markdown')

    await harness.unmount()
  })

  it('shows guidance and source controls when no file is selected yet', async () => {
    const harness = createHarness()

    await harness.render(
      <MarkdownContentField
        baseName="about"
        contentSource={null}
        onContentSourceChange={vi.fn()}
        variant="authoring"
      />
    )

    expect(harness.container.textContent).toContain('site:pageEditor.noSourceSelected')
    expect(harness.container.textContent).toContain('site:pageEditor.manageContentSource')
    expect(harness.container.textContent).toContain('site:pageEditor.sourceFile')

    await harness.unmount()
  })

  it('keeps the default variant lighter than the authoring shell', async () => {
    const harness = createHarness()

    await harness.render(
      <MarkdownContentField
        baseName="about"
        contentSource="templates/content/about.md"
        onContentSourceChange={vi.fn()}
      />
    )

    const root = harness.container.querySelector('[data-markdown-field-variant="default"]')
    expect(root).not.toBeNull()
    expect((root as HTMLDivElement).className).not.toContain('shadow-sm')

    await harness.unmount()
  })

  it('keeps multilingual mode wired to the dedicated multilingual editor', async () => {
    const harness = createHarness()
    useLanguages.mockReturnValue({
      languages: ['fr', 'en'],
      defaultLang: 'fr',
    })

    await harness.render(
      <MarkdownContentField
        baseName="about"
        contentSource="templates/content/about"
        onContentSourceChange={vi.fn()}
      />
    )

    expect(harness.container.querySelector('[data-testid="multilingual-editor"]')).not.toBeNull()
    expect(harness.container.textContent).toContain('about.[lang].md')

    await harness.unmount()
  })
})
