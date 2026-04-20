// @vitest-environment jsdom

import { act, type ReactNode } from 'react'
import { createRoot, type Root } from 'react-dom/client'
import { renderToStaticMarkup } from 'react-dom/server'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { SiteBuilder } from './SiteBuilder'

globalThis.IS_REACT_ACT_ENVIRONMENT = true

type SiteBuilderStateMock = ReturnType<typeof buildState>

interface MockWizardCompleteResult {
  tree: Array<unknown>
  pages: Array<{ name: string; template: string; output_file: string }>
  footerSections: Array<unknown>
  site: {
    title: string
    lang: string
    languages: string[]
    primary_color: string
    nav_color: string
  }
}

const stateRef: { value: SiteBuilderStateMock | null } = {
  value: null,
}

vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (_key: string, defaultValue?: string) => defaultValue ?? 'Site setup',
    i18n: { language: 'fr', resolvedLanguage: 'fr' },
  }),
}))

vi.mock('../hooks/useSiteBuilderState', () => ({
  useSiteBuilderState: () => stateRef.value,
}))

vi.mock('@/shared/hooks/useSiteConfig', () => ({
  useFileContent: () => ({ data: null }),
  useGroupIndexPreview: () => ({ mutate: vi.fn(), isPending: false }),
  getCanonicalStaticPageOutputFile: (page: { output_file?: string | null }) => page.output_file ?? 'index.html',
  isRootIndexTemplate: (template?: string | null) => template === 'index.html',
}))

vi.mock('./SiteSetupWizard', () => ({
  SiteSetupWizard: (props: { onComplete: (result: MockWizardCompleteResult) => void }) => (
    <div>
      <div>Site setup</div>
      <button
        type="button"
        data-testid="complete-setup"
        onClick={() => props.onComplete({
          tree: [],
          pages: [{ name: 'home', template: 'index.html', output_file: 'index.html' }],
          footerSections: [],
          site: {
            title: 'Niamoto',
            lang: 'fr',
            languages: ['fr'],
            primary_color: '#228b22',
            nav_color: '#ffffff',
          },
        })}
      >
        Complete setup
      </button>
    </div>
  ),
}))

vi.mock('./PagesOverview', () => ({
  PagesOverview: () => <div>Pages overview</div>,
}))

vi.mock('@/components/ui/resizable', () => ({
  ResizablePanelGroup: (props: { children: ReactNode }) => <div>{props.children}</div>,
  ResizablePanel: (props: { children: ReactNode }) => <div>{props.children}</div>,
  ResizableHandle: () => <div />,
}))

vi.mock('@/components/motion/PanelTransition', () => ({
  PanelTransition: (props: { children: ReactNode }) => <>{props.children}</>,
}))

vi.mock('./UnifiedSiteTree', () => ({
  UnifiedSiteTree: () => <div>Tree</div>,
}))

vi.mock('./SiteBuilderPreview', () => ({
  SitePreview: () => <div>Preview</div>,
  GroupIndexPreviewPanel: () => <div>Group preview</div>,
}))

function buildState(overrides: Record<string, unknown> = {}) {
  return {
    siteConfig: {
      site: { title: 'Niamoto', lang: 'fr', languages: ['fr'], primary_color: '#228b22', nav_color: '#ffffff' },
      navigation: [],
      footer_navigation: [],
      static_pages: [],
      template_dir: 'templates/',
      output_dir: 'exports/web',
      copy_assets_from: [],
    },
    isLoading: false,
    error: null,
    refetch: vi.fn(),
    groupsLoading: false,
    groups: [],
    availableNewPageTemplates: [],
    unifiedTree: [],
    setUnifiedTree: vi.fn(),
    allPages: [],
    setAllPages: vi.fn(),
    editedNavigation: [],
    editedPages: [],
    editedSite: { title: 'Niamoto', lang: 'fr', languages: ['fr'], primary_color: '#228b22', nav_color: '#ffffff' },
    setEditedSite: vi.fn(),
    editedFooterNavigation: [],
    setEditedFooterNavigation: vi.fn(),
    selection: null,
    setSelection: vi.fn(),
    pageToDelete: null,
    setPageToDelete: vi.fn(),
    hasChanges: false,
    hasExistingHomePage: false,
    isSaving: false,
    isEnablingIndexPage: false,
    handleSave: vi.fn(),
    saveConfig: vi.fn(),
    handleAddPage: vi.fn(),
    handleTemplateSelected: vi.fn(),
    handleCreatePageFromNavigation: vi.fn(),
    handleUpdatePage: vi.fn(),
    handleDeletePage: vi.fn(),
    confirmDeletePage: vi.fn(),
    handleDuplicatePage: vi.fn(),
    handleAddPageToNavigation: vi.fn(),
    handleEnableGroupIndexPage: vi.fn(),
    isPageInMenu: vi.fn(() => false),
    togglePageInMenu: vi.fn(),
    findMenuRefsForPage: vi.fn(() => []),
    findMenuRefsForCollection: vi.fn(() => []),
    updateMenuItemLabel: vi.fn(),
    removeMenuItem: vi.fn(),
    addPageToMenu: vi.fn(),
    addCollectionToMenu: vi.fn(),
    toggleItemVisibility: vi.fn(),
    addExternalLink: vi.fn(),
    removeExternalLink: vi.fn(),
    updateExternalLink: vi.fn(),
    ...overrides,
  }
}

