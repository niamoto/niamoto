// @vitest-environment jsdom

import { act, type ReactElement } from 'react'
import { createRoot } from 'react-dom/client'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { StaticPageEditor } from './StaticPageEditor'

globalThis.IS_REACT_ACT_ENVIRONMENT = true

vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
    i18n: { language: 'fr', resolvedLanguage: 'fr' },
  }),
}))

vi.mock('sonner', () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
  },
}))

vi.mock('./TemplateSelect', () => ({
  TemplateSelect: () => <div data-testid="template-select">Template select</div>,
}))

vi.mock('@/components/ui/localized-input', () => ({
  LocalizedInput: (props: { label?: string }) => (
    <div data-testid="localized-input">{props.label || 'localized-input'}</div>
  ),
}))

vi.mock('@/shared/hooks/useSiteConfig', () => ({
  useTemplates: () => ({
    data: {
      templates: [
        { name: 'index.html' },
        { name: 'about.html' },
      ],
    },
    isLoading: false,
  }),
  ROOT_INDEX_OUTPUT_FILE: 'index.html',
  ROOT_INDEX_TEMPLATE: 'index.html',
  isRootIndexTemplate: (template?: string | null) => template === 'index.html',
}))

vi.mock('./forms', () => ({
  hasTemplateForm: (template: string) => template === 'index.html',
  MarkdownContentField: (props: { variant?: string }) => (
    <div data-testid={`markdown-field-${props.variant ?? 'default'}`}>Markdown field</div>
  ),
  IndexPageForm: () => <div data-testid="index-form">Index page form</div>,
  BibliographyForm: () => <div>Bibliography form</div>,
  TeamForm: () => <div>Team form</div>,
  ResourcesForm: () => <div>Resources form</div>,
  ContactForm: () => <div>Contact form</div>,
  GlossaryForm: () => <div>Glossary form</div>,
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

describe('StaticPageEditor', () => {
  afterEach(() => {
    document.body.innerHTML = ''
    vi.clearAllMocks()
  })

  it('puts markdown content first and keeps page settings collapsed for markdown-backed pages', async () => {
    const harness = createHarness()

    await harness.render(
      <StaticPageEditor
        page={{
          name: 'about',
          template: 'about.html',
          output_file: 'about.html',
          context: { content_source: 'templates/content/about.md' },
        }}
        onChange={vi.fn()}
        onBack={vi.fn()}
      />
    )

    const html = harness.container.innerHTML
    expect(html.indexOf('static-page-markdown-content')).toBeLessThan(
      html.indexOf('static-page-settings-toggle')
    )
    expect(harness.container.querySelector('[data-testid="markdown-field-authoring"]')).not.toBeNull()
    expect(harness.container.querySelector('#page-name')).toBeNull()

    await act(async () => {
      ;(harness.container.querySelector(
        '[data-testid="static-page-settings-toggle"]'
      ) as HTMLButtonElement).click()
    })

    expect(harness.container.querySelector('#page-name')).not.toBeNull()
    expect(harness.container.querySelector('[data-testid="localized-input"]')).not.toBeNull()

    await harness.unmount()
  })

  it('keeps dedicated template pages on the existing form path', async () => {
    const harness = createHarness()

    await harness.render(
      <StaticPageEditor
        page={{
          name: 'home',
          template: 'index.html',
          output_file: 'index.html',
          context: {},
        }}
        onChange={vi.fn()}
        onBack={vi.fn()}
      />
    )

    expect(harness.container.querySelector('#page-name')).not.toBeNull()
    expect(harness.container.querySelector('[data-testid="index-form"]')).not.toBeNull()
    expect(harness.container.querySelector('[data-testid="markdown-field-authoring"]')).toBeNull()

    await harness.unmount()
  })
})
