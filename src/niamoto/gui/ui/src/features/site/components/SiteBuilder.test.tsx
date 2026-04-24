// @vitest-environment jsdom

import { act, type ReactNode } from 'react'
import { createRoot, type Root } from 'react-dom/client'
import { renderToStaticMarkup } from 'react-dom/server'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { SiteBuilder } from './SiteBuilder'

globalThis.IS_REACT_ACT_ENVIRONMENT = true

type SiteBuilderStateMock = ReturnType<typeof buildState>
type SiteWorkbenchPreferencesMock = ReturnType<typeof buildWorkbenchPreferences>

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

const workbenchRef: { value: SiteWorkbenchPreferencesMock | null } = {
  value: null,
}

vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string, defaultValue?: string) => defaultValue ?? key,
    i18n: { language: 'fr', resolvedLanguage: 'fr' },
  }),
}))

vi.mock('../hooks/useSiteBuilderState', () => ({
  useSiteBuilderState: () => stateRef.value,
}))

vi.mock('../hooks/useSiteWorkbenchPreferences', () => ({
  useSiteWorkbenchPreferences: () => workbenchRef.value,
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

vi.mock('./SiteConfigForm', () => ({
  SiteConfigForm: () => <div>Site config form</div>,
}))

vi.mock('./ThemeConfigForm', () => ({
  ThemeConfigForm: () => <div>Theme config form</div>,
}))

vi.mock('./NavigationBuilder', () => ({
  NavigationBuilder: () => <div>Navigation builder</div>,
}))

vi.mock('./FooterSectionsEditor', () => ({
  FooterSectionsEditor: () => <div>Footer sections editor</div>,
}))

vi.mock('./StaticPageEditor', () => ({
  StaticPageEditor: (props: {
    showRestorePreview?: boolean
    onRestorePreview?: () => void
  }) => (
    <div>
      <div>Static page editor</div>
      {props.showRestorePreview && props.onRestorePreview ? (
        <button
          type="button"
          data-testid="inline-restore-preview"
          onClick={props.onRestorePreview}
        >
          preview.title
        </button>
      ) : null}
    </div>
  ),
}))

vi.mock('./TemplateList', () => ({
  TemplateList: () => <div>Template list</div>,
}))

vi.mock('./GroupPageViewer', () => ({
  GroupPageViewer: () => <div>Group page viewer</div>,
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
  SitePreview: (props: { onClose?: () => void }) => (
    <div>
      <div>Preview</div>
      {props.onClose ? (
        <button type="button" data-testid="close-preview" onClick={props.onClose}>
          Close preview
        </button>
      ) : null}
    </div>
  ),
  GroupIndexPreviewPanel: (props: { onClose?: () => void }) => (
    <div>
      <div>Group preview</div>
      {props.onClose ? (
        <button type="button" data-testid="close-group-preview" onClick={props.onClose}>
          Close group preview
        </button>
      ) : null}
    </div>
  ),
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

function buildWorkbenchPreferences(overrides: Record<string, unknown> = {}) {
  return {
    projectScope: 'desktop:/tmp/niamoto',
    previewState: 'unset',
    previewDevice: 'desktop',
    previewLayout: null,
    setPreviewState: vi.fn(),
    setPreviewDevice: vi.fn(),
    setPreviewLayout: vi.fn(),
    resetPreferences: vi.fn(),
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
  workbenchRef.value = null
})

describe('SiteBuilder empty-state regressions', () => {
  it('renders Site Setup for an empty persisted config', () => {
    stateRef.value = buildState()
    workbenchRef.value = buildWorkbenchPreferences()
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
    workbenchRef.value = buildWorkbenchPreferences()

    const html = renderToStaticMarkup(<SiteBuilder />)
    expect(html).toContain('Site setup')
  })

  it('renders the overview path for a genuinely configured root page', () => {
    stateRef.value = buildState({
      siteConfig: buildConfiguredSiteConfig(),
      editedNavigation: [{ text: 'Home', url: '/index.html' }],
      editedPages: [{ name: 'home', template: 'index.html', output_file: 'index.html' }],
    })
    workbenchRef.value = buildWorkbenchPreferences()

    const html = renderToStaticMarkup(<SiteBuilder />)
    expect(html).not.toContain('<div>Site setup</div>')
    expect(html).toContain('Pages overview')
  })

  it('reopens the wizard when the site becomes unconfigured again after dismissal', async () => {
    const container = document.createElement('div')
    document.body.appendChild(container)
    let root: Root | null = createRoot(container)

    stateRef.value = buildState()
    workbenchRef.value = buildWorkbenchPreferences()
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
    workbenchRef.value = buildWorkbenchPreferences()
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
    workbenchRef.value = buildWorkbenchPreferences()
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

describe('SiteBuilder workbench preview behavior', () => {
  it('auto-opens previewable pages when no explicit preference exists', () => {
    stateRef.value = buildState({
      siteConfig: buildConfiguredSiteConfig(),
      selection: { type: 'page', id: 'home' },
      editedNavigation: [{ text: 'Home', url: '/index.html' }],
      editedPages: [{ name: 'home', template: 'index.html', output_file: 'index.html' }],
    })
    workbenchRef.value = buildWorkbenchPreferences({
      previewState: 'unset',
    })

    const html = renderToStaticMarkup(<SiteBuilder />)
    expect(html).toContain('Preview')
  })

  it('auto-opens previewable groups when an index page is available', () => {
    stateRef.value = buildState({
      siteConfig: buildConfiguredSiteConfig(),
      selection: { type: 'group', id: 'taxons' },
      groups: [
        {
          name: 'taxons',
          index_generator: { enabled: true },
          index_output_pattern: 'taxons/index.html',
        },
      ],
    })
    workbenchRef.value = buildWorkbenchPreferences({
      previewState: 'unset',
    })

    const html = renderToStaticMarkup(<SiteBuilder />)
    expect(html).toContain('Group preview')
  })

  it('keeps the preview hidden when the stored preference is closed', () => {
    stateRef.value = buildState({
      siteConfig: buildConfiguredSiteConfig(),
      selection: { type: 'page', id: 'home' },
      editedNavigation: [{ text: 'Home', url: '/index.html' }],
      editedPages: [{ name: 'home', template: 'index.html', output_file: 'index.html' }],
    })
    workbenchRef.value = buildWorkbenchPreferences({
      previewState: 'closed',
    })

    const html = renderToStaticMarkup(<SiteBuilder />)
    expect(html).not.toContain('Preview')
    expect(html).toContain('preview.title')
  })

  it('hides preview surfaces entirely for non-previewable selections', () => {
    stateRef.value = buildState({
      siteConfig: buildConfiguredSiteConfig(),
      selection: { type: 'general' },
      editedNavigation: [{ text: 'Home', url: '/index.html' }],
      editedPages: [{ name: 'home', template: 'index.html', output_file: 'index.html' }],
    })
    workbenchRef.value = buildWorkbenchPreferences({
      previewState: 'open',
    })

    const html = renderToStaticMarkup(<SiteBuilder />)
    expect(html).not.toContain('Preview')
    expect(html).not.toContain('preview.title')
  })

  it('lets the preview close button persist an explicit closed preference', async () => {
    const container = document.createElement('div')
    document.body.appendChild(container)
    const root = createRoot(container)
    const setPreviewState = vi.fn()

    stateRef.value = buildState({
      siteConfig: buildConfiguredSiteConfig(),
      selection: { type: 'page', id: 'home' },
      editedNavigation: [{ text: 'Home', url: '/index.html' }],
      editedPages: [{ name: 'home', template: 'index.html', output_file: 'index.html' }],
    })
    workbenchRef.value = buildWorkbenchPreferences({
      previewState: 'open',
      setPreviewState,
    })

    await act(async () => {
      root.render(<SiteBuilder />)
    })

    const closeButton = container.querySelector('[data-testid="close-preview"]')
    expect(closeButton).not.toBeNull()

    await act(async () => {
      ;(closeButton as HTMLButtonElement).click()
    })

    expect(setPreviewState).toHaveBeenCalledWith('closed')

    await act(async () => {
      root.unmount()
    })
  })

  it('offers a local restore button when preview is explicitly closed', async () => {
    const container = document.createElement('div')
    document.body.appendChild(container)
    const root = createRoot(container)
    const setPreviewState = vi.fn()

    stateRef.value = buildState({
      siteConfig: buildConfiguredSiteConfig(),
      selection: { type: 'page', id: 'home' },
      editedNavigation: [{ text: 'Home', url: '/index.html' }],
      editedPages: [{ name: 'home', template: 'index.html', output_file: 'index.html' }],
    })
    workbenchRef.value = buildWorkbenchPreferences({
      previewState: 'closed',
      setPreviewState,
    })

    await act(async () => {
      root.render(<SiteBuilder />)
    })

    const restoreBar = container.querySelector('[data-testid="preview-restore-bar"]')
    expect(restoreBar).toBeNull()

    const restoreButton = container.querySelector('[data-testid="inline-restore-preview"]')
    expect(restoreButton).not.toBeNull()

    await act(async () => {
      ;(restoreButton as HTMLButtonElement).click()
    })

    expect(setPreviewState).toHaveBeenCalledWith('open')

    await act(async () => {
      root.unmount()
    })
  })

  it('offers a header restore button for closed collection previews', async () => {
    const container = document.createElement('div')
    document.body.appendChild(container)
    const root = createRoot(container)
    const setPreviewState = vi.fn()

    stateRef.value = buildState({
      siteConfig: buildConfiguredSiteConfig(),
      selection: { type: 'group', id: 'taxons' },
      groups: [
        {
          name: 'taxons',
          index_generator: { enabled: true },
          index_output_pattern: 'taxons/index.html',
        },
      ],
    })
    workbenchRef.value = buildWorkbenchPreferences({
      previewState: 'closed',
      setPreviewState,
    })

    await act(async () => {
      root.render(<SiteBuilder />)
    })

    expect(container.innerHTML).toContain('Group page viewer')
    expect(container.innerHTML).not.toContain('Group preview')

    const restoreButton = container.querySelector('[data-testid="preview-restore-bar"]')
    expect(restoreButton).not.toBeNull()

    await act(async () => {
      ;(restoreButton as HTMLButtonElement).click()
    })

    expect(setPreviewState).toHaveBeenCalledWith('open')

    await act(async () => {
      root.unmount()
    })
  })
})