function buildConfiguredSiteConfig() {
  return {
    site: { title: 'Niamoto', lang: 'fr', languages: ['fr'], primary_color: '#228b22', nav_color: '#ffffff' },
    navigation: [{ text: 'Home', url: '/index.html' }],
    footer_navigation: [],
    static_pages: [{ name: 'home', template: 'index.html', output_file: 'index.html' }],
    template_dir: 'templates/',
    output_dir: 'exports/web',
    copy_assets_from: [],
  }
}

afterEach(() => {
  document.body.innerHTML = ''
  stateRef.value = null
})

describe('SiteBuilder empty-state regressions', () => {
  it('renders Site Setup for an empty persisted config', () => {
    stateRef.value = buildState()
    const html = renderToStaticMarkup(<SiteBuilder />)
    expect(html).toContain('Site setup')
  })

  it('renders Site Setup again when the draft becomes empty after deleting home', () => {
    stateRef.value = buildState({
      siteConfig: {
        site: { title: 'Niamoto', lang: 'fr', languages: ['fr'], primary_color: '#228b22', nav_color: '#ffffff' },
        navigation: [{ text: 'Home', url: '/index.html' }],
        footer_navigation: [],
        static_pages: [{ name: 'home', template: 'index.html', output_file: 'index.html' }],
        template_dir: 'templates/',
        output_dir: 'exports/web',
        copy_assets_from: [],
      },
      editedNavigation: [],
      editedPages: [],
      hasChanges: true,
    })

    const html = renderToStaticMarkup(<SiteBuilder />)
    expect(html).toContain('Site setup')
  })

  it('renders the overview path for a genuinely configured root page', () => {
    stateRef.value = buildState({
      siteConfig: buildConfiguredSiteConfig(),
      editedNavigation: [{ text: 'Home', url: '/index.html' }],
      editedPages: [{ name: 'home', template: 'index.html', output_file: 'index.html' }],
    })

    const html = renderToStaticMarkup(<SiteBuilder />)
    expect(html).not.toContain('<div>Site setup</div>')
    expect(html).toContain('Pages overview')
  })

  it('reopens the wizard when the site becomes unconfigured again after dismissal', async () => {
    const container = document.createElement('div')
    document.body.appendChild(container)
    let root: Root | null = createRoot(container)

    stateRef.value = buildState()
    await act(async () => {
      root!.render(<SiteBuilder />)
    })
    expect(container.innerHTML).toContain('<div>Site setup</div>')

    const completeButton = container.querySelector('[data-testid="complete-setup"]')
    expect(completeButton).not.toBeNull()

    await act(async () => {
      ;(completeButton as HTMLButtonElement).click()
      await Promise.resolve()
      await Promise.resolve()
    })
    expect(container.innerHTML).not.toContain('<div>Site setup</div>')
    expect(container.innerHTML).toContain('Pages overview')

    stateRef.value = buildState({
      siteConfig: buildConfiguredSiteConfig(),
      editedNavigation: [{ text: 'Home', url: '/index.html' }],
      editedPages: [{ name: 'home', template: 'index.html', output_file: 'index.html' }],
    })
    await act(async () => {
      root!.render(<SiteBuilder />)
    })
    expect(container.innerHTML).not.toContain('<div>Site setup</div>')
    expect(container.innerHTML).toContain('Pages overview')

    stateRef.value = buildState({
      siteConfig: buildConfiguredSiteConfig(),
      editedNavigation: [],
      editedPages: [],
      hasChanges: true,
    })
    await act(async () => {
      root!.render(<SiteBuilder />)
    })
    expect(container.innerHTML).toContain('<div>Site setup</div>')

    await act(async () => {
      root?.unmount()
      root = null
    })
  })
})
